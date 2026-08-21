#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stamp_pages.py, schreibt die Tageszaehler fest in die Seiten.

WARUM ES DAS GIBT
Die Zaehler auf den Zyklusseiten rechnen im Browser. Fuer jeden Menschen
und fuer Google, das JavaScript ausfuehrt, steht dort immer die richtige
Zahl. Im Quelltext selbst steht aber weiter der Wert vom Tag der
Auslieferung.

Das war egal, solange nur Google zaehlt. Es ist nicht mehr egal, seit
Antwortmaschinen die Seiten abrufen. Viele davon lesen den rohen
Quelltext und fuehren kein JavaScript aus. Die wuerden bei uns fuer immer
853 sehen. Ausgerechnet bei zwei Seiten, deren ganzer Vorteil darin
besteht, dass ihre Zahl aktuell ist.

Also schreibt dieses Skript die Zahlen einmal taeglich in den Quelltext.
Danach stimmt beides, der Quelltext und das, was der Browser rechnet.

⚠️ FOLGE, DIE MAN KENNEN MUSS
Ab jetzt gilt fuer diese Seiten dieselbe Regel wie fuer index.html im
Repo kaspa-pulse. **Niemals eine alte lokale Kopie hochladen.** Der Bot
hat die Datei seit dem letzten Bearbeiten veraendert. Wer eine alte
Fassung hochlaedt, setzt die Zahlen zurueck.

    python3 scripts/stamp_pages.py
    python3 scripts/stamp_pages.py --selftest
"""

import datetime
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# seite, dann je element-id das startdatum, ab dem gezaehlt wird.
# die ids stehen im html, sie sind der anker. wer im html eine id
# umbenennt, muss sie hier mitaendern, sonst faellt es beim lauf auf.
SEITEN = {
    "bitcoin-halving-to-top.html": {
        "d1": "2024-04-20",   # tage seit dem halving
        "d2": "2025-10-06",   # tage seit dem hoch
    },
    "bitcoin-top-to-bottom.html": {
        "d1": "2025-10-06",   # tage seit dem hoch, kasten
        "d2": "2025-10-06",   # dieselbe zahl in der tabelle
    },
}


def heute():
    return datetime.datetime.now(datetime.timezone.utc).date()


def tage(startdatum, bis=None):
    a = datetime.date(*[int(x) for x in startdatum.split("-")])
    return ((bis or heute()) - a).days


def stempeln(html, ids, bis=None):
    """ersetzt den inhalt der genannten id-elemente. liefert text und anzahl."""
    treffer = 0
    fehlend = []
    for kennung, start in ids.items():
        wert = "{:,}".format(tage(start, bis))
        muster = re.compile(r'(id="%s"[^>]*>)([^<]*)(<)' % re.escape(kennung))
        html, n = muster.subn(lambda m: m.group(1) + wert + m.group(3), html)
        if n == 0:
            fehlend.append(kennung)
        treffer += n
    return html, treffer, fehlend


def lauf():
    fehler = 0
    for datei, ids in SEITEN.items():
        pfad = os.path.join(REPO, datei)
        if not os.path.exists(pfad):
            print("  FEHL %-30s datei fehlt" % datei)
            fehler += 1
            continue
        with open(pfad, "r", encoding="utf-8") as fh:
            alt = fh.read()
        neu, treffer, fehlend = stempeln(alt, ids)
        if fehlend:
            # das ist kein schoenheitsfehler. wenn eine id verschwindet,
            # friert die zahl ein und niemand merkt es.
            print("  FEHL %-30s id nicht gefunden %s" % (datei, ", ".join(fehlend)))
            fehler += 1
            continue
        if neu == alt:
            print("  ok   %-30s unveraendert, %d zaehler" % (datei, treffer))
            continue
        with open(pfad, "w", encoding="utf-8") as fh:
            fh.write(neu)
        werte = ", ".join("%s %d" % (k, tage(v)) for k, v in sorted(ids.items()))
        print("  neu  %-30s %s" % (datei, werte))
    return fehler


def selftest():
    schlecht = 0

    def pruefe(name, ist, soll):
        nonlocal schlecht
        if ist != soll:
            schlecht += 1
            print("  FEHL %s\n    ist  %r\n    soll %r" % (name, ist, soll))
        else:
            print("  ok   %s" % name)

    bis = datetime.date(2026, 8, 21)

    pruefe("tage seit dem halving", tage("2024-04-20", bis), 853)
    pruefe("tage seit dem hoch", tage("2025-10-06", bis), 319)

    html = '<div class="v" id="d1">1</div> und <td class="n" id="d2">2</td>'
    neu, treffer, fehlend = stempeln(html, {"d1": "2024-04-20", "d2": "2025-10-06"}, bis)
    pruefe("beide gestempelt", neu,
           '<div class="v" id="d1">853</div> und <td class="n" id="d2">319</td>')
    pruefe("zwei treffer", treffer, 2)
    pruefe("nichts fehlt", fehlend, [])

    # tausendertrennung, ab tag 1000 relevant und das kommt bestimmt
    pruefe("tausendertrennung",
           stempeln('<b id="d1">x</b>', {"d1": "2023-01-01"},
                    datetime.date(2026, 1, 1))[0],
           '<b id="d1">1,096</b>')

    # eine fehlende id muss auffallen, nicht stillschweigend durchgehen
    pruefe("fehlende id faellt auf",
           stempeln('<b id="andere">x</b>', {"d1": "2024-04-20"}, bis)[2], ["d1"])

    # zweimal stempeln aendert nichts mehr
    einmal = stempeln('<b id="d1">x</b>', {"d1": "2024-04-20"}, bis)[0]
    pruefe("zweiter lauf ist ruhig",
           stempeln(einmal, {"d1": "2024-04-20"}, bis)[0], einmal)

    print("%d von 8 faellen falsch" % schlecht)
    return 1 if schlecht else 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    print("pulsehawk seitenstempel")
    print("laufzeitpunkt %s utc\n"
          % datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    fehler = lauf()
    if fehler:
        print("\n%d datei/en nicht gestempelt" % fehler)
        return 1
    print("\nfertig")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
