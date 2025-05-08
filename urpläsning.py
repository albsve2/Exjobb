import gzip
import xml.etree.ElementTree as ET

# Läs in och dekomprimera URP‑filen
with gzip.open('albin.urp', 'rb') as f:
    xml = f.read()

root = ET.fromstring(xml)

# Hitta alla MoveJ under MainProgram
for move in root.findall('.//MainProgram//Move'):
    mtype = move.get('motionType')            # "MoveJ" eller "MoveL"
    speed = float(move.get('speed'))
    accel = float(move.get('acceleration'))

    # Plocka varje waypoint
    for wp in move.findall('.//Waypoint'):
        # Först försök kartesiskt pose
        pic = wp.find('poseInFeatureCoordinates')
        if pic is not None:
            pose = pic.get('pose')
            # pose är en sträng "x, y, z, rx, ry, rz"
            print(f"{mtype} p[{pose}] , a={accel:.3f}, v={speed:.3f}")
        else:
            # annars led‑värden
            pos = wp.find('position')
            joints = pos.get('joints')
            print(f"{mtype} [{joints}] , a={accel:.3f}, v={speed:.3f}")
