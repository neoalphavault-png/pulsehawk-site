#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""day_n_post.py, der taegliche DAY-N-Post auf @pulsehawkio.

WARUM ES DAS GIBT
Bis zum 16.09.2026 war der taegliche PulseHawk-Short der Tagesbeitrag.
Er faellt weg. An seine Stelle tritt das, was ohnehin jeden Tag neu ist und
bisher nur auf der Seite stand: der Tageszaehler seit dem Zyklushoch. Eine
Zahl, jeden Tag, ohne Hand.

WARUM DIE BAUFORM SO AUSSIEHT (Belege: docs/projekt/befund-shares.md)
Geteilt wird nach Aktivierung, nicht nach Nuetzlichkeit. Staunen +30 %,
Ueberraschung +14 %, praktischer Nutzen nur +13 %, Traurigkeit MINUS 16 %.
Alle drei gereposteten Posts der Woche vom 08.09. hatten die Wendung in
Zeile 1 oder 2 und waren in EINEM Satz zitierbar. Also:

  Zeile 1  die Zahl, die staunen laesst, nackt und ohne Vorrede
  Zeile 2  das Gegenstueck, das sie einordnet: die drei Referenztage,
           mit der Quellzeile, weil dort die historische Aussage steht
  Zeile 3  DIE WENDUNG, der eine Satz, den jemand zitieren kann
  Zeile 4  was das Konto ist, als Grund wiederzukommen (feste Schlusszeile)

DIE WENDUNG KOMMT AUS DEN DATEN, NICHT AUS EINEM TEXTBAUSTEIN. Sie wird
danach gewaehlt, WO die heutige Zahl relativ zu den drei Tiefs der letzten
drei Zyklen liegt (406, 364, 378). Trifft keine Vorlage, bricht der Lauf ab
und meldet; lieber kein Post als ein flacher.

DIE TRAURIGKEITSREGEL. Jede Zahl, die einen Verlust beschreibt, braucht die
Wendung im selben Post. Ein Verlust allein ist der einzige gemessene
NEGATIVE Faktor fuers Teilen (-16 %). Enthaelt ein Post ein Wort aus
{below, down, less, fell, lost} und fehlt die Wendung, bricht der Lauf ab.
Das gilt auch fuer die Selbstantwort, die keine Wendung traegt und deshalb
gar kein Verlustwort tragen darf.

KEIN LINK IM HAUPTPOST. Ein externer Link kostet 50-90 % Reichweite und bei
X 0,20 $ statt 0,015 $. Der Link auf pulsehawk.io geht als SELBSTANTWORT
darunter, als eigener Beitrag.

EIN BILD, PFLICHT. Kein Text ohne Bild. Weitergeschickt wird oft nur das
Bild, deshalb steht die Wendung auch darin. Schlaegt scripts/day_n_cover.py
fehl, wird nicht gepostet.

VIER SPERREN, DAMIT NIE UNSINN RAUSGEHT
  1. Der Schluss muss frisch sein. Ist die juengste btc-Zeile aelter als
     --max-age Tage (Standard 3), wird nicht gepostet. Ein Marktlogger, der
     still steht, hat das Haus schon einmal zwoelf Tage gekostet.
  2. Die Zahl im Post muss der Zahl auf der Seite entsprechen. Gelesen wird
     LAST_CLOSE / LAST_DATE aus bitcoin-top-to-bottom.html; weichen sie vom
     Log ab, bricht der Lauf ab. Der Seitenstempel laeuft vorher, also ist
     eine Abweichung ein echter Fehler und kein Zeitversatz.
  3. Doppelpost-Sperre ueber x_post.py, Schluessel dayn-<datum des schlusses>.
     Zwei Laeufe am selben Tag posten einmal. data/x-post-log.json merkt es.
  4. Ohne Wendung und ohne Bild geht nichts raus.

