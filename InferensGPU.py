import os
import pathlib
import warnings
import torch
import statistics

# Tystar FutureWarnings
warnings.filterwarnings("ignore", category=FutureWarning)

# 1) Patch för Windows så att hubconf.py inte kraschar på PosixPath
if os.name == "nt":
    pathlib.PosixPath = pathlib.WindowsPath

# 2) Byt arbetskatalog till scriptets mapp (där hubconf.py finns)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 3) Ladda modellen med force_reload för att rensa cache
model = torch.hub.load(
    repo_or_dir=".",      # “.” = den katalog som innehåller hubconf.py
    model="custom",       # custom-läge i hubconf.py
    path="runs/train/exp6/weights/best.pt",
    source="local",
    force_reload=True
)
model.conf = 0.6
model.to("cuda").eval()

# 4) Enklaste GPU-timing med medelvärde + standardavvikelse
def measure_gpu_inference(model, input_shape=(1,3,640,640), n_warmup=10, n_runs=1000):
    # Skapa dummy-input på GPU
    device = torch.device("cuda")
    inp = torch.zeros(input_shape, device=device)

    # Warm-up
    with torch.no_grad():
        for _ in range(n_warmup):
            _ = model(inp)
    torch.cuda.synchronize()

    # Mätloop
    times = []
    with torch.no_grad():
        for _ in range(n_runs):
            start = torch.cuda.Event(enable_timing=True)
            end   = torch.cuda.Event(enable_timing=True)
            start.record()
            _ = model(inp)
            end.record()
            torch.cuda.synchronize()
            times.append(start.elapsed_time(end))

    # Beräkna statistik
    avg = sum(times) / len(times)
    stdev = statistics.pstdev(times)

    # Skriv ut resultat
    print(f"Genomsnittlig GPU-inferenstid över {n_runs} körningar: {avg:.2f} ms")
    print(f"Standardavvikelse: ±{stdev:.2f} ms")

if __name__ == "__main__":
    measure_gpu_inference(model)
