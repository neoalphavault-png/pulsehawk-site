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

DREI TEILE, ZWEI QUELLEN
  1. die zwei Zyklusseiten. Ihre Zahlen sind reine Arithmetik aus festen
     Daten, Halving und Zyklushoch. Keine Datenquelle noetig.
  2. die Dominanzseite. Ihre Zahl kommt aus data/market-log.json, das der
     Marktlogger taeglich schreibt.
  3. die Marktseite, seit 22.08.2026. Gold, Aktien und Bitcoin ueber
     dieselben sieben Kalendertage, dazu die Stablecoins und die
     Sektorneigung. Ebenfalls aus data/market-log.json.

⚠️ FOLGE, DIE MAN KENNEN MUSS
Fuer alle vier Seiten gilt ab jetzt dasselbe wie fuer index.html im Repo
kaspa-pulse. **Niemals eine alte lokale Kopie hochladen.** Der Bot hat die
Datei seit dem letzten Bearbeiten veraendert.

Nicht gestempelt wird Geometrie im SVG, also weder die Balkenbreite der
Zyklusseite noch der Linienzug im Diagramm der Marktseite. Die setzt das
Skript im Browser, und wer kein JavaScript ausfuehrt, liest ohnehin den
Text daneben und nicht die Kurve.

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
MARKT_SEITE = "markets.html"

# die drei preisreihen muessen am selben tag alle drei dastehen, sonst
# vergleicht man einen handelstag mit einem wochenende.
DREI = ("gld", "spy", "btc")
SEKTOREN = ("xlk", "xly", "xlu", "xlp")


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


def geld_delta(n):
    """vorzeichenbehaftet und ausgeschrieben, weil ein minuszeichen vor
    einem dollarbetrag in einem fliesstext zu leicht uebersehen wird."""
    v = abs(float(n))
    if v >= 1e9:
        z = "$%.1fB" % (v / 1e9)
    elif v >= 1e6:
        z = "$%.1fM" % (v / 1e6)
    else:
        z = "$%.0f" % v
    return ("minus " if n < 0 else "plus ") + z


def proz(neu, alt):
    p = (float(neu) / float(alt) - 1.0) * 100.0
    return "%s%.2f%%" % ("+" if p >= 0 else "", p)


def versatz(iso, n):
    a = datetime.date(*[int(x) for x in iso.split("-")])
    return (a + datetime.timedelta(days=n)).isoformat()


def _hat(r, keys):
    return isinstance(r, dict) and all(
        isinstance(r.get(k), (int, float)) for k in keys)


def letzte(rows, keys):
    """juengste zeile, die alle verlangten felder wirklich hat."""
    for r in reversed(rows if isinstance(rows, list) else []):
        if _hat(r, keys):
            return r
    return None


def vor(rows, bis, keys):
    """juengste zeile am oder vor einem datum, die alle felder hat.
    faellt der stichtag auf ein wochenende, nimmt sie den freitag."""
    for r in reversed(rows if isinstance(rows, list) else []):
        if _hat(r, keys) and isinstance(r.get("d"), str) and r["d"] <= bis:
            return r
    return None


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


# --- teil 3, die marktseite ------------------------------------------

def markt_werte(rows):
    """rechnet genau das, was das skript im browser rechnet. gibt die
    stempelwerte zurueck, oder None wenn die grundlage fehlt.

    die dopplung mit dem javascript ist bewusst und laesst sich nicht
    vermeiden, weil der rohe quelltext ohne javascript stimmen muss. sie
    ist der grund, warum unten fuer jede zahl ein testfall steht."""
    rows = sorted([r for r in (rows or []) if isinstance(r, dict)
                   and isinstance(r.get("d"), str)], key=lambda r: r["d"])
    neu = letzte(rows, DREI)
    if not neu:
        return None
    alt = vor(rows, versatz(neu["d"], -7), DREI)
    if not alt:
        return None
    werte = {
        "dend": lang(neu["d"]),
        "periodlabel": "%s to %s" % (lang(alt["d"]), lang(neu["d"])),
    }
    for feld, kennung in (("gld", "g7"), ("spy", "s7"), ("btc", "b7")):
        werte[kennung] = proz(neu[feld], alt[feld])
        werte[kennung + "b"] = werte[kennung]

    sn = letzte(rows, ("stables",))
    sa = vor(rows, versatz(sn["d"], -7), ("stables",)) if sn else None
    if sn and sa:
        werte["stab7"] = geld_delta(sn["stables"] - sa["stables"])

    rn = letzte(rows, SEKTOREN)
    ra = vor(rows, versatz(rn["d"], -7), SEKTOREN) if rn else None
    if rn and ra:
        korb = lambda r: (r["xlk"] + r["xly"]) / (r["xlu"] + r["xlp"])
        werte["rot7"] = proz(korb(rn), korb(ra))
    return werte


