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
send_urscript("movel(p[0.30145,-0.15804,0.20,2.592,-1.979,0], a=1.2, v=0.3)")
#time.sleep(1.0)
#send_urscript("set_analog_out(0, 0.8)")
#time.sleep(0.5)
#send_urscript("set_digital_out(2, False)")
#send_urscript("set_digital_out(7, True)")
#send_urscript("set_tool_digital_out(1, True)")

#SMALL_DROP  = "movel(p[0.30145,-0.15804,0.23,2.592,-1.979,0], a=1.2, v=0.3)"
#MEDIUM_DROP = "movel(p[0.22736,-0.11185,0.23,2.592,-1.979,0], a=1.2, v=0.3)"


