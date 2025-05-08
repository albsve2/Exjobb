
import csv
from statistics import mean, stdev

LOGG_FIL = "cykeltider_steglogg.csv"

def analysera_steglogg():
    stegdata = [[] for _ in range(9)]  # 9 steg
    total_tider = []

    with open(LOGG_FIL, mode='r') as fil:
        reader = csv.reader(fil)
        for rad in reader:
            if len(rad) < 11:
                continue
            steg_tider = [float(v) for v in rad[2:11]]
            total = float(rad[11])
            for i, tid in enumerate(steg_tider):
                stegdata[i].append(tid)
            total_tider.append(total)

    print("Analys av cykeltider per steg:")
    for i, steg in enumerate([
        "Till plockposition ovanför batteri",
        "Närma sig grepphöjd",
        "Sänk till plockhöjd",
        "Aktivera gripdon",
        "Lyft batteriet",
        "Gå till släppzon",
        "Släpp batteri",
        "Återgå till HOME",
        "Starta transportband"
    ]):
        if stegdata[i]:
            print(f"- {steg}: medel = {mean(stegdata[i]):.2f}s, std = {stdev(stegdata[i]):.2f}s")

    if total_tider:
        print(f" Total cykeltid: medel = {mean(total_tider):.2f}s, std = {stdev(total_tider):.2f}s")


if __name__ == "__main__":
    analysera_steglogg()
