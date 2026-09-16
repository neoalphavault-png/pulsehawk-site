#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""day_n_post.py, der taegliche DAY-N-Post auf @pulsehawkio.

WARUM ES DAS GIBT
Bis zum 16.09.2026 war der taegliche PulseHawk-Short der Tagesbeitrag.
Er faellt weg. An seine Stelle tritt das, was ohnehin jeden Tag neu ist und
bisher nur auf der Seite stand: der Tageszaehler seit dem Zyklushoch und der
Abstand zum Hoch. Eine Zahl, jeden Tag, ohne Hand.

Kein manueller Schritt heisst: das Skript rechnet selbst, aus derselben Datei,
aus der die Seite rechnet (data/market-log.json), mit demselben Stichtag wie
das Skript auf der Seite (TOP_DATE = 2025-10-07, der TAGESSCHLUSS, nicht das
Intraday-Hoch vom 6. Oktober). Steht die Zahl nicht in beiden gleich, ist eine
von beiden falsch, und dann postet hier nichts.

DREI SPERREN, DAMIT NIE UNSINN RAUSGEHT
  1. Der Schluss muss frisch sein. Ist die juengste btc-Zeile aelter als
     --max-age Tage (Standard 3), wird nicht gepostet. Ein Marktlogger, der
     still steht, hat das Haus schon einmal zwoelf Tage gekostet.
  2. Die Zahl im Post muss der Zahl auf der Seite entsprechen. Gelesen wird
     LAST_CLOSE / LAST_DATE aus bitcoin-top-to-bottom.html; weichen sie vom
     Log ab, bricht der Lauf ab. Der Seitenstempel laeuft vorher, also ist
     eine Abweichung ein echter Fehler und kein Zeitversatz.
  3. Doppelpost-Sperre ueber x_post.py, Schluessel dayn-<datum des schlusses>.
     Zwei Laeufe am selben Tag posten einmal. data/x-post-log.json merkt es.

KEIN LINK IM HAUPTPOST (Kostenregel aus stufe3-x.md): 0,015 $ statt 0,20 $.
KEIN KURSZIEL, KEIN MOTIV, KEIN GEDANKENSTRICH, KEIN PFEIL.

    python3 scripts/day_n_post.py --dry-run
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

# dieselben Konstanten wie im Skript auf der Seite. Wer eine davon aendert,
# muss die andere mitaendern; der Selbsttest liest beide gegeneinander.
TOP = 124776.68
TOP_DATE = "2025-10-07"

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


def text(n, close, datum):
    """Der Post. Vier kurze Zeilen, die Zahl zuerst, die Methode zuletzt.
    Kein Link (Kostenregel), keine Deutung, kein Kursziel."""
    return "\n".join([
        "day %s." % "{:,}".format(n),
        "",
        "bitcoin closed at %s on %s." % ("{:,.0f}".format(close), lang(datum)),
        "",
        # abs(): "minus 39,4 Prozent unter" waere doppelt verneint. Liegt der
        # Schluss ueber dem Hoch, heisst die Zeile "above" und der Zyklus ist
        # ein anderer; dann faellt es hier auf und nicht erst im Post.
        "%.1f percent %s the %s top of %s." % (
            abs(prozent(close)), "below" if prozent(close) < 0 else "above",
            lang(TOP_DATE), "{:,.0f}".format(TOP)),
        "",
        "counted from daily closes, never intraday highs.",
    ])