KEIN KURSZIEL, KEINE PROGNOSE, KEIN MOTIV, KEIN GEDANKENSTRICH, KEIN PFEIL.

    python3 scripts/day_n_post.py --dry-run
    python3 scripts/day_n_post.py --dry-run --tag 364     # Trockenlauf Fall B
    python3 scripts/day_n_post.py --post
    python3 scripts/day_n_post.py --selftest
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LOG = os.path.join(REPO, "data", "market-log.json")
SEITE = os.path.join(REPO, "bitcoin-top-to-bottom.html")
XLOG = os.path.join(REPO, "data", "x-post-log.json")
BILD = os.path.join(REPO, "build", "day-n.png")

# dieselben Konstanten wie im Skript auf der Seite. Wer eine davon aendert,
# muss die andere mitaendern; der Selbsttest liest beide gegeneinander.
TOP = 124776.68
TOP_DATE = "2025-10-07"

# DIE REFERENZMENGE: die Tage, an denen die letzten drei Zyklen ihr Tief
# gefunden haben. Nicht geraten, sondern aus dem eigenen Archiv gerechnet:
# tiefster Tagesschluss zwischen zwei Zyklushochs, data/history.json,
# 5.849 Tagesschluesse seit dem 18.08.2010. Der Selbsttest rechnet die
# Spalte "tage" unten jedes Mal neu aus dem Archiv nach und bricht ab, wenn
# eine Zahl nicht mehr stimmt. Dieselben drei Zahlen stehen als 406, 364
# und 378 auf bitcoin-top-to-bottom.html.
ZYKLEN = (
    # (name,          hoch,         tief,         tage, schluss im tief)
    ("2013 to 2015", "2013-12-05", "2015-01-15", 406, 172.0),
    ("2017 to 2018", "2017-12-17", "2018-12-16", 364, 3231.91),
    ("2021 to 2022", "2021-11-09", "2022-11-22", 378, 15759.61),
)
TIEF_TAGE = tuple(z[3] for z in ZYKLEN)

QUELLZEILE = "counted from daily closes, never intraday highs"
SCHLUSSZEILE = "we count this every day. we never predict the next one."
LINK = "pulsehawk.io/bitcoin-top-to-bottom.html"

# Die drei Vorlagen fuer Zeile 3. Reihenfolge ist die Pruefreihenfolge;
# {lo} ist der frueheste, {hi} der spaeteste Tiefpunkt der Referenzmenge,
# {weg} die Zahl der Tage bis {lo}. Trifft keine Bedingung, gibt es keine
# Wendung und damit keinen Post.
WENDUNGEN = (
    ("A", lambda n, lo, hi: n < lo,
     "the earliest low of the last three cycles came on day {lo}. "
     "that is {weg} days from here."),
    ("B", lambda n, lo, hi: lo <= n <= hi,
     "we are inside that window now."),
    ("C", lambda n, lo, hi: n > hi,
     "all three previous cycles had already found their low by now. "
     "this one has not."),
)

# Ein Verlust deaktiviert (-16 %). Steht eines dieser Worte im Post, muss
# die Wendung im selben Post stehen, die ihn einordnet.
VERLUSTWORTE = ("below", "down", "less", "fell", "lost")

MONATE = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
VERBOTEN = ("—", "–", "→", "←", "->", "<-")


def lang(iso):
    t = iso.split("-")
    return "%d %s %s" % (int(t[2]), MONATE[int(t[1]) - 1], t[0])


def tage(seit, bis):
    a = datetime.date(*[int(x) for x in seit.split("-")])
    b = datetime.date(*[int(x) for x in bis.split("-")])
    return (b - a).days


def letzter_btc(rows):
    for r in reversed(rows if isinstance(rows, list) else []):
        if isinstance(r, dict) and isinstance(r.get("btc"), (int, float)) \
                and isinstance(r.get("d"), str):
            return r
    return None


def seite_lesen(html):
    """LAST_CLOSE und LAST_DATE aus der Seite. Gibt (close, datum) oder
    (None, None), wenn eine der beiden Zuweisungen fehlt."""
    a = re.search(r"var LAST_CLOSE\s*=\s*([0-9][0-9_.]*)", html)
    b = re.search(r"LAST_DATE\s*=\s*\"(\d{4}-\d{2}-\d{2})\"", html)
    if not (a and b):
        return None, None
    return float(a.group(1).replace("_", "")), b.group(1)


