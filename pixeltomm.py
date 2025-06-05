import warnings
import torch
import cv2
import numpy as np
import socket
import time
import os
import pathlib
import threading
import queue
import re

CLASS_NAMES = {0: "small", 1: "medium"}

# Tysta torch-varningar
warnings.filterwarnings("ignore", category=FutureWarning)

# ── Robotens IP och port ─────────────────────────────────────────────────────────
robotIP, PORT = "130.130.130.86", 30001

def send_urscript(cmd: str):
    """Skicka ett helt URScript-block på en ny socket, sedan stäng."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        s.connect((robotIP, PORT))
        s.sendall((cmd + "\n").encode())
        s.close()
        print(">>>", cmd.split("\n")[0], "…")
        return True
    except Exception as e:
        print("!!! could not send script:", e)
        return False

# ── Patch för Windows pathlib ───────────────────────────────────────────────────
if os.name == 'nt':
    pathlib.PosixPath = pathlib.WindowsPath

# ── Ladda affine-matris + offset ────────────────────────────────────────────────
affine_matrix = np.loadtxt("affine_matrix.txt", dtype=np.float32)
manual_offset = np.array([-16.34, 11.86])  # mm

# ── Ladda YOLOv5-modellen ───────────────────────────────────────────────────────
model = torch.hub.load(
    "./", "custom",
    path="runs/train/exp6/weights/best.pt",
    source="local", force_reload=True
)
model.conf = 0.6
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device).eval()

# ── Robot-positioner (oförändrat) ────────────────────────────────────────────────
RX, RY, RZ = 3.186, -0.124, 0.106
HOME        = "movel(p[0.32199,-0.11007,0.12600,3.186,-0.124,0], a=1.2, v=2.0)"
SMALL_DROP  = "movel(p[0.30145,-0.15804,0.23,2.592,-1.979,0], a=1.2, v=0.3)"
MEDIUM_DROP = "movel(p[0.22736,-0.11185,0.23,2.592,-1.979,0], a=1.2, v=0.3)"

# ── Globals ─────────────────────────────────────────────────────────────────────
busy = False
frame_queue   = queue.Queue(maxsize=1)
display_queue = queue.Queue(maxsize=1)

def robot_task(cx, cy, cls):
    global busy
    busy = True

    # Transformera pixlar → mm → m
    pt         = np.array([[[cx, cy]]], dtype=np.float32)
    tr         = cv2.transform(pt, affine_matrix)[0][0]
    x_mm, y_mm = tr + manual_offset
    x_m, y_m   = x_mm/1000, y_mm/1000

    # Plockhöjder
    if cls == 1:
        z_pick, z_app, typ = 0.082, 0.092, "medium"
    else:
        z_pick, z_app, typ = 0.070, 0.080, "small"

    # Bygg URScript med interna tidsmätningar
    script = f"""
def pick():
  t0 = get_time()
  movel(p[{x_m:.5f},{y_m:.5f},0.12,{RX},{RY},{RZ}], a=2.5, v=2.0)
  t1 = get_time(); textmsg("STEP1", t1 - t0)
  movel(p[{x_m:.5f},{y_m:.5f},{z_app:.5f},{RX},{RY},{RZ}], a=0.2, v=0.2)
  t2 = get_time(); textmsg("STEP2", t2 - t1)
  movel(p[{x_m:.5f},{y_m:.5f},{z_pick:.5f},{RX},{RY},{RZ}], a=0.1, v=0.05)
  t3 = get_time(); textmsg("STEP3", t3 - t2)
  set_digital_out(1, True)
  sleep(0.2)
  t4 = get_time(); textmsg("STEP4_VAC_ON", t4 - t3)
  movel(p[{x_m:.5f},{y_m:.5f},{z_app:.5f},{RX},{RY},{RZ}], a=0.5, v=2.0)
  t5 = get_time(); textmsg("STEP5", t5 - t4)
  {SMALL_DROP if cls==0 else MEDIUM_DROP}
  t6 = get_time(); textmsg("STEP6_DROP", t6 - t5)
  set_digital_out(1, False)
  t7 = get_time(); textmsg("STEP7_VAC_OFF", t7 - t6)
  {HOME}
  t8 = get_time(); textmsg("STEP8_HOME", t8 - t7)
end
pick()
"""
    send_urscript(script)

    # Läs tillbaka STEP-meddelanden
    buf = ""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect((robotIP, PORT))
        start = time.time()
        while time.time() - start < 2.0:
            try:
                chunk = s.recv(1024).decode('utf-8', errors='ignore')
                if not chunk:
                    break
                buf += chunk
            except socket.timeout:
                break
        s.close()
    except Exception:
        pass

    # Filtrera ut tider
    steps = {}
    for line in buf.splitlines():
        m = re.match(r"(STEP\d+)[^0-9]*([\d\.]+)", line)
        if m:
            idx = int(m.group(1)[4:])
            steps[idx] = float(m.group(2))

    if len(steps) == 8:
        durations = [steps[i] for i in sorted(steps)]
        total = sum(durations)
        print(f"{typ} steg-tider: {durations}")
        print(f"{typ} total tid: {total:.3f}s")
    else:
        print("Missade steg-meddelanden, rådata:\n", buf)

    # Rensa kö och markera klar
    while not frame_queue.empty():
        frame_queue.get()
    busy = False

def detect_thread():
    global busy
    while True:
        if frame_queue.empty() or busy:
            continue
        frame = frame_queue.get()
        disp  = frame.copy()
        with torch.amp.autocast(device_type="cuda"):
            results = model(frame)
        for *box, conf, cls in results.pred[0].cpu().numpy():
            if conf < model.conf:
                continue
            x1,y1,x2,y2 = map(int, box)
            cx, cy = (x1+x2)//2, (y1+y2)//2
            color = (0,0,255) if cls==1 else (255,0,0)
            cv2.rectangle(disp,(x1,y1),(x2,y2),color,2)
            cv2.putText(disp,f"{CLASS_NAMES[int(cls)]} {conf:.2f}",
                        (x1,y1-5),cv2.FONT_HERSHEY_SIMPLEX,0.5,color,1)
            if 170 <= cx <= 400 and 5 <= cy <= 350 and not busy:
                busy = True
                print(f"🟢 Detekterat vid ({cx},{cy}) – startar pick")
                send_urscript("set_analog_out(0,0.0)")
                threading.Thread(target=robot_task,
                                 args=(cx, cy, int(cls)),
                                 daemon=True).start()
                break
        if not display_queue.full():
            display_queue.put(disp)

threading.Thread(target=detect_thread, daemon=True).start()

# ── Huvudprogram ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        send_urscript(HOME); time.sleep(2.5)
        send_urscript("set_analog_out(0,0.04)")
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT,640)
        cap.set(cv2.CAP_PROP_FPS,30)

        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            if not frame_queue.full():
                frame_queue.put(frame.copy())
            shown = display_queue.get() if not display_queue.empty() else frame
            cv2.rectangle(shown,(170,5),(400,350),(0,255,0),2)
            cv2.putText(shown,"Detection Area",(180,20),
                        cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,255,0),1)
            cv2.imshow("Live Detect", shown)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        send_urscript("set_analog_out(0,0.0)")
        send_urscript("set_digital_out(1,False)")
        cap.release()
        cv2.destroyAllWindows()
        print("Program avslutat.")
