# Färdigt TESTPROGRAM för kamera och robotkalibrering

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

# --- Ladda modell ---
model = torch.hub.load('./', 'custom', path='runs/train/exp6/weights/best.pt', source='local', force_reload=True)
model.conf = 0.5

# --- Kamera ---
cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)
cap.set(cv2.CAP_PROP_FPS, 30)

if not cap.isOpened():
    print("Kunde inte öppna kameran.")
    exit()

# --- Robotparametrar ---
Z_APPROACH_HEIGHT = 0.25
Z_PICK_HEIGHT = 0.15
RX, RY, RZ = 3.14, 0, 0.7
PIXELS_PER_METER = 640 / 0.6  # Anpassa om din kamera är monterad annorlunda

def pixel_to_meter(cx, cy):
    x_meters = (cx - 320) / PIXELS_PER_METER
    y_meters = -(cy - 320) / PIXELS_PER_METER
    return x_meters, y_meters

print("\nPlacera ett batteri i mitten av bilden och tryck på valfri tangent...")
input()

ret, frame = cap.read()
if not ret:
    print("Kunde inte läsa bild.")
    exit()

results = model(frame)
annotated_frame = results.render()[0]

found = False

for detection in results.pred[0]:
    x1, y1, x2, y2, conf, cls = detection.cpu().numpy()
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)

    if conf < 0.6:
        continue

    x_meters, y_meters = pixel_to_meter(cx, cy)

    print(f"\nDetekterat batteri på pixel ({cx}, {cy})")
    print(f"Beräknad position (meter): X={x_meters:.3f}, Y={y_meters:.3f}")

    # 1. Flytta ovanför batteriet
    move_above = f"movel(p[{x_meters:.3f}, {y_meters:.3f}, {Z_APPROACH_HEIGHT:.3f}, {RX:.2f}, {RY:.2f}, {RZ:.2f}], a=0.5, v=0.3)"
    send_urscript(move_above)
    time.sleep(2.0)

    # 2. Gå ner till plockhöjd
    move_down = f"movel(p[{x_meters:.3f}, {y_meters:.3f}, {Z_PICK_HEIGHT:.3f}, {RX:.2f}, {RY:.2f}, {RZ:.2f}], a=0.2, v=0.1)"
    send_urscript(move_down)
    time.sleep(2.0)

    # 3. Gå tillbaka till säker höjd
    send_urscript(move_above)
    time.sleep(2.0)

    found = True
    break

if not found:
    print("\nInget batteri hittades i mitten!")

cv2.imshow("Kamerabild", annotated_frame)
print("\nTryck valfri tangent för att avsluta...")
cv2.waitKey(0)

cap.release()
cv2.destroyAllWindows()
