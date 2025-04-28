import time

print("Transportbandshastighetsmätning")
print("--------------------------------")
print("1. Mät upp en sträcka på bandet (t.ex. 30 cm)")
print("2. Placera kameran så att du ser när märket passerar")
print("3. Tryck ENTER första gången märket passerar synfältet")
print("4. Tryck ENTER igen när nästa märke passerar")

input("Tryck ENTER när första märket passerar...")
start_time = time.time()

input("Tryck ENTER när andra märket passerar...")
end_time = time.time()

elapsed = end_time - start_time

# Ange sträckan du markerat på bandet (kan justeras)
distance_cm = float(input("Ange avståndet mellan märkena (i cm): "))
speed = distance_cm / elapsed

print(f"\n Tid: {elapsed:.2f} sekunder")
print(f" Sträcka: {distance_cm:.1f} cm")
print(f" Bandets hastighet: {speed:.2f} cm/s")


