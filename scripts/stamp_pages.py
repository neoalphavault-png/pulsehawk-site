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

import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
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
# Beide Seiten rechnen im Browser mit LAST_CLOSE weiter, also wird in beide
# gestempelt. Die Drawdownseite hat zusaetzlich LOW_CLOSE und LOW_DATE.
SCHLUSS_SEITEN = ("bitcoin-top-to-bottom.html", DD_SEITE)
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
        meldung = "letzter schluss %s vom %s" % (zahl(zeile["btc"]), zeile["d"])
        if datei == DD_SEITE:
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
        fehler += schreiben(pfad, alt, neu, datei,
                            "%d rueckgangszahlen, heute %s"
                            % (treffer, felder.get("ddnow") or felder.get("dd")))
    return fehler


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

    def pruefe(name, ist, soll):
        nonlocal schlecht
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
    pruefe("eigene seite nicht doppelt",
           leiste("markets.html").count("markets"), 1)
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

    # die neue seite muss in der leiste stehen und in beiden stempelwegen
    pruefe("drawdownseite in der leiste",
           "bitcoin-drawdown.html" in [d for d, _ in SEITEN], True)
    pruefe("drawdownseite bekommt LAST_CLOSE", DD_SEITE in SCHLUSS_SEITEN, True)

    print("%d von 90 faellen falsch" % schlecht)
    return 1 if schlecht else 0


def main(argv):
    if "--selftest" in argv:
        return selbsttest()
    print("pulsehawk seitenstempel")
    print("laufzeitpunkt %s utc\n"
          % datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    fehler = (lauf_leiste() + lauf_zyklus() + lauf_dominanz() + lauf_markt()
              + lauf_schluss() + lauf_rueckgang())
    if fehler:
        print("\n%d seite(n) nicht gestempelt" % fehler)
        return 1
    print("\nfertig")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
