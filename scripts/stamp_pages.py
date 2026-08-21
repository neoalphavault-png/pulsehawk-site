#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stamp_pages.py, schreibt die taeglichen Zahlen fest in die Seiten.

WARUM ES DAS GIBT
Die Zahlen auf den Datenseiten rechnen im Browser. Fuer jeden Menschen und
fuer Google, das JavaScript ausfuehrt, steht dort immer der richtige Wert.
Im Quelltext selbst stand aber weiter der Wert vom Tag der Auslieferung.

Das war egal, solange nur Google zaehlt. Es ist nicht mehr egal, seit
Antwortmaschinen die Seiten abrufen. Viele davon lesen den rohen Quelltext
und fuehren kein JavaScript aus. Die wuerden bei uns fuer immer dieselbe
Zahl sehen, ausgerechnet bei Seiten, deren ganzer Vorteil darin besteht,
dass ihre Zahl aktuell ist.

ZWEI TEILE, ZWEI QUELLEN
  1. die zwei Zyklusseiten. Ihre Zahlen sind reine Arithmetik aus festen
     Daten, Halving und Zyklushoch. Keine Datenquelle noetig.
  2. die Dominanzseite. Ihre Zahl kommt aus data/market-log.json, das der
     Marktlogger taeglich schreibt.

⚠️ FOLGE, DIE MAN KENNEN MUSS
Fuer alle drei Seiten gilt ab jetzt dasselbe wie fuer index.html im Repo
kaspa-pulse. **Niemals eine alte lokale Kopie hochladen.** Der Bot hat die
Datei seit dem letzten Bearbeiten veraendert.

Nicht gestempelt wird die Balkengeometrie im SVG der Zyklusseite. Die
setzt das Skript im Browser, und wer kein JavaScript ausfuehrt, liest
ohnehin den Text daneben und nicht die Balkenbreite.

    python3 scripts/stamp_pages.py
    python3 scripts/stamp_pages.py --selftest
