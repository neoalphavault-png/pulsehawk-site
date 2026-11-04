#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""unsicherheit.py, Messunsicherheit fuer PulseHawk-Kennzahlen (Ben, 4.11.2026).

Jede Kennzahl auf einer Mess- oder Report-Seite bekommt eine Zeile
"measurement uncertainty". Gerechnet wird ohne Annahme ueber die Verteilung:

  Perzentile (p50, p90, p99)  95-%-Intervall aus den Rangstatistiken, die
                              Raenge j und k um n q mit 1.96 sqrt(n q (1 - q))
  Mittel                      Mittel +- 1.96 s / sqrt(n), s die Stichproben-
                              Standardabweichung
  Anteil                      95-%-Wilson-Intervall
  Zaehlung, Laengste Luecke   keine Stichprobe, die Grenze ist die Abdeckung
                              des Zuhoerers oder die Aufloesung der Kopfzeiten

Die Kopfzeiten setzen die Miner, in ganzen Sekunden. Diese Aufloesung gilt
zusaetzlich fuer jeden Wert aus Kopfzeiten.

    python3 scripts/unsicherheit.py --csv <datei> --spalte interval_s
    python3 scripts/unsicherheit.py --koepfe koepfe.csv.gz --von 3489717 --bis 3533510 --aus <json>
"""

import argparse
import csv
import gzip
import json
import math
import sys

Z95 = 1.959963984540054


def perzentil_intervall(werte, q):
    """95-%-intervall fuer das q-perzentil aus den rangstatistiken."""
    s = sorted(werte)
    n = len(s)
    if n < 20:
        return None
    rand = Z95 * math.sqrt(n * q * (1 - q))
    j = max(1, math.floor(n * q - rand))
    k = min(n, math.ceil(n * q + rand))
    return s[j - 1], s[k - 1]


def mittel_intervall(werte):
    n = len(werte)
    if n < 2:
        return None
    m = sum(werte) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in werte) / (n - 1))
    h = Z95 * sd / math.sqrt(n)
    return m - h, m + h


def anteil_intervall(k, n):
    """95-%-wilson-intervall fuer k von n, in prozent."""
    if n == 0:
        return None
    p = k / n
    z2 = Z95 * Z95
    mitte = (p + z2 / (2 * n)) / (1 + z2 / n)
    h = Z95 * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)
    return 100 * max(0.0, mitte - h), 100 * min(1.0, mitte + h)


def alle(werte):
    """die intervalle, die eine tabelle mit mittel, p50, p90, p99 braucht."""
    aus = {"n": len(werte)}
    mi = mittel_intervall(werte)
    if mi:
        aus["mittel"] = [round(mi[0], 2), round(mi[1], 2)]
    for name, q in (("p50", 0.5), ("p90", 0.9), ("p99", 0.99)):
        pi = perzentil_intervall(werte, q)
        if pi:
            aus[name] = list(pi)
    return aus


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    ap.add_argument("--spalte", default="interval_s")
    ap.add_argument("--koepfe")
    ap.add_argument("--von", type=int)
    ap.add_argument("--bis", type=int)
    ap.add_argument("--aus")
    a = ap.parse_args(argv)
    if a.csv:
        with open(a.csv, newline="") as f:
            werte = [int(z[a.spalte]) for z in csv.DictReader(f) if z[a.spalte]]
    elif a.koepfe:
        opener = gzip.open if a.koepfe.endswith(".gz") else open
        with opener(a.koepfe, "rt") as f:
            zeit = {int(z["hoehe"]): int(z["zeit"]) for z in csv.DictReader(f)}
        werte = [zeit[h] - zeit[h - 1] for h in range(a.von + 1, a.bis + 1) if h in zeit and h - 1 in zeit]
    else:
        ap.error("--csv oder --koepfe")
    erg = alle(werte)
    text = json.dumps(erg, indent=1)
    if a.aus:
        with open(a.aus, "w") as f:
            f.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
