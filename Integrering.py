import torch
import cv2
import numpy as np
import os
import pathlib
import urx  # Lägg till URX-importen
import time

# Patch för att konvertera PosixPath till WindowsPath vid behov
if os.name == 'nt':
    pathlib.PosixPath = pathlib.WindowsPath

# Anslut till UR-roboten (ange rätt IP-adress)
robot_ip = "10.0.2.15"  # Ändra till din robots adress
robot = urx.Robot(robot_ip)

# Ladda YOLOv5-modellen från den lokala mappen
model = torch.hub.load('./', 'custom', path='runs/train/exp6/weights/best.pt', source='local', force_reload=True)

# Justera modellparametrar
model.conf = 0.84   # Högre konfidenströskel för att minska falska positiva
model.iou = 0.6     # Minska IOU för att fånga överlappande objekt bättre
model.max_det = 5   # Öka max antal detektioner per bild

# Starta kameran
cap = cv2.VideoCapture(2)
cap.set(cv2.CAP_PROP_FPS, 60)
cap.set(cv2.CAP_PROP_AUTO_WB, 1)
cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)
cap.set(cv2.CAP_PROP_SATURATION, 100)
cap.set(cv2.CAP_PROP_CONTRAST, 40)
cap.set(cv2.CAP_PROP_BRIGHTNESS, 150)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)

if not cap.isOpened():
    print("Kunde inte öppna kameran.")
    exit()

# Funktion för att transformera bildkoordinater till robotkoordinater
def transform_to_robot_coords(cx, cy, img_shape):
    """
    Denna funktion tar in mitten av bounding boxen (cx, cy) samt bildens dimensioner.
    Här utförs en enkel transformation (skalning och offset) som exempel.
    Du bör ersätta dessa värden med din faktiska kalibreringsdata.
    """
    img_h, img_w = img_shape[:2]
    # Exempel på skalning och offset – justera efter din robots arbetsområde!
    # T.ex. kan du tänka dig att pixlar -> meter med en linjär transformation
    robot_x = 0.3 + (cx / img_w) * 0.2  # Omvandling från pixel till meter (exempelvärde)
    robot_y = 0.3 + (cy / img_h) * 0.2  # Samma här
    robot_z = 0.2  # Fastsatt höjd, exempelvis från en separat mätning

    # Returnera målposition i robotens koordinatsystem med en enkel rotationsvektor (exempel)
    return [robot_x, robot_y, robot_z, 0, 3.14, 0]

while True:
    ret, frame = cap.read()
    if not ret:
        print("Kunde inte läsa från kameran.")
        break

    # Om videon är svartvit, konvertera till RGB
    if len(frame.shape) == 2 or frame.shape[2] == 1:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)

    # Förbättra kontrast med adaptiv histogramutjämning (CLAHE)
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge((l, a, b))
    frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # Öka skärpan med skärpefilter
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    frame = cv2.filter2D(frame, -1, kernel)

    # Förbättra färgintensitet med HSV-mättnad
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hsv[:, :, 1] = cv2.add(hsv[:, :, 1], 50)
    frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    # Brusreducering med Gaussisk suddning
    frame = cv2.GaussianBlur(frame, (5, 5), 0)

    # Kör inferens med YOLOv5
    results = model(frame)

    # Filtrera resultat baserat på konfidens
    detections = results.pandas().xyxy[0]
    filtered_results = detections[detections['confidence'] > 0.7]

    # Dynamiskt justera konfidenströskeln
    if len(filtered_results) < 3:
        model.conf = 0.6  # Minska konfidenströskeln om få detekteringar
    else:
        model.conf = 0.7  # Annars öka den

    # Hämta FPS från kameran
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # Rendera annoterad bild
    annotated_frame = results.render()[0].copy()

    for detection in results.pred[0]:
        # Extrahera bounding box och konfidens
        x1, y1, x2, y2, conf, cls = detection.cpu().numpy()
        cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)

        # Skriv ut koordinaterna i terminalen
        print(f"Battery detected at: ({cx}, {cy}) - Confidence: {conf:.2f}")

        # Rita en cirkel på detekterat centrum
        cv2.circle(annotated_frame, (cx, cy), 10, (255, 0, 255), -1)
        cv2.putText(annotated_frame, f'({cx}, {cy})', (cx + 15, cy - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)

        # Transformera bildkoordinaterna till robotens koordinatsystem
        target_pose = transform_to_robot_coords(cx, cy, frame.shape)
        print("Transformerad målposition:", target_pose)

        # Skicka rörelsekommandot till roboten
        try:
            robot.movel(target_pose, acc=0.5, vel=0.25)
        except Exception as e:
            print("Kunde inte skicka kommando till roboten:", e)

    # Visa FPS och modellens konfidensnivå på bilden
    cv2.putText(annotated_frame, f'FPS: {fps}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (0, 255, 0), 1)
    cv2.putText(annotated_frame, f'Conf: {model.conf}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (0, 255, 0), 1)

    # Visa bilden med detekterade batterier
    cv2.imshow("Batteridetektion", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# Stäng robotanslutningen vid programmets slut
robot.close()