"""

import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LOG = os.path.join(REPO, "data", "market-log.json")

MONATE = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

HALVING = "2024-04-20"
HOCH = "2025-10-06"

# seite, dann je element-id das startdatum und ein anhaengsel.
# die ids stehen im html, sie sind der anker. wer im html eine id
# umbenennt, muss sie hier mitaendern, sonst faellt es beim lauf auf.
ZYKLUS = {
    "bitcoin-halving-to-top.html": [
        ("d1", HALVING, ""),          # tage seit dem halving
        ("d2", HOCH, ""),             # tage seit dem hoch
    ],
    "bitcoin-top-to-bottom.html": [
        ("d1", HOCH, ""),             # tage seit dem hoch, kasten
        ("d2", HOCH, ""),             # dieselbe zahl in der tabelle
        ("d3", HOCH, " and counting"),  # beschriftung am offenen balken
    ],
}

DOM_SEITE = "bitcoin-dominance.html"


# --- werkzeug --------------------------------------------------------

def heute():
    return datetime.datetime.now(datetime.timezone.utc).date()


def tage(startdatum, bis=None):
    a = datetime.date(*[int(x) for x in startdatum.split("-")])
    return ((bis or heute()) - a).days


def lang(iso):
    t = iso.split("-")
    return "%d %s %s" % (int(t[2]), MONATE[int(t[1]) - 1], t[0])


def geld(n):
    if n >= 1e12:
        return "$%.2fT" % (n / 1e12)
    if n >= 1e9:
        return "$%.0fB" % (n / 1e9)
    return "$%.0f" % n


def setz_text(html, werte):
    """ersetzt den inhalt der genannten id-elemente.
    liefert text, treffer und die ids, die nicht gefunden wurden."""
    treffer = 0
    fehlend = []
    for kennung, wert in werte.items():
        muster = re.compile(r'(id="%s"[^>]*>)([^<]*)(<)' % re.escape(kennung))
        html, n = muster.subn(lambda m: m.group(1) + wert + m.group(3), html)
        if n == 0:
            fehlend.append(kennung)
        treffer += n
    return html, treffer, fehlend


def setz_breite(html, kennung, prozent):
    """setzt die breite eines balkens im style-attribut."""
    muster = re.compile(r'(id="%s"[^>]*style="width:)[^%%"]*(%%)' % re.escape(kennung))
    return muster.subn(lambda m: m.group(1) + ("%.1f" % prozent) + m.group(2), html)


def schreiben(pfad, alt, neu, name, meldung):
    if neu == alt:
        print("  ok   %-30s unveraendert, %s" % (name, meldung))
        return 0
    with open(pfad, "w", encoding="utf-8") as fh:
        fh.write(neu)
    print("  neu  %-30s %s" % (name, meldung))
    return 0


# --- teil 1, die zyklusseiten ----------------------------------------

def lauf_zyklus():
    fehler = 0
    for datei, felder in ZYKLUS.items():
        pfad = os.path.join(REPO, datei)
        if not os.path.exists(pfad):
            print("  FEHL %-30s datei fehlt" % datei)
            fehler += 1
            continue
        with open(pfad, "r", encoding="utf-8") as fh:
            alt = fh.read()
        werte = dict((k, "{:,}".format(tage(start)) + anhang)
                     for k, start, anhang in felder)
        neu, treffer, fehlend = setz_text(alt, werte)
        if fehlend:
            # das ist kein schoenheitsfehler. wenn eine id verschwindet,
            # friert die zahl ein und niemand merkt es.
            print("  FEHL %-30s id nicht gefunden %s" % (datei, ", ".join(fehlend)))
            fehler += 1
            continue
        fehler += schreiben(pfad, alt, neu, datei, "%d zaehler" % treffer)
    return fehler


# --- teil 2, die dominanzseite ---------------------------------------

def neueste_dominanz(rows):
    """letzte zeile mit einem dominanzwert. der backfill hat keine,
    die kommt erst ab dem ersten taeglichen lauf ins log."""
    for r in reversed(rows if isinstance(rows, list) else []):
        if isinstance(r, dict) and isinstance(r.get("btc_dom"), (int, float)):
            return r
    return None


def lauf_dominanz():
    pfad = os.path.join(REPO, DOM_SEITE)
    if not os.path.exists(pfad):
        print("  ok   %-30s nicht vorhanden, uebersprungen" % DOM_SEITE)
        return 0
    if not os.path.exists(LOG):
        print("  FEHL %-30s data/market-log.json fehlt" % DOM_SEITE)
        return 1
    with open(LOG, "r", encoding="utf-8") as fh:
        rows = json.load(fh)
    zeile = neueste_dominanz(rows)
    if not zeile:
        print("  FEHL %-30s kein btc_dom im log" % DOM_SEITE)
        return 1

    dom = float(zeile["btc_dom"])
    werte = {
        "dom": "%.1f%%" % dom,
        "dom2": "%.1f%%" % dom,
        "domdate": lang(zeile["d"]),
        "domdate2": lang(zeile["d"]),
        "legb": "Bitcoin %.1f%%" % dom,
        "legr": "everything else %.1f%%" % (100 - dom),
    }
    if isinstance(zeile.get("total_mcap"), (int, float)):
        werte["mcap"] = geld(zeile["total_mcap"])

    with open(pfad, "r", encoding="utf-8") as fh:
        alt = fh.read()
    neu, _, fehlend = setz_text(alt, werte)
    if fehlend:
        print("  FEHL %-30s id nicht gefunden %s" % (DOM_SEITE, ", ".join(fehlend)))
        return 1
    neu, n1 = setz_breite(neu, "barb", dom)
    neu, n2 = setz_breite(neu, "barr", 100 - dom)
    if not (n1 and n2):
        print("  FEHL %-30s balken nicht gefunden" % DOM_SEITE)
        return 1
    return schreiben(pfad, alt, neu, DOM_SEITE,
                     "%.1f%% vom %s" % (dom, zeile["d"]))


# --- selbsttest ------------------------------------------------------

def selbsttest():
    schlecht = 0

    def pruefe(name, ist, soll):
        nonlocal schlecht
        if ist != soll:
            schlecht += 1
            print("  FEHL %s\n    ist  %r\n    soll %r" % (name, ist, soll))
        else:
            print("  ok   %s" % name)

    bis = datetime.date(2026, 8, 21)
    pruefe("tage seit dem halving", tage(HALVING, bis), 853)
    pruefe("tage seit dem hoch", tage(HOCH, bis), 319)
    pruefe("datum ausgeschrieben", lang("2026-08-21"), "21 August 2026")
    pruefe("billionen", geld(4023456789012), "$4.02T")
    pruefe("milliarden", geld(4023456789), "$4B")

    html = '<b id="d1">x</b> und <td id="d2">y</td> und <i id="d3">z</i>'
    neu, treffer, fehlend = setz_text(html, {"d1": "853", "d2": "319",
                                             "d3": "319 and counting"})
    pruefe("text gestempelt", neu,
           '<b id="d1">853</b> und <td id="d2">319</td> und <i id="d3">319 and counting</i>')
    pruefe("drei treffer", treffer, 3)
    pruefe("nichts fehlt", fehlend, [])
    pruefe("fehlende id faellt auf",
           setz_text('<b id="andere">x</b>', {"d1": "1"})[2], ["d1"])

    einmal = setz_text('<b id="d1">x</b>', {"d1": "853"})[0]
    pruefe("zweiter lauf ist ruhig", setz_text(einmal, {"d1": "853"})[0], einmal)

    bar = '<i class="b" id="barb" style="width:60%"></i>'
    pruefe("balken gestempelt", setz_breite(bar, "barb", 57.34)[0],
           '<i class="b" id="barb" style="width:57.3%"></i>')

    pruefe("neueste dominanz",
           neueste_dominanz([{"d": "2026-08-19", "btc_dom": 57.1},
                             {"d": "2026-08-20", "btc_dom": 57.4},
                             {"d": "2026-08-21", "gld": 400.0}])["d"],
           "2026-08-20")
    pruefe("log ohne dominanz",
           neueste_dominanz([{"d": "2026-05-01", "gld": 1.0}]), None)

    print("%d von 12 faellen falsch" % schlecht)
    return 1 if schlecht else 0


def main(argv):
    if "--selftest" in argv:
        return selbsttest()
    print("pulsehawk seitenstempel")
    print("laufzeitpunkt %s utc\n"
          % datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    fehler = lauf_zyklus() + lauf_dominanz()
    if fehler:
        print("\n%d seite(n) nicht gestempelt" % fehler)
        return 1
    print("\nfertig")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
