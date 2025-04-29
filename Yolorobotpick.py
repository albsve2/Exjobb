import torch
import cv2
import numpy as np
import socket
import time
import os
import pathlib

# --- Robotkommunikation ---
robotIP = "130.130.130.86"
PORT = 30001

def send_urscript(command: str):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((robotIP, PORT))
        s.sendall((command + "\n").encode('utf-8'))
        s.close()
        print(f"Sent to robot: {command}")
    except Exception as e:
        print("Error sending to robot:", e)

if os.name == 'nt':
    pathlib.PosixPath = pathlib.WindowsPath

# --- Ladda YOLOv5-modellen ---
model = torch.hub.load('./', 'custom', path='runs/train/exp6/weights/best.pt', source='local', force_reload=True)
model.conf = 0.5

# --- Starta kamera ---
cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)
cap.set(cv2.CAP_PROP_FPS, 30)

if not cap.isOpened():
    print("Kunde inte öppna kameran.")
    exit()

# --- Robotens fasta parametrar ---
Z_PICK_HEIGHT = 0.15  # Plockhöjd (meter)
Z_APPROACH_HEIGHT = 0.25  # Säker höjd över bandet
RX, RY, RZ = 3.14, 0, 0.7  # Robotens vinkel (sned plock)
PIXELS_PER_METER = 640 / 0.6  # Om 640 pixlar = 60 cm

# --- Drop-off position ---
DROP_OFF_X = 0.3   # Meter från robotens nollpunkt (justera!)
DROP_OFF_Y = 0.0
DROP_OFF_Z = 0.25  # Höjd vid släppning

while True:
    ret, frame = cap.read()
    if not ret:
        print("Kunde inte läsa bild.")
        break

    frame = cv2.GaussianBlur(frame, (5, 5), 0)
    results = model(frame)
    annotated_frame = results.render()[0]

    for detection in results.pred[0]:
        x1, y1, x2, y2, conf, cls = detection.cpu().numpy()
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)

        if conf < 0.6:
            continue

        print(f"Batteri hittat på ({cx}, {cy}) med confidence {conf:.2f}")

        x_meters = (cx - 320) / PIXELS_PER_METER
        y_meters = -(cy - 320) / PIXELS_PER_METER

        # --- 1. Flytta ovanför batteriet ---
        move_above = f"movel(p[{x_meters:.3f}, {y_meters:.3f}, {Z_APPROACH_HEIGHT:.3f}, {RX:.2f}, {RY:.2f}, {RZ:.2f}], a=0.5, v=0.3)"
        send_urscript(move_above)
        time.sleep(1.0)

        # --- 2. Gå ner och plocka ---
        move_down = f"movel(p[{x_meters:.3f}, {y_meters:.3f}, {Z_PICK_HEIGHT:.3f}, {RX:.2f}, {RY:.2f}, {RZ:.2f}], a=0.2, v=0.1)"
        send_urscript(move_down)
        time.sleep(1.0)

        # --- 3. Aktivera sugkopp ---
        send_urscript("set_digital_out(1, True)")
        time.sleep(0.5)

        # --- 4. Gå upp igen ---
        send_urscript(move_above)
        time.sleep(1.0)

        # --- 5. Flytta till drop-off position ---
        move_dropoff = f"movel(p[{DROP_OFF_X:.3f}, {DROP_OFF_Y:.3f}, {DROP_OFF_Z:.3f}, {RX:.2f}, {RY:.2f}, {RZ:.2f}], a=0.5, v=0.3)"
        send_urscript(move_dropoff)
        time.sleep(1.0)

        # --- 6. Stäng av sugkopp för att släppa ---
        send_urscript("set_digital_out(1, False)")
        time.sleep(0.5)

        # --- 7. Gå tillbaka till säker startposition ---
        send_urscript(f"movel(p[{DROP_OFF_X:.3f}, {DROP_OFF_Y:.3f}, {Z_APPROACH_HEIGHT:.3f}, {RX:.2f}, {RY:.2f}, {RZ:.2f}], a=0.5, v=0.3)")
        time.sleep(1.0)

        break  # Bara en plock per körning

    cv2.imshow("YOLO Robot Detection", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
