import socket, time

robotIP, PORT = "130.130.130.86", 30001

def send_urscript(cmd, pause=0.0):
    s=socket.socket(); s.settimeout(2.0)
    try:
        s.connect((robotIP, PORT))
        s.sendall((cmd+"\n").encode())
        # ev. läs ACK
        try: print("ACK:", s.recv(1024))
        except: pass
    except Exception as e:
        print("ERROR sending:", cmd, e)
    finally:
        s.close()
    if pause>0: time.sleep(pause)

if __name__=="__main__":
    # 0) välj ditt kamerafeature (frame 6 i detta exempel)
    send_urscript("set_user_frame(6)", 0.5)

    # 1) startposition
    send_urscript(
      "movel(p[-0.15410, 0.27879, -0.24356, 2.634, 1.716, -0.034], a=1.396, v=1.047)",
      1.0)

    # 2) grepp‑position
    send_urscript(
      "movel(p[-0.29046, 0.19016, -0.33856, 2.398, 1.096, -0.559], a=1.396, v=1.047)",
      1.0)

    # 3) upp från grepp
    send_urscript(
      "movel(p[-0.18686, 0.29456, -0.24507, 2.969, 1.222, -0.041], a=1.396, v=1.047)",
      1.0)

    # 4) medium batteri
    send_urscript(
      "movel(p[-0.14880, 0.44006, -0.27940, 3.245, 0.756, -0.094], a=1.396, v=1.047)",
      1.0)

    # 5) small batteri
    send_urscript(
      "movel(p[0.00120, 0.47467, -0.31819, 3.321, 0.185, -0.104], a=1.396, v=1.047)",
      1.0)

    print("Done.")