def lauf_markt():
    pfad = os.path.join(REPO, MARKT_SEITE)
    if not os.path.exists(pfad):
        print("  ok   %-30s nicht vorhanden, uebersprungen" % MARKT_SEITE)
        return 0
    if not os.path.exists(LOG):
        print("  FEHL %-30s data/market-log.json fehlt" % MARKT_SEITE)
        return 1
    with open(LOG, "r", encoding="utf-8") as fh:
        rows = json.load(fh)
    werte = markt_werte(rows)
    if not werte:
        print("  FEHL %-30s keine woche mit gold, aktien und bitcoin" % MARKT_SEITE)
        return 1

    with open(pfad, "r", encoding="utf-8") as fh:
        alt = fh.read()
    neu, _, fehlend = setz_text(alt, werte)
    if fehlend:
        print("  FEHL %-30s id nicht gefunden %s" % (MARKT_SEITE, ", ".join(fehlend)))
        return 1
    return schreiben(pfad, alt, neu, MARKT_SEITE, werte["periodlabel"])


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

    # --- die marktseite ---
    pruefe("prozent mit vorzeichen", proz(110.0, 100.0), "+10.00%")
    pruefe("prozent nach unten", proz(99.0, 100.0), "-1.00%")
    pruefe("geld hoch", geld_delta(1_540_000_000), "plus $1.5B")
    pruefe("geld runter", geld_delta(-212_000_000), "minus $212.0M")
    pruefe("versatz sieben tage", versatz("2026-08-21", -7), "2026-08-14")

    # eine woche mit wochenende drin. der 22. und 23. haben keine kurse,
    # der vergleich muss deshalb auf dem 21. und dem 14. landen.
    log = [
        {"d": "2026-08-14", "gld": 400.0, "spy": 600.0, "btc": 100000.0,
         "stables": 300_000_000_000, "xlk": 280.0, "xly": 220.0,
         "xlu": 80.0, "xlp": 78.0},
        {"d": "2026-08-15", "btc": 101000.0, "stables": 300_100_000_000},
        {"d": "2026-08-21", "gld": 412.0, "spy": 594.0, "btc": 110000.0,
         "stables": 301_500_000_000, "xlk": 290.0, "xly": 220.0,
         "xlu": 80.0, "xlp": 78.0},
        {"d": "2026-08-22", "btc": 111000.0, "stables": 301_600_000_000},
    ]
    w = markt_werte(log)
    pruefe("gold ueber die woche", w["g7"], "+3.00%")
    pruefe("aktien ueber die woche", w["s7"], "-1.00%")
    pruefe("bitcoin ueber die woche", w["b7"], "+10.00%")
    pruefe("grosse zahl gleich kleiner", w["b7b"], w["b7"])
    pruefe("bezugspunkt in der beschriftung", w["periodlabel"],
           "14 August 2026 to 21 August 2026")
    pruefe("enddatum", w["dend"], "21 August 2026")
    # stablecoins laufen sieben tage die woche, ihre spanne endet am 22.
    pruefe("stablecoins eigene spanne", w["stab7"], "plus $1.5B")
    # zyklisch 500 auf 510 bei unveraendert defensiv, also glatte zwei prozent
    pruefe("sektorneigung", w["rot7"], "+2.00%")

    # ohne eine zweite woche gibt es nichts zu vergleichen, und dann wird
    # nichts gestempelt statt irgendetwas gestempelt
    pruefe("zu kurzes log",
           markt_werte([{"d": "2026-08-21", "gld": 1.0, "spy": 1.0, "btc": 1.0}]),
           None)
    pruefe("leeres log", markt_werte([]), None)

    print("%d von 26 faellen falsch" % schlecht)
    return 1 if schlecht else 0


def main(argv):
    if "--selftest" in argv:
        return selbsttest()
    print("pulsehawk seitenstempel")
    print("laufzeitpunkt %s utc\n"
          % datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    fehler = lauf_zyklus() + lauf_dominanz() + lauf_markt()
    if fehler:
        print("\n%d seite(n) nicht gestempelt" % fehler)
        return 1
    print("\nfertig")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
