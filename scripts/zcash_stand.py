#!/usr/bin/env python3
"""zcash_stand.py - holt den Zcash-Mainnet-Stand fuer /zcash-nu7.

Ben, 27.10.2026: /zcash-nu7 zeigt oben unsere Prognose fuer die NU7-Hoehe aus
dem juengsten Mainnet-Stand und ab der Aktivierung die ersten gezaehlten
Zahlen (Kurznotiz nach NU7). Die Staende schreibt in kaspa-pulse der Workflow
zcash-mainnet.yml auf den Datenbranch messung/zcash-mainnet
(data/zcash-mainnet/stand-JJJJ-MM-TT.json).

Dieses Skript nimmt eine solche Datei und schreibt eine gekuerzte Kopie nach
data/zcash-nu7/mainnet-stand.json. Uebernommen werden nur die Zahlen, die die
Seite braucht. Peer-Software und die Zakura-Schaetzung bleiben draussen
(Ben, Auftrag zu den Zcash-Endzahlen: das Zakura-Detail nicht auf die Seite).

  git clone --depth 1 --branch messung/zcash-mainnet <kaspa-pulse> /tmp/zm
  python3 scripts/zcash_stand.py /tmp/zm/data/zcash-mainnet/stand-2026-10-28.json
  python3 scripts/b2b_pages.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ZIEL = os.path.join(REPO, "data", "zcash-nu7", "mainnet-stand.json")
QUELLE = "kaspa-pulse, Branch messung/zcash-mainnet, data/zcash-mainnet/%s"


def kuerzen(st, name):
    m = re.match(r"stand-(\d{4}-\d{2}-\d{2})\.json$", name)
    if not m:
        raise SystemExit("erwartet stand-JJJJ-MM-TT.json, bekommen %r" % name)
    aus = {"hinweis": ("Gekuerzte Kopie des Zcash-Mainnet-Stands fuer /zcash-nu7, erzeugt mit "
                       "scripts/zcash_stand.py. Nicht von Hand aendern, neu holen."),
           "quelle": QUELLE % name, "stand": m.group(1), "abruf_utc": st["abruf_utc"],
           "nu7_hoehe": st["nu7_hoehe"], "bereich": st["bereich"],
           "pruefungen": st.get("pruefungen"),
           "gegenproben": [{"verglichen": g["verglichen"], "gleich": g["gleich"]}
                           for g in st.get("gegenproben", [])]}
    if st.get("vor_nu7"):
        v = st["vor_nu7"]
        aus["vor_nu7"] = {k: v[k] for k in ("abstaende", "gezaehlt", "berechnet", "bereich") if k in v}
    if st.get("vorhersage") and "median_utc" in st["vorhersage"]:
        aus["vorhersage"] = {k: w for k, w in st["vorhersage"].items() if not k.startswith("zakura")}
    for teil in ("nach_nu7", "einpendeln"):
        if st.get(teil):
            aus[teil] = st[teil]
    return aus


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    pfad = argv[0]
    with open(pfad, encoding="utf-8") as fh:
        st = json.load(fh)
    if st.get("nu7_hoehe") != 3543405:
        raise SystemExit("nu7_hoehe passt nicht: %r" % st.get("nu7_hoehe"))
    aus = kuerzen(st, os.path.basename(pfad))
    with open(ZIEL, "w", encoding="utf-8") as fh:
        json.dump(aus, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("%s geschrieben, stand %s, %s" % (os.path.relpath(ZIEL, REPO), aus["stand"],
                                             "nach nu7" if "nach_nu7" in aus else "vor nu7"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
