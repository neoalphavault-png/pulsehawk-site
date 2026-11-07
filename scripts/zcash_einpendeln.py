#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zcash_einpendeln.py, Einpendeln nach NU7 und 95-%-Intervalle fuer /zcash-nu7
(Ben, 7.11.2026).

Kriterium von Ben: Das Einpendeln ist gezaehlt, wenn das Mittel ueber die
letzten 250 Blockabstaende in seinem 95-%-Intervall die 25 s enthaelt. Das
Intervall ist Mittel +- 1.96 s / sqrt(n), wie in scripts/unsicherheit.py.

Gerechnet wird aus den eigenen Koepfen (koepfe.csv.gz vom Datenbranch
messung/zcash-mainnet in kaspa-pulse), nur bis zur Hoehe des Stands, damit die
Zahlen zu data/zcash-nu7/mainnet-stand.json passen. Das Ergebnis geht als
"nach_nu7" und "einpendeln_250" nach data/zcash-nu7/mainnet-unsicherheit.json.

    python3 scripts/zcash_einpendeln.py <koepfe.csv.gz>
"""

import csv
import datetime
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import unsicherheit  # noqa: E402

STAND = os.path.join(REPO, "data", "zcash-nu7", "mainnet-stand.json")
ZIEL = os.path.join(REPO, "data", "zcash-nu7", "mainnet-unsicherheit.json")
FENSTER = 250
ZIEL_S = 25


def utc(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def rechnen(zeit, nu7, bis):
    """zeit: {hoehe: kopfzeit}. Abstaende der bloecke nu7+1 bis bis."""
    fehlt = [h for h in range(nu7, bis + 1) if h not in zeit]
    if fehlt:
        raise SystemExit("koepfe fehlen, erste fehlende hoehe %d" % fehlt[0])
    w = [zeit[h] - zeit[h - 1] for h in range(nu7 + 1, bis + 1)]
    if len(w) < FENSTER:
        raise SystemExit("erst %d abstaende nach nu7, das fenster braucht %d" % (len(w), FENSTER))
    alle = unsicherheit.alle(w)
    erstmals = None
    for i in range(FENSTER, len(w) + 1):
        lo, hi = unsicherheit.mittel_intervall(w[i - FENSTER:i])
        if lo <= ZIEL_S <= hi:
            erstmals = nu7 + i
            break
    letzte = w[-FENSTER:]
    lo, hi = unsicherheit.mittel_intervall(letzte)
    ein = {"fenster": FENSTER, "ziel_s": ZIEL_S,
           "letzte": {"bis_hoehe": bis, "bis_utc": utc(zeit[bis]),
                      "mittel": round(sum(letzte) / FENSTER, 2), "intervall": [round(lo, 2), round(hi, 2)],
                      "drin": lo <= ZIEL_S <= hi},
           "erstmals_bis_hoehe": erstmals, "erstmals_utc": utc(zeit[erstmals]) if erstmals else None}
    return alle, ein


def main(argv):
    if len(argv) != 1:
        raise SystemExit(__doc__)
    with open(STAND, encoding="utf-8") as fh:
        st = json.load(fh)
    nach = st.get("nach_nu7")
    if not nach:
        raise SystemExit("mainnet-stand.json hat noch kein nach_nu7")
    nu7, bis = st["nu7_hoehe"], nach["bereich"]["bis_hoehe"]
    with gzip.open(argv[0], "rt", newline="") as fh:
        zeit = {int(z["hoehe"]): int(z["zeit"]) for z in csv.DictReader(fh)}
    alle, ein = rechnen(zeit, nu7, bis)
    if alle["n"] != nach["abstaende"]:
        raise SystemExit("koepfe ergeben %d abstaende, der stand %d" % (alle["n"], nach["abstaende"]))
    if abs(alle["mittel"][0] + alle["mittel"][1] - 2 * nach["gezaehlt"]["mittel_s"]) > 0.02:
        raise SystemExit("mittel aus den koepfen passt nicht zum stand")
    with open(ZIEL, encoding="utf-8") as fh:
        u = json.load(fh)
    u["nach_nu7"] = {"stand": st["stand"], "bereich": [nu7, bis], "n": alle["n"],
                     **{k: alle[k] for k in ("mittel", "p50", "p90", "p99")}}
    u["einpendeln_250"] = dict(ein, stand=st["stand"])
    with open(ZIEL, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(u, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(u["einpendeln_250"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
