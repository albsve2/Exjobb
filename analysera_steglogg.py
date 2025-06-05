import csv
from statistics import mean, stdev

LOGG_FIL = "cykeltider_steglogg.csv"

def analysera_steglogg():
    # Initiera listor för per-steg-tider och totala tider
    stegdata_small   = [[] for _ in range(9)]
    stegdata_medium  = [[] for _ in range(9)]
    stegdata_both    = [[] for _ in range(9)]
    total_small      = []
    total_medium     = []
    total_both       = []

    with open(LOGG_FIL, mode='r', newline='') as fil:
        reader = csv.reader(fil)
        for rad in reader:
            # Förväntar minst 12 kolumner: id, storlek, t1...t9, total
            if len(rad) < 12:
                continue

            storlek    = rad[1].strip().lower()
            steg_tider = [float(v) for v in rad[2:11]]
            total_tid  = float(rad[11])

            # Filtrera small
            if storlek == 'small':
                for i, t in enumerate(steg_tider):
                    stegdata_small[i].append(t)
                    stegdata_both[i].append(t)
                total_small.append(total_tid)
                total_both.append(total_tid)

            # Filtrera medium
            elif storlek == 'medium':
                for i, t in enumerate(steg_tider):
                    stegdata_medium[i].append(t)
                    stegdata_both[i].append(t)
                total_medium.append(total_tid)
                total_both.append(total_tid)

    steg_namn = [
        "Till plockposition ovanför batteri",
        "Närma sig grepphöjd",
        "Sänk till plockhöjd",
        "Aktivera gripdon",
        "Lyft batteriet",
        "Gå till släppzon",
        "Släpp batteri",
        "Återgå till HOME",
        "Starta transportband"
    ]

    def skriv_ut_stats(titel, stegdata, totaltider):
        print(f"\n=== {titel} ===")
        for i, namn in enumerate(steg_namn):
            if stegdata[i]:
                m = mean(stegdata[i])
                s = stdev(stegdata[i])
                print(f"- {namn}: medel={m:.2f}s, std={s:.2f}s")
        if totaltider:
            print(f"  Totalt (hela cykeln): medel={mean(totaltider):.2f}s, std={stdev(totaltider):.2f}s")

    # Skriv ut för respektive grupp
    skriv_ut_stats("SMALL", stegdata_small, total_small)
    skriv_ut_stats("MEDIUM", stegdata_medium, total_medium)
    skriv_ut_stats("SMALL + MEDIUM (båda tillsammans)", stegdata_both, total_both)


if __name__ == "__main__":
    analysera_steglogg()
