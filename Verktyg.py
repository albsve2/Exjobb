#Verktyg
def send_rg2_command(width_mm=110, force_pct=50):
    robot_ip = "192.168.0.10"
    port = 54321  # Standardport för OnRobot gripper TCP-server

    # Bygg JSON-kommando
    json_cmd = f"""{{
        "id": 1,
        "action": "move",
        "width": {width_mm},
        "force": {force_pct}
    }}"""

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((robot_ip, port))
        s.sendall(json_cmd.encode('utf-8'))
        print("Sent RG2 command:", json_cmd)
        s.close()
    except Exception as e:
        print("RG2 error:", e)

# Test: Stäng gripper till 10 mm med 60 % kraft
send_rg2_command(width_mm=10, force_pct=60)

# Vänta lite innan nästa kommando
time.sleep(1.0)

# Öppna helt (110 mm) med låg kraft
(width_mm=110, force_pct=30)