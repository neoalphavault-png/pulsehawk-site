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

SECHS TEILE, DREI QUELLEN
  1. die Zyklusseiten. Ihre Tageszaehler sind reine Arithmetik aus festen
     Daten, Halving und Zyklushoch. Keine Datenquelle noetig.
  2. die Dominanzseite. Ihre Zahl kommt aus data/market-log.json, das der
     Marktlogger taeglich schreibt.
  3. die Menueleiste, seit 22.08.2026. Sie steht nur noch an einer Stelle,
     in der Liste SEITEN weiter unten. Der Bot schreibt sie in jede Seite,
     also kostet ein neuer Menuepunkt eine Zeile und keine vier Uploads.
  4. die Marktseite, seit 22.08.2026. Gold, Aktien und Bitcoin ueber
     dieselben sieben Kalendertage, dazu die Stablecoins und die
     Sektorneigung. Ebenfalls aus data/market-log.json.
  5. der letzte Bitcoin-Schluss auf den Zyklusseiten, seit 16.09.2026.
     Die beiden Zeilen

         var LAST_CLOSE = 75608, LAST_DATE = "2026-09-15";

     in bitcoin-top-to-bottom.html sind die Grundlage fuer jede
     Rueckgangszahl auf der Seite. Sie standen bis jetzt von Hand da, und
     einmal von Hand heisst irgendwann veraltet. Sie kommen aus derselben
     Datei wie alles andere, data/market-log.json, aus der juengsten Zeile
     mit einem btc-Wert. Hier wird bewusst nicht in ein Element gestempelt,
     sondern in den Code: das Skript auf der Seite rechnet mit diesen
     Werten weiter, ein gestempeltes Element waere nur die Anzeige.
     Seit 22.09.2026 gilt dasselbe fuer bitcoin-drawdown.html, die
     zusaetzlich LOW_CLOSE und LOW_DATE traegt.
  6. die Rueckgangszahlen auf beiden Zyklusseiten, seit 22.09.2026. Das
     ist der eine Teil, der data/history.json liest, denn das tiefste
     Niveau eines Zyklus steht nicht im Log, das nur ein halbes Jahr
     zurueckreicht. Der Lauf prueft dabei, ob das Archiv dasselbe
     Zyklushoch kennt wie die Seiten, und bleibt stehen, wenn nicht.

⚠️ FOLGE, DIE MAN KENNEN MUSS
Fuer alle fuenf Seiten gilt ab jetzt dasselbe wie fuer index.html im Repo
kaspa-pulse. **Niemals eine alte lokale Kopie hochladen.** Der Bot hat die
Datei seit dem letzten Bearbeiten veraendert.

Nicht gestempelt wird Geometrie im SVG, also weder die Balkenbreite der
Zyklusseite noch der Linienzug im Diagramm der Marktseite. Die setzt das
Skript im Browser, und wer kein JavaScript ausfuehrt, liest ohnehin den
Text daneben und nicht die Kurve.

    python3 scripts/stamp_pages.py
    python3 scripts/stamp_pages.py --selftest
