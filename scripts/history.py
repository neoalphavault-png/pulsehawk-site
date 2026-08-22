#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
pulsehawk - langzeitarchiv

WARUM ES DAS GIBT
THE MARKET FORGETS lebt von Saetzen wie "vor zehn Jahren stand Bitcoin bei
586 Dollar". Solche Zahlen kursieren staendig, und fast nie zaehlt sie
jemand nach. Wenn wir sie von anderen uebernehmen, sind wir das, was wir
anderen vorwerfen, naemlich ein Kanal der weiterreicht statt zu messen.

Also holen wir die Historie einmal selbst und schreiben sie in unser
eigenes Repo. Danach hat jeder Tag im Jahr seine eigene belegbare Zahl,
fuer immer, ohne weitere Abfrage.

WARUM EINE EIGENE DATEI
data/market-log.json ist die taegliche Reihe mit allen Feldern. Sie wird
zweimal am Tag gelesen und geschrieben, vom Marktlogger und vom
Seitenstempel. Zehntausend alte Zeilen haetten dort nichts zu suchen, sie
wuerden jeden Lauf verlangsamen und jeden Diff unlesbar machen.
data/history.json ist deshalb getrennt und wird genau einmal gefuellt.

Die Zeilenform ist dieselbe wie im Marktlog, damit beide Dateien mit
demselben Werkzeug gelesen werden koennen.

WAS DRIN IST
btc von CoinGecko, gld und spy von Twelve Data. Krypto sieben Tage die
Woche, die beiden anderen nur an Handelstagen. Wochenenden bleiben bei
gld und spy leer, das ist gewollt und ehrlich.

    python3 scripts/history.py --backfill              einmalig, holt die historie
    python3 scripts/history.py --rueckblick 2026-08-26 was war vor n jahren
    python3 scripts/history.py --selftest              rechnet ohne netz
