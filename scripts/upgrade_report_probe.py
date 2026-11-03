#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""upgrade_report_probe.py, zeigt, dass report_v1.py (kaspa-pulse) und der
Waechter (upgrade_report.py) auf denselben Testdaten exakt gleich rechnen
(Ben, 3.11.2026).

Aus einem Testszenario mit festem Zufall entstehen
  - die Eingaenge der Wache (koepfe.csv.gz, wache-log.csv, zustand.json,
    Kettenkonfiguration), daraus rechnet report_v1.py die Messwert-CSV;
  - ueber report_import.py die Roh-CSV im PH-Format und "werte".
Dann laeuft der volle Waechter. Die Probe vergleicht jede Kennzahl, Wert und
n, als Text.

    python3 scripts/upgrade_report_probe.py --wache <kaspa-pulse>/scripts/wache [--m6-nachgezogen]

--m6-nachgezogen rechnet mit einer Kopie von report_v1.py, in der M6 so steht
wie in der Spezifikation v1.0 (60 min ganz in den Daten, ganze Sekunden). Das
ist der Auftrag an die Zcash-Sitzung; ohne den Schalter rechnet report_v1.py,
wie es auf main steht.
"""

import argparse
import csv
import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import report_import  # noqa: E402
import report_waechter as rw  # noqa: E402
import upgrade_report as ur  # noqa: E402

# die aenderung an report_v1.py, die der zcash-sitzung als auftrag geht
M6_ALT = ['''            if j == len(verlauf) or verlauf[j][0] > t + STABIL_HALTEN_S:''',
          '''        zeile("M6", "zeit_bis_stabil", round((stabil - von) / 60, 1) if stabil else "nie", "min", "counted",''']
M6_NEU = ['''            if j < len(verlauf) and verlauf[j][0] > t + STABIL_HALTEN_S:''',
          '''        zeile("M6", "zeit_bis_stabil", int(stabil - von) if stabil else "nie", "s", "counted",''']


def eingaenge_der_wache(sz, kopf, ordner):
    """das szenario in den dateien, die report_v1.py liest."""
    os.makedirs(os.path.join(ordner, "roh"), exist_ok=True)
    koepfe = os.path.join(ordner, "koepfe.csv.gz")
    with gzip.open(koepfe, "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hoehe", "hash", "zeit", "nbits"])
        for h in sorted(sz["kette"]):
            w.writerow([h, "%064x" % h, sz["kette"][h], "1d00ffff"])
    with open(os.path.join(ordner, "roh", "wache-log.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["utc", "hoehe", "signal", "wert", "schwelle", "stufe"])
        for z in sz["log"]:
            w.writerow([z["utc"], z["hoehe"], z["signal"], z["wert"], z["schwelle"], z["stufe"]])
    with open(os.path.join(ordner, "roh", "zustand.json"), "w") as f:
        json.dump({"signale": {}, "aktiv_gesehen_utc": None, "proben": sz["proben"]}, f, indent=1)
    s = kopf["schaetzung"]
    cfg = {"kette": "testchain", "aktivierung": {"name": "up1", "hoehe": kopf["aktivierungshoehe"]["wert"],
                                                 "erwartet_utc": s["zeit_utc"],
                                                 "band_utc": [s["band_von_utc"], s["band_bis_utc"]]},
           "min_protokoll": sz["min_protokoll"], "ziel_s": kopf["ziel_vorher"]["wert"],
           "ziel_nach_s": kopf["ziel_nachher"]["wert"],
           "signale": {"kettenspaltung": dict(kopf["kettenspaltung"], ruhe_s=1800),
                       "peers_vor_upgrade": {"zeitpunkte_h": list(ur.PROBEN_H)}}}
    kette = os.path.join(ordner, "kette.json")
    with open(kette, "w") as f:
        json.dump(cfg, f, indent=1)
    return kette, koepfe, os.path.join(ordner, "roh")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--wache", required=True, help="ordner scripts/wache aus kaspa-pulse")
    ap.add_argument("--m6-nachgezogen", action="store_true")
    ap.add_argument("--saat", type=int, default=2026)
    a = ap.parse_args(argv)
    sys.path.insert(0, HERE)
    import b2b_pages
    kopf = ur.testkopf()
    sz = ur.testszenario(kopf, a.saat)
    with tempfile.TemporaryDirectory() as tmp:
        wache = os.path.join(tmp, "wache")
        shutil.copytree(a.wache, wache, ignore=shutil.ignore_patterns("__pycache__"))
        rv1 = os.path.join(wache, "report_v1.py")
        if a.m6_nachgezogen:
            code = open(rv1, encoding="utf-8").read()
            for alt, neu in zip(M6_ALT, M6_NEU):
                if alt not in code:
                    raise SystemExit("report_v1.py hat die erwartete m6-zeile nicht: %s" % alt.strip())
                code = code.replace(alt, neu)
            open(rv1, "w", encoding="utf-8").write(code)
        kette, koepfe, roh = eingaenge_der_wache(sz, kopf, tmp)
        aus = os.path.join(tmp, "aus")
        r = subprocess.run([sys.executable, rv1, "--kette", kette, "--koepfe", koepfe, "--roh", roh, "--aus", aus],
                           capture_output=True, text=True)
        if r.returncode:
            raise SystemExit("report_v1.py bricht ab\n" + r.stderr[-2000:])
        metriken = json.loads(r.stdout.strip().splitlines()[-1])["csv"]
        with open(metriken, newline="") as f:
            alle = {z["kennzahl"]: z for z in csv.DictReader(f)}
        text = ur.ph_csv(report_import.szenario_aus_wache(json.load(open(kette)), koepfe, roh), kopf)
        unsere = ur.oeffentlich(ur.rechnen(kopf, ur.zeilen(text)))
        print("%-38s %-22s %-22s %s" % ("kennzahl", "report_v1.py (wert, n)", "waechter (wert, n)", "gleich"))
        gleich = 0
        for k in ur.kennzahlen():
            v1 = alle.get(k)
            v1t = (v1["wert"], v1["n"]) if v1 else ("fehlt", "")
            un = unsere.get(k)
            unt = (un["wert"], un["n"]) if un else ("fehlt", "")
            g = v1t == unt
            gleich += g
            print("%-38s %-22s %-22s %s" % (k, "%s, %s" % v1t, "%s, %s" % unt, "ja" if g else "NEIN"))
        print("%d von %d kennzahlen exakt gleich" % (gleich, len(ur.kennzahlen())))
        # der volle waechter mit den werten aus report_v1.py
        try:
            werte = report_import.werte_aus_metriken(metriken)
            rw.pruefe_report(dict(kopf, werte=werte), text, b2b_pages.render)
            print("waechter: alle pruefungen gruen, die seite wuerde gebaut")
            gruen = True
        except SystemExit as exc:
            print("waechter: nicht gestartet, %s" % exc)
            gruen = False
        except rw.Rot as rot:
            print("waechter: rot")
            for x in rot.funde[:12]:
                print("  %s) %s" % x)
            gruen = False
        print("roh-csv %d zeilen, sha256 %s" % (text.count("\n") - 1,
                                                __import__("hashlib").sha256(text.encode()).hexdigest()))
    return 0 if gleich == len(ur.kennzahlen()) and gruen else 1


if __name__ == "__main__":
    sys.exit(main())
