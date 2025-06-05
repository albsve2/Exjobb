import time
start = time.time()
send_urscript("set_analog_out(0, 0.0)")
# vänta på signal från fotocell/sensor, t.ex. GPIO-läsning eller serial-input…
wait_for_sensor_stop()
stop = time.time()
delay_ms = (stop - start) * 1000
print(f"Stoppfördröjning: {delay_ms:.0f} ms")
