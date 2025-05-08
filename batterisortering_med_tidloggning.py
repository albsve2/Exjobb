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
import csv
from datetime import datetime

CLASS_NAMES = {0: "small", 1: "medium"}

# Tystar torch-varningar
warnings.filterwarnings("ignore", category=FutureWarning)

# Robotens IP och port
robotIP, PORT = "130.130.130.86", 30001

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

# Windows-patch för pathlib
if os.name == 'nt':
    pathlib.PosixPath = pathlib.WindowsPath

# Ladda in affinitetsmatris + offset
affine_matrix = np.loadtxt("affine_matrix.txt", dtype=np.float32)
manual_offset = np.array([7.0, -5.0])

# Ladda YOLOv5-modellen
model = torch.hub.load(
    "./", "custom",
    path="runs/train/exp6/weights/best.pt",
    source="local", force_reload=True
)
model.conf = 0.6
model = model.to("cuda")

# Robotpositioner
RX, RY, RZ = 3.186, -0.124, 0.106
HOME = "movel(p[0.34677,-0.13007,0.12600,3.186,-0.124,0], a=1.2, v=0.3)"
SMALL_DROP = "movel(p[0.30145,-0.15804,0.23,2.592,-1.979,0], a=1.2, v=0.3)"
MEDIUM_DROP = "movel(p[0.22736,-0.11185,0.23,2.592,-1.979,0], a=1.2, v=0.3)"

# Globals
busy = False
batteri_raknare = 0
frame_queue = queue.Queue(maxsize=1)
display_queue = queue.Queue(maxsize=1)

def logga_stegdata(tidpunkter, batterityp):
    """Loggar tider för varje steg + total tid till CSV."""
    tidssteg = [round(tidpunkter[i+1] - tidpunkter[i], 2) for i in range(len(tidpunkter)-1)]
    total_tid = round(tidpunkter[-1] - tidpunkter[0], 2)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("cykeltider_steglogg.csv", "a", newline="") as fil:
        writer = csv.writer(fil)
        writer.writerow([timestamp, batterityp] + tidssteg + [total_tid])

def robot_task(cx, cy, cls):
    """Kör plocksekvensen, mäter varje steg och loggar tider."""
    global busy
    busy = True

    # Transformera pixel till meter
    pt = np.array([[[cx, cy]]], dtype=np.float32)
    transformed = cv2.transform(pt, affine_matrix)[0][0] + manual_offset
    x_m, y_m = transformed[0]/1000, transformed[1]/1000

    # Plockhöjder
    if int(cls)==1:
        z_pick, z_app = 0.082, 0.092
    else:
        z_pick, z_app = 0.070, 0.080

    # Tidmätning start
    t0 = time.time()

    # Steg 1: Till plockposition ovanför
    send_urscript(f"movel(p[{x_m:.5f},{y_m:.5f},0.12,{RX},{RY},{RZ}],a=2.5,v=2.0)")
    time.sleep(1.0); t1 = time.time()

    # Steg 2: Närma grepphöjd
    send_urscript(f"movel(p[{x_m:.5f},{y_m:.5f},{z_app:.5f},{RX},{RY},{RZ}],a=0.2,v=0.2)")
    time.sleep(1.2); t2 = time.time()

    # Steg 3: Ta i plockhöjd
    send_urscript(f"movel(p[{x_m:.5f},{y_m:.5f},{z_pick:.5f},{RX},{RY},{RZ}],a=0.1,v=0.05)")
    time.sleep(1.5); t3 = time.time()

    # Steg 4: Aktivera vakuum
    send_urscript("set_digital_out(1,True)")
    time.sleep(0.5); t4 = time.time()

    # Steg 5: Lyft till grepphöjd
    send_urscript(f"movel(p[{x_m:.5f},{y_m:.5f},{z_app:.5f},{RX},{RY},{RZ}],a=0.5,v=2.0)")
    time.sleep(1.2); t5 = time.time()

    # Steg 6: Förflytta till släppzon
    send_urscript(SMALL_DROP if cls==0 else MEDIUM_DROP)
    time.sleep(2.0); t6 = time.time()

    # Steg 7: Släpp batteri
    send_urscript("set_digital_out(1,False)")
    time.sleep(0.3); t7 = time.time()

    # Steg 8: Återgå HOME
    send_urscript(HOME)
    time.sleep(2.0); t8 = time.time()

    # Steg 9: Starta bandet
    send_urscript("set_analog_out(0,0.04)")
    time.sleep(0.3); t9 = time.time()

    # Logga alla tider
    logga_stegdata([t0,t1,t2,t3,t4,t5,t6,t7,t8,t9],
                   "small" if cls==0 else "medium")

    busy = False

def detect_thread():
    """Bakgrundstråd som detekterar och startar plocksekvens."""
    global busy, batteri_raknare
    while True:
        if not frame_queue.empty() and not busy:
            frame = frame_queue.get()
            display = frame.copy()

            with torch.amp.autocast(device_type="cuda"):
                results = model(frame)

            for det in results.pred[0]:
                x1,y1,x2,y2,conf,cls = det.cpu().numpy()
                if conf < 0.6: continue

                cx,cy = int((x1+x2)/2), int((y1+y2)/2)
                label = CLASS_NAMES[int(cls)]
                # Rita ruta
                cv2.rectangle(display,
                              (int(x1),int(y1)),(int(x2),int(y2)),
                              (0,0,255),2)
                cv2.putText(display,
                            f"{label} {conf:.2f}",
                            (int(x1),int(y1)-5),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,(0,0,255),1)

                # Om inom plockzon
                if 170<=cx<=400 and 5<=cy<=350:
                    busy = True
                    batteri_raknare += 1
                    print(f"🟢 {label} vid ({cx},{cy})")
                    send_urscript("set_analog_out(0,0.0)")
                    threading.Thread(target=robot_task,
                                     args=(cx,cy,cls),
                                     daemon=True).start()
                    break

            if not display_queue.full():
                display_queue.put(display)

# Starta detektionstråden
threading.Thread(target=detect_thread, daemon=True).start()

# Huvudloop: kamera + GUI
try:
    send_urscript(HOME); time.sleep(2.5)
    send_urscript("set_analog_out(0,0.04)")
    cap = cv2.VideoCapture(1)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT,640)
    cap.set(cv2.CAP_PROP_FPS,30)

    while True:
        ret, frame = cap.read()
        if not ret: continue
        if not frame_queue.full(): frame_queue.put(frame.copy())
        shown = display_queue.get() if not display_queue.empty() else frame

        # Visa plockzon
        cv2.rectangle(shown,(170,5),(400,350),(0,255,0),2)
        cv2.putText(shown,"Detection Area",(225,25),
                    cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,255,0),1)
        cv2.putText(shown,
                    f"Batterier: {batteri_raknare}",
                    (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255), 2)

        cv2.imshow("Detect", shown)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    send_urscript("set_analog_out(0,0.0)")
    send_urscript("set_digital_out(1,False)")
    cap.release()
    cv2.destroyAllWindows()
    print("Program avslutat.")
