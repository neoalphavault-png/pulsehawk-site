#!/usr/bin/env python3
"""te_sync.py - Prognosen der Rubrik "scheduled protocol events" uebernehmen (Ben, 16.11.2026).

Liest den Zustand des Prognoselaufs (JSON, Datei oder URL aus der Umgebung
TE_QUELLE) und traegt neue Prognosen und das Ergebnis in
data/track-record-events.json ein. Eine schon eingetragene Prognose wird nie
geaendert; weicht die Quelle davon ab, bricht das Skript ab. Der Commit der
Datei ist der Zeitstempel der Prognose auf pulsehawk.io.

  python3 scripts/te_sync.py --zustand zustand.json --eintrag TE-001
  python3 scripts/te_sync.py --selbsttest
"""
import argparse
import copy
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATEI = os.path.join(HERE, "..", "data", "track-record-events.json")
FELDER = ("stufe", "erstellt_utc", "p50_utc", "band80_utc", "band95_utc", "vorlauf_s", "ref_utc", "ref_daa",
          "fenster", "ziehungen", "saat")


def lade_quelle(pfad):
    if pfad.startswith("https://"):
        with urllib.request.urlopen(pfad, timeout=30) as r:
            return json.loads(r.read().decode())
    with open(pfad, encoding="utf-8") as f:
        return json.load(f)


def uebernehmen(eintrag, zustand):
    """Gibt (eintrag neu, liste der aenderungen). Bricht bei Abweichung ab."""
    e = copy.deepcopy(eintrag)
    ev = zustand.get("ereignis") or {}
    if ev and ev.get("ziel_daa") != e["trigger_daa"]:
        raise SystemExit("ziel-daa der quelle %s passt nicht zu %s" % (ev.get("ziel_daa"), e["trigger_daa"]))
    neu = []
    da = {f["stufe"]: f for f in e["forecasts"]}
    for p in zustand.get("prognosen") or []:
        f = {k: p[k] for k in FELDER if k in p}
        if p["stufe"] in da:
            if da[p["stufe"]] != f:
                raise SystemExit("prognose %s weicht von der veroeffentlichten ab" % p["stufe"])
            continue
        if p["stufe"] not in e["stages"]:
            raise SystemExit("unbekannte stufe %s" % p["stufe"])
        e["forecasts"].append(f)
        neu.append("prognose %s" % p["stufe"])
    erg = zustand.get("ergebnis")
    if erg and e.get("result") is None:
        e["result"] = erg
        neu.append("ergebnis")
    elif erg and e["result"] != erg:
        raise SystemExit("ergebnis weicht vom eingetragenen ab")
    return e, neu


def selbsttest():
    e = {"id": "TE-1", "trigger_daa": 10, "stages": ["14d", "7d"], "forecasts": [], "result": None}
    p = {"stufe": "14d", "erstellt_utc": "2026-11-21T03:41:00Z", "p50_utc": "2026-12-05T00:20:00Z",
         "band80_utc": ["a", "b"], "band95_utc": ["c", "d"], "vorlauf_s": 1, "extra": 5}
    z = {"ereignis": {"ziel_daa": 10}, "prognosen": [p]}
    e1, neu = uebernehmen(e, z)
    fall = [len(e1["forecasts"]) == 1 and neu == ["prognose 14d"] and "extra" not in e1["forecasts"][0]]
    e2, neu2 = uebernehmen(e1, z)
    fall.append(e2 == e1 and neu2 == [])
    try:
        uebernehmen(e1, {"prognosen": [dict(p, p50_utc="2026-12-06T00:00:00Z")]})
        fall.append(False)
    except SystemExit:
        fall.append(True)
    try:
        uebernehmen(e, {"ereignis": {"ziel_daa": 11}})
        fall.append(False)
    except SystemExit:
        fall.append(True)
    e3, neu3 = uebernehmen(e1, dict(z, ergebnis={"zeit_utc": "x"}))
    fall.append(e3["result"] == {"zeit_utc": "x"} and neu3 == ["ergebnis"])
    print("%d von %d faellen richtig" % (sum(fall), len(fall)))
    return 0 if all(fall) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zustand", default=os.environ.get("TE_QUELLE"))
    ap.add_argument("--eintrag", default="TE-001")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    if not a.zustand:
        print("keine quelle gesetzt (TE_QUELLE), nichts zu tun")
        return 0
    try:
        zustand = lade_quelle(a.zustand)
    except OSError as e:
        print("quelle nicht lesbar (%s), nichts zu tun" % type(e).__name__)
        return 0
    with open(DATEI, encoding="utf-8") as f:
        d = json.load(f)
    i = next(k for k, x in enumerate(d["entries"]) if x["id"] == a.eintrag)
    d["entries"][i], neu = uebernehmen(d["entries"][i], zustand)
    if not neu:
        print("nichts neu")
        return 0
    with open(DATEI, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("neu: " + ", ".join(neu))
    return 0


if __name__ == "__main__":
    sys.exit(main())
