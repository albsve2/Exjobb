import torch
import cv2
import numpy as np
import pathlib
import warnings
import os

# ── Tysta amp.autocast‑varningar ───────────────────────────────────────────────
warnings.filterwarnings(
    "ignore",
    message="`torch.cuda.amp.autocast\\(args...\\)` is deprecated.*",
    category=FutureWarning
)

# ── Patch Windows pathlib ───────────────────────────────────────────────────────
if os.name == 'nt':
    pathlib.PosixPath = pathlib.WindowsPath

# ── Ladda YOLOv5 på GPU ───────────────────────────────────────────────────────
model = torch.hub.load(
    "./", "custom",
    path="runs/train/exp6/weights/best.pt",
    source="local", force_reload=True
)
model.conf = 0.3
model.iou  = 0.4
model = model.to("cuda")

# ── Kamera ────────────────────────────────────────────────────────────────────
cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH , 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)
cap.set(cv2.CAP_PROP_FPS         , 30)
if not cap.isOpened():
    raise RuntimeError("Kunde inte öppna kameran.")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # --- tryck ut till exakt 640×640 ---
        frame = cv2.resize(frame, (640, 640))

        # --- inferens på GPU ---
        with torch.amp.autocast(device_type="cuda"):
            results = model(frame)

        # --- ta renderad bild och se till att den är 640×640 ---
        annotated = results.render()[0]
        annotated = cv2.resize(annotated, (640, 640))

        # --- loop över detektioner ---
        for det in results.pred[0]:
            x1, y1, x2, y2, conf, cls = det.cpu().numpy()
            if conf < 0.5:
                continue

            # mitten i pixlar
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            # skriv ut i terminal
            print(f"Batteri klass={int(cls)}, conf={conf:.2f}")
            print(f"  Pixel (cx,cy)=({cx},{cy})\n")

            # markera på bilden
            cv2.circle(annotated, (cx, cy), 8, (0,255,0), -1)
            cv2.putText(annotated,
                        f"({cx},{cy})",
                        (cx + 10, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)

        cv2.imshow("Detektion", annotated)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