def prozent(close, top=TOP):
    """derselbe Ausdruck wie auf der Seite: ((close/top) - 1) * 100,
    eine Nachkommastelle."""
    return (float(close) / float(top) - 1.0) * 100.0


def wendung(n, referenz=TIEF_TAGE):
    """Zeile 3, gewaehlt danach, WO n relativ zur Referenzmenge liegt.
    Gibt (fall, satz) oder (None, None), wenn keine Vorlage greift."""
    if not referenz or not isinstance(n, int) or n <= 0:
        return None, None
    lo, hi = min(referenz), max(referenz)
    for fall, trifft, vorlage in WENDUNGEN:
        if trifft(n, lo, hi):
            return fall, vorlage.format(lo=lo, hi=hi, weg=lo - n)
    return None, None


def referenzzeile(referenz=TIEF_TAGE):
    """Zeile 2: das Gegenstueck, das die Zahl einordnet. Die Quellzeile
    haengt daran, weil hier die historische Aussage steht."""
    z = ["%d" % t for t in referenz]
    return "the three completed cycles bottomed on day %s and %s, %s." % (
        ", ".join(z[:-1]), z[-1], QUELLZEILE)


def traurigkeitsregel(text, satz):
    """Verlustwort ohne die Wendung im selben Post bricht ab. Gibt den
    Grund zurueck oder None."""
    treffer = [w for w in VERLUSTWORTE
               if re.search(r"\b%s\b" % w, text or "", re.I)]
    if treffer and not (satz and satz in (text or "")):
        return ("traurigkeitsregel: %s steht im post, die wendung nicht. "
                "ein verlust ohne wendung ist der einzige gemessene negative "
                "faktor fuers teilen." % ", ".join(treffer))
    return None


def text(n, satz, referenz=TIEF_TAGE):
    """Der Post. Vier Bloecke, die Zahl zuerst, die Wendung als dritter."""
    return "\n\n".join([
        "day %s." % "{:,}".format(n),
        referenzzeile(referenz),
        satz,
        SCHLUSSZEILE,
    ])


def antwort():
    """Die Selbstantwort, eigener Beitrag, traegt den Link. Sie traegt
    keine Wendung und darf deshalb kein Verlustwort tragen."""
    return "the whole count, every cycle on the same day number: %s" % LINK


def bauen(rows, html, heute, max_age, tag=None):
    """Alles, was ohne Netz geprueft werden kann.
    Gibt (posten, problem); posten ist ein dict oder None."""
    zeile = letzter_btc(rows)
    if not zeile:
        return None, "kein btc-schluss in data/market-log.json"
    alt = tage(zeile["d"], heute)
    if alt > max_age:
        return None, ("juengster btc-schluss ist %d tage alt (%s), "
                      "marktlogger pruefen" % (alt, zeile["d"]))
    if alt < 0:
        return None, "btc-schluss liegt in der zukunft (%s)" % zeile["d"]
    s_close, s_datum = seite_lesen(html)
    if s_close is None:
        return None, "LAST_CLOSE/LAST_DATE stehen nicht in der seite"
    if s_datum != zeile["d"] or abs(s_close - float(zeile["btc"])) > 0.005:
        return None, ("seite und log widersprechen sich: seite %s vom %s, "
                      "log %s vom %s. seitenstempel zuerst laufen lassen."
                      % (s_close, s_datum, zeile["btc"], zeile["d"]))
    n = tage(TOP_DATE, zeile["d"]) if tag is None else tag
    if n <= 0:
        return None, "tageszahl nicht positiv (%d)" % n

    fall, satz = wendung(n)
    if not satz:
        return None, ("keine vorlage trifft auf tag %d zu (referenz %s). "
                      "lieber kein post als ein flacher."
                      % (n, ", ".join(str(t) for t in TIEF_TAGE)))
    t = text(n, satz)
    r = antwort()
    for name, s in (("post", t), ("antwort", r)):
        for z in VERBOTEN:
            if z in s:
                return None, "schreibregel verletzt in der %s, gefunden %r" % (name, z)
        grund = traurigkeitsregel(s, satz if name == "post" else None)
        if grund:
            return None, "%s: %s" % (name, grund)
    if len(t) > 280:
        return None, "post ist %d zeichen lang" % len(t)
    if "http" in t or LINK in t:
        return None, "der hauptpost traegt einen link"
    return {"text": t, "reply": r, "key": "dayn-%s" % zeile["d"], "tag": n,
            "fall": fall, "wendung": satz, "datum": zeile["d"],
            "close": float(zeile["btc"])}, None