def bauen(rows, html, heute, max_age):
    """Alles, was ohne Netz geprueft werden kann. Gibt (text, key, problem)."""
    zeile = letzter_btc(rows)
    if not zeile:
        return None, None, "kein btc-schluss in data/market-log.json"
    alt = tage(zeile["d"], heute)
    if alt > max_age:
        return None, None, ("juengster btc-schluss ist %d tage alt (%s), "
                            "marktlogger pruefen" % (alt, zeile["d"]))
    if alt < 0:
        return None, None, "btc-schluss liegt in der zukunft (%s)" % zeile["d"]
    s_close, s_datum = seite_lesen(html)
    if s_close is None:
        return None, None, "LAST_CLOSE/LAST_DATE stehen nicht in der seite"
    if s_datum != zeile["d"] or abs(s_close - float(zeile["btc"])) > 0.005:
        return None, None, ("seite und log widersprechen sich: seite %s vom %s, "
                            "log %s vom %s. seitenstempel zuerst laufen lassen."
                            % (s_close, s_datum, zeile["btc"], zeile["d"]))
    n = tage(TOP_DATE, zeile["d"])
    if n <= 0:
        return None, None, "tageszahl nicht positiv (%d)" % n
    t = text(n, float(zeile["btc"]), zeile["d"])
    for z in VERBOTEN:
        if z in t:
            return None, None, "schreibregel verletzt, gefunden %r" % z
    if len(t) > 280:
        return None, None, "post ist %d zeichen lang" % len(t)
    return t, "dayn-%s" % zeile["d"], None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--post", action="store_true", help="wirklich posten")
    ap.add_argument("--dry-run", action="store_true", help="nur zeigen")
    ap.add_argument("--max-age", type=int, default=3,
                    help="hoechstalter des btc-schlusses in tagen (Standard 3)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return selbsttest()

    with open(LOG, encoding="utf-8") as fh:
        rows = json.load(fh)
    with open(SEITE, encoding="utf-8") as fh:
        html = fh.read()
    heute = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    t, key, problem = bauen(rows, html, heute, a.max_age)
    if problem:
        print("kein post: %s" % problem)
        return 1
    print("key %s, %d zeichen\n" % (key, len(t)))
    print(t)
    if not a.post or a.dry_run:
        print("\n(dry run, nichts gepostet)")
        return 0
    return subprocess.call([sys.executable, os.path.join(HERE, "x_post.py"),
                            "--text", t, "--key", key, "--log", XLOG])


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

    js = 'var LAST_CLOSE = 75608, LAST_DATE = "2026-09-15";'
    pruefe("seite gelesen", seite_lesen(js), (75608.0, "2026-09-15"))
    pruefe("seite ohne zuweisung", seite_lesen("var X = 1;"), (None, None))

    log = [{"d": "2026-09-15", "btc": 75608.0}]
    t, key, problem = bauen(log, js, "2026-09-16", 3)
    pruefe("kein problem", problem, None)
    pruefe("sperrschluessel traegt das datum des schlusses", key, "dayn-2026-09-15")
    pruefe("die zahl steht zuerst", t.split("\n")[0], "day 343.")
    pruefe("post passt in einen tweet", len(t) <= 280, True)
    pruefe("kein link im hauptpost", "http" in t or ".com" in t or ".io" in t, False)
    pruefe("rueckgang im text", "39.4 percent below" in t, True)
    pruefe("kein doppeltes minus", "-39.4" in t, False)
    ueber = bauen([{"d": "2026-09-15", "btc": 130000.0}],
                  'var LAST_CLOSE = 130000, LAST_DATE = "2026-09-15";', "2026-09-16", 3)[0]
    pruefe("ueber dem hoch heisst above", "percent above the" in ueber, True)
    pruefe("methode steht dabei", t.strip().endswith("counted from daily closes, never intraday highs."), True)

    # die drei Sperren
    pruefe("alter schluss postet nicht",
           bauen([{"d": "2026-09-01", "btc": 75608.0}],
                 'var LAST_CLOSE = 75608, LAST_DATE = "2026-09-01";',
                 "2026-09-16", 3)[2] is not None, True)
    pruefe("widerspruch zur seite postet nicht",
           bauen(log, 'var LAST_CLOSE = 70000, LAST_DATE = "2026-09-15";',
                 "2026-09-16", 3)[2] is not None, True)
    pruefe("falsches datum auf der seite postet nicht",
           bauen(log, 'var LAST_CLOSE = 75608, LAST_DATE = "2026-09-14";',
                 "2026-09-16", 3)[2] is not None, True)
    pruefe("leeres log postet nicht", bauen([], js, "2026-09-16", 3)[2] is not None, True)

    # das Skript auf der Seite und dieses hier muessen dieselbe Zahl rechnen
    if os.path.exists(SEITE):
        with open(SEITE, encoding="utf-8") as fh:
            html = fh.read()
        m = re.search(r"var TOP = ([0-9.]+), TOP_DATE = \"(\d{4}-\d{2}-\d{2})\"", html)
        pruefe("seite traegt dieselben konstanten",
               (float(m.group(1)), m.group(2)) if m else None, (TOP, TOP_DATE))

    print("%d von 22 faellen falsch" % schlecht)
    return 1 if schlecht else 0


if __name__ == "__main__":
    sys.exit(main())