"""

import calendar
import datetime
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# Die Vorrangregel steht genau einmal, dort. Bricht dieser Import, faellt
# der Lauf laut aus, und das ist gewollt: lieber ein roter Stempellauf als
# eine zweite Kopie der Regel, die leise auseinanderlaeuft.
from market_log import reihe_mit_logvorrang  # noqa: E402

REPO = os.path.dirname(HERE)
LOG = os.path.join(REPO, "data", "market-log.json")
ARCHIV = os.path.join(REPO, "data", "history.json")

MONATE = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

HALVING = "2024-04-20"

# EIN HOCH FUER DIE GANZE SEITE: DER TAGESSCHLUSS
# Bis zum 16.09.2026 gab es hier zwei Lesarten. Die Halving-Seite zaehlte zum
# INTRADAY-Hoch 126.198 am 6. Oktober 2025, die Top-to-Bottom-Seite zum
# TAGESSCHLUSS 124.776,68 am 7. Oktober. Zwei Seiten desselben Hauses, zwei
# Antworten auf dieselbe Frage, und eine davon widersprach der eigenen FAQ
# der anderen ("jede hoehere Zahl vom 6. Oktober ist ein Intraday-Hoch einer
# einzelnen Boerse").
#
# Bens Entscheidung vom 16.09.2026: eine Definition, und zwar der hoechste
# TAGESSCHLUSS in UTC. Der gilt jetzt auf beiden Seiten. Die Halving-Seite
# zaehlt damit 535 Tage vom Halving zum Hoch statt 534, und ihre Tabelle ist
# in sich stimmig, weil die drei abgeschlossenen Zyklen ohnehin schon
# Tagesschluesse waren.
# UMDATIERT AM 22.09.2026
# Die Bitcoinreihe im Archiv kam von blockchain.com und war um einen Tag
# zu spaet gestempelt, siehe bc_tag() in scripts/history.py. Gemessen an
# der Naht zum taeglichen Log: gld und spy stimmten auf den Tag genau,
# btc nicht. Bens Entscheidung vom 22.09.2026: die Reihe einen Tag
# zurueck. Aus dem 07.10.2025 wird damit der 06.10.2025, aus dem Tief vom
# 01.07.2026 der 30.06.2026.
#
# Was sich dadurch NICHT aendert: kein Preis, kein Prozentwert und keine
# Tagesspanne. Hoch und Tief wandern gemeinsam, also bleiben 406, 364 und
# 378 Tage stehen und ebenso die Drawdowns. Nur die gedruckten Daten
# ruecken um einen Tag.
#
# Vom Halving zum Hoch sind es damit wieder 534 Tage statt 535. Das ist
# dieselbe Zahl, die die Halving-Seite vor dem 16.09.2026 hatte, und
# diesmal steht das richtige Datum dahinter statt des Intraday-Hochs.
HOCH_CLOSE = "2025-10-06"    # hoechster Tagespreis, UTC, beide Zyklusseiten
HOCH = HOCH_CLOSE            # alter Name, damit nichts still bricht

# Der Preis zu diesem Tag. Er steht hier nicht, damit man ihn glauben muss,
# sondern damit der Lauf ihn gegen data/history.json pruefen kann. Weicht das
# Archiv ab, faellt der Lauf durch, statt eine falsche Zahl zu stempeln.
HOCH_WERT = 124776.68

# seite, dann je element-id das startdatum und ein anhaengsel.
# die ids stehen im html, sie sind der anker. wer im html eine id
# umbenennt, muss sie hier mitaendern, sonst faellt es beim lauf auf.
# seiten, die ihren bezugstag ausgeschrieben zeigen, und die id dafuer
ZYKLUS_ASOF = {"bitcoin-halving-to-top.html": "hvasof"}

ZYKLUS = {
    "bitcoin-halving-to-top.html": [
        ("d1", HALVING, ""),              # tage seit dem halving
        ("d2", HOCH_CLOSE, ""),           # tage seit dem schlusshoch
    ],
    "bitcoin-top-to-bottom.html": [
        ("d1", HOCH_CLOSE, ""),           # tage seit dem schlusshoch, kasten
        ("d2", HOCH_CLOSE, ""),           # dieselbe zahl in der tabelle
        ("d3", HOCH_CLOSE, " and counting"),  # beschriftung am offenen balken
    ],
}

DOM_SEITE = "bitcoin-dominance.html"
MARKT_SEITE = "markets.html"
DD_SEITE = "bitcoin-drawdown.html"
BL_SEITE = "bitcoin-bull-run-length.html"
GOLD_SEITE = "gold-in-bitcoin-bear-markets.html"
WI_SEITE = "what-if.html"

# WHAT-IF, DIE VOREINGESTELLTE ANSICHT
# Die Seite rechnet auf Eingaben, aber im Quelltext kann nur EINE Ansicht
# stehen: die, die ein Besucher ohne Klick sieht. Genau die stand bis zum
# 24.09.2026 als "loading" da, also existierte die Seite fuer
# Antwortmaschinen nicht. Diese Werte sind die Voreinstellungen der drei
# Eingabefelder; wer sie im HTML aendert, muss sie hier mitaendern, und
# der Selbsttest liest beide gegeneinander.
WI_LUMP = ("btc", 1000.0, 5)          # betrag, anlage, jahre
WI_DCA = ("spy", 200.0, 5)            # monatlich
WI_DAY = (8.0, 10, "a pack of cigarettes")

# EIN HEUTE FUER ALLE ZYKLUSSEITEN, SEIT 24.09.2026
# Jede Zyklusseite mit einem Preis rechnet auf einen juengsten Tag. Wenn
# zwei Seiten verschiedene Tage tragen, sieht ein Leser, der zwischen
# ihnen wechselt, zwei verschiedene "heute", und keine der beiden Zahlen
# ist falsch genug, dass es auffiele. Genau das war am 24.09.2026 der
# Fall: die Goldseite rechnete auf den Archivrand (22.09.), die drei
# anderen auf den Marktlog (23.09.), weil das Archiv nur sonntags
# nachgezogen wird.
#
# Jeder Teil traegt seinen Stichtag hier ein, und lauf_stichtag() am Ende
# haelt den Lauf an, wenn sie auseinanderlaufen.
#
# bitcoin-halving-to-top.html steht bewusst NICHT drin: die Seite zeigt
# keinen Preis, ihre beiden Zaehler sind reine Datumsarithmetik.
STICHTAG = {}      # datei -> tag des juengsten PREISES
ZAEHLTAG = {}      # datei -> tag, gegen den die TAGESZAEHLER rechnen

# Die Halving-Seite zeigt keinen Preis, aber ihre beiden Zaehler rechnen
# gegen heute, und das ist genauso ein Stichtag. Faellt ihr Stempel aus,
# zeigt sie stillschweigend gestern, waehrend die anderen heute zeigen:
# derselbe Fehler, nur in Tagen statt in Dollar. Sie muss ihren Bezugstag
# deshalb sichtbar nennen, sonst ist ein eingefrorener Zaehler von aussen
# ueberhaupt nicht zu erkennen.
NENNT_ZAEHLTAG = ("bitcoin-halving-to-top.html",)

# Der taegliche DAY-N-Post ist keine Seite, gehoert aber seit dem
# 24.09.2026 in dieselbe Zaehltag-Gruppe: er zaehlt bis heute, wie die
# Seiten. Er steht hier mit drin, damit die Gruppe vollstaendig ist und
# eine kuenftige Aenderung an einer der beiden Seiten sichtbar wird.
# Durchgesetzt wird der Gleichstand nicht hier, sondern in day_n_post.py:
# Sperre 5 liest den gestempelten Zaehler d1 der Seite und postet nicht,
# wenn er von der eigenen Zahl abweicht.
ZAEHLTAG_MIT = ("dayn.yml",)


# ---------------------------------------------------------------------------
# EINE QUELLE FUER "HEUTE", REGEL VOM 24.09.2026
#
# Es gibt zwei Dateien mit Preisen, und sie sind verschieden alt:
#   data/market-log.json   taeglich 21:23 UTC
#   data/history.json      nur sonntags, unter der woche bis zu 6 tage alt
#
# Der rechte Rand jeder LAUFENDEN Zahl kommt IMMER aus dem Marktlog.
# history.json liefert Historie, nie den aktuellen Wert. Wer das dreht,
# baut ein zweites "heute", und keine der beiden Zahlen ist falsch genug,
# dass es auffiele. Genau so ist der Fehler der Goldseite entstanden.
#
# mit_rand() ist die eine erlaubte Mischung: das Archiv gewinnt fuer jeden
# Tag, den es hat, das Log haengt nur hinten an. Das ist fuer ein Minimum
# ueber den ganzen Zyklus richtig und beruehrt den rechten Rand nicht.
# ---------------------------------------------------------------------------

# KOPF-WACHE, AUSNAHMEN
# Was der Stempel in den Rumpf schreibt, darf nicht zusaetzlich im <head>
# stehen: dorthin kommt setz_text nicht, der Wert friert also ein. Die
# Ausnahmen unten sind bewusst gesetzte Dopplungen, keine Versehen. Es sind
# durchweg ABGESCHLOSSENE Werte, die sich nur aendern, wenn das Archiv
# selbst korrigiert wird. Passiert das, ist diese Liste die Stelle, an der
# man nachsieht.
#
# Nicht auf dieser Liste stehen und deshalb am 24.09.2026 aus den Koepfen
# entfernt wurden: das Zyklustief der Drawdownseite (faellt Bitcoin
# tiefer, wandert es) und das Datum der Goldspitze (wandert bei einem
# neuen Hoch). Beide waren schon eingefroren, nur hatte es niemand gesehen.
KOPF_AUSNAHMEN = {
    "bitcoin-bull-run-length.html": ("blrange2", "blspread", "blfaq"),
    "gold-in-bitcoin-bear-markets.html": (
        "b1btc", "b1gld", "b1spy", "b2btc", "b2gld", "b2spy",
        "b3btc", "b3gld", "b3spy", "gldspread", "spyspread", "gworst"),
}
# Beide Seiten rechnen im Browser mit LAST_CLOSE weiter, also wird in beide
# gestempelt. Die Drawdownseite hat zusaetzlich LOW_CLOSE und LOW_DATE.
SCHLUSS_SEITEN = ("bitcoin-top-to-bottom.html", DD_SEITE, BL_SEITE)
# Seiten, die zusaetzlich LOW_CLOSE/LOW_DATE tragen, also das Tief
# dieses Zyklus im Skript weiterrechnen.
TIEF_SEITEN = (DD_SEITE, BL_SEITE)
SCHLUSS_SEITE = SCHLUSS_SEITEN[0]   # alter Name, damit nichts still bricht

# die zwei Zuweisungen werden einzeln ersetzt, nicht die ganze Zeile. wer
# die Zeile umbricht oder eine dritte Variable dazuschreibt, verliert sonst
# beim naechsten Lauf, was er geschrieben hat.
RE_CLOSE = re.compile(r"(var LAST_CLOSE\s*=\s*)([0-9][0-9_.]*)")
RE_DATE = re.compile(r"(LAST_DATE\s*=\s*\")(\d{4}-\d{2}-\d{2})(\")")
RE_LOW = re.compile(r"(var LOW_CLOSE\s*=\s*)([0-9][0-9_.]*)")
RE_LOWDATE = re.compile(r"(LOW_DATE\s*=\s*\")(\d{4}-\d{2}-\d{2})(\")")

# EINE LISTE, EINE WAHRHEIT
# Wer hier eine Seite eintraegt, hat sie in der Leiste jeder anderen Seite.
# Der Bot schreibt den Inhalt von <div class="pnav"> bei jedem Lauf neu und
# markiert dabei die Seite, auf der man gerade steht. Damit muss niemand
# mehr vier Dateien anfassen, um einen Menuepunkt zu ergaenzen.
# Reihenfolge hier ist Reihenfolge auf der Seite.
SEITEN = [
    ("bitcoin-halving-to-top.html", "halving to top"),
    ("bitcoin-top-to-bottom.html", "top to bottom"),
    ("bitcoin-drawdown.html", "drawdown"),
    # "bull run length" auf "bull run" gekuerzt und die goldseite nur
    # "gold" genannt: bei fuenf zyklusseiten soll die leiste nicht
    # weiter wachsen. die hub-seite ist beschlossen und ein eigener
    # auftrag, bis dahin traegt die leiste alles.
    ("bitcoin-bull-run-length.html", "bull run"),
    ("gold-in-bitcoin-bear-markets.html", "gold"),
    ("bitcoin-dominance.html", "dominance"),
    ("markets.html", "markets"),
    ("what-if.html", "what if"),
]

# die drei preisreihen muessen am selben tag alle drei dastehen, sonst
# vergleicht man einen handelstag mit einem wochenende.
# Die drei abgeschlossenen Zyklen, Hoch und Element-id auf der
# Top-to-Bottom-Seite. CYC_LEN ist die Laenge der Reihen im Seitenskript;
# der Stempel muss genauso abschneiden, sonst weicht er ab Tag 451 ab.
VORZYKLEN = (("c13", "2013-12-04"), ("c17", "2017-12-16"), ("c21", "2021-11-08"))

# DIE VIER ZYKLEN ALS PAARE, SEIT 23.09.2026
# Tief und darauffolgendes Hoch. Dieselben acht Eckpunkte, die auch die
# anderen drei Zyklusseiten benutzen; sie stehen hier, damit die
# Bullenseite nicht ihre eigene Lesart erfindet. Das letzte Paar ist offen,
# sein Hoch ist noch nicht gelaufen.
#
# ⚠️ Das Tief 2026-06-30 ist das tiefste bisher, kein bestaetigter Boden.
# Faellt Bitcoin tiefer, zieht der Lauf es aus dem Archiv nach und die
# Seite zaehlt ab dem neuen Tag. Genau deshalb steht auf der Seite
# ueberall "if that low holds" daneben.
ZYKLEN = (("2015-01-14", "2017-12-16"),
          ("2018-12-15", "2021-11-08"),
          ("2022-11-21", HOCH_CLOSE))

# DIE DREI ABGESCHLOSSENEN BAERMAERKTE, fuer die Goldseite.
# Hoch, Tief, Vorsilbe der Element-ids. Der laufende kommt nicht aus
# dieser Liste, sein Tief holt der Lauf aus dem Archiv, damit die Seite
# nachzieht, wenn Bitcoin tiefer faellt.
BAERFENSTER = (("2013-12-04", "2015-01-14", "b1"),
               ("2017-12-16", "2018-12-15", "b2"),
               ("2021-11-08", "2022-11-21", "b3"))
CYC_LEN = 451

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


def als_datum(iso):
    return datetime.date(*[int(x) for x in iso.split("-")])


def kurz(iso):
    """4 Dec 2013, die kurzform in den tabellenzellen."""
    t = iso.split("-")
    return "%d %s %s" % (int(t[2]), MONATE[int(t[1]) - 1][:3], t[0])


def proz1(wert, bezug):
    """eine nachkommastelle, vorzeichen nur wenn negativ. genau das, was
    toFixed(1) im seitenskript liefert."""
    return "%.1f%%" % ((float(wert) / float(bezug) - 1.0) * 100.0)


def dollar(v):
    """ganze dollar mit tausendertrenner, wie Math.round(v).toLocaleString
    im seitenskript. gerundet wird wie in javascript, also die halbe stelle
    nach oben und nicht zur geraden zahl."""
    return "{:,}".format(int(float(v) + 0.5))


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
        if datei in ZYKLUS_ASOF:
            werte[ZYKLUS_ASOF[datei]] = lang(heute().isoformat())
        neu, treffer, fehlend = setz_text(alt, werte)
        if fehlend:
            # das ist kein schoenheitsfehler. wenn eine id verschwindet,
            # friert die zahl ein und niemand merkt es.
            print("  FEHL %-30s id nicht gefunden %s" % (datei, ", ".join(fehlend)))
            fehler += 1
            continue
        ko = kopf_funde(datei, neu, werte)
        if ko:
            print("  FEHL %-30s %s" % (datei, "; ".join(ko)))
            fehler += 1
            continue
        ZAEHLTAG[datei] = heute().isoformat()
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
    ko = kopf_funde(DOM_SEITE, neu, werte)
    if ko:
        print("  FEHL %-30s %s" % (DOM_SEITE, "; ".join(ko)))
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
    # die drei beschriftungen des diagramms. das skript setzt sie aus
    # derselben reihe, also aus den log-zeilen mit allen drei preisen.
    # geometrie wird weiter nicht gestempelt, aber ein datum ist keine
    # geometrie, und im quelltext stand dort "today" und "start of record".
    mitdrei = [r for r in rows if _hat(r, DREI)]
    werte = {
        "dend": lang(neu["d"]),
        "periodlabel": "%s to %s" % (lang(alt["d"]), lang(neu["d"])),
        "chstart": lang(mitdrei[0]["d"]),
        "chend": lang(mitdrei[-1]["d"]),
        "chartperiod": "since " + lang(mitdrei[0]["d"]),
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
    ko = kopf_funde(MARKT_SEITE, neu, werte)
    if ko:
        print("  FEHL %-30s %s" % (MARKT_SEITE, "; ".join(ko)))
        return 1
    return schreiben(pfad, alt, neu, MARKT_SEITE, werte["periodlabel"])


# --- teil 5, der letzte schluss --------------------------------------

def letzter_schluss(rows):
    """juengste zeile mit einem btc-schluss. der marktlogger schreibt btc
    auch am wochenende (coingecko/kraken laufen durch), gold und aktien
    nicht. deshalb wird hier nur btc verlangt und nicht die dreiergruppe."""
    return letzte(rows if isinstance(rows, list) else [], ("btc",))


def zahl(v):
    """ganze dollar bleiben ganz, sonst zwei stellen. javascript liest
    beides, aber ein 75608.0 im quelltext sieht nach zufall aus."""
    f = float(v)
    return str(int(round(f))) if abs(f - round(f)) < 0.005 else ("%.2f" % f)


def setz_schluss(html, close, datum):
    """ersetzt die beiden zuweisungen. liefert text und trefferzahl."""
    html, n1 = RE_CLOSE.subn(lambda m: m.group(1) + zahl(close), html)
    html, n2 = RE_DATE.subn(lambda m: m.group(1) + datum + m.group(3), html)
    return html, n1, n2


def setz_tief(html, close, datum):
    """dasselbe fuer LOW_CLOSE/LOW_DATE auf der drawdownseite."""
    html, n1 = RE_LOW.subn(lambda m: m.group(1) + zahl(close), html)
    html, n2 = RE_LOWDATE.subn(lambda m: m.group(1) + datum + m.group(3), html)
    return html, n1, n2


def lauf_schluss():
    if not os.path.exists(LOG):
        print("  FEHL %-30s data/market-log.json fehlt" % SCHLUSS_SEITE)
        return 1
    with open(LOG, "r", encoding="utf-8") as fh:
        rows = json.load(fh)
    zeile = letzter_schluss(rows)
    if not zeile:
        print("  FEHL %-30s kein btc-schluss im log" % SCHLUSS_SEITE)
        return 1

    # das tief kommt aus dem archiv, nicht aus dem log. der rand des logs
    # kommt nur dazu, falls das archiv aelter ist als das tief.
    tief = None
    if os.path.exists(ARCHIV):
        with open(ARCHIV, "r", encoding="utf-8") as fh:
            tief = tief_nach(mit_rand(archiv_reihe(json.load(fh)), rows), HOCH_CLOSE)

    fehler = 0
    for datei in SCHLUSS_SEITEN:
        pfad = os.path.join(REPO, datei)
        if not os.path.exists(pfad):
            print("  ok   %-30s nicht vorhanden, uebersprungen" % datei)
            continue
        with open(pfad, "r", encoding="utf-8") as fh:
            alt = fh.read()
        neu, n1, n2 = setz_schluss(alt, zeile["btc"], zeile["d"])
        if not (n1 and n2):
            # ohne die beiden zuweisungen friert der rueckgang auf der seite
            # ein, und das sieht niemand, weil die tageszahl daneben weiterlaeuft
            print("  FEHL %-30s LAST_CLOSE/LAST_DATE nicht gefunden (%d/%d)"
                  % (datei, n1, n2))
            fehler += 1
            continue
        STICHTAG[datei] = zeile["d"]
        meldung = "letzter schluss %s vom %s" % (zahl(zeile["btc"]), zeile["d"])
        if datei in TIEF_SEITEN:
            if not tief:
                print("  FEHL %-30s kein tief aus dem archiv" % datei)
                fehler += 1
                continue
            neu, m1, m2 = setz_tief(neu, tief[1], tief[0])
            if not (m1 and m2):
                print("  FEHL %-30s LOW_CLOSE/LOW_DATE nicht gefunden (%d/%d)"
                      % (datei, m1, m2))
                fehler += 1
                continue
            meldung += ", tief %s vom %s" % (zahl(tief[1]), tief[0])
        fehler += schreiben(pfad, alt, neu, datei, meldung)
    return fehler


# --- teil 6, die rueckgangszahlen ------------------------------------
#
# WARUM ES DAS SEIT 22.09.2026 GIBT
# Die Top-to-Bottom-Seite stempelte bis dahin ihre Tageszaehler und die
# beiden Variablen LAST_CLOSE/LAST_DATE, aber nicht den Rueckgang daneben.
# Der rechnete nur im Browser. Im Quelltext stand deshalb "-39.4%, price of
# 15 September 2026", waehrend zwei Zeilen tiefer das gestempelte
# LAST_CLOSE schon den 22. September trug. Die Vergleichszellen c13, c17
# und c21 standen sogar voellig leer da. Fuer eine Antwortmaschine, die
# kein JavaScript ausfuehrt, war die Seite damit falsch, und zwar genau an
# der Zahl, um die es geht.
#
# Ab jetzt gilt: was das Seitenskript setzt, wird auch gestempelt. Die
# Dopplung zwischen hier und dem Skript ist unvermeidlich und der Grund,
# warum unten fuer jede Zahl ein Testfall steht.

def archiv_reihe(rows):
    """archiv als sortierte liste (tag, preis), nur zeilen mit btc."""
    return sorted((r["d"], float(r["btc"])) for r in (rows or [])
                  if isinstance(r, dict) and isinstance(r.get("d"), str)
                  and isinstance(r.get("btc"), (int, float)))


def mit_rand(reihe, logrows):
    """das archiv, dazu die tage nach seinem rand, die nur im log stehen.

    das archiv endet dort, wo der letzte backfill lief, der taegliche
    logger laeuft weiter. fuer ein tief ueber den ganzen zyklus muss
    beides dastehen, sonst uebersieht die seite ein tief, das nach dem
    letzten backfill entstanden ist. fuer denselben tag werden die reihen
    nie gemischt, das archiv gewinnt ueberall, wo es etwas hat."""
    if not reihe:
        return []
    rand = reihe[-1][0]
    zu = sorted((r["d"], float(r["btc"])) for r in (logrows or [])
                if isinstance(r, dict) and isinstance(r.get("d"), str)
                and isinstance(r.get("btc"), (int, float)) and r["d"] > rand)
    return list(reihe) + zu


def hoch_seit(reihe, ab):
    """hoechster preis am oder nach einem stichtag."""
    kand = [p for p in reihe if p[0] >= ab]
    return max(kand, key=lambda p: p[1]) if kand else None


def tief_nach(reihe, tag):
    """tiefster preis nach einem stichtag."""
    kand = [p for p in reihe if p[0] > tag]
    return min(kand, key=lambda p: p[1]) if kand else None


def am_oder_vor(reihe, tag):
    """der preis an einem tag, sonst der letzte davor."""
    tref = None
    for d, v in reihe:
        if d > tag:
            break
        tref = (d, v)
    return tref


def rueckgang_werte(archivrows, logrows, bis=None):
    """rechnet, was die beiden zyklusseiten im browser rechnen.
    liefert (werte je seite, None) oder (None, grund)."""
    reihe = archiv_reihe(archivrows)
    if not reihe:
        return None, "kein btc im archiv"
    hoch = hoch_seit(reihe, HALVING)
    if not hoch:
        return None, "kein preis nach dem halving im archiv"
    # Das Hoch ist eine getroffene Entscheidung, keine Laufzeitfrage. Sagt
    # das Archiv etwas anderes, ist eine der beiden Seiten falsch, und dann
    # soll der Lauf stehenbleiben statt zu raten.
    if hoch[0] != HOCH_CLOSE or abs(hoch[1] - HOCH_WERT) > 0.005:
        return None, ("archiv sagt hoch %s %.2f, die seiten sagen %s %.2f"
                      % (hoch[0], hoch[1], HOCH_CLOSE, HOCH_WERT))
    tief = tief_nach(mit_rand(reihe, logrows), HOCH_CLOSE)
    if not tief:
        return None, "kein preis nach dem hoch"
    jetzt = letzter_schluss(logrows)
    if not jetzt:
        return None, "kein btc-schluss im log"

    n = tage(HOCH_CLOSE, bis)
    if n <= 0:
        return None, "das hoch liegt nicht in der vergangenheit"
    ntxt = "{:,}".format(n)
    tieftag = tage(HOCH_CLOSE, als_datum(tief[0]))
    tieftxt = "{:,}".format(tieftag)
    jetztproz = proz1(jetzt["btc"], HOCH_WERT)
    tiefproz = proz1(tief[1], HOCH_WERT)
    jetztquelle = "%s, %s USD" % (lang(jetzt["d"]), dollar(jetzt["btc"]))

    dd = {
        "ddnow": jetztproz, "ddlead": jetztproz,
        "ddtoday2": jetztproz, "ddfaq": jetztproz,
        "ddnowsrc": "price of " + jetztquelle,
        "ddday": ntxt,
        "ddlowpct": tiefproz, "ddfaq2": tiefproz, "r25dd": tiefproz,
        "ddlowsrc": "%s, %s USD" % (lang(tief[0]), dollar(tief[1])),
        "ddlowday": tieftxt, "r25days": tieftxt, "ddfaq4": tieftxt,
        "ddfaq3": lang(tief[0]),
        "ddleadlow": tieftxt + " days",
        "r25low": "%s, %s" % (kurz(tief[0]), dollar(tief[1])),
        "ddbarlbl": tiefproz + " so far",
    }

    ttb = {
        "dd": jetztproz, "dd2": jetztproz, "c25": jetztproz,
        "ddts": "price of " + jetztquelle,
        "c25d": kurz(jetzt["d"]),
    }
    # die drei vergleichszeilen: wo stand jeder alte zyklus am selben tag.
    # das seitenskript liest dafuer die reihe CYC, die auf drei stellen
    # gerundet ist. hier wird genauso gerundet, sonst weicht die gestempelte
    # zahl in der letzten stelle von der angezeigten ab.
    preis = dict(reihe)
    for kennung, top in VORZYKLEN:
        if top not in preis:
            return None, "zyklushoch %s fehlt im archiv" % top
        j = min(n, CYC_LEN - 1)
        ziel = versatz(top, j)
        tref = am_oder_vor(reihe, ziel)
        if not tref:
            return None, "kein preis am oder vor %s" % ziel
        r = round(tref[1] / preis[top], 3)
        ttb[kennung] = "%.1f%%" % ((r - 1.0) * 100.0)
        ttb[kennung + "d"] = kurz(ziel)
    return {DD_SEITE: dd, "bitcoin-top-to-bottom.html": ttb}, None


def lauf_rueckgang():
    if not os.path.exists(ARCHIV):
        print("  FEHL %-30s data/history.json fehlt" % DD_SEITE)
        return 1
    if not os.path.exists(LOG):
        print("  FEHL %-30s data/market-log.json fehlt" % DD_SEITE)
        return 1
    with open(ARCHIV, "r", encoding="utf-8") as fh:
        archivrows = json.load(fh)
    with open(LOG, "r", encoding="utf-8") as fh:
        logrows = json.load(fh)
    werte, grund = rueckgang_werte(archivrows, logrows)
    if werte is None:
        print("  FEHL %-30s %s" % (DD_SEITE, grund))
        return 1

    fehler = 0
    for datei, felder in sorted(werte.items()):
        pfad = os.path.join(REPO, datei)
        if not os.path.exists(pfad):
            print("  ok   %-30s nicht vorhanden, uebersprungen" % datei)
            continue
        with open(pfad, "r", encoding="utf-8") as fh:
            alt = fh.read()
        neu, treffer, fehlend = setz_text(alt, felder)
        if fehlend:
            print("  FEHL %-30s id nicht gefunden %s" % (datei, ", ".join(fehlend)))
            fehler += 1
            continue
        ko = kopf_funde(datei, neu, felder)
        if ko:
            print("  FEHL %-30s %s" % (datei, "; ".join(ko)))
            fehler += 1
            continue
        ZAEHLTAG[datei] = heute().isoformat()
        fehler += schreiben(pfad, alt, neu, datei,
                            "%d rueckgangszahlen, heute %s"
                            % (treffer, felder.get("ddnow") or felder.get("dd")))
    return fehler


# --- teil 7, die bullenseite -----------------------------------------
#
# Spiegelbild von Teil 6: dort der Weg vom Hoch nach unten, hier der vom
# Tief nach oben. Die Eckpunkte sind dieselben, nur anders gepaart, und
# der Lauf prueft sie gegen das Archiv, statt sie zu glauben.

def proz0(wert, bezug):
    """ganze prozent mit vorzeichen, wie Math.round im seitenskript.

    math.floor(p + 0.5) ist Math.round, Stelle fuer Stelle: beide runden die
    halbe Stelle nach OBEN, also -47,5 auf -47 und nicht auf -48. Ein
    int(p - 0.5) fuer negative Werte waere eine Stelle daneben. Hier faellt
    das nicht auf, weil der Anstieg ueber einem Tief nie negativ wird, aber
    die Funktion soll auch dann stimmen, wenn sie jemand anders benutzt."""
    p = (float(wert) / float(bezug) - 1.0) * 100.0
    return ("+" if p >= 0 else "") + "{:,}".format(int(math.floor(p + 0.5)))


# ZWEI WACHEN FUER DIE BULLENSEITE, SEIT 23.09.2026
#
# 1. DIE ABGESCHLOSSENEN ANSTIEGE
# Sie stehen als Text auf der Seite, an vier Stellen: Tabelle, Fliesstext,
# FAQ und FAQPage-JSON-LD. Gestempelt werden sie nicht, weil sie sich nie
# mehr aendern. Genau deshalb ist ein Tippfehler dort unsichtbar, und genau
# das ist am 23.09.2026 passiert: 67562,17 / 3231,91 sind 1990,47 Prozent,
# auf eine Stelle 1990,5, und daraus wurde von Hand 1991 statt 1990. Zweimal
# gerundet ist einmal zu oft. Der Lauf rechnet die drei jetzt selbst nach
# und bleibt stehen, wenn eine davon nicht wortgleich auf der Seite steht.
#
# 2. KEIN ABGELEITETES DATUM
# Die Seite darf aus 1050 Tagen kein Zieldatum machen, auch nicht als
# Rechenbeispiel, auch nicht in der FAQ, auch nicht im JSON-LD. Wer
# 30.06.2026 plus 1050 rechnen will, soll das selbst tun. Geprueft wird das
# ganze Dokument ausser der Fusszeile; dort steht auf jeder Seite "no hype,
# no price targets", also die Absage und nicht die Sache selbst.
BULL_VERBOTEN = ("would put", "points to", "targets", "expect", "due in", "by 20")

# JAHRE RELATIV ZUM LAUFENDEN JAHR, SEIT 23.09.2026
# Hier stand "jede Jahreszahl ab 2027", fest verdrahtet. Das waere am
# 1. Januar 2027 auf jeder Seite angesprungen, die schlicht das laufende
# Jahr nennt, und zwar an dem Tag, an dem niemand damit rechnet. Gesucht
# ist ein Jahr in der ZUKUNFT, also wird gegen das laufende Jahr geprueft.
RE_JAHR = re.compile(r"\b(?:19|20)\d\d\b")
RE_FUSS = re.compile(r"<footer>.*?</footer>", re.S)


def ohne_fuss(html):
    return RE_FUSS.sub("", html)


def prognose_funde(html, jahr=None):
    """was nach vorhersage aussieht. leere liste heisst sauber.

    jahr ist das laufende Jahr; ohne Angabe das heutige in UTC. Der
    Parameter ist der Eingriffspunkt fuer den Selbsttest, der damit ein
    anderes Systemjahr vorgaukelt."""
    if jahr is None:
        jahr = heute().year
    roh = ohne_fuss(html)
    funde = [w for w in BULL_VERBOTEN if w in roh.lower()]
    return funde + sorted(set(j for j in RE_JAHR.findall(roh) if int(j) > jahr))


def _zahl_steht(html, text):
    """steht diese zahl als eigene zahl da, nicht als teil einer groesseren.
    ohne die beiden lookarounds faende "692" auch die 692 in "1,692"."""
    return re.search(r"(?<![\d,])%s(?![\d,])" % re.escape(text), html) is not None


# Ein Anstieg steht in zwei Schreibweisen auf der Seite: "+1,990%" im
# Fliesstext und in der Tabelle, "1,990 percent" im JSON-LD. Beide werden
# eingesammelt. Nicht eingesammelt werden Prozentwerte mit Nachkommastelle
# wie "1.6%", das sind die Streuungsspalten und keine Anstiege.
RE_ANSTIEG = re.compile(r"\+([\d,]+)%|([\d,]+) percent")


def anstiege_im_text(html):
    """jeder wert, der auf der seite wie ein anstieg aussieht, einmal."""
    roh = ohne_fuss(html)
    return sorted(set(a or b for a, b in RE_ANSTIEG.findall(roh)))


def anstieg_funde(html, erlaubt):
    """vergleicht die Seite gegen die aus dem Archiv gerechnete Menge.

    ZWEI RICHTUNGEN, SEIT 23.09.2026
    Vorher wurde nur auf den Nachbarn geprueft, also auf eine Abweichung um
    eins. Das faengt das doppelte Runden vom 23.09.2026, aber weder einen
    Zahlendreher wie 1.909 statt 1.990 noch eine veraltete Zahl aus einem
    frueheren Backfill. Jetzt wird jeder Prozentwert, der auf der Seite wie
    ein Anstieg aussieht, gegen die gerechnete Menge gehalten. Ein Wert, der
    dort nicht vorkommt, ist ein Fehler und keine Warnung.

    Die Gegenrichtung bleibt: ein gerechneter Anstieg, der auf der Seite
    ueberhaupt nicht steht, faellt ebenfalls auf."""
    erlaubt = set(str(x).lstrip("+").rstrip("%") for x in erlaubt)
    fehler = ["%s steht da, gerechnet sind nur %s" % (a, ", ".join(sorted(erlaubt)))
              for a in anstiege_im_text(html) if a not in erlaubt]
    fehler += ["%s fehlt" % a for a in sorted(erlaubt)
               if not _zahl_steht(ohne_fuss(html), a)]
    return fehler


def bull_anstiege(reihe):
    """die drei abgeschlossenen anstiege, gerechnet wie auf der seite.
    liefert None, wenn ein eckpunkt fehlt."""
    preis = dict(reihe)
    out = []
    for tief, hoch in ZYKLEN:
        if tief not in preis or hoch not in preis:
            return None
        out.append(proz0(preis[hoch], preis[tief]))
    return out


def bullrun_werte(archivrows, logrows, bis=None):
    """rechnet, was bitcoin-bull-run-length.html im browser rechnet.
    liefert (werte, None) oder (None, grund)."""
    reihe = archiv_reihe(archivrows)
    if not reihe:
        return None, "kein btc im archiv"
    preis = dict(reihe)

    # jedes eckdatum muss im archiv stehen, sonst wird nicht gestempelt
    spannen = []
    for tief, hoch in ZYKLEN:
        if tief not in preis or hoch not in preis:
            return None, "eckpunkt fehlt im archiv (%s oder %s)" % (tief, hoch)
        spannen.append(tage(tief, als_datum(hoch)))
    if min(spannen) <= 0:
        return None, "ein hoch liegt nicht nach seinem tief"

    # das laufende tief kommt aus dem archiv, nicht aus der konstante:
    # faellt bitcoin tiefer, zaehlt die seite ab dem neuen tag.
    tief = tief_nach(mit_rand(reihe, logrows), HOCH_CLOSE)
    if not tief:
        return None, "kein preis nach dem hoch"
    jetzt = letzter_schluss(logrows)
    if not jetzt:
        return None, "kein btc-schluss im log"

    n = tage(tief[0], bis)
    if n <= 0:
        return None, "das tief liegt nicht in der vergangenheit"
    ntxt = "{:,}".format(n)
    kurz_txt = "{:,}".format(min(spannen))
    lang_txt = "{:,}".format(max(spannen))
    return {
        "blrange": "%s to %s days" % (kurz_txt, lang_txt),
        "blrange2": "%s to %s" % (kurz_txt, lang_txt),
        "blspread": "{:,} days".format(max(spannen) - min(spannen)),
        "blfaq": ", ".join("{:,}".format(x) for x in spannen[:-1])
                 + " and {:,} days".format(spannen[-1]),
        "blnow": ntxt,
        "r26days": ntxt,
        "blfaq2": ntxt + " days",
        "blnowsrc": "days since %s, %s USD" % (lang(tief[0]), dollar(tief[1])),
        "blbarlbl": ntxt + " and counting",
        "blasof": lang(jetzt["d"]),
        "r26low": "%s, %s" % (kurz(tief[0]), dollar(tief[1])),
        "r26gain": proz0(jetzt["btc"], tief[1]) + "%",
    }, None


def lauf_bullrun():
    pfad = os.path.join(REPO, BL_SEITE)
    if not os.path.exists(pfad):
        print("  ok   %-30s nicht vorhanden, uebersprungen" % BL_SEITE)
        return 0
    if not (os.path.exists(ARCHIV) and os.path.exists(LOG)):
        print("  FEHL %-30s archiv oder log fehlt" % BL_SEITE)
        return 1
    with open(ARCHIV, "r", encoding="utf-8") as fh:
        archivrows = json.load(fh)
    with open(LOG, "r", encoding="utf-8") as fh:
        logrows = json.load(fh)
    werte, grund = bullrun_werte(archivrows, logrows)
    if werte is None:
        print("  FEHL %-30s %s" % (BL_SEITE, grund))
        return 1
    with open(pfad, "r", encoding="utf-8") as fh:
        alt = fh.read()

    # wache 1: stehen die drei abgeschlossenen anstiege richtig da
    anst = bull_anstiege(archiv_reihe(archivrows))
    if anst is None:
        print("  FEHL %-30s eckpunkt fuer die anstiege fehlt im archiv" % BL_SEITE)
        return 1
    neu, treffer, fehlend = setz_text(alt, werte)
    if fehlend:
        print("  FEHL %-30s id nicht gefunden %s" % (BL_SEITE, ", ".join(fehlend)))
        return 1

    # BEIDE WACHEN LAUFEN AUF DEM GESTEMPELTEN TEXT, NICHT AUF DEM ALTEN.
    # Die erste Fassung pruefte vorher, und das ging am 24.09.2026 schief:
    # der laufende Anstieg war ueber Nacht von +47 auf +44 Prozent gewandert,
    # die gerechnete Menge kannte schon die 44, auf der Seite stand noch die
    # 47, und die Wache blockierte damit genau die Aktualisierung, die den
    # Widerspruch aufgeloest haette. Geprueft wird das Ergebnis.
    erlaubt = list(anst) + [werte["r26gain"]]
    fehlt = anstieg_funde(neu, erlaubt)
    if fehlt:
        print("  FEHL %-30s anstieg falsch: %s" % (BL_SEITE, "; ".join(fehlt)))
        return 1
    funde = prognose_funde(neu)
    if funde:
        print("  FEHL %-30s sieht nach vorhersage aus: %s"
              % (BL_SEITE, ", ".join(funde)))
        return 1
    ko = kopf_funde(BL_SEITE, neu, werte)
    if ko:
        print("  FEHL %-30s %s" % (BL_SEITE, "; ".join(ko)))
        return 1
    ZAEHLTAG[BL_SEITE] = heute().isoformat()
    return schreiben(pfad, alt, neu, BL_SEITE,
                     "%d zahlen, anstiege %s, tag %s seit dem tief"
                     % (treffer, "/".join(anst), werte["blnow"]))


# --- teil 8, gold in bitcoins baermaerkten ---------------------------
#
# Dieselben Fenster wie ueberall, nur mit zwei weiteren Reihen daneben.
# Bitcoin hat fuer jeden Kalendertag einen Wert, GLD und SPY nur fuer
# Boersentage. Fuer eine Fenstergrenze, die auf einen Samstag faellt,
# wird bei GLD und SPY der letzte Boersentag davor genommen. Das steht
# so auch auf der Seite, mit Zahl und Datum.

def archiv_feld(rows, feld):
    """eine beliebige spalte des archivs als sortierte liste."""
    return sorted((r["d"], float(r[feld])) for r in (rows or [])
                  if isinstance(r, dict) and isinstance(r.get("d"), str)
                  and isinstance(r.get(feld), (int, float)))


def proz2(neu, alt):
    """zwei nachkommastellen mit vorzeichen. auf der goldseite steht eine
    stelle mehr als sonst, weil die seite von kleinen unterschieden
    handelt: aus -5,0 laesst sich nicht ablesen, dass der wert ueber
    fuenf prozent liegt, aus -5,03 schon."""
    return "%+.2f%%" % ((float(neu) / float(alt) - 1.0) * 100.0)


def _roh(neu, alt):
    return (float(neu) / float(alt) - 1.0) * 100.0


def gold_werte(archivrows, logrows, bis=None):
    """rechnet, was die goldseite zeigt. (werte, None) oder (None, grund).

    Der rechte Rand des laufenden Fensters kommt aus dem MARKTLOG, nicht
    aus dem Archiv. Das Archiv wird nur sonntags nachgezogen und haengt
    unter der Woche bis zu sechs Tage hinterher; die anderen Zyklusseiten
    rechnen laengst auf den Marktlog. Gold und Aktien kommen weiter aus
    dem Archiv, zum selben Stichtag mit Rueckgriff auf den letzten
    Boersentag."""
    btc = archiv_reihe(archivrows)
    gld = archiv_feld(archivrows, "gld")
    spy = archiv_feld(archivrows, "spy")
    if not (btc and gld and spy):
        return None, "btc, gld oder spy fehlt im archiv"
    reihen = {"btc": btc, "gld": gld, "spy": spy}

    werte = {}
    gld_fertig = []
    spy_fertig = []
    for von, nach, vorsilbe in BAERFENSTER:
        for feld in ("btc", "gld", "spy"):
            a = am_oder_vor(reihen[feld], von)
            b = am_oder_vor(reihen[feld], nach)
            if not a or not b:
                return None, "kein %s-wert fuer %s..%s" % (feld, von, nach)
            werte[vorsilbe + feld] = proz2(b[1], a[1])
            if feld == "gld":
                gld_fertig.append(_roh(b[1], a[1]))
            if feld == "spy":
                spy_fertig.append(_roh(b[1], a[1]))

    # der laufende: einmal bis zum tief, einmal bis zum juengsten tag
    jetzt = letzter_schluss(logrows)
    if not jetzt:
        return None, "kein btc-schluss im log"
    tief = tief_nach(mit_rand(btc, logrows), HOCH_CLOSE)
    if not tief:
        return None, "kein preis nach dem hoch"
    rand = jetzt["d"]
    for nach, vorsilbe in ((tief[0], "b4"), (rand, "b5")):
        for feld in ("btc", "gld", "spy"):
            a = am_oder_vor(reihen[feld], HOCH_CLOSE)
            # fuer btc am rechten rand gilt der marktlog, sonst das archiv
            if feld == "btc" and nach == rand:
                b = (rand, jetzt["btc"])
            else:
                b = am_oder_vor(reihen[feld], nach)
            if not a or not b:
                return None, "kein %s-wert fuer das laufende fenster" % feld
            werte[vorsilbe + feld] = proz2(b[1], a[1])
    werte["b5end"] = kurz(rand)
    werte["b5tag"] = rand      # nur fuer die stichtagswache, nicht gestempelt
    werte["cur1"] = werte["b4gld"]
    werte["cur2"] = werte["b5gld"]
    werte["cur2d"] = lang(rand)
    werte["faq1"] = werte["b5gld"]

    # gold gegen den hoechsten schluss im archiv
    spitze = max(gld, key=lambda x: x[1])
    letzt = gld[-1]
    werte["gpeakd"] = lang(spitze[0])
    werte["gpeak"] = "%.2f" % spitze[1]
    werte["gnowd"] = lang(letzt[0])
    werte["gnow"] = "%.2f" % letzt[1]
    werte["gdd"] = "%.2f%%" % abs(_roh(letzt[1], spitze[1]))
    werte["faq2"] = werte["gdd"]

    # die beiden spannen, aus den ungerundeten werten
    werte["gldspread"] = "%.2f" % (max(gld_fertig) - min(gld_fertig))
    werte["spyspread"] = "%.2f" % (max(spy_fertig) - min(spy_fertig))

    # "innerhalb von X" wird AUFGERUNDET, sonst behauptet die seite etwas,
    # das um hundertstel nicht stimmt. -5,0279 ergibt 5,1 und nicht 5,0.
    # vor dem aufrunden wird die darstellungsunschaerfe weggerundet. ohne
    # das round() wuerde ein wert, der mathematisch genau 5,00 ist, als
    # 5.000000000000004 ankommen und zu 5,1 aufgerundet, also strenger
    # behauptet als noetig. der selbsttest haelt beide faelle fest.
    schlimmst = round(max(abs(x) for x in gld_fertig), 6)
    werte["gworst"] = "within %.1f%%" % (math.ceil(schlimmst * 10) / 10.0)
    return werte, None


def lauf_gold():
    pfad = os.path.join(REPO, GOLD_SEITE)
    if not os.path.exists(pfad):
        print("  ok   %-30s nicht vorhanden, uebersprungen" % GOLD_SEITE)
        return 0
    if not (os.path.exists(ARCHIV) and os.path.exists(LOG)):
        print("  FEHL %-30s archiv oder log fehlt" % GOLD_SEITE)
        return 1
    with open(ARCHIV, "r", encoding="utf-8") as fh:
        archivrows = json.load(fh)
    with open(LOG, "r", encoding="utf-8") as fh:
        logrows = json.load(fh)
    werte, grund = gold_werte(archivrows, logrows)
    if werte is None:
        print("  FEHL %-30s %s" % (GOLD_SEITE, grund))
        return 1
    with open(pfad, "r", encoding="utf-8") as fh:
        alt = fh.read()
    stempel = dict((k, v) for k, v in werte.items() if k != "b5tag")
    neu, treffer, fehlend = setz_text(alt, stempel)
    if fehlend:
        print("  FEHL %-30s id nicht gefunden %s" % (GOLD_SEITE, ", ".join(fehlend)))
        return 1
    # wie bei der bullenseite: geprueft wird das ergebnis, nicht der stand
    # von gestern.
    funde = prognose_funde(neu)
    if funde:
        print("  FEHL %-30s sieht nach vorhersage aus: %s"
              % (GOLD_SEITE, ", ".join(funde)))
        return 1
    ko = kopf_funde(GOLD_SEITE, neu, stempel)
    if ko:
        print("  FEHL %-30s %s" % (GOLD_SEITE, "; ".join(ko)))
        return 1
    STICHTAG[GOLD_SEITE] = werte["b5tag"]
    return schreiben(pfad, alt, neu, GOLD_SEITE,
                     "%d zahlen, gold %s im laufenden baer, %s unter der spitze"
                     % (treffer, werte["b5gld"], werte["gdd"]))


# --- teil 9, ein heute fuer alle -------------------------------------

def nur_kopf(html):
    """alles vor </head>. dort kommt setz_text nicht hin."""
    i = html.find("</head>")
    return html[:i] if i >= 0 else ""


def kopf_funde(datei, html, werte):
    """jeder wert, den dieser lauf in den rumpf geschrieben hat und der
    zusaetzlich im kopf steht, ohne dort angemeldet zu sein.

    keine heuristik: geprueft wird nicht, ob ein wert beweglich AUSSIEHT,
    sondern ob der stempel ihn in diesem lauf gesetzt hat. hat er das,
    kontrolliert er ihn, und eine zweite kopie im kopf kontrolliert er
    nicht."""
    kopf = nur_kopf(html)
    frei = set(KOPF_AUSNAHMEN.get(datei, ()))
    return ["%s=%r steht auch im kopf" % (i, v)
            for i, v in sorted(werte.items())
            if i not in frei and v and str(v) in kopf]


def stichtag_funde(eintraege, lies=None, nennen=None):
    """prueft, ob alle zyklusseiten denselben stichtag tragen.

    zwei pruefungen, beide muessen halten:
      1. alle eingetragenen seiten nennen denselben tag,
      2. dieser tag steht ausgeschrieben auch wirklich auf jeder seite.

    die zweite faengt den fall, dass eine seite gar nicht gestempelt
    wurde und noch den tag von gestern zeigt, waehrend die sammelstelle
    schon den neuen kennt.

    lies(datei) liefert den seitentext; ohne angabe wird von platte
    gelesen. der selbsttest reicht hier eine eigene funktion herein."""
    if not eintraege:
        return ["keine zyklusseite hat einen stichtag eingetragen"]
    tage = sorted(set(eintraege.values()))
    if len(tage) > 1:
        return ["%s rechnet auf %s" % (d, t)
                for d, t in sorted(eintraege.items())]
    tag = tage[0]
    if lies is None:
        def lies(datei):
            pfad = os.path.join(REPO, datei)
            if not os.path.exists(pfad):
                return ""
            with open(pfad, "r", encoding="utf-8") as fh:
                return fh.read()
    pflicht = sorted(eintraege) if nennen is None else sorted(set(eintraege) & set(nennen))
    return ["%s nennt %s nicht" % (d, lang(tag))
            for d in pflicht if lang(tag) not in lies(d)]


def zaehltag_nachtragen():
    """die mitzaehler eintragen, die keine seite sind."""
    for name in ZAEHLTAG_MIT:
        ZAEHLTAG[name] = heute().isoformat()
    return ZAEHLTAG


def lauf_stichtag():
    """zwei gruppen, jede fuer sich stimmig.

    preis     der juengste preis, den eine seite zeigt
    zaehltag  der tag, gegen den ihre tageszaehler rechnen

    Die beiden duerfen sich unterscheiden, und sie tun es meistens: der
    zaehler laeuft bis heute, der juengste preis ist der von gestern
    abend. Was nicht sein darf, ist dass zwei SEITEN innerhalb derselben
    gruppe auseinanderlaufen."""
    zaehltag_nachtragen()
    fehler = 0
    for name, eintraege, nennen in (("preis", STICHTAG, None),
                                    ("zaehltag", ZAEHLTAG, NENNT_ZAEHLTAG)):
        funde = stichtag_funde(eintraege, None, nennen)
        if funde:
            print("  FEHL stichtag %-8s             %s" % (name, "; ".join(funde)))
            print("       zwei seiten mit verschiedenem heute sind ein fehler,")
            print("       nicht eine kleinigkeit. der lauf haelt hier an.")
            fehler += 1
        else:
            # "stelle(n)", nicht "seite(n)": in der zaehltag-gruppe steht
            # seit dem 24.09.2026 auch dayn.yml, und das ist keine seite.
            print("  ok   stichtag %-8s             %s auf %d stelle(n)"
                  % (name, sorted(set(eintraege.values()))[0], len(eintraege)))
    return fehler


# --- teil 10, what-if ------------------------------------------------
#
# Die Seite rechnet im Browser auf Eingaben. Gestempelt wird die
# voreingestellte Ansicht, also das, was ohne einen einzigen Klick
# dasteht. Die Arithmetik unten ist dieselbe wie im Seitenskript,
# einschliesslich der Rundungen; die Dopplung ist unvermeidlich und der
# Grund, warum fuer jede Zahl ein Testfall steht.

def wi_usd(x):
    """usd() aus dem seitenskript, zeichen fuer zeichen."""
    x = float(x)
    if x >= 1e9:
        return "$%.2fB" % (x / 1e9)
    if x >= 1e6:
        return "$%.2fM" % (x / 1e6)
    return "$" + "{:,}".format(int(math.floor(x + 0.5)))


def wi_px(x):
    """px() aus dem seitenskript."""
    x = float(x)
    return "$" + ("{:,}".format(int(math.floor(x + 0.5))) if x >= 100
                  else "%.2f" % x)


def wi_jahre_zurueck(iso_tag, jahre):
    """setUTCFullYear(y - n) aus javascript. der 29. februar rutscht dort
    auf den 1. maerz, weil der 29.02. im zieljahr nicht existiert."""
    j, m, t = [int(x) for x in iso_tag.split("-")]
    z = j - jahre
    letzter = calendar.monthrange(z, m)[1]
    if t > letzter:
        return (datetime.date(z, m, letzter)
                + datetime.timedelta(days=t - letzter)).isoformat()
    return datetime.date(z, m, t).isoformat()


def wi_ab(reihe, tag):
    """erster punkt am oder nach dem tag."""
    for d, v in reihe:
        if d >= tag:
            return (d, v)
    return None


def wi_bis(reihe, tag):
    """letzter punkt am oder vor dem tag."""
    tref = None
    for d, v in reihe:
        if d > tag:
            break
        tref = (d, v)
    return tref


def wi_lump(reihe, betrag, jahre):
    if not reihe:
        return None
    jetzt = reihe[-1]
    davor = wi_ab(reihe, wi_jahre_zurueck(jetzt[0], jahre))
    if not davor or davor[1] <= 0:
        return None
    mult = jetzt[1] / davor[1]
    return {"davor": davor, "jetzt": jetzt, "mult": mult, "wert": betrag * mult}


def wi_dca(reihe, monatlich, jahre):
    """monatsend-kaeufe, genau wie im seitenskript."""
    if not reihe:
        return None
    jetzt = reihe[-1]
    ende = datetime.date(*[int(x) for x in jetzt[0].split("-")])
    j, m = ende.year - jahre, ende.month - 1        # m nullbasiert
    anteile = paid = kaeufe = 0.0
    erster = None
    while j < ende.year or (j == ende.year and m <= ende.month - 1):
        me = datetime.date(j, m + 1, calendar.monthrange(j, m + 1)[1])
        if me > ende:
            break
        pkt = wi_bis(reihe, me.isoformat())
        if pkt and pkt[1] > 0:
            anteile += monatlich / pkt[1]
            paid += monatlich
            kaeufe += 1
            if erster is None:
                erster = pkt[0]
        m += 1
        if m > 11:
            m = 0
            j += 1
    if kaeufe < 6:
        return None
    return {"wert": anteile * jetzt[1], "paid": paid, "kaeufe": int(kaeufe),
            "erster": erster, "jetzt": jetzt}


WI_LABEL = {"btc": "bitcoin", "spy": "the S&amp;P 500", "gld": "gold"}


def whatif_werte(archivrows, logrows):
    """(werte, None) oder (None, grund). werte fuer die voreingestellte
    ansicht der drei reiter."""
    reihen = dict((f, reihe_mit_logvorrang(f, archiv=archivrows, log=logrows))
                  for f in ("btc", "spy", "gld"))
    if not all(reihen.values()):
        return None, "btc, spy oder gld fehlt"
    asof = min(r[-1][0] for r in reihen.values())

    lf, lbetrag, ljahre = WI_LUMP
    L = wi_lump(reihen[lf], lbetrag, ljahre)
    if not L:
        return None, "einmalkauf laesst sich nicht rechnen"
    df, dbetrag, djahre = WI_DCA
    D = wi_dca(reihen[df], dbetrag, djahre)
    if not D:
        return None, "sparplan laesst sich nicht rechnen"
    proTag, ajahre, aname = WI_DAY
    monatlich = proTag * 365.0 / 12.0
    A = dict((f, wi_dca(reihen[f], monatlich, ajahre)) for f in ("spy", "gld", "btc"))
    if not all(A.values()):
        return None, "tagesbetrag laesst sich nicht rechnen"

    tag = lambda n: ("%d" % n) if float(n) == int(n) else ("%s" % n)
    werte = {
        "asof": "%s (bitcoin %s)" % (lang(asof), lang(reihen["btc"][-1][0])),
        "l-big": wi_usd(L["wert"]),
        "l-used": "Counted with: close on %s %s \u2192 close on %s %s."
                  % (lang(L["davor"][0]), wi_px(L["davor"][1]),
                     lang(L["jetzt"][0]), wi_px(L["jetzt"][1])),
        "d-big": wi_usd(D["wert"]),
        "d-used": "Counted with: %d month-end buys from %s to %s, valued at %s."
                  % (D["kaeufe"], lang(D["erster"]), lang(D["jetzt"][0]),
                     wi_px(D["jetzt"][1])),
        "a-k": "$%s a day (%s), bought at every month end, %d years"
               % (tag(proTag), aname, ajahre),
        "a-spent": wi_usd(A["spy"]["paid"]),
        "a-spy": wi_usd(A["spy"]["wert"]),
        "a-gld": wi_usd(A["gld"]["wert"]),
        "a-btc": wi_usd(A["btc"]["wert"]),
        "a-used": ("Counted with: $%s \u00d7 365 \u00f7 12 = %s a month, %d "
                   "month-end buys from %s to %s, each asset at its own closes."
                   % (tag(proTag), wi_usd(monatlich), A["spy"]["kaeufe"],
                      lang(A["spy"]["erster"]), lang(A["spy"]["jetzt"][0]))),
    }
    # die beiden saetze mit <b> darin, als ganzer innenraum ersetzt
    innen = {
        "l-sub": ("<b>%s</b> in %s %d years ago is <b>%s</b> today, <b>%s\u00d7</b> "
                  "the money." % (wi_usd(lbetrag), WI_LABEL[lf], ljahre,
                                  wi_usd(L["wert"]),
                                  ("%.0f" % L["mult"]) if L["mult"] >= 10
                                  else ("%.2f" % L["mult"]))),
        "d-sub": ("<b>%s a month</b> into %s for %d years: <b>%s</b> paid in, "
                  "worth <b>%s</b> today (%.2f\u00d7 what you paid)."
                  % (wi_usd(dbetrag), WI_LABEL[df], djahre, wi_usd(D["paid"]),
                     wi_usd(D["wert"]), D["wert"] / D["paid"])),
    }
    return {"text": werte, "innen": innen, "asof": asof}, None


RE_INNEN = {}


def setz_innen(html, kennung, inhalt):
    """ersetzt den ganzen innenraum eines div, auch wenn tags darin stehen.
    setz_text kann das nicht, es hoert beim ersten < auf."""
    muster = re.compile(r'(<div[^>]*id="%s"[^>]*>)(.*?)(</div>)'
                        % re.escape(kennung), re.S)
    return muster.subn(lambda m: m.group(1) + inhalt + m.group(3), html)


def lauf_whatif():
    pfad = os.path.join(REPO, WI_SEITE)
    if not os.path.exists(pfad):
        print("  ok   %-30s nicht vorhanden, uebersprungen" % WI_SEITE)
        return 0
    if not (os.path.exists(ARCHIV) and os.path.exists(LOG)):
        print("  FEHL %-30s archiv oder log fehlt" % WI_SEITE)
        return 1
    with open(ARCHIV, "r", encoding="utf-8") as fh:
        archivrows = json.load(fh)
    with open(LOG, "r", encoding="utf-8") as fh:
        logrows = json.load(fh)
    w, grund = whatif_werte(archivrows, logrows)
    if w is None:
        print("  FEHL %-30s %s" % (WI_SEITE, grund))
        return 1
    with open(pfad, "r", encoding="utf-8") as fh:
        alt = fh.read()
    neu, treffer, fehlend = setz_text(alt, w["text"])
    if fehlend:
        print("  FEHL %-30s id nicht gefunden %s" % (WI_SEITE, ", ".join(fehlend)))
        return 1
    for kennung, inhalt in sorted(w["innen"].items()):
        neu, n = setz_innen(neu, kennung, inhalt)
        if n != 1:
            print("  FEHL %-30s %s nicht genau einmal gefunden (%d)"
                  % (WI_SEITE, kennung, n))
            return 1
        treffer += 1
    ko = kopf_funde(WI_SEITE, neu, w["text"])
    if ko:
        print("  FEHL %-30s %s" % (WI_SEITE, "; ".join(ko)))
        return 1
    STICHTAG[WI_SEITE] = w["asof"]
    return schreiben(pfad, alt, neu, WI_SEITE,
                     "%d zahlen, stand %s" % (treffer, w["asof"]))


# --- teil 4, die leiste ----------------------------------------------

PNAV = re.compile(r'(<div class="pnav">)(.*?)(</div>)', re.S)


def leiste(aktuell):
    """baut den inhalt der pillenreihe fuer eine bestimmte seite.
    die eigene seite wird zur beschrifteten pille ohne verweis, alle
    anderen werden verweise."""
    teile = []
    for datei, name in SEITEN:
        if datei == aktuell:
            teile.append("<span>%s</span>" % name)
        else:
            teile.append('<a href="/%s">%s</a>' % (datei, name))
    return "\n  " + "\n  ".join(teile) + "\n"


def setz_leiste(html, aktuell):
    """ersetzt den inhalt des pnav-blocks. gibt text und trefferzahl."""
    return PNAV.subn(lambda m: m.group(1) + leiste(aktuell) + m.group(3), html)


def lauf_leiste():
    fehler = 0
    gebaut = 0
    for datei, _ in SEITEN:
        pfad = os.path.join(REPO, datei)
        if not os.path.exists(pfad):
            print("  ok   %-30s nicht vorhanden, uebersprungen" % datei)
            continue
        with open(pfad, "r", encoding="utf-8") as fh:
            alt = fh.read()
        neu, n = setz_leiste(alt, datei)
        if n == 0:
            # ohne den block kann die leiste nicht wachsen, und das faellt
            # sonst erst auf, wenn jemand die seite besucht.
            print("  FEHL %-30s kein pnav-block gefunden" % datei)
            fehler += 1
            continue
        fehler += schreiben(pfad, alt, neu, datei, "leiste mit %d punkten" % len(SEITEN))
        gebaut += 1
    if gebaut == 0:
        print("  FEHL leiste                        keine seite gefunden")
        return fehler + 1
    return fehler


# --- selbsttest ------------------------------------------------------

def selbsttest():
    schlecht = 0
    gezaehlt = 0

    def pruefe(name, ist, soll):
        nonlocal schlecht, gezaehlt
        gezaehlt += 1
        if ist != soll:
            schlecht += 1
            print("  FEHL %s\n    ist  %r\n    soll %r" % (name, ist, soll))
        else:
            print("  ok   %s" % name)

    bis = datetime.date(2026, 8, 21)
    pruefe("tage seit dem halving", tage(HALVING, bis), 853)
    pruefe("tage seit dem schlusshoch", tage(HOCH_CLOSE, bis), 319)
    # EINE Definition fuer beide Zyklusseiten: der hoechste Tagesschluss.
    pruefe("top-to-bottom zaehlt zum schlusshoch",
           set(d for _, d, _ in ZYKLUS["bitcoin-top-to-bottom.html"]), {HOCH_CLOSE})
    pruefe("halving-seite zaehlt zum selben hoch",
           set(d for _, d, _ in ZYKLUS["bitcoin-halving-to-top.html"]),
           {HALVING, HOCH_CLOSE})
    pruefe("vom halving zum hoch sind es 534 tage",
           tage(HALVING, datetime.date(2025, 10, 6)), 534)
    # das hoch muss das umdatierte sein. stuende hier wieder der 7., waere
    # die ganze seite um einen tag daneben und niemand saehe es an der zahl.
    pruefe("das hoch ist umdatiert", HOCH_CLOSE, "2025-10-06")
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

    # --- der letzte schluss ---
    log5 = [{"d": "2026-09-13", "btc": 76706.0},
            {"d": "2026-09-14", "gld": 392.84, "spy": 760.88, "btc": 78150.0},
            {"d": "2026-09-15", "btc": 75608.0}]
    pruefe("juengster btc-schluss", letzter_schluss(log5)["d"], "2026-09-15")
    # btc laeuft am wochenende weiter, gold und aktien nicht. wer hier die
    # dreiergruppe verlangt, stempelt am sonntag den freitagsschluss.
    pruefe("btc allein reicht", letzter_schluss(log5)["btc"], 75608.0)
    pruefe("log ohne btc", letzter_schluss([{"d": "2026-09-15", "gld": 1.0}]), None)
    pruefe("ganze dollar bleiben ganz", zahl(75608.0), "75608")
    pruefe("cents bleiben cents", zahl(75608.25), "75608.25")

    js = 'var LAST_CLOSE = 1, LAST_DATE = "2000-01-01";'
    fertig, n1, n2 = setz_schluss(js, 75608.0, "2026-09-15")
    pruefe("schluss gestempelt", fertig, 'var LAST_CLOSE = 75608, LAST_DATE = "2026-09-15";')
    pruefe("beide zuweisungen getroffen", (n1, n2), (1, 1))
    pruefe("zweiter lauf ist ruhig", setz_schluss(fertig, 75608.0, "2026-09-15")[0], fertig)
    # eine umbenannte variable muss auffallen, sonst friert die zahl ein
    pruefe("fehlende zuweisung faellt auf",
           setz_schluss('var SOMETHING = 1;', 1.0, "2026-09-15")[1:], (0, 0))
    pruefe("mehr abstand stoert nicht",
           setz_schluss('var LAST_CLOSE  =  1 , LAST_DATE  =  "2000-01-01" ;', 9.0, "2026-09-15")[1:],
           (1, 1))

    # --- die leiste ---
    pruefe("eigene seite ohne verweis",
           "<span>markets</span>" in leiste("markets.html"), True)
    # gezaehlt wird die PILLE, nicht der teilstring: seit es
    # gold-in-bitcoin-bear-markets.html gibt, steht "markets" auch in einem
    # fremden href, und eine teilstringzaehlung waere hier falsch geworden.
    pruefe("eigene seite nicht doppelt",
           leiste("markets.html").count("<span>markets</span>"), 1)
    pruefe("und nicht zusaetzlich als verweis",
           ">markets</a>" in leiste("markets.html"), False)
    pruefe("fremde seiten als verweis",
           leiste("markets.html").count("<a href="), len(SEITEN) - 1)
    pruefe("alle punkte drin",
           all(name in leiste("markets.html") for _, name in SEITEN), True)

    roh = ('<div class="pnav">\n  <a href="/alt.html">alt</a>\n</div>'
           '<div class="pnav">zweiter</div>')
    fertig, n = setz_leiste(roh, "bitcoin-dominance.html")
    pruefe("beide bloecke getroffen", n, 2)
    pruefe("alte pille ist weg", "alt.html" in fertig, False)
    pruefe("aktuelle seite markiert", "<span>dominance</span>" in fertig, True)
    pruefe("zweiter lauf ist ruhig", setz_leiste(fertig, "bitcoin-dominance.html")[0], fertig)
    pruefe("ohne block kein treffer", setz_leiste("<div>nix</div>", "markets.html")[1], 0)
    # eine seite, die nicht in SEITEN steht, bekommt eine leiste ohne
    # markierung. das ist gewollt, sie soll trotzdem navigierbar sein.
    pruefe("unbekannte seite ohne markierung",
           "<span>" in leiste("gibtsnicht.html"), False)

    # --- die rueckgangszahlen ---
    pruefe("kurzdatum", kurz("2013-12-04"), "4 Dec 2013")
    pruefe("langdatum", lang("2026-06-30"), "30 June 2026")
    pruefe("eine stelle nach unten", proz1(58534.28, 124776.68), "-53.1%")
    pruefe("eine stelle nach oben", proz1(110.0, 100.0), "10.0%")
    pruefe("dollar gerundet", dollar(58534.28), "58,534")
    # javascript rundet die halbe stelle nach oben, python normalerweise zur
    # geraden zahl. ginge das auseinander, waere die gestempelte zahl um
    # einen dollar neben der angezeigten.
    pruefe("halbe stelle wie javascript", dollar(2.5), "3")

    reihe = archiv_reihe([{"d": "2026-01-02", "btc": 2.0},
                          {"d": "2026-01-01", "btc": 1.0},
                          {"d": "2026-01-03", "gld": 5.0}])
    pruefe("archiv sortiert und gefiltert", reihe, [("2026-01-01", 1.0), ("2026-01-02", 2.0)])
    pruefe("hoechster seit stichtag", hoch_seit(reihe, "2026-01-01"), ("2026-01-02", 2.0))
    pruefe("nichts nach dem stichtag", hoch_seit(reihe, "2027-01-01"), None)
    pruefe("tiefster danach", tief_nach(reihe, "2025-12-31"), ("2026-01-01", 1.0))
    pruefe("am oder vor, genauer treffer", am_oder_vor(reihe, "2026-01-02"), ("2026-01-02", 2.0))
    pruefe("am oder vor, tag davor", am_oder_vor(reihe, "2026-01-05"), ("2026-01-02", 2.0))
    pruefe("am oder vor, nichts davor", am_oder_vor(reihe, "2025-01-01"), None)

    # der rand des logs kommt nur fuer tage nach dem archivrand dazu. fuer
    # denselben tag gewinnt immer das archiv, sonst stuenden zwei
    # verschiedene preisdefinitionen in einer spalte.
    randlog = [{"d": "2026-01-02", "btc": 99.0}, {"d": "2026-01-04", "btc": 3.0}]
    pruefe("rand angehaengt", mit_rand(reihe, randlog),
           [("2026-01-01", 1.0), ("2026-01-02", 2.0), ("2026-01-04", 3.0)])
    pruefe("archiv gewinnt am selben tag",
           dict(mit_rand(reihe, randlog))["2026-01-02"], 2.0)
    pruefe("leeres archiv bleibt leer", mit_rand([], randlog), [])

    # ein vollstaendiger durchlauf auf gesetzten zahlen. der stichtag steht
    # fest, damit der fall nicht morgen ein anderes ergebnis hat.
    tarchiv = [{"d": "2013-12-04", "btc": 1000.0}, {"d": "2014-11-20", "btc": 250.0},
               {"d": "2017-12-16", "btc": 20000.0}, {"d": "2018-12-02", "btc": 4000.0},
               {"d": "2021-11-08", "btc": 50000.0}, {"d": "2022-10-25", "btc": 20000.0},
               {"d": HOCH_CLOSE, "btc": HOCH_WERT}, {"d": "2026-06-30", "btc": 62388.34}]
    tlog = [{"d": "2026-09-22", "btc": 99821.344}]
    w, grund = rueckgang_werte(tarchiv, tlog, datetime.date(2026, 9, 22))
    pruefe("kein grund zum abbruch", grund, None)
    dd, ttb = w[DD_SEITE], w["bitcoin-top-to-bottom.html"]
    pruefe("rueckgang heute", dd["ddnow"], "-20.0%")
    pruefe("quelle mit datum und preis", dd["ddnowsrc"],
           "price of 22 September 2026, 99,821 USD")
    pruefe("tage seit dem hoch", dd["ddday"], "351")
    pruefe("tiefster punkt", dd["ddlowpct"], "-50.0%")
    pruefe("tiefpunkt mit datum", dd["ddlowsrc"], "30 June 2026, 62,388 USD")
    # hoch und tief sind beide um einen tag gerueckt, der abstand nicht
    pruefe("tag des tiefpunkts", dd["ddlowday"], "267")
    pruefe("tabellenzelle kurz", dd["r25low"], "30 Jun 2026, 62,388")
    pruefe("balkenbeschriftung offen", dd["ddbarlbl"], "-50.0% so far")
    pruefe("dieselbe zahl auf beiden seiten", ttb["dd"], dd["ddnow"])
    pruefe("schlusszeile der zyklusseite", ttb["ddts"],
           "price of 22 September 2026, 99,821 USD")
    pruefe("datum in der vergleichszeile", ttb["c25d"], "22 Sep 2026")
    pruefe("zyklus 2013 am selben tag", (ttb["c13"], ttb["c13d"]), ("-75.0%", "20 Nov 2014"))
    pruefe("zyklus 2017 am selben tag", (ttb["c17"], ttb["c17d"]), ("-80.0%", "2 Dec 2018"))
    pruefe("zyklus 2021 am selben tag", (ttb["c21"], ttb["c21d"]), ("-60.0%", "25 Oct 2022"))

    # ein archiv, das ein anderes hoch kennt als die seiten, darf nichts
    # stempeln. sonst stuende eine falsche zahl da, und zwar genau die.
    falsch = [{"d": HOCH_CLOSE, "btc": HOCH_WERT}, {"d": "2025-11-01", "btc": 999999.0},
              {"d": "2026-06-30", "btc": 1.0}]
    pruefe("fremdes hoch faellt auf", rueckgang_werte(falsch, tlog,
           datetime.date(2026, 9, 22))[0], None)
    pruefe("archiv ohne bitcoin faellt auf",
           rueckgang_werte([{"d": "2026-01-01", "gld": 1.0}], tlog)[0], None)
    pruefe("log ohne schluss faellt auf",
           rueckgang_werte(tarchiv, [{"d": "2026-09-22", "gld": 1.0}],
                           datetime.date(2026, 9, 22))[0], None)

    js2 = 'var LOW_CLOSE = 1, LOW_DATE = "2000-01-01";'
    fertig2, k1, k2 = setz_tief(js2, 58534.28, "2026-06-30")
    pruefe("tief gestempelt", fertig2,
           'var LOW_CLOSE = 58534.28, LOW_DATE = "2026-06-30";')
    pruefe("beide tief-zuweisungen", (k1, k2), (1, 1))
    pruefe("zweiter lauf ist ruhig",
           setz_tief(fertig2, 58534.28, "2026-06-30")[0], fertig2)

    # --- die bullenseite ---
    pruefe("ganze prozent hoch", proz0(150.0, 100.0), "+50")
    pruefe("ganze prozent runter", proz0(50.0, 100.0), "-50")
    pruefe("grosse prozent mit trenner", proz0(19279.90, 172.0), "+11,109")
    pruefe("rundet ab", proz0(147.4, 100.0), "+47")
    pruefe("rundet auf", proz0(147.6, 100.0), "+48")
    # Math.round rundet die halbe Stelle nach oben, auch im negativen.
    pruefe("halbe stelle negativ wie javascript", proz0(52.5, 100.0), "-47")

    # ein vollstaendiger durchlauf auf gesetzten zahlen, fester stichtag
    barchiv = [{"d": "2015-01-14", "btc": 100.0}, {"d": "2017-12-16", "btc": 10000.0},
               {"d": "2018-12-15", "btc": 200.0}, {"d": "2021-11-08", "btc": 4000.0},
               {"d": "2022-11-21", "btc": 500.0}, {"d": HOCH_CLOSE, "btc": HOCH_WERT},
               {"d": "2026-06-30", "btc": 50000.0}]
    blog = [{"d": "2026-09-22", "btc": 75000.0}]
    w, grund = bullrun_werte(barchiv, blog, datetime.date(2026, 9, 23))
    pruefe("kein grund zum abbruch", grund, None)
    # 2015-01-14 -> 2017-12-16 sind 1067 tage, 2018-12-15 -> 2021-11-08 sind
    # 1059, 2022-11-21 -> 2025-10-06 sind 1050. spanne also 17 tage.
    pruefe("spanne der drei bullen", w["blrange"], "1,050 to 1,067 days")
    pruefe("dieselbe zahl im kasten", w["blrange2"], "1,050 to 1,067")
    pruefe("streuung", w["blspread"], "17 days")
    pruefe("faq zaehlt alle drei auf", w["blfaq"], "1,067, 1,059 and 1,050 days")
    pruefe("tage seit dem tief", w["blnow"], "85")
    pruefe("dieselbe zahl in der tabelle", w["r26days"], "85")
    pruefe("tief mit datum und preis", w["blnowsrc"], "days since 30 June 2026, 50,000 USD")
    pruefe("balken bleibt offen", w["blbarlbl"], "85 and counting")
    pruefe("tabellenzelle kurz", w["r26low"], "30 Jun 2026, 50,000")
    pruefe("anstieg bisher", w["r26gain"], "+50%")

    # faellt bitcoin unter das bisherige tief, zaehlt die seite ab dem neuen
    # tag. genau dafuer steht "if that low holds" auf der seite.
    tiefer = barchiv + [{"d": "2026-08-01", "btc": 40000.0}]
    w2, _ = bullrun_werte(tiefer, blog, datetime.date(2026, 9, 23))
    pruefe("neues tief zieht den zaehler nach", (w2["blnow"], w2["r26low"]),
           ("53", "1 Aug 2026, 40,000"))

    pruefe("fehlender eckpunkt faellt auf",
           bullrun_werte([{"d": "2015-01-14", "btc": 1.0}], blog,
                         datetime.date(2026, 9, 23))[0], None)
    pruefe("log ohne schluss faellt auf",
           bullrun_werte(barchiv, [{"d": "2026-09-22", "gld": 1.0}],
                         datetime.date(2026, 9, 23))[0], None)

    # --- wache 1, die abgeschlossenen anstiege ---
    # der echte fall vom 23.09.2026: 1990,47 darf nicht ueber 1990,5 auf
    # 1991 laufen. einmal runden, nicht zweimal.
    pruefe("anstieg 2018 bis 2021 rundet einmal", proz0(67562.17, 3231.91), "+1,990")
    pruefe("und nicht ueber die zwischenstelle",
           round((67562.17 / 3231.91 - 1) * 100, 1), 1990.5)
    pruefe("anstieg 2015 bis 2017", proz0(19279.90, 172.00), "+11,109")
    pruefe("anstieg 2022 bis 2025", proz0(124776.68, 15759.61), "+692")
    pruefe("alle drei auf einmal",
           bull_anstiege([("2015-01-14", 172.00), ("2017-12-16", 19279.90),
                          ("2018-12-15", 3231.91), ("2021-11-08", 67562.17),
                          ("2022-11-21", 15759.61), (HOCH_CLOSE, HOCH_WERT)]),
           ["+11,109", "+1,990", "+692"])
    pruefe("fehlender eckpunkt meldet nichts statt irgendwas",
           bull_anstiege([("2015-01-14", 172.00)]), None)

    drei = ["+11,109", "+1,990", "+692"]
    ok_seite = "11,109 percent and +1,990% and +692%"
    pruefe("richtige seite faellt nicht auf", anstieg_funde(ok_seite, drei), [])
    pruefe("beide schreibweisen werden eingesammelt",
           anstiege_im_text("+1,990% im text, 692 percent im json-ld"),
           ["1,990", "692"])
    # streuungsspalten sind keine anstiege und duerfen nicht anschlagen
    pruefe("prozent mit nachkommastelle zaehlt nicht",
           anstiege_im_text("spread 1.6% gegen 11.0%"), [])

    # der echte fehler vom 23.09.2026: eine stelle daneben
    pruefe("eine stelle daneben faellt auf",
           [f.split(" steht")[0] for f in
            anstieg_funde("11,109 percent, +1,991%, 1,990 percent, +692%", drei)],
           ["1,991"])
    # was der alte nachbarcheck NICHT gefangen haette: ein zahlendreher
    # hier meldet die wache zwei dinge auf einmal: der fremde wert steht da
    # UND der richtige fehlt. beides ist gewollt, deshalb je ein fall.
    pruefe("zahlendreher faellt auf",
           [f.split(" steht")[0] for f in
            anstieg_funde("11,109 percent and +1,909% and +692%", drei)
            if " steht da" in f],
           ["1,909"])
    pruefe("und die fehlende richtige zahl faellt gleich mit auf",
           [f for f in anstieg_funde("11,109 percent and +1,909% and +692%", drei)
            if "fehlt" in f], ["1,990 fehlt"])
    # eine veraltete zahl aus einem frueheren backfill
    pruefe("veralteter wert faellt auf",
           [f.split(" steht")[0] for f in
            anstieg_funde("11,109 percent, +1,990%, +688%, +692%", drei)],
           ["688"])
    pruefe("fehlende zahl faellt auf",
           [f for f in anstieg_funde("+1,990% and +692%", drei) if "fehlt" in f],
           ["11,109 fehlt"])

    # ein vierter anstieg, den wir bewusst dazunehmen: erst rot, dann gruen,
    # sobald er in der gerechneten menge steht.
    vier_seite = ok_seite + " and +1,234%"
    pruefe("neuer anstieg faellt erst durch",
           [f.split(" steht")[0] for f in anstieg_funde(vier_seite, drei)], ["1,234"])
    pruefe("und wird gruen, sobald er gerechnet ist",
           anstieg_funde(vier_seite, drei + ["+1,234"]), [])
    # der laufende anstieg kommt mit prozentzeichen herein
    pruefe("laufender anstieg wird mitgenommen",
           anstieg_funde(ok_seite + " and +47%", drei + ["+47%"]), [])

    pruefe("teil einer groesseren zahl zaehlt nicht",
           _zahl_steht("das sind 1,692 dollar", "692"), False)
    pruefe("und mit vorzeichen davor schon", _zahl_steht("+692%", "692"), True)

    # --- wache 2, kein abgeleitetes datum ---
    pruefe("sauberer text faellt nicht auf",
           prognose_funde("<h1>x</h1><p>1,050 days from the low of 30 June 2026.</p>"), [])
    # das jahr wird gegen das LAUFENDE jahr geprueft, nicht gegen eine
    # feste 2027. sonst schlaegt die wache am 01.01.2027 auf jeder seite an,
    # die schlicht das aktuelle jahr nennt.
    pruefe("kommendes jahr faellt auf",
           prognose_funde("<p>that lands in 2027.</p>", jahr=2026), ["2027"])
    pruefe("auch ein spaeteres jahr", prognose_funde("<p>2031</p>", jahr=2026), ["2031"])
    pruefe("vergangene jahre sind in ordnung",
           prognose_funde("<p>2015, 2021, 2025 and 2026</p>", jahr=2026), [])
    # gefaelschtes systemjahr: dieselbe seite, ein jahr spaeter gelesen
    pruefe("2027 ist 2027 kein fund mehr",
           prognose_funde("<p>that lands in 2027.</p>", jahr=2027), [])
    pruefe("2028 waere es dann aber",
           prognose_funde("<p>2027 and 2028</p>", jahr=2027), ["2028"])
    pruefe("und 2031 gelesen faellt gar kein jahr mehr auf",
           prognose_funde("<p>2027, 2028, 2029, 2030, 2031</p>", jahr=2031), [])
    # ohne angabe gilt das echte systemjahr
    pruefe("ohne angabe das laufende jahr",
           prognose_funde("<p>%d</p>" % (heute().year + 1)), [str(heute().year + 1)])
    pruefe("das laufende jahr selbst ist sauber",
           prognose_funde("<p>%d</p>" % heute().year), [])
    # vierstellige zahlen, die keine jahresform haben, bleiben aussen vor
    pruefe("day 1200 ist kein jahr", prognose_funde("<p>day 1200</p>", jahr=2026), [])
    pruefe("rechenbeispiel faellt auf",
           prognose_funde("<p>that would put the next top around then.</p>"), ["would put"])
    pruefe("weitere wendungen faellen auf",
           sorted(prognose_funde("<p>points to, targets, expect, due in, by 20</p>")),
           ["by 20", "due in", "expect", "points to", "targets"])
    # die fusszeile steht auf jeder seite und sagt das gegenteil
    pruefe("fusszeile ausgenommen",
           prognose_funde("<h1>x</h1><footer>No hype, no price targets. 2031</footer>"), [])
    pruefe("die echte seite ist sauber",
           prognose_funde(open(os.path.join(REPO, BL_SEITE), encoding="utf-8").read())
           if os.path.exists(os.path.join(REPO, BL_SEITE)) else [], [])

    # die acht eckpunkte muessen dieselben sein wie auf den anderen seiten
    pruefe("bullenhochs sind die zyklushochs",
           [h for _, h in ZYKLEN],
           [t for _, t in VORZYKLEN][1:] + [HOCH_CLOSE])

    # --- die goldseite ---
    pruefe("zwei stellen mit vorzeichen", proz2(105.0, 100.0), "+5.00%")
    pruefe("und nach unten", proz2(95.0, 100.0), "-5.00%")
    # der grund fuer die zweite stelle: -5,0279 darf nicht als -5,0
    # dastehen, sonst liest man "innerhalb von fuenf prozent" heraus.
    pruefe("die zweite stelle traegt die aussage",
           proz2(161.88, 170.45), "-5.03%")

    # gesetztes archiv: boersentage nur mo-fr, btc jeden tag.
    # 2013-12-04 ist ein mittwoch, 2015-01-14 ein mittwoch,
    # 2017-12-16 ein SAMSTAG, 2018-12-15 ein SAMSTAG.
    garchiv = []
    for tag, b, g, sp in (
            ("2013-12-04", 1000.0, 100.0, 100.0),
            ("2015-01-14", 150.0, 98.0, 110.0),
            ("2017-12-15", None, 200.0, 200.0),   # freitag vor dem samstag
            ("2017-12-16", 2000.0, None, None),   # samstag, nur btc
            ("2018-12-14", None, 190.0, 180.0),   # freitag vor dem samstag
            ("2018-12-15", 400.0, None, None),    # samstag, nur btc
            ("2021-11-08", 5000.0, 300.0, 300.0),
            ("2022-11-21", 1000.0, 285.0, 240.0),
            (HOCH_CLOSE, 10000.0, 400.0, 400.0),
            ("2026-06-30", 5000.0, 404.0, 440.0),
            ("2026-09-22", 7000.0, 440.0, 460.0)):
        z = {"d": tag}
        if b is not None:
            z["btc"] = b
        if g is not None:
            z["gld"] = g
            z["spy"] = sp
        garchiv.append(z)
    # der rechte rand kommt aus dem LOG, nicht aus dem archiv, genau wie
    # im echten lauf. das archiv endet hier am 22., das log am 23.
    glog = [{"d": "2026-09-22", "btc": 6500.0}, {"d": "2026-09-23", "btc": 7000.0}]
    w, grund = gold_werte(garchiv, glog)
    pruefe("kein grund zum abbruch", grund, None)
    pruefe("fenster 1 btc", w["b1btc"], "-85.00%")
    pruefe("fenster 1 gold", w["b1gld"], "-2.00%")
    pruefe("fenster 1 aktien", w["b1spy"], "+10.00%")
    # hier zaehlt der rueckgriff: der samstag hat keinen gld-wert, also
    # muss der freitag davor genommen werden, an beiden raendern.
    pruefe("samstagsgrenze greift auf den freitag zurueck",
           (w["b2gld"], w["b2spy"]), ("-5.00%", "-10.00%"))
    pruefe("btc rechnet am samstag selbst", w["b2btc"], "-80.00%")
    pruefe("fenster 3 gold", w["b3gld"], "-5.00%")
    # der laufende: einmal bis zum tief, einmal bis zum archivrand
    pruefe("laufend bis zum tief", (w["b4btc"], w["b4gld"]), ("-50.00%", "+1.00%"))
    pruefe("laufend bis zum rand", (w["b5btc"], w["b5gld"]), ("-30.00%", "+10.00%"))
    pruefe("faq und fliesstext tragen dieselbe zahl",
           (w["cur1"], w["cur2"], w["faq1"]), (w["b4gld"], w["b5gld"], w["b5gld"]))

    # gold gegen den hoechsten schluss im archiv
    pruefe("spitze gefunden", (w["gpeakd"], w["gpeak"]), ("22 September 2026", "440.00"))
    pruefe("stand heute", (w["gnowd"], w["gnow"]), ("22 September 2026", "440.00"))
    pruefe("kein abstand, wenn heute die spitze ist", w["gdd"], "0.00%")

    # spannen aus den UNGERUNDETEN werten. gold -2, -5, -5 spannt 3,00.
    pruefe("goldspanne", w["gldspread"], "3.00")
    # spy: +10,00 / -10,00 / -20,00 im testarchiv, spanne also 30,00
    pruefe("aktienspanne", w["spyspread"], "30.00")

    # "innerhalb von" wird aufgerundet, nie ab
    # genau 5,00 bleibt 5,0 und wird nicht von der gleitkommaunschaerfe
    # auf 5,1 hochgezogen
    pruefe("genau fuenf bleibt fuenf", w["gworst"], "within 5.0%")
    g2 = [dict(z) for z in garchiv]
    for z in g2:
        if z["d"] == "2022-11-21":
            z["gld"] = 284.9          # -5,0333 prozent
    w2, _ = gold_werte(g2, glog)
    pruefe("5,03 wird zu 5,1 und nicht zu 5,0", w2["gworst"], "within 5.1%")

    pruefe("archiv ohne gold faellt auf",
           gold_werte([{"d": "2020-01-01", "btc": 1.0}], glog)[0], None)
    pruefe("log ohne schluss faellt auf",
           gold_werte(garchiv, [{"d": "2026-09-23", "gld": 1.0}])[0], None)
    # der stichtag der goldseite ist der LOGRAND, nicht der archivrand.
    # genau daran ist am 24.09.2026 das zweite "heute" entstanden.
    pruefe("stichtag kommt aus dem log", w["b5tag"], "2026-09-23")
    pruefe("und nicht aus dem archiv", w["b5tag"] != garchiv[-1]["d"], True)
    pruefe("das enddatum auf der seite passt dazu", w["b5end"], "23 Sep 2026")
    # --- die gemeinsame vorrangregel ---
    a = [{"d": "2026-09-22", "gld": 1.0}, {"d": "2026-09-23", "gld": 2.0}]
    l = [{"d": "2026-09-23", "gld": 99.0}, {"d": "2026-09-24", "gld": 3.0}]
    pruefe("am gemeinsamen tag gewinnt das log",
           reihe_mit_logvorrang("gld", archiv=a, log=l),
           [("2026-09-22", 1.0), ("2026-09-23", 99.0), ("2026-09-24", 3.0)])
    # die reihenfolge laesst sich nicht mehr versehentlich drehen
    fehl = None
    try:
        reihe_mit_logvorrang("gld", a, l)
    except TypeError as exc:
        fehl = "positional"
    pruefe("archiv und log sind keyword-only", fehl, "positional")
    pruefe("null und leeres faellt raus",
           reihe_mit_logvorrang("gld", archiv=[{"d": "x", "gld": 0}, "kein dict"],
                                log=[{"d": "y"}]), [])

    # --- what-if ---
    pruefe("usd unter einer million", wi_usd(1880.6), "$1,881")
    pruefe("usd in millionen", wi_usd(2_500_000), "$2.50M")
    pruefe("usd in milliarden", wi_usd(3_100_000_000), "$3.10B")
    pruefe("preis ab hundert ohne cents", wi_px(84424.0), "$84,424")
    pruefe("preis darunter mit cents", wi_px(44.889), "$44.89")
    pruefe("fuenf jahre zurueck", wi_jahre_zurueck("2026-09-23", 5), "2021-09-23")
    # javascript schiebt den 29. februar auf den 1. maerz, wenn das zieljahr
    # keinen hat. das muss hier genauso laufen.
    pruefe("schalttag wie in javascript", wi_jahre_zurueck("2024-02-29", 3), "2021-03-01")
    pruefe("schalttag auf schaltjahr bleibt", wi_jahre_zurueck("2024-02-29", 4), "2020-02-29")

    # der 20.09. liegt VOR dem stichtag 2021-09-23 und darf nicht genommen
    # werden. wuerde er es, kaeme 4000 statt 2000 heraus.
    reihe = [("2021-09-20", 50.0), ("2021-09-30", 100.0), ("2026-09-23", 200.0)]
    r = wi_lump(reihe, 1000.0, 5)
    pruefe("einmalkauf nimmt den ersten tag AB dem stichtag",
           (r["davor"][0], r["wert"]), ("2021-09-30", 2000.0))
    pruefe("ohne genug reihe nichts", wi_lump([], 1000.0, 5), None)

    # sparplan: monatsende von 2025-10 bis 2026-09, also 12 kaeufe
    mreihe = []
    for j, m in [(2025, x) for x in range(9, 13)] + [(2026, x) for x in range(1, 10)]:
        mreihe.append(("%04d-%02d-%02d" % (j, m, 28), 10.0))
    mreihe.append(("2026-09-23", 10.0))
    mreihe.sort()
    d = wi_dca(mreihe, 100.0, 1)
    pruefe("sparplan zaehlt die monatsenden", (d["kaeufe"], d["paid"]), (12, 1200.0))
    pruefe("und bewertet zum letzten kurs", d["wert"], 1200.0)
    pruefe("unter sechs kaeufen nichts", wi_dca(mreihe[:3], 100.0, 1), None)

    # die voreinstellungen muessen zu denen im html passen, sonst stempelt
    # der lauf eine ansicht, die niemand zu sehen bekommt
    wipfad = os.path.join(REPO, WI_SEITE)
    if os.path.exists(wipfad):
        with open(wipfad, encoding="utf-8") as fh:
            wihtml = fh.read()
        def _vor(kennung):
            m = re.search(r'id="%s"[^>]*value="([^"]*)"' % kennung, wihtml)
            return float(m.group(1)) if m else None
        pruefe("einmalkauf-betrag wie im html", _vor("l-amt"), WI_LUMP[1])
        pruefe("sparplan-betrag wie im html", _vor("d-amt"), WI_DCA[1])
        pruefe("tagesbetrag wie im html", _vor("a-amt"), WI_DAY[0])
        pruefe("what-if steht in der leiste",
               WI_SEITE in [d for d, _ in SEITEN], True)

    # --- die kopf-wache ---
    seite = ('<head><meta name="description" content="fiel -53.1% am 30 June 2026">'
             '</head><body><b id="a">-53.1%</b><b id="b">267</b></body>')
    pruefe("gestempelter wert im kopf faellt auf",
           kopf_funde("x.html", seite, {"a": "-53.1%", "b": "267"}),
           ["a='-53.1%' steht auch im kopf"])
    pruefe("was nur im rumpf steht ist in ordnung",
           kopf_funde("x.html", seite, {"b": "267"}), [])
    pruefe("ohne kopf kein fund", kopf_funde("x.html", "<body>-53.1%</body>",
           {"a": "-53.1%"}), [])
    pruefe("nur_kopf schneidet vor dem schliessenden tag ab",
           nur_kopf("<head>oben</head><body>unten</body>"), "<head>oben")
    pruefe("ohne head bleibt nichts uebrig", nur_kopf("<body>nur rumpf</body>"), "")
    # die angemeldete ausnahme: ein abgeschlossener wert darf doppelt stehen
    pruefe("angemeldete ausnahme schweigt",
           kopf_funde("bitcoin-bull-run-length.html",
                      "<head>1,050 to 1,067</head><body>x</body>",
                      {"blrange2": "1,050 to 1,067"}), [])
    pruefe("aber nur fuer ihre eigene seite",
           kopf_funde("andere.html", "<head>1,050 to 1,067</head><body>x</body>",
                      {"blrange2": "1,050 to 1,067"}),
           ["blrange2='1,050 to 1,067' steht auch im kopf"])
    pruefe("leerer wert schlaegt nicht an",
           kopf_funde("x.html", "<head></head><body></body>", {"a": ""}), [])
    # jede ausnahme muss eine id sein, die es auch gibt, sonst schuetzt sie
    # nichts und niemand merkt es
    pruefe("keine ausnahme ohne seite",
           [d for d in KOPF_AUSNAHMEN if not os.path.exists(os.path.join(REPO, d))], [])

    # --- die stichtagswache ---
    seiten = {"a.html": "2026-09-23", "b.html": "2026-09-23"}
    text = {"a.html": "price of 23 September 2026",
            "b.html": "as of 23 September 2026"}
    pruefe("gleicher tag, beide nennen ihn",
           stichtag_funde(seiten, lambda d: text[d]), [])
    # der echte fall vom 24.09.2026: die goldseite rechnete auf den
    # archivrand, die drei anderen auf den marktlog.
    zwei = {"a.html": "2026-09-23", "b.html": "2026-09-22"}
    pruefe("zwei verschiedene heute halten den lauf an",
           stichtag_funde(zwei, lambda d: "egal"),
           ["a.html rechnet auf 2026-09-23", "b.html rechnet auf 2026-09-22"])
    # gleicher tag, aber eine seite nennt ihn nicht: dann wurde sie nicht
    # gestempelt und zeigt noch gestern
    pruefe("stiller tag faellt auf",
           stichtag_funde(seiten, lambda d: text[d] if d == "a.html" else "nichts"),
           ["b.html nennt 23 September 2026 nicht"])
    pruefe("leere sammelstelle faellt auf", stichtag_funde({}, lambda d: ""),
           ["keine zyklusseite hat einen stichtag eingetragen"])
    pruefe("eine einzige seite reicht",
           stichtag_funde({"a.html": "2026-09-23"}, lambda d: text[d]), [])
    # drei gegen eine, alle vier werden gemeldet, damit man sieht welche
    drei = {"a.html": "2026-09-23", "b.html": "2026-09-23",
            "c.html": "2026-09-23", "d.html": "2026-09-21"}
    pruefe("alle vier werden genannt", len(stichtag_funde(drei, lambda d: "egal")), 4)
    # die halving-seite zeigt keinen PREIS, aber sie zaehlt tage, und
    # dafuer steht sie sehr wohl in der zweiten gruppe.
    pruefe("halving-seite traegt keinen preisstichtag",
           "bitcoin-halving-to-top.html" in SCHLUSS_SEITEN, False)
    pruefe("aber sie muss ihren zaehltag nennen",
           "bitcoin-halving-to-top.html" in NENNT_ZAEHLTAG, True)
    # der DAY-N-Post zaehlt seit dem 24.09.2026 bis heute, wie die Seiten,
    # und gehoert damit in dieselbe Gruppe.
    pruefe("der day-n-post steht in der zaehltag-gruppe",
           "dayn.yml" in ZAEHLTAG_MIT, True)
    pruefe("und wird beim lauf wirklich eingetragen",
           zaehltag_nachtragen().get("dayn.yml"), heute().isoformat())
    pruefe("er nennt seinen zaehltag nicht auf einer seite, also keine "
           "nennpflicht", "dayn.yml" in NENNT_ZAEHLTAG, False)
    pruefe("und sie hat eine id dafuer",
           ZYKLUS_ASOF.get("bitcoin-halving-to-top.html"), "hvasof")

    # nennen: nur die genannten seiten muessen den tag ausschreiben
    drei2 = {"a.html": "2026-09-24", "b.html": "2026-09-24"}
    pruefe("ohne nennpflicht reicht uebereinstimmung",
           stichtag_funde(drei2, lambda d: "nichts", nennen=()), [])
    pruefe("mit nennpflicht wird ausgeschrieben verlangt",
           stichtag_funde(drei2, lambda d: "nichts", nennen=("b.html",)),
           ["b.html nennt 24 September 2026 nicht"])
    pruefe("und erfuellt schweigt sie",
           stichtag_funde(drei2, lambda d: "24 September 2026",
                          nennen=("b.html",)), [])
    # ein eingefrorener zaehler: die seite zaehlt noch gegen gestern
    pruefe("eingefrorener zaehltag faellt auf",
           stichtag_funde({"a.html": "2026-09-24", "b.html": "2026-09-23"},
                          lambda d: "egal"),
           ["a.html rechnet auf 2026-09-24", "b.html rechnet auf 2026-09-23"])

    pruefe("goldseite in der leiste",
           "gold-in-bitcoin-bear-markets.html" in [d for d, _ in SEITEN], True)
    pruefe("bullenpille ist gekuerzt",
           dict((n, d) for d, n in SEITEN)["bull run"], "bitcoin-bull-run-length.html")

    # die neue seite muss in der leiste stehen und in beiden stempelwegen
    pruefe("bullenseite in der leiste",
           "bitcoin-bull-run-length.html" in [d for d, _ in SEITEN], True)
    pruefe("bullenseite bekommt LAST_CLOSE", BL_SEITE in SCHLUSS_SEITEN, True)
    pruefe("bullenseite bekommt LOW_CLOSE", BL_SEITE in TIEF_SEITEN, True)
    pruefe("drawdownseite in der leiste",
           "bitcoin-drawdown.html" in [d for d, _ in SEITEN], True)
    pruefe("drawdownseite bekommt LAST_CLOSE", DD_SEITE in SCHLUSS_SEITEN, True)

    # die gesamtzahl kommt aus der fallliste, nicht von hand.
    print("%d von %d faellen falsch" % (schlecht, gezaehlt))
    return 1 if schlecht else 0


def main(argv):
    if "--selftest" in argv:
        return selbsttest()
    print("pulsehawk seitenstempel")
    print("laufzeitpunkt %s utc\n"
          % datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    fehler = (lauf_leiste() + lauf_zyklus() + lauf_dominanz() + lauf_markt()
              + lauf_schluss() + lauf_rueckgang() + lauf_bullrun()
              + lauf_gold() + lauf_whatif() + lauf_stichtag())
    if fehler:
        print("\n%d seite(n) nicht gestempelt" % fehler)
        return 1
    print("\nfertig")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