def bild_bauen(tag, satz, pfad):
    """Das Pflichtbild. Gibt den Pfad zurueck oder None; ohne Bild kein Post."""
    ruf = [sys.executable, os.path.join(HERE, "day_n_cover.py"),
           "--day", str(tag), "--wendung", satz,
           "--marken", ",".join(str(t) for t in TIEF_TAGE), "--out", pfad]
    if subprocess.call(ruf) != 0 or not os.path.isfile(pfad):
        return None
    return pfad


def marke_setzen(wert):
    """posted=true/false nach $GITHUB_OUTPUT, damit dayn.yml das Sperrlog
    nur dann committet, wenn wirklich etwas rausgegangen ist."""
    ziel = os.environ.get("GITHUB_OUTPUT")
    if ziel:
        with open(ziel, "a", encoding="utf-8") as fh:
            fh.write("posted=%s\n" % ("true" if wert else "false"))


def schon_gepostet(key):
    try:
        with open(XLOG, encoding="utf-8") as fh:
            for e in json.load(fh):
                if e.get("key") == key and e.get("id"):
                    return True
    except (OSError, ValueError):
        pass
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--post", action="store_true", help="wirklich posten")
    ap.add_argument("--dry-run", action="store_true", help="nur zeigen")
    ap.add_argument("--max-age", type=int, default=3,
                    help="hoechstalter des btc-schlusses in tagen (Standard 3)")
    ap.add_argument("--tag", type=int,
                    help="Tageszahl erzwingen, nur mit --dry-run (Trockenlauf "
                         "fuer einen kuenftigen Tag)")
    ap.add_argument("--image", default=BILD, help="wohin das Bild geschrieben wird")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return selbsttest()
    if a.tag is not None and a.post and not a.dry_run:
        return fehler("--tag ist nur fuer den trockenlauf, nicht fuer --post")

    with open(LOG, encoding="utf-8") as fh:
        rows = json.load(fh)
    with open(SEITE, encoding="utf-8") as fh:
        html = fh.read()
    heute = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    p, problem = bauen(rows, html, heute, a.max_age, a.tag)
    if problem:
        return fehler(problem)

    pfad = a.image
    if a.tag is not None:
        pfad = "%s-tag%d%s" % (os.path.splitext(a.image)[0], p["tag"],
                               os.path.splitext(a.image)[1])
    if not bild_bauen(p["tag"], p["wendung"], pfad):
        return fehler("das bild konnte nicht gebaut werden. kein text ohne bild.")

    print("key %s, fall %s, %d zeichen, bild %s\n"
          % (p["key"], p["fall"], len(p["text"]), pfad))
    print(p["text"])
    print("\n-- selbstantwort (eigener beitrag, traegt den link) --\n")
    print(p["reply"])
    if not a.post or a.dry_run:
        print("\n(dry run, nichts gepostet)")
        return 0

    code = subprocess.call([sys.executable, os.path.join(HERE, "x_post.py"),
                            "--text", p["text"], "--reply", p["reply"],
                            "--image", pfad, "--key", p["key"], "--log", XLOG])
    # Die Marke haengt daran, ob wirklich ein Post im Sperrlog steht, nicht am
    # Rueckgabewert: geht der Hauptpost raus und die Antwort faellt aus, muss
    # das Sperrlog trotzdem committet werden, sonst postet der naechste Lauf
    # den Hauptpost ein zweites Mal.
    marke_setzen(schon_gepostet(p["key"]))
    return code


def fehler(grund):
    print("kein post: %s" % grund)
    marke_setzen(False)
    return 1


