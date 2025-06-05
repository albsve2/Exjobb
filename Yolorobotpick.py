import warnings
import torch  # För att köra min yolo modell
import cv2    # Allt med kameran
import numpy as np  # Numeriska metoder
import socket  # Kommunikation över nätverk med ip
import time    # Pauser mellan kommandon
import os
import pathlib  # Hantera filvägar
import threading  # Parallellisering
import queue      # Kommunikation mellan trådar

#ncpa.cpl ipconfig

CLASS_NAMES = {0: "small", 1: "medium"}

# Quiet torch warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# ── Robot communication ─────────────────────────────────────────────────────────
robotIP, PORT = "130.130.130.86", 30001

# Persistent socket
robot_sock = None

def init_robot_socket(timeout=1.0):
    global robot_sock
    if robot_sock is None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((robotIP, PORT))
        robot_sock = s
        print(f">>> Persistent socket connected to {robotIP}:{PORT}")
    return robot_sock

def send_urscript(cmd: str):
    """Skicka URScript över persistent socket."""
    global robot_sock
    try:
        s = init_robot_socket()
        s.sendall((cmd + "\n").encode())
        print(">>>", cmd)
        return True
    except Exception as e:
        print("!!! send_urscript failed:", e)
        # Försök återansluta en gång
        try:
            if robot_sock:
                robot_sock.close()
        except:
            pass
        robot_sock = None
        try:
            s = init_robot_socket()
            s.sendall((cmd + "\n").encode())
            print(">>>", cmd)
            return True
        except Exception as e2:
            print("!!! reconnect failed:", e2)
            return False

# ── Patch för Windows pathlib ───────────────────────────────────────────────────
if os.name == 'nt':
    pathlib.PosixPath = pathlib.WindowsPath

# ── Ladda affine-matris & offset ────────────────────────────────────────────────
affine_matrix = np.loadtxt("affine_matrix.txt", dtype=np.float32)
# Efter (lägger till kompensation för +13.14 mm i x och -14.43 mm i y):
manual_offset = np.array([-16.34,  11.86])  # nytt, kalibrerat offset i mm


# ── Ladda YOLOv5-modellen ───────────────────────────────────────────────────────
model = torch.hub.load(
    "./", "custom",
    path="runs/train/exp6/weights/best.pt",
    source="local", force_reload=True
)
model.conf = 0.6
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device).eval()

# ── Robot-positioner ─────────────────────────────────────────────────────────────
RX, RY, RZ = 3.186, -0.124, 0.106
HOME        = "movel(p[0.32199,-0.11007,0.12600,3.186,-0.124,0], a=1.2, v=2.0)"
SMALL_DROP  = "movel(p[0.30145,-0.15804,0.23,2.592,-1.979,0], a=1.2, v=1.3)"
MEDIUM_DROP = "movel(p[0.22736,-0.11185,0.23,2.592,-1.979,0], a=1.2, v=1.3)"

# ── Synkronisering och köer ───────────────────────────────────────────────────────
busy = False
frame_queue   = queue.Queue(maxsize=1)  # bilder för inferens
display_queue = queue.Queue(maxsize=1)  # bilder med ritade boxar