"""

import datetime
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# eine einzige stelle fuer die quellen und fuer die plausibilitaetsgrenzen.
# doppelt gefuehrte grenzen laufen frueher oder spaeter auseinander.
from market_log import (BAND, CG, TD, TD_KEY, get_json, load_log,
                        merge, _hide)  # noqa: E402

REPO = os.path.dirname(HERE)
ARCHIV = os.path.join(REPO, "data", "history.json")
LOG = os.path.join(REPO, "data", "market-log.json")

JAHRE = 11          # ein jahr mehr als wir brauchen, damit der rand sitzt
TAG = 86400
FELDER = ["gld", "spy", "btc"]

MONATE = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

# DAS BAND DER HISTORIE IST EIN ANDERES
# Der taegliche Logger fragt "kann dieser wert heute stimmen" und wirft
# deshalb alles unter tausend dollar bei Bitcoin weg. Fuer die Historie
# waere das toedlich, 2016 stand Bitcoin wirklich bei knapp sechshundert
# und 2013 unter hundert. Die Untergrenzen werden hier also aufgemacht,
# die Obergrenzen bleiben, wie der Logger sie kennt. So bleibt eine
# einzige Stelle fuer die Frage, was oben noch plausibel ist.
BAND_ARCHIV = dict(BAND)
for _feld, _unten in (("btc", 0.01), ("eth", 0.01), ("gld", 5.0), ("spy", 5.0)):
    if _feld in BAND_ARCHIV:
        BAND_ARCHIV[_feld] = (_unten, BAND_ARCHIV[_feld][1])


def im_band(feld, wert):
    """dieselbe pruefung wie im logger, nur mit dem weiteren band."""
    grenzen = BAND_ARCHIV.get(feld)
    if grenzen is None or wert is None:
        return True
    try:
        zahl = float(wert)
    except (TypeError, ValueError):
        return False
    return grenzen[0] <= zahl <= grenzen[1]


# --- werkzeug --------------------------------------------------------

def tag_von(stempel):
    return time.strftime("%Y-%m-%d", time.gmtime(stempel))


def lang(iso):
    t = iso.split("-")
    return "%d %s %s" % (int(t[2]), MONATE[int(t[1]) - 1], t[0])


def datum(iso):
    return datetime.date(*[int(x) for x in iso.split("-")])


def jahre_zurueck(iso, n):
    """dasselbe datum n jahre frueher. der 29. februar faellt auf den 28.,
    weil es das jahr davor sonst gar nicht gibt."""
    d = datum(iso)
    try:
        return d.replace(year=d.year - n).isoformat()
    except ValueError:
        return d.replace(year=d.year - n, day=28).isoformat()


def naechste_zeile(rows, ziel, feld, spanne=6):
    """
    die zeile, die dem zieldatum am naechsten liegt und das feld hat.
    boersen haben feiertage und wochenenden, ein exaktes datum trifft
    deshalb oft ins leere. wir suchen von innen nach aussen, damit der
    kleinste abstand gewinnt, und geben den abstand mit zurueck, damit
    der aufrufer ihn nennen kann.

    bei gleichem abstand gewinnt der tag davor. das ist die uebliche
    lesart, man nimmt den letzten bekannten kurs und nicht einen, der
    zum stichtag noch gar nicht feststand.
    """
    nach = {}
    for r in rows:
        if isinstance(r, dict) and isinstance(r.get(feld), (int, float)):
            nach[r.get("d")] = r
    if not nach:
        return None, None
    z = datum(ziel)
    for weite in range(0, spanne + 1):
        for richtung in ((0,) if weite == 0 else (-1, 1)):
            k = (z + datetime.timedelta(days=weite * richtung)).isoformat()
            if k in nach:
                return nach[k], weite * richtung
    return None, None


def vielfaches(neu, alt):
    return float(neu) / float(alt)


def pro_jahr(faktor, jahre):
    """
    die jaehrliche rate hinter einem vielfachen. absichtlich als eigene
    funktion, weil genau hier der haeufigste fehler solcher posts sitzt.
    131 mal mehr in zehn jahren sind nicht 1310 prozent pro jahr.
    """
    if faktor <= 0 or jahre <= 0:
        return 0.0
    return (faktor ** (1.0 / jahre) - 1.0) * 100.0


def verdopplungen(faktor):
    return math.log(faktor, 2) if faktor > 0 else 0.0


# --- quellen ---------------------------------------------------------

def cg_verlauf(coin, tage):
    """
    tageskurse von coingecko. erst der einfache weg ueber days, und wenn
    der zu wenig liefert, jahresweise ueber den bereichsaufruf. beide
    endpunkte geben ab neunzig tagen von selbst tageswerte zurueck.
    """
    punkte = {}
    try:
        data = get_json("%s/coins/%s/market_chart?vs_currency=usd&days=%d"
                        % (CG, coin, tage))
        for stempel, preis in (data.get("prices") or []):
            punkte[tag_von(stempel / 1000.0)] = round(float(preis), 6)
        print("  OK    %-7s %d tage ueber days" % (coin, len(punkte)))
    except Exception as exc:  # noqa: BLE001
        print("  leer  %-7s days ging nicht, %s" % (coin, str(exc)[:70]))

    if len(punkte) >= tage * 0.8:
        return punkte

    print("  ...   %-7s zweiter versuch, jahresweise" % coin)
    ende = int(time.time())
    for i in range(int(tage / 365) + 1):
        bis = ende - i * 365 * TAG
        von = bis - 365 * TAG
        try:
            data = get_json("%s/coins/%s/market_chart/range"
                            "?vs_currency=usd&from=%d&to=%d" % (CG, coin, von, bis))
        except Exception as exc:  # noqa: BLE001
            print("  FEHL  %-7s %s bis %s, %s"
                  % (coin, tag_von(von), tag_von(bis), str(exc)[:50]))
            time.sleep(3)
            continue
        neu = 0
        for stempel, preis in (data.get("prices") or []):
            t = tag_von(stempel / 1000.0)
            if t not in punkte:
                neu += 1
            punkte[t] = round(float(preis), 6)
        print("  OK    %-7s %s bis %s, %d neu"
              % (coin, tag_von(von), tag_von(bis), neu))
        time.sleep(3)
    return punkte


def td_verlauf(symbol, punkte):
    """schlusskurse von twelve data. ein aufruf, ein credit."""
    if not TD_KEY:
        raise RuntimeError("kein twelvedata schluessel gesetzt")
    data = get_json("%s/time_series?symbol=%s&interval=1day&outputsize=%d&apikey=%s"
                    % (TD, symbol, punkte, TD_KEY))
    if str(data.get("status", "")).lower() == "error":
        raise RuntimeError(_hide(str(data.get("message", ""))[:120]))
    out = {}
    for row in data.get("values") or []:
        t = (row.get("datetime") or "")[:10]
        schluss = row.get("close")
        if t and schluss is not None:
            out[t] = round(float(schluss), 4)
    if not out:
        raise RuntimeError("keine werte fuer %s" % symbol)
    return out


# --- laeufe ----------------------------------------------------------

def zu_zeilen(reihen):
    """
    aus {feld: {tag: wert}} werden zeilen, eine je kalendertag. werte
    ausserhalb ihres bandes kommen gar nicht erst hinein, dieselbe regel
    wie im taeglichen logger.
    """
    tage = {}
    verworfen = []
    for feld, reihe in reihen.items():
        for t, wert in reihe.items():
            if not im_band(feld, wert):
                verworfen.append("%s %s %s" % (t, feld, wert))
                continue
            tage.setdefault(t, {"d": t})[feld] = wert
    return [tage[t] for t in sorted(tage)], verworfen


def lauf_backfill():
    reihen = {}
    tage = JAHRE * 365

    try:
        reihen["btc"] = cg_verlauf("bitcoin", tage)
    except Exception as exc:  # noqa: BLE001
        print("  FEHL  btc     %s" % str(exc)[:90])

    for feld, symbol in (("gld", "GLD"), ("spy", "SPY")):
        try:
            reihen[feld] = td_verlauf(symbol, tage)
            print("  OK    %-7s %d handelstage" % (feld, len(reihen[feld])))
        except Exception as exc:  # noqa: BLE001
            print("  FEHL  %-7s %s" % (feld, _hide(str(exc))[:90]))
        time.sleep(8)

    zeilen, verworfen = zu_zeilen(reihen)
    if verworfen:
        print("\n%d werte ausserhalb ihres bandes, nicht uebernommen" % len(verworfen))
        for v in verworfen[:10]:
            print("  " + v)

    if not zeilen:
        print("\nnichts geholt, archiv bleibt unveraendert")
        return 1

    alt = load_log(ARCHIV)
    rows = merge(alt, zeilen)
    os.makedirs(os.path.dirname(ARCHIV), exist_ok=True)
    with open(ARCHIV, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, separators=(",", ":"))
        fh.write("\n")

    print("\narchiv hat jetzt %d tage, %s bis %s"
          % (len(rows), rows[0]["d"], rows[-1]["d"]))
    for feld in FELDER:
        n = len([r for r in rows if r.get(feld) is not None])
        print("  %-4s %d tage" % (feld, n))
    return 0


def alle_zeilen():
    """archiv und taegliches log zusammen, nach tag sortiert. das archiv
    endet dort, wo der logger angefangen hat, beide zusammen sind
    lueckenlos."""
    rows = load_log(ARCHIV) + load_log(LOG)
    nach = {}
    for r in rows:
        if isinstance(r, dict) and isinstance(r.get("d"), str):
            nach.setdefault(r["d"], {"d": r["d"]}).update(
                dict((k, v) for k, v in r.items() if v is not None))
    return [nach[t] for t in sorted(nach)]


def rueckblick(rows, ziel, feld="btc", spannen=(1, 5, 10)):
    """
    was stand da vor n jahren, und was ist daraus geworden. gibt eine
    liste von befunden zurueck, jeder mit seinem eigenen datum, damit
    keine zahl ohne bezugspunkt herauskommt.
    """
    jetzt, _ = naechste_zeile(rows, ziel, feld)
    if not jetzt:
        return None, []
    befunde = []
    for n in spannen:
        alt, versatz = naechste_zeile(rows, jahre_zurueck(ziel, n), feld)
        if not alt:
            continue
        f = vielfaches(jetzt[feld], alt[feld])
        befunde.append({
            "jahre": n,
            "damals_tag": alt["d"],
            "damals": alt[feld],
            "versatz": versatz,
            "faktor": f,
            "pro_jahr": pro_jahr(f, n),
            "verdopplungen": verdopplungen(f),
        })
    return jetzt, befunde


def lauf_rueckblick(ziel, feld):
    rows = alle_zeilen()
    if not rows:
        print("kein archiv und kein log gefunden")
        return 1
    jetzt, befunde = rueckblick(rows, ziel, feld)
    if not jetzt:
        print("kein wert fuer %s um %s herum" % (feld, ziel))
        return 1

    print("rueckblick auf %s, feld %s" % (lang(ziel), feld))
    print("heutiger stand %s vom %s\n" % (jetzt[feld], lang(jetzt["d"])))
    if not befunde:
        print("keine vergleichsdaten weit genug zurueck")
        return 1
    for b in befunde:
        hinweis = ""
        if b["versatz"]:
            hinweis = "  (naechster handelstag, %+d tage)" % b["versatz"]
        wort = "jahr" if b["jahre"] == 1 else "jahren"
        print("  vor %d %s, %s%s"
              % (b["jahre"], wort, lang(b["damals_tag"]), hinweis))
        print("    stand              %s" % b["damals"])
        print("    das               %.1ffache" % b["faktor"])
        print("    pro jahr           %.1f prozent" % b["pro_jahr"])
        print("    verdopplungen      %.1f\n" % b["verdopplungen"])
    return 0


# --- selbsttest ------------------------------------------------------

def selbsttest():
    schlecht = [0]

    def pruefe(name, ist, soll):
        if ist != soll:
            schlecht[0] += 1
            print("  FEHL %s\n    ist  %r\n    soll %r" % (name, ist, soll))
        else:
            print("  ok   %s" % name)

    def fast(name, ist, soll, tol=0.05):
        pruefe(name, abs(ist - soll) < tol, True)

    pruefe("zehn jahre zurueck", jahre_zurueck("2026-08-23", 10), "2016-08-23")
    pruefe("ein jahr zurueck", jahre_zurueck("2026-01-01", 1), "2025-01-01")
    # der 29. februar existiert im vorjahr nicht und darf nicht umfallen
    pruefe("schalttag faellt auf den 28.", jahre_zurueck("2024-02-29", 1), "2023-02-28")

    pruefe("vielfaches", round(vielfaches(77004.71, 586.0), 1), 131.4)
    fast("pro jahr", pro_jahr(131.4, 10), 62.9)
    fast("verdopplungen", verdopplungen(131.4), 7.0)
    # der klassische fehler, den dieses format vermeiden soll
    pruefe("pro jahr ist nicht das vielfache geteilt durch jahre",
           round(pro_jahr(131.4, 10)) != round(13140.0 / 10), True)
    fast("verdoppelung ist hundert prozent", pro_jahr(2.0, 1), 100.0)
    pruefe("null faellt nicht um", pro_jahr(0.0, 10), 0.0)

    rows = [
        {"d": "2016-08-24", "btc": 586.0},
        {"d": "2021-08-23", "btc": 49500.0},
        {"d": "2026-08-21", "btc": 78154.0},
        {"d": "2026-08-23", "btc": 77004.71},
    ]

    # ein exakter treffer gewinnt
    z, v = naechste_zeile(rows, "2026-08-23", "btc")
    pruefe("exakter tag", (z["d"], v), ("2026-08-23", 0))

    # ohne exakten treffer gewinnt der kleinste abstand
    z, v = naechste_zeile(rows, "2016-08-23", "btc")
    pruefe("naechster handelstag", (z["d"], v), ("2016-08-24", 1))

    # bei gleichem abstand gewinnt der tag davor, der letzte bekannte kurs
    beide = [{"d": "2016-08-22", "btc": 585.0}, {"d": "2016-08-24", "btc": 586.0}]
    pruefe("gleichstand geht rueckwaerts",
           naechste_zeile(beide, "2016-08-23", "btc")[0]["d"], "2016-08-22")

    # ausserhalb der spanne wird nichts erfunden
    pruefe("zu weit weg", naechste_zeile(rows, "2019-01-01", "btc")[0], None)

    # ein feld, das es nicht gibt, liefert nichts statt irgendetwas
    pruefe("unbekanntes feld", naechste_zeile(rows, "2026-08-23", "gld")[0], None)

    jetzt, befunde = rueckblick(rows, "2026-08-23", "btc", spannen=(5, 10))
    pruefe("heutiger stand", jetzt["d"], "2026-08-23")
    pruefe("zwei spannen", [b["jahre"] for b in befunde], [5, 10])
    pruefe("zehn jahre findet den 24.", befunde[1]["damals_tag"], "2016-08-24")
    fast("faktor ueber zehn jahre", befunde[1]["faktor"], 131.4, 0.1)
    fast("faktor ueber fuenf jahre", befunde[0]["faktor"], 1.556, 0.01)

    # der waechter aus dem marktlogger gilt auch hier
    zeilen, verworfen = zu_zeilen({"btc": {"2016-08-24": 586.0,
                                           "2016-08-25": 5e15}})
    pruefe("kaputter wert kommt nicht ins archiv",
           [r["d"] for r in zeilen], ["2016-08-24"])
    pruefe("und wird gemeldet", len(verworfen), 1)
    # die obergrenze kommt weiter aus dem logger, die untergrenze nicht
    pruefe("obergrenze geerbt", BAND_ARCHIV["btc"][1], BAND["btc"][1])
    pruefe("untergrenze aufgemacht", BAND_ARCHIV["btc"][0], 0.01)
    pruefe("der logger wuerde 586 dollar wegwerfen", BAND["btc"][0], 1000.0)
    pruefe("das archiv nimmt sie", im_band("btc", 586.0), True)
    pruefe("unsinn faellt trotzdem", im_band("btc", 5e15), False)

    # zwei quellen am selben tag ergeben eine zeile
    zeilen, _ = zu_zeilen({"btc": {"2016-08-24": 586.0},
                           "gld": {"2016-08-24": 128.5}})
    pruefe("ein tag, eine zeile", zeilen,
           [{"d": "2016-08-24", "gld": 128.5, "btc": 586.0}])

    if schlecht[0]:
        print("\n%d faelle falsch" % schlecht[0])
        return 1
    print("\nselftest ok, 27 faelle")
    return 0


def main(argv):
    if "--selftest" in argv:
        return selbsttest()

    if "--rueckblick" in argv:
        i = argv.index("--rueckblick")
        ziel = argv[i + 1] if len(argv) > i + 1 else None
        if not ziel:
            ziel = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
        feld = "btc"
        if "--feld" in argv:
            feld = argv[argv.index("--feld") + 1]
        return lauf_rueckblick(ziel, feld)

    if "--backfill" in argv:
        print("pulsehawk langzeitarchiv, backfill")
        print("laufzeitpunkt %s utc"
              % time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
        print("twelvedata schluessel %s\n"
              % ("gesetzt" if TD_KEY else "FEHLT"))
        return lauf_backfill()

    print(__doc__.strip().splitlines()[-3])
    print("nichts zu tun. --backfill, --rueckblick oder --selftest")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