def selbsttest():
    schlecht = 0

    def pruefe(name, ist, soll):
        nonlocal schlecht
        if ist != soll:
            schlecht += 1
            print("  FEHL %s\n    ist  %r\n    soll %r" % (name, ist, soll))
        else:
            print("  ok   %s" % name)

    pruefe("tage seit dem schlusshoch", tage(TOP_DATE, "2026-09-15"), 343)
    pruefe("ein tag weiter", tage(TOP_DATE, "2026-09-16"), 344)
    pruefe("datum ausgeschrieben", lang("2025-10-07"), "7 October 2025")
    pruefe("rueckgang", round(prozent(75608.0), 1), -39.4)
    pruefe("juengste btc-zeile",
           letzter_btc([{"d": "2026-09-14", "btc": 78150.0},
                        {"d": "2026-09-15", "btc": 75608.0},
                        {"d": "2026-09-16", "gld": 1.0}])["d"], "2026-09-15")
    pruefe("log ohne btc", letzter_btc([{"d": "2026-09-15", "gld": 1.0}]), None)

    js = 'var LAST_CLOSE = 76070, LAST_DATE = "2026-09-16";'
    pruefe("seite gelesen", seite_lesen(js), (76070.0, "2026-09-16"))
    pruefe("seite ohne zuweisung", seite_lesen("var X = 1;"), (None, None))

    # DIE WENDUNG: drei Faelle, drei Vorlagen, und keine vierte
    pruefe("fall A unterhalb des fruehesten tiefs", wendung(344),
           ("A", "the earliest low of the last three cycles came on day 364. "
                 "that is 20 days from here."))
    pruefe("fall A rechnet den abstand", wendung(300)[1].endswith("that is 64 days from here."), True)
    pruefe("fall B ab dem fruehesten tief", wendung(364), ("B", "we are inside that window now."))
    pruefe("fall B mitten im fenster", wendung(378)[0], "B")
    pruefe("fall B bis zum spaetesten tief einschliesslich", wendung(406)[0], "B")
    pruefe("fall C darueber", wendung(407)[0], "C")
    pruefe("fall C sagt, dass dieser zyklus es nicht getan hat",
           wendung(420)[1], "all three previous cycles had already found their "
                            "low by now. this one has not.")
    pruefe("ohne referenzmenge keine wendung", wendung(344, ()), (None, None))
    pruefe("tageszahl null gibt keine wendung", wendung(0), (None, None))

    # DIE TRAURIGKEITSREGEL
    satz = "we are inside that window now."
    pruefe("verlustwort ohne wendung bricht ab",
           traurigkeitsregel("bitcoin closed 39 percent below the top.", None) is not None, True)
    pruefe("verlustwort mit wendung im selben post ist erlaubt",
           traurigkeitsregel("39 percent below the top. " + satz, satz), None)
    pruefe("jedes der fuenf worte wird gefunden",
           [traurigkeitsregel("the number %s here." % w, None) is not None
            for w in VERLUSTWORTE], [True] * 5)
    # Wortgrenzen: "unless" ist kein "less", "downtown" kein "down"
    pruefe("teilwort loest nicht aus", traurigkeitsregel("unless downtown", None), None)
    pruefe("harmloser satz loest nicht aus", traurigkeitsregel(satz, None), None)

    log = [{"d": "2026-09-16", "btc": 76070.0}]
    p, problem = bauen(log, js, "2026-09-17", 3)
    pruefe("kein problem", problem, None)
    pruefe("sperrschluessel traegt das datum des schlusses", p["key"], "dayn-2026-09-16")
    t = p["text"]
    zeilen = [z for z in t.split("\n") if z.strip()]
    pruefe("vier bloecke", len(zeilen), 4)
    pruefe("die zahl steht zuerst, nackt", zeilen[0], "day 344.")
    pruefe("zeile 2 traegt alle drei referenztage",
           all(str(x) in zeilen[1] for x in TIEF_TAGE), True)
    pruefe("zeile 2 traegt die quellzeile", QUELLZEILE in zeilen[1], True)
    pruefe("zeile 3 ist die wendung", zeilen[2], p["wendung"])
    pruefe("zeile 4 ist die feste schlusszeile, woertlich", zeilen[3], SCHLUSSZEILE)
    pruefe("post passt in einen tweet", len(t) <= 280, True)
    pruefe("kein link im hauptpost", "http" in t or ".io" in t or ".com" in t, False)
    pruefe("keine prognose im post",
           any(w in t.lower() for w in ("will ", "expect", "target", "forecast",
                                        "predict the next one." in t and "xx")), False)
    pruefe("die selbstantwort traegt den link", LINK in p["reply"], True)
    pruefe("die selbstantwort traegt kein verlustwort",
           traurigkeitsregel(p["reply"], None), None)

    # Trockenlauf fuer kuenftige Tage
    pruefe("tag 364 erzwungen ist fall B", bauen(log, js, "2026-09-17", 3, 364)[0]["fall"], "B")
    pruefe("tag 420 erzwungen ist fall C", bauen(log, js, "2026-09-17", 3, 420)[0]["fall"], "C")

    # die Sperren
    pruefe("alter schluss postet nicht",
           bauen([{"d": "2026-09-01", "btc": 75608.0}],
                 'var LAST_CLOSE = 75608, LAST_DATE = "2026-09-01";',
                 "2026-09-17", 3)[1] is not None, True)
    pruefe("widerspruch zur seite postet nicht",
           bauen(log, 'var LAST_CLOSE = 70000, LAST_DATE = "2026-09-16";',
                 "2026-09-17", 3)[1] is not None, True)
    pruefe("falsches datum auf der seite postet nicht",
           bauen(log, 'var LAST_CLOSE = 76070, LAST_DATE = "2026-09-14";',
                 "2026-09-17", 3)[1] is not None, True)
    pruefe("leeres log postet nicht", bauen([], js, "2026-09-17", 3)[1] is not None, True)

    # das Skript auf der Seite und dieses hier muessen dieselbe Zahl rechnen
    if os.path.exists(SEITE):
        with open(SEITE, encoding="utf-8") as fh:
            html = fh.read()
        m = re.search(r"var TOP = ([0-9.]+), TOP_DATE = \"(\d{4}-\d{2}-\d{2})\"", html)
        pruefe("seite traegt dieselben konstanten",
               (float(m.group(1)), m.group(2)) if m else None, (TOP, TOP_DATE))
        for _, _, _, t_age, _ in ZYKLEN:
            pruefe("die seite nennt %d auch" % t_age, str(t_age) in html, True)

    # DIE REFERENZMENGE gegen das eigene Archiv, nicht geraten
    schlecht += archivprobe(pruefe)

    print("%d faelle falsch" % schlecht)
    return 1 if schlecht else 0


