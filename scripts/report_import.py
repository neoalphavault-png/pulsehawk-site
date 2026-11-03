#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report_import.py, Daten der Upgrade-Wache in einen PulseHawk Upgrade Report
uebernehmen (Ben, 3.11.2026).

Die messende Sitzung in kaspa-pulse liefert auf ihrem Datenbranch:
  - die Koepfe (hoehe,hash,zeit,nbits), etwa data/zcash-mainnet/koepfe.csv.gz
  - die Rohdaten der Wache aus roh_export.py (wache-log.csv, zustand.json)
  - die Messwert-CSV aus scripts/wache/report_v1.py (metrik,kennzahl,wert,...)
  - die Konfiguration der Kette (scripts/wache/ketten/<kette>.json)

Dieses Skript baut daraus
  - reports/<slug>.csv, die Roh-CSV im PH-Format (upgrade_report.ph_csv), und
  - "werte" in data/reports/<slug>.json: wert und n jeder Kennzahl aus der
    Messwert-CSV, unveraendert als Text.
Danach prueft der Waechter (report_waechter.py --pruefen <slug>): er rechnet
jede Kennzahl aus der Roh-CSV neu und vergleicht exakt mit "werte". Zwei
Rechnungen aus zwei Codebasen, auf denselben Eingangsdaten.

Keine Adressen: wache-log.csv und zustand.json enthalten keine, und
upgrade_report.ph_csv uebernimmt nur Hoehe, Zeit, Tiefe, Stufe und die
Protokollversion als 0 oder 1.

    python3 scripts/report_import.py --slug zcash-nu7 --kette <kette.json> \\
        --koepfe <koepfe.csv.gz> --roh <ordner> --metriken <report-v1-...csv>
"""

import argparse
import csv
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import upgrade_report as ur  # noqa: E402


def szenario_aus_wache(cfg, koepfe, roh):
    """das gemeinsame modell aus den dateien der wache."""
    opener = gzip.open if koepfe.endswith(".gz") else open
    with opener(koepfe, "rt") as f:
        kette = {int(x["hoehe"]): int(x["zeit"]) for x in csv.DictReader(f)}
    log, zustand = [], {}
    lp, zp = os.path.join(roh, "wache-log.csv"), os.path.join(roh, "zustand.json")
    if os.path.exists(lp):
        with open(lp, newline="") as f:
            log = list(csv.DictReader(f))
    if os.path.exists(zp):
        with open(zp) as f:
            zustand = json.load(f)
    return {"kette": kette, "log": log, "proben": zustand.get("proben", {}), "hat_log": bool(log),
            "min_protokoll": cfg["min_protokoll"]}


def werte_aus_metriken(pfad):
    """wert und n jeder kennzahl, die der report zeigt, als text wie in der datei."""
    with open(pfad, newline="") as f:
        zeilen = {z["kennzahl"]: z for z in csv.DictReader(f)}
    if "zeit_bis_stabil" in zeilen and zeilen["zeit_bis_stabil"]["einheit"] != "s":
        raise SystemExit("M6 zeit_bis_stabil in %r, die spezifikation v1.0 verlangt ganze sekunden. "
                         "report_v1.py ist noch nicht nachgezogen." % zeilen["zeit_bis_stabil"]["einheit"])
    return {k: {"wert": zeilen[k]["wert"], "n": zeilen[k]["n"]} for k in ur.kennzahlen() if k in zeilen}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--kette", required=True)
    ap.add_argument("--koepfe", required=True)
    ap.add_argument("--roh", required=True)
    ap.add_argument("--metriken", required=True)
    ap.add_argument("--geaendert", help="JJJJ-MM-TT, sonst bleibt das datum")
    a = ap.parse_args(argv)
    kopf_pfad = os.path.join(REPO, "data", "reports", a.slug + ".json")
    with open(kopf_pfad, encoding="utf-8") as f:
        kopf = json.load(f)
    with open(a.kette) as f:
        cfg = json.load(f)
    if cfg["aktivierung"]["hoehe"] != kopf["aktivierungshoehe"]["wert"]:
        raise SystemExit("aktivierungshoehe der wache %s, im report %s"
                         % (cfg["aktivierung"]["hoehe"], kopf["aktivierungshoehe"]["wert"]))
    text = ur.ph_csv(szenario_aus_wache(cfg, a.koepfe, a.roh), kopf)
    kopf["csv"] = "reports/%s.csv" % a.slug
    kopf["werte"] = werte_aus_metriken(a.metriken)
    if a.geaendert:
        kopf["geaendert"] = a.geaendert
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, kopf["csv"]), "w", encoding="utf-8", newline="") as f:
        f.write(text)
    with open(kopf_pfad, "w", encoding="utf-8") as f:
        json.dump(kopf, f, indent=1, ensure_ascii=False)
    print("roh-csv %s, %d zeilen; %d kennzahlen aus %s"
          % (kopf["csv"], text.count("\n") - 1, len(kopf["werte"]), os.path.basename(a.metriken)))
    print("weiter mit: python3 scripts/report_waechter.py --pruefen %s" % a.slug)
    return 0


if __name__ == "__main__":
    sys.exit(main())
