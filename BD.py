import torch
import cv2
import numpy as np
import os
import pathlib
import csv
from datetime import datetime
from collections import defaultdict


# Definiera linjens x-position (mitten av bilden)
line_x = 208
line_threshold = 50  # tillåten zon för linjekorsning (i pixlar)
track_memory = defaultdict(list)
total_detected = 0
object_id_counter = 0

# Öppna CSV-fil för loggning
csv_file = open("batterilogg.csv", mode="w", newline="")
csv_writer = csv.writer(csv_file)
csv_writer.writerow(["Tid", "Batteri-ID", "Totalt räknade"])

# Patch för att konvertera PosixPath till WindowsPath vid behov
if os.name == 'nt':
    pathlib.PosixPath = pathlib.WindowsPath

# Ladda YOLOv5-modellen
model = torch.hub.load('./', 'custom', path='runs/train/exp6/weights/best.pt', source='local', force_reload=True)
model.conf = 0.3
model.iou = 0.4


# Starta kameran
cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FPS, 60)
cap.set(cv2.CAP_PROP_AUTO_WB, 0)
cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)
cap.set(cv2.CAP_PROP_SATURATION, 70)
cap.set(cv2.CAP_PROP_CONTRAST, 30)
cap.set(cv2.CAP_PROP_BRIGHTNESS, 120)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)

if not cap.isOpened():
    print("Kunde inte öppna kameran.")
    exit()

# Glidande medelvärden för stabilisering
prev_positions = {}  # {id: (cx, cy)}
alpha = 0.7  # 0.1 = mycket stabilt, 0.9 = snabbt reagerande

#hoppa över varannan frame
frame_count = 0


while True:
    ret, frame = cap.read()
    if not ret:
        print("Kunde inte läsa från kameran.")
        break

    if len(frame.shape) == 2 or frame.shape[2] == 1:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)

    frame_count += 1
    if frame_count % 2 != 0:
        continue  # Hoppar över varannan frame


    # Förbehandling
    #lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    #l, a, b = cv2.split(lab)
    #clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    #l = clahe.apply(l)
    #lab = cv2.merge((l, a, b))
    #frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    frame = cv2.filter2D(frame, -1, kernel)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hsv[:, :, 1] = cv2.add(hsv[:, :, 1], 50)
    frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    frame = cv2.GaussianBlur(frame, (3, 3), 0)
    # Definiera ROI (justera efter din transportbandsposition)
    roi_x1, roi_y1 = 0, 0
    roi_x2, roi_y2 = 640, 640

    # Beskär och skala upp för modellen
    roi = frame[roi_y1:roi_y2, roi_x1:roi_x2]
    roi_resized = cv2.resize(roi, (416, 416))
    results = model(roi_resized)

    #results = model(frame)
    detections = results.pandas().xyxy[0]
    filtered_results = detections[detections['confidence'] > 0.5]

    if len(filtered_results) < 3:
        model.conf = 0.5
    else:
        model.conf = 0.5

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    annotated_frame = results.render()[0].copy()

    # Rita ROI-rektangel på originalbilden
    cv2.rectangle(annotated_frame, (roi_x1, roi_y1), (roi_x2, roi_y2), (0, 255, 255), 2)

    current_objects = []
    for detection in results.pred[0]:
        x1, y1, x2, y2, conf, cls = detection.cpu().numpy()
        cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
        current_objects.append((cx, cy))

    for cx, cy in current_objects:
        matched_id = None
        for obj_id, positions in track_memory.items():
            if len(positions) > 0 and abs(positions[-1][0] - cx) < 50 and abs(positions[-1][1] - cy) < 50:
                matched_id = obj_id
                break

        if matched_id is None:
            matched_id = object_id_counter
            object_id_counter += 1

        track_memory[matched_id].append((cx, cy))

        if len(track_memory[matched_id]) >= 2:
            x_prev = track_memory[matched_id][-2][0]
            x_curr = track_memory[matched_id][-1][0]

            if x_prev > line_x and x_curr <= line_x:
                total_detected += 1
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                csv_writer.writerow([timestamp, matched_id, total_detected])
                track_memory[matched_id] = []

        # Lagra fler tidigare punkter (lista med max 5)
        if not isinstance(prev_positions.get(matched_id), list):
            prev_positions[matched_id] = []

        prev_positions[matched_id].append((cx, cy))
        if len(prev_positions[matched_id]) > 10:
            prev_positions[matched_id].pop(0)

        # Räkna ut medelvärde av senaste 5 positioner
        smooth_cx = int(np.mean([p[0] for p in prev_positions[matched_id]]))
        smooth_cy = int(np.mean([p[1] for p in prev_positions[matched_id]]))

        # Spara nya positionen
        prev_positions[matched_id] = (smooth_cx, smooth_cy)

        # Rita smidigare cirkel och ID
        cv2.circle(annotated_frame, (smooth_cx, smooth_cy), 8, (0, 255, 255), -1)
        cv2.putText(annotated_frame, f'ID {matched_id}', (smooth_cx + 10, smooth_cy), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                    (0, 255, 0), 1)

    # Rita linje och räkne-info
    cv2.line(annotated_frame, (line_x, 0), (line_x, 640), (255, 0, 0), 2)
    cv2.putText(annotated_frame, f'Total: {total_detected}', (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    cv2.putText(annotated_frame, f'FPS: {fps}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    cv2.putText(annotated_frame, f'Conf: {model.conf}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    # Visa koordinater med lila cirkel också
    for detection in results.pred[0]:
        x1, y1, x2, y2, conf, cls = detection.cpu().numpy()
        cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
        #print(f"Battery detected at: ({cx}, {cy}) - Confidence: {conf:.2f}")
        cv2.circle(annotated_frame, (cx, cy), 10, (255, 0, 255), -1)
        cv2.putText(annotated_frame, f'({cx}, {cy})', (cx + 15, cy - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)

    cv2.imshow("Batteridetektion", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
csv_file.close()
cv2.destroyAllWindows()