def archivprobe(pruefe):
    """Rechnet die Referenzmenge aus data/history.json nach: tiefster
    Tagesschluss zwischen zwei Zyklushochs, und wie viele Tage nach dem Hoch
    er lag. Fehlt das Archiv, wird der Punkt uebersprungen statt behauptet."""
    pfad = os.path.join(REPO, "data", "history.json")
    if not os.path.exists(pfad):
        print("  --   archiv nicht da, referenzmenge nicht nachgerechnet")
        return 0
    with open(pfad, encoding="utf-8") as fh:
        rows = json.load(fh)
    reihe = [(r["d"], float(r["btc"])) for r in rows
             if isinstance(r, dict) and isinstance(r.get("btc"), (int, float))]
    grenzen = [z[1] for z in ZYKLEN] + [TOP_DATE]
    for i, (name, hoch, tief, t_age, close) in enumerate(ZYKLEN):
        fenster = [(d, c) for d, c in reihe if hoch < d <= grenzen[i + 1]]
        if not fenster:
            print("  --   %s nicht im archiv" % name)
            continue
        d_tief, c_tief = min(fenster, key=lambda x: x[1])
        pruefe("archiv: %s hat sein tief am %s" % (name, tief), d_tief, tief)
        pruefe("archiv: %s tief bei %s" % (name, close), round(c_tief, 2), close)
        pruefe("archiv: %s sind %d tage" % (name, t_age), tage(hoch, d_tief), t_age)
    return 0


if __name__ == "__main__":
    sys.exit(main())