# ── Robot-task: skicka hela sekvensen i ett URScript-block ───────────────────────
def robot_task(cx, cy, cls):
    global busy
    busy = True

    # Transformera pixelkoordinater → robotkoordinater
    inp_pt = np.array([[[cx, cy]]], dtype=np.float32)
    tr     = cv2.transform(inp_pt, affine_matrix)[0][0]
    x_mm, y_mm = tr + manual_offset

    # Add compensation for conveyor movement
    # You'll need to adjust these values based on your conveyor speed
    conveyor_compensation = 1  # Adjust this value (in meters)
    y_mm += conveyor_compensation

    x_m, y_m = x_mm/1000, y_mm/1000

    # Z-offset beroende på klass
    if cls == 1:
        z_pick     = 0.070 + 0.010
        z_approach = 0.080 + 0.010
    else:
        z_pick     = 0.070
        z_approach = 0.080

    # Bygg URScript-block with increased speed for catching moving objects
    drop_cmd = SMALL_DROP if cls == 0 else MEDIUM_DROP
    script = f"""
def pick():
  movel(p[{x_m:.5f},{y_m:.5f},0.12,{RX},{RY},{RZ}], a=3.0, v=3.0)  # Increased speed
  movel(p[{x_m:.5f},{y_m:.5f},{z_approach:.5f},{RX},{RY},{RZ}], a=2.0, v=2.0)  # Faster approach
  movel(p[{x_m:.5f},{y_m:.5f},{z_pick:.5f},{RX},{RY},{RZ}], a=1.0, v=1.0)  # Faster pick
  set_digital_out(1, True)
  sleep(0.2)
  movel(p[{x_m:.5f},{y_m:.5f},{z_approach:.5f},{RX},{RY},{RZ}], a=2.0, v=2.0)
  {drop_cmd}
  set_digital_out(1, False)
  {HOME}
end
pick()
"""
    # Skicka allt i ett svep
    send_urscript(script)

    # Reduce wait time if possible
    time.sleep(5.5)


    # Rensa inferens-kön
    while not frame_queue.empty():
        frame_queue.get()
    busy = False


# ── Detekterings-tråd ───────────────────────────────────────────────────────────
def detect_thread():
    global busy
    while True:
        if not frame_queue.empty() and not busy:
            frame = frame_queue.get()
            display = frame.copy()

            # Gör om BGR → RGB
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Kör inferens (YOLOv5-hub förväntar sig RGB numpy-array)
            results = model(img)

            # results.pred[0] är tensor [N,6] med (x1,y1,x2,y2,conf,cls)
            preds = results.pred[0].cpu().numpy()

            for x1, y1, x2, y2, conf, cls in preds:
                if conf < model.conf:
                    continue

                x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                label = CLASS_NAMES.get(int(cls), str(int(cls)))
                color = (0,0,255) if cls == 1 else (255,0,0)

                # Rita
                cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
                cv2.putText(display, f"{label} ({conf:.2f})",
                            (x1, y1-5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

                # Trigga plock om i zon - utan att stoppa bandet
                if 195 <= cx <= 425 and 5 <= cy <= 350 and not busy:
                    print(f"🟢 {label} vid ({cx},{cy}) – startar plock")
                    # Starta robotsekvens
                    threading.Thread(
                        target=robot_task,
                        args=(cx, cy, int(cls)),
                        daemon=True
                    ).start()
                    break

            # Skicka bilden för visning
            if not display_queue.full():
                display_queue.put(display)

# Starta detektions-tråden
threading.Thread(target=detect_thread, daemon=True).start()

# ── Huvudprogram ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        # Initiera robot & kamera
        send_urscript(HOME)
        time.sleep(2.5)
        # Set constant conveyor speed
        send_urscript("set_analog_out(0, 0.04)")  # Adjust speed value as needed
        print("System ready - Conveyor running")

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_BUFFERSIZE , 1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH , 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)
        cap.set(cv2.CAP_PROP_FPS         , 30)
        if not cap.isOpened():
            raise RuntimeError("Kunde inte öppna kamera")

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            # Skicka till inferens om kö ej full
            if not frame_queue.full():
                frame_queue.put(frame.copy())

            # Visa senaste bearbetade bild
            if not display_queue.empty():
                shown = display_queue.get()
            else:
                shown = frame

            # Rita detektionszon
            cv2.rectangle(shown, (195,5), (425,350), (0,255,0), 2)
            cv2.putText(shown, "Detection Area", (180,20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)

            cv2.imshow("Live Detect", shown)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        send_urscript("set_analog_out(0, 0.0)")
        send_urscript("set_digital_out(1, False)")
        cap.release()
        cv2.destroyAllWindows()
        if robot_sock:
            robot_sock.close()
        print("Program avslutat.")