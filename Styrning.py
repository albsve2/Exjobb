import socket
import time

robotIP = "130.130.130.86"
PORT = 30001

def send_urscript(command: str):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((robotIP, PORT))
        s.sendall((command + "\n").encode('utf-8'))
        s.close()
        print(f"Sent: {command}")
    except Exception as e:
        print("Error:", e)

# Stegvis styrning
#send_urscript("movel(p[0.42261, -0.05421, 0.257, 1.8392, -2.5593, 0.0072], a=0.5, v=0.25)")
#time.sleep(1.0)
send_urscript("set_digital_out(1, True)")
#time.sleep(0.5)
#send_urscript("set_digital_out(2, False)")
#send_urscript("set_digital_out(7, True)")
#send_urscript("set_tool_digital_out(1, True)")



