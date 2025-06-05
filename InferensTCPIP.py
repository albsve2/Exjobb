import time
def send_urscript_timed(cmd):
    t0 = time.time()
    send_urscript(cmd)
    t1 = time.time()
    print(f"TCP/IP-latens: {(t1-t0)*1000:.1f} ms")
