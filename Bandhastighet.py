# belt_control_and_measure.py

import socket
import time

# --- Konfiguration ---
robotIP = "130.130.130.86"
PORT    = 30001

# --- URScript-kommunikation ---
def send_urscript(command: str):
    """Skickar ett URScript-kommando till roboten."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((robotIP, PORT))
            s.sendall((command + "\n").encode("utf-8"))
        print(f"[OK] Skickat: {command}")
    except Exception as e:
        print(f"[ERROR] Kunde inte skicka kommandot: {e}")

def set_belt_speed_analog(value: float):
    """
    Sätter bandets hastighet via analog utgång 0.
    value ska vara mellan 0.0 och 1.0.
    """
    if not 0.0 <= value <= 1.0:
        raise ValueError("Analogvärdet måste vara mellan 0.0 och 1.0")
    send_urscript(f"set_analog_out(0, {value:.3f})")

# --- Mätfunktion ---
def measure_speed_mm_per_s():
    """
    Mäter transportbandets hastighet i mm/s genom att
    timera två markeringar med angivet avstånd i mm.
    """
    print("\n=== Transportbandshastighetsmätning ===")
    print("1) Mät upp ett avstånd på bandet i millimeter (t.ex. 300 mm)")
    print("2) Placera kameran så att du ser när första och andra märket passerar")
    input("\nTryck ENTER när **första** märket passerar synfältet...")
    t_start = time.time()
    input("Tryck ENTER när **andra** märket passerar synfältet...")
    t_end = time.time()

    elapsed = t_end - t_start
    if elapsed <= 0:
        print("[ERROR] Tidsmätningen blev 0 eller negativ. Försök igen.")
        return None

    try:
        distance_mm = float(input("Ange avståndet mellan märkena (i mm): "))
        if distance_mm <= 0:
            raise ValueError
    except ValueError:
        print("[ERROR] Ogiltigt avstånd. Ange en positiv siffra i millimeter.")
        return None

    speed_mm_s = distance_mm / elapsed
    print("\n--- Resultat ---")
    print(f"Tid:       {elapsed:.3f} s")
    print(f"Avstånd:   {distance_mm:.1f} mm")
    print(f"Hastighet: {speed_mm_s:.2f} mm/s")
    return speed_mm_s

# --- Huvudprogram ---
if __name__ == "__main__":
    print("=== Styr och mät transportband ===")
    try:
        analog = float(input("Ange analog output (0.0–1.0) för bandets hastighet: "))
        set_belt_speed_analog(analog)
    except ValueError as e:
        print(f"[ERROR] Ogiltigt värde: {e}")
        exit(1)

    # Låt bandet gå en liten stund för att nå jämn hastighet
    print("Väntar 2 sekunder för att hastigheten stabiliseras...")
    time.sleep(2)

    # Kör mätningen
    speed = measure_speed_mm_per_s()
    if speed is not None:
        print(f"\n=> Inmätt hastighet: {speed:.2f} mm/s")
    else:
        print("Mätningen avbröts på grund av fel.")
