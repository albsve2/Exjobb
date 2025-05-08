import warnings
import torch #För att köra min yolo modell
import cv2 #allt med kameran
import numpy as np #Numeriska metoder
import socket # kommunikation över nätverk med ip
import time #pauser mellan kommandon
import os
import pathlib #hantera filvägar
import threading #parallellisering
import queue #kommunikation mellan trådar

CLASS_NAMES = {0: "small", 1: "medium"}

# Quiet torch warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Robot communication
robotIP, PORT = "130.130.130.86", 30001 #robotens ip och port nr

def send_urscript(cmd: str, timeout=1.0):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((robotIP, PORT))
        s.sendall((cmd + "\n").encode())
        s.close()
        print(">>>", cmd)
        return True
    except Exception as e:
        print("!!! could not send:", cmd, e)
        return False

# Patch for Windows
if os.name == 'nt':
    pathlib.PosixPath = pathlib.WindowsPath

# Load affine matrix from file
affine_matrix = np.loadtxt("affine_matrix.txt", dtype=np.float32)

# Manuell justering av plockposition (i mm)
manual_offset = np.array([7.0, -5.0])  # t.ex. np.array([5.0, -3.0])

# Load YOLOv5 model
model = torch.hub.load(
    "./", "custom",
    path="runs/train/exp6/weights/best.pt",
    source="local", force_reload=True
)
model.conf = 0.6
model = model.to("cuda")

# Robot positions
RX, RY, RZ = 3.186, -0.124, 0.106
HOME = "movel(p[0.34677,-0.13007,0.12600,3.186,-0.124,0], a=1.2, v=0.3)"
SMALL_DROP = "movel(p[0.30145,-0.15804,0.23,2.592,-1.979,0], a=1.2, v=0.3)"
MEDIUM_DROP = "movel(p[0.22736,-0.11185,0.23,2.592,-1.979,0], a=1.2, v=0.3)"

busy = False
frame_queue = queue.Queue(maxsize=1)
display_queue = queue.Queue(maxsize=1)

# Robot sequence thread
def robot_task(cx, cy, cls):
    global busy
    busy = True

    input_pt = np.array([[[cx, cy]]], dtype=np.float32)
    transformed = cv2.transform(input_pt, affine_matrix)
    x_mm, y_mm = transformed[0][0] + manual_offset
    x_m = x_mm / 1000
    y_m = y_mm / 1000

    if int(cls) == 1:
        z_pick = 0.070 + 0.012
        z_approach = 0.080 + 0.012
    else:
        z_pick = 0.070
        z_approach = 0.080

    print(f"\n Kör robotsekvens till x={x_mm:.1f}, y={y_mm:.1f}, klass={int(cls)}")

    sequence = [
        (f"movel(p[{x_m:.5f},{y_m:.5f},0.12,{RX},{RY},{RZ}], a=2.5, v=2.0)", 1.0),
        (f"movel(p[{x_m:.5f},{y_m:.5f},{z_approach:.5f},{RX},{RY},{RZ}], a=0.2, v=0.2)", 1.2),
        (f"movel(p[{x_m:.5f},{y_m:.5f},{z_pick:.5f},    {RX},{RY},{RZ}], a=0.1, v=0.05)", 1.5),
        ("set_digital_out(1, True)", 0.5),
        (f"movel(p[{x_m:.5f},{y_m:.5f},{z_approach:.5f},{RX},{RY},{RZ}], a=0.5, v=2.0)", 1.2),
        (SMALL_DROP if cls == 0 else MEDIUM_DROP, 2.0),
        ("set_digital_out(1, False)", 0.3),
        (HOME, 2.0),
        ("set_analog_out(0, 0.04)", 0.3),
    ]

    for cmd, pause in sequence:
        send_urscript(cmd)
        time.sleep(pause)

    print("Sekvens klar. Väntar innan ny detektion.")
    time.sleep(1.5)

    while not frame_queue.empty():
        frame_queue.get()

    busy = False

# Inference thread
def detect_thread():
    global busy
    while True:
        if not frame_queue.empty() and not busy:
            frame = frame_queue.get()
            display = frame.copy()

            with torch.amp.autocast(device_type="cuda"):
                results = model(frame)

            if len(results.pred[0]) > 0:
                for det in results.pred[0]:
                    x1, y1, x2, y2, conf, cls = det.cpu().numpy()
                    if conf < 0.6:
                        continue

                    cx = int((x1 + x2) / 2)
                    cy = int((y1 + y2) / 2)

                    label = CLASS_NAMES.get(int(cls), f"class {int(cls)}")

                    cv2.rectangle(display, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
                    cv2.putText(display, f"{label} ({conf:.2f})", (int(x1), int(y1) - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

                    if 170 <= cx <= 400 and 5 <= cy <= 350:
                        print(f"🟢 {label} batteri vid ({cx},{cy}) – stoppar band direkt.")
                        send_urscript("set_analog_out(0, 0.0)")
                        threading.Thread(target=robot_task, args=(cx, cy, cls), daemon=True).start()
                        break

            if not display_queue.full():
                display_queue.put(display)

# Start detection thread
threading.Thread(target=detect_thread, daemon=True).start()

# Main loop
try:
    send_urscript(HOME)
    time.sleep(2.5)
    send_urscript("set_analog_out(0, 0.04)")
    print(" System ready.")

    cap = cv2.VideoCapture(1)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)
    cap.set(cv2.CAP_PROP_FPS, 30)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        if not frame_queue.full():
            frame_queue.put(frame.copy())

        if not display_queue.empty():
            shown = display_queue.get()
        else:
            shown = frame

        cv2.rectangle(shown, (170, 5), (400, 350), (0, 255, 0), 2)
        cv2.putText(shown, "Detection Area", (225, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        cv2.imshow("Detect", shown)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    send_urscript("set_analog_out(0, 0.0)")
    send_urscript("set_digital_out(1, False)")
    cap.release()
    cv2.destroyAllWindows()
    print(" Program avslutat.")
