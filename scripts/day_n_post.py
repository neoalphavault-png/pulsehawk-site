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
das Skript auf der Seite (TOP_DATE = 2025-10-06). Steht die Zahl nicht in
beiden gleich, ist eine von beiden falsch, und dann postet hier nichts.

STICHTAG UMDATIERT AM 22.09.2026
Hier stand bis dahin der 07.10.2025 mit dem Zusatz "der TAGESSCHLUSS, nicht
das Intraday-Hoch vom 6. Oktober". Der Zusatz war der richtige Gedanke an
der falschen Reihe: die Bitcoinreihe im Archiv kam von blockchain.com und
war um einen Tag zu spaet gestempelt, siehe bc_tag() in history.py. Nach der
Korrektur faellt der hoechste Tagespreis auf den 06.10.2025. Das ist
derselbe Kalendertag wie das Intraday-Hoch, aber weiter ein anderer Preis:
124.776,68 statt 126.198. Die Tageszahl im Post steigt dadurch um eins.

SECHS SPERREN, DAMIT NIE UNSINN RAUSGEHT
  1. Der Schluss muss frisch sein. Ist die juengste btc-Zeile aelter als
     --max-age Tage (Standard 3), wird nicht gepostet. Ein Marktlogger, der
     still steht, hat das Haus schon einmal zwoelf Tage gekostet.
  2. Die Zahl im Post muss der Zahl auf der Seite entsprechen. Gelesen wird
     LAST_CLOSE / LAST_DATE aus bitcoin-top-to-bottom.html; weichen sie vom
     Log ab, bricht der Lauf ab. Der Seitenstempel laeuft vorher, also ist
     eine Abweichung ein echter Fehler und kein Zeitversatz. Seit dem
     24.09.2026 wird zusaetzlich der TAGESZAEHLER der Seite gelesen (d1):
     zaehlen Post und Seite verschieden, geht nichts raus. Das ist die
     Sperre, die die Zaehltag-Gruppe der Stichtagswache hier durchsetzt.
  3. Doppelpost-Sperre ueber x_post.py, Schluessel dayn-<datum des schlusses>.
     Zwei Laeufe am selben Tag posten einmal. data/x-post-log.json merkt es.
  6. Die Karte muss den Check bestehen. grafik_check.py baut sie, prueft sie
     und schreibt die 390px-Vorschau. Reisst der Check, geht KEIN Post raus,
     auch kein reiner Textpost: lieber eine Luecke im Archiv als eine
     unlesbare Karte. Es gibt absichtlich keinen Schalter, der das umgeht.

KARTE, TEXT UND SEITEN ZAEHLEN DENSELBEN TAG
Seit dem 24.09.2026 zaehlen alle drei bis heute. Die Karte bekommt ihren
Zaehltag von hier uebergeben, statt ihn selbst zu raten, und Sperre 2
liest zusaetzlich den Zaehler der Seite. Drei Quellen, ein Tag.

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
TOP_DATE = "2025-10-06"

MONATE = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

# EINE EINZIGE ZEILE, AN EINEM EINZIGEN TAG
# WARUM AN EINEM TAG EIN VERMERK UNTER DEM POST STEHT
#
# Die veroeffentlichte Reihe war in sich stimmig, entgegen dem ersten
# Verdacht: 344, 345, 346, 347, 348, 350 - alle gerechnet vom damaligen
# Top 2025-10-07 bis zum Schlusstag, eine Regel, keine zwei. Der Sprung
# 348 -> 350 ist kein Regelwechsel, sondern ein fehlender Post: am
# 21.09. stand im Marktlog eine Zeile ohne btc-Wert, die Quelle war aus.
# Dass die Posts im Profil einen Tag nach ihrem Preis zu stehen scheinen,
# ist der Zeitzonenrand: gelaufen wird 21:52 utc, angekommen gegen 23:37
# utc, und das ist in Berlin schon der naechste Tag.
#
# Der Sprung von 350 auf 353 heute hat drei Glieder, und nur zwei davon
# aendern die Zahl:
#   350   letzter Post (22.09., Top 2025-10-07, bis zum Schlusstag)
#   351   waere heute ohne jede Aenderung
#   +1    Umdatierung des Tops auf 2025-10-06
#   +1    Zaehltag heute statt Schlusstag
#   353   heute
# Der fehlende Post vom 23.09. traegt 0 bei. Er ist der Grund, warum
# beide Aenderungen in EINEM Schritt sichtbar werden statt in zweien.
#
# Deshalb steht der Vermerk heute einmal da, und er wird gerechnet, nicht
# geschrieben: die 353 ist die eigene Zahl, die 350 steht im zuletzt
# veroeffentlichten Post. Waere eine von beiden hier festgeschrieben,
# waere der Vermerk beim naechsten Mal falsch.

# DIE UMSTELLUNG WIRD ERKLAERT, SOLANGE SIE UNERKLAERT IST.
# Kein Datum. Ein Datum waere eine Vermutung darueber, WANN etwas
# passiert; faellt der Post an dem Tag aus, steht morgen ein vergangenes
# Datum im Code und der Sprung im Feed ohne Erklaerung. Die Bedingung ist
# eine Aussage darueber, was WAHR sein muss: der Zaehler springt, und die
# Erklaerung ist noch nicht raus.
#
# Abgeschrieben wird sie im Sperrlog, nicht ueber eine Konstante: steht
# die Marke unten in einem veroeffentlichten Post, feuert sie nie wieder.
# Eine Konstante muesste jemand von Hand zuruecksetzen, und das vergisst
# man.
UMSTELLUNG = "counter now runs to today"

VERBOTEN = ("\u2014", "\u2013", "\u2192", "\u2190", "->", "<-")


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
        # "traded at", nicht "closed at": der Wert kommt aus dem
        # Marktlogger, der um 21:23 UTC einen Momentanpreis abgreift.
        # Ein Schlusskurs ist das nicht, und der Tagesdurchschnitt aus
        # dem Archiv waere es auch nicht.
        "bitcoin traded at %s on %s (21:23 utc)."
        % ("{:,.0f}".format(close), lang(datum)),
        "",
        # abs(): "minus 39,4 Prozent unter" waere doppelt verneint. Liegt der
        # Schluss ueber dem Hoch, heisst die Zeile "above" und der Zyklus ist
        # ein anderer; dann faellt es hier auf und nicht erst im Post.
        "%.1f percent %s the %s top of %s." % (
            abs(prozent(close)), "below" if prozent(close) < 0 else "above",
            lang(TOP_DATE), "{:,.0f}".format(TOP)),
        "",
        # "prices", nicht "closes": die Archivreihe ist ein
        # boersenuebergreifender Tagesdurchschnitt von blockchain.com.
        "counted from daily prices, never intraday highs.",
    ])
    # Der Vermerk bei einem Sprung haengt NICHT hier dran: er braucht den
    # zuletzt veroeffentlichten Post und den Zaehltag, und beides kennt
    # nur bauen(). Frueher wurde er hier am SCHLUSStag festgemacht - das
    # war der falsche Anker, seit der Zaehler bis heute laeuft.


def bestaetigt(e):
    """ein DAY-N-Eintrag, der nachweislich veroeffentlicht wurde.

    Nur Eintraege mit einer Post-ID zaehlen. x_post.py schreibt zwar erst
    nach erfolgreichem Post, aber erzwungen war das nicht: ein Eintrag
    ohne ID ist ein Versuch, kein Post, und der naechste Post darf sich
    nicht an ihm messen."""
    return (str(e.get("key", "")).startswith("dayn-")
            and str(e.get("id") or "").strip() != "")


def letzte_zahl(xlog):
    """(tageszahl, kalendertag) des juengsten DAY-N-Posts, oder (None, None).

    Gelesen wird der veroeffentlichte TEXT, nicht eine mitgefuehrte Zahl.
    Was im Profil steht, ist die Wahrheit, gegen die der naechste Post
    sich messen lassen muss."""
    letzte = None
    for e in xlog or []:
        if bestaetigt(e):
            letzte = e
    if not letzte:
        return None, None
    m = re.search(r"\bday (\d+)\.", letzte.get("text", ""))
    if not m:
        return None, None
    # Der Kalendertag kommt aus posted_at, NICHT aus dem Schluessel: der
    # Schluessel traegt den Preistag, und der liegt seit dem 24.09.2026
    # einen Tag vor dem Zaehltag. Mit dem Schluessel als Anker haette ab
    # morgen JEDER Post "no post yesterday" getragen, obwohl keiner fehlt.
    # Unter der neuen Regel ist der Zaehltag der utc-Tag des Laufs, und
    # genau den haelt posted_at fest.
    tag = str(letzte.get("posted_at", ""))[:10]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", tag):
        tag = letzte["key"][len("dayn-"):]
    return int(m.group(1)), tag


def umstellung_erklaert(xlog):
    """steht die erklaerung schon in einem veroeffentlichten post?

    Gelesen wird der Text im Sperrlog, also das, was im Profil steht.
    Damit schreibt sich die Zeile selbst ab, sobald sie einmal drausen
    war - ohne dass jemand etwas zuruecksetzen muss."""
    for e in xlog or []:
        if bestaetigt(e) and UMSTELLUNG in str(e.get("text", "")):
            return True
    return False


def nach_alter_regel(letzter_n, letzter_tag):
    """wurde der letzte bestaetigte post noch nach der alten regel gezaehlt?

    Nach der neuen Regel ist die Tageszahl eines Posts genau die Zahl der
    Tage von TOP_DATE bis zu seinem Lauftag. Stimmt das nicht, stammt er
    aus der Zeit davor (anderes Top, Zaehlung bis zum Schlusstag), und
    zwischen ihm und heute liegt die Umstellung.

    Warum das noetig ist (Entscheidung vom 25.09.2026, Variante a): der
    Sprung 350 -> 354 wurde nie erklaert, die Marke steht in keinem Post.
    Mit der Marke allein haette der erste Ausfall im Oktober die
    Umstellung vom September angekuendigt. Diese Pruefung folgt aus den
    Daten, nicht aus einem Datum: sobald ein Post nach neuer Regel draussen
    ist, kann sie nie wieder wahr werden."""
    if letzter_n is None or not letzter_tag:
        return False
    return tage(TOP_DATE, letzter_tag) != letzter_n


def hinweis(letzter_n, luecke, erklaeren):
    """der vermerk unter dem post, wenn der zaehler nicht um 1 gewachsen ist.

    Die eigene Zahl steht schon in der ersten Zeile des Posts, der
    Vermerk nennt deshalb nur die vorige - und die kommt aus dem zuletzt
    veroeffentlichten Text, nicht von hier. Waere eine der beiden Zahlen
    festgeschrieben, waere der Vermerk beim naechsten Mal falsch. Das ist
    auch der Grund fuer die knappe Fassung: 280 Zeichen sind hart, und
    der Grundpost braucht davon 173."""
    teile = []
    if luecke == 1:
        teile.append("no post yesterday.")
    elif luecke > 1:
        teile.append("no post for %d days." % luecke)
    # Die Luecke steht GENAU EINMAL da, auch wenn beide Ursachen
    # zusammenfallen: sie gehoert zum Lueckensatz oben, nicht in den
    # Umstellungssatz. Faellt naechsten Monat ein Tag aus, ohne dass sich
    # an der Zaehlung etwas geaendert hat, steht nur der Lueckensatz da.
    if erklaeren:
        teile.append("%s, top moved to %s." % (UMSTELLUNG, lang(TOP_DATE)))
    if not teile:
        return ""
    teile.append("the last post read %d." % letzter_n)
    return " ".join(teile)


def sprung_problem(n, letzter_n, vermerk, volltext=""):
    """haelt den post an, wenn der zaehler nicht sauber weiterlaeuft.

    Der Zaehler ist ein Kalenderzaehler: zwischen zwei Posts waechst er
    um genau 1, sonst fehlt ein Tag - und dann muss die Luecke im Text
    stehen, nicht nur in der Logdatei."""
    if letzter_n is None:
        return None
    d = n - letzter_n
    if d == 0:
        return ("zaehler steht still: der letzte post stand schon auf tag %d. "
                "zweimal derselbe tag geht nicht raus." % n)
    if d < 0:
        return ("zaehler laeuft rueckwaerts: tag %d nach tag %d"
                % (n, letzter_n))
    if d == 1:
        return None
    if not vermerk:
        return ("zaehler springt von %d auf %d ohne vermerk im text"
                % (letzter_n, n))
    # beide zahlen muessen im post stehen, damit ein leser den sprung
    # nachvollziehen kann. die eigene steht in zeile eins, die vorige im
    # vermerk - geprueft wird deshalb der ganze text.
    for zahl in (n, letzter_n):
        if str(zahl) not in volltext:
            return "der post nennt %d nicht, obwohl er springt" % zahl
    return None


def seite_tageszahl(html):
    """der gestempelte tageszaehler der seite (id="d1"), oder None.

    None heisst "steht nicht drin", nicht "stimmt". Fehlt der Stempel,
    greift Sperre 2 ueber LAST_CLOSE/LAST_DATE weiter."""
    m = re.search(r'id="d1">([\d,]+)<', html)
    return int(m.group(1).replace(",", "")) if m else None


def bauen(rows, html, heute, max_age, xlog=None):
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
    # ZAEHLTAG IST HEUTE, NICHT DER SCHLUSSTAG (24.09.2026).
    # "day N of the cycle" ist ein Kalenderzaehler, kein Kursbefund: der
    # Tag vergeht, ob eine Kerze geschlossen hat oder nicht. Die Seiten
    # zaehlen schon so, und die Seiten sind das dauerhafte Artefakt.
    # Damit gilt hier dieselbe Trennung wie in der Stichtagswache:
    # Zaehltag heute, Preistag gestern - und jeder Preis traegt sein
    # eigenes Datum, im Text wie auf der Karte.
    n = tage(TOP_DATE, heute)
    if n <= 0:
        return None, None, "tageszahl nicht positiv (%d)" % n
    s_tag = seite_tageszahl(html)
    if s_tag is not None and s_tag != n:
        return None, None, ("post zaehlt tag %d, die seite zaehlt tag %d. "
                            "zwei zaehltage sind ein fehler, kein zeitversatz."
                            % (n, s_tag))
    # der zaehler muss gegenueber dem zuletzt veroeffentlichten post um
    # genau 1 gewachsen sein, sonst fehlt ein tag und der muss dastehen
    letzter_n, letzter_tag = letzte_zahl(xlog)
    # Ein Vermerk entsteht NUR, wenn der Zaehler wirklich springt. Vorher
    # wurde die Luecke unabhaengig davon gerechnet, und ein
    # Rundungsproblem im Anker haette sie jeden Tag erzeugt.
    sprung = (n - letzter_n) if letzter_n is not None else 1
    if sprung > 1:
        luecke = max(0, tage(letzter_tag, heute) - 1) if letzter_tag else 0
        erklaeren = (nach_alter_regel(letzter_n, letzter_tag)
                     and not umstellung_erklaert(xlog))
        vermerk = hinweis(letzter_n, luecke, erklaeren)
    else:
        vermerk = ""

    t = text(n, float(zeile["btc"]), zeile["d"])
    if vermerk:
        t = t.rstrip() + "\n\n" + vermerk
    fehl = sprung_problem(n, letzter_n, vermerk, t)
    if fehl:
        return None, None, fehl
    for z in VERBOTEN:
        if z in t:
            return None, None, "schreibregel verletzt, gefunden %r" % z
    if len(t) > 280:
        return None, None, "post ist %d zeichen lang" % len(t)
    return t, "dayn-%s" % zeile["d"], None


import dayn_grafik  # noqa: E402  (nach sys.path-anpassung oben)
from x_post import log_eintrag  # noqa: E402


def laufzeit(jetzt=None):
    """(zaehltag, posted_at) aus EINEM Zeitpunkt.

    Frueher kam der Zaehltag aus einem now() hier und posted_at aus einem
    zweiten now() in x_post.py, in einem anderen Prozess, nach Kartenbau
    und Bild-Upload. Laeuft der Post um 23:59:58 utc, fiel der Zaehltag
    auf den einen Tag und posted_at auf den naechsten - und der Folgetag
    rechnete eine Luecke von 0 statt 1, der Vermerk fehlte genau dann,
    wenn er gebraucht wird. Jetzt gibt es im ganzen Lauf genau einen
    Zeitpunkt, und x_post.py bekommt ihn mit."""
    if jetzt is None:
        jetzt = datetime.datetime.now(datetime.timezone.utc)
    jetzt = jetzt.astimezone(datetime.timezone.utc)
    return (jetzt.date().isoformat(),
            jetzt.isoformat(timespec="seconds").replace("+00:00", "Z"))


def post_befehl(t, key, stempel):
    """der aufruf von x_post.py. herausgezogen, damit ein test sieht, dass
    der zeitstempel wirklich mitgeht."""
    return [sys.executable, os.path.join(HERE, "x_post.py"),
            "--text", t, "--key", key, "--log", XLOG,
            "--image", dayn_grafik.ZIEL, "--posted-at", stempel]


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
    # EIN zeitpunkt fuer den ganzen lauf. kein zweites now() weiter unten.
    heute, stempel = laufzeit()
    with open(XLOG, encoding="utf-8") as fh:
        xlog = json.load(fh)
    t, key, problem = bauen(rows, html, heute, a.max_age, xlog)
    if problem:
        print("kein post: %s" % problem)
        return 1
    print("key %s, %d zeichen\n" % (key, len(t)))
    print(t)

    # sperre 4: die karte. sie zaehlt bis zum tag des schlusses, also bis
    # zu demselben tag wie der text darueber.
    zaehltag = heute   # derselbe zaehltag wie der text darueber
    print("\n--- grafik_check, zaehltag %s ---" % zaehltag)
    try:
        import grafik_check
        rc = grafik_check.lauf(bis=zaehltag)
    except Exception as e:
        print("kein post: die karte liess sich nicht bauen (%s: %s)"
              % (type(e).__name__, e))
        return 1
    if rc != 0:
        print("\nkein post: der grafik-check ist gerissen.")
        return 1

    if not a.post or a.dry_run:
        print("\n(dry run, nichts gepostet)")
        return 0
    return subprocess.call(post_befehl(t, key, stempel))


def selbsttest():
    schlecht = 0
    gezaehlt = 0

    def pruefe(name, ist, soll):
        nonlocal gezaehlt
        gezaehlt += 1
        nonlocal schlecht
        if ist != soll:
            schlecht += 1
            print("  FEHL %s\n    ist  %r\n    soll %r" % (name, ist, soll))
        else:
            print("  ok   %s" % name)

    pruefe("tage seit dem schlusshoch", tage(TOP_DATE, "2026-09-15"), 344)
    pruefe("ein tag weiter", tage(TOP_DATE, "2026-09-16"), 345)
    pruefe("datum ausgeschrieben", lang("2025-10-06"), "6 October 2025")
    # der stichtag muss der umdatierte sein, sonst zaehlt der post einen
    # tag anders als die seite und sperre 2 schlaegt jeden tag zu
    pruefe("stichtag ist umdatiert", TOP_DATE, "2025-10-06")
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
    # 344 waere der schlusstag (15.09.), 345 ist heute (16.09.). seit dem
    # 24.09.2026 zaehlt der post bis heute, also 345.
    pruefe("die zahl steht zuerst und zaehlt bis heute",
           t.split("\n")[0], "day 345.")
    pruefe("post passt in einen tweet", len(t) <= 280, True)
    pruefe("kein link im hauptpost", "http" in t or ".com" in t or ".io" in t, False)
    pruefe("rueckgang im text", "39.4 percent below" in t, True)
    pruefe("kein doppeltes minus", "-39.4" in t, False)
    ueber = bauen([{"d": "2026-09-15", "btc": 130000.0}],
                  'var LAST_CLOSE = 130000, LAST_DATE = "2026-09-15";', "2026-09-16", 3)[0]
    pruefe("ueber dem hoch heisst above", "percent above the" in ueber, True)
    pruefe("methode steht dabei",
           t.strip().endswith("counted from daily prices, never intraday highs."), True)
    pruefe("kein schlusskurs behauptet", "traded at" in t and "closed at" not in t, True)
    pruefe("uhrzeit steht dabei", "(21:23 utc)" in t, True)

    # --- die umstellungszeile haengt an einer bedingung, nicht an einem datum ---
    # nach namen im modul gefragt, nicht nach text in der datei: die
    # frage "steht das wort im quelltext" beantwortet sich selbst mit ja,
    # sobald sie im quelltext steht.
    pruefe("kein datum mehr, nur eine bedingung",
           [x for x in globals() if x.startswith("EINMAL")], [])
    pruefe("die marke steht im text, an dem sie sich wiedererkennt",
           UMSTELLUNG in hinweis(350, 1, True), True)
    pruefe("sie nennt das top aus der konstante",
           lang(TOP_DATE) in hinweis(350, 1, True), True)
    pruefe("ohne erklaerungsbedarf nennt sie die regel nicht",
           UMSTELLUNG in hinweis(350, 1, False), False)
    # kein grund, kein vermerk - und weil hinweis() nur bei sprung > 1
    # gerufen wird, faellt ein sprung ohne erkennbaren grund danach bei
    # sprung_problem() laut durch, statt still einen satz zu erfinden.
    pruefe("ohne luecke und ohne umstellung gibt es keinen vermerk",
           hinweis(352, 0, False), "")
    pruefe("eine luecke allein reicht fuer einen vermerk",
           hinweis(352, 1, False),
           "no post yesterday. the last post read 352.")

    # sie schreibt sich im sperrlog ab, nicht ueber eine konstante
    raus = [{"id": "1", "key": "dayn-2026-09-24", "posted_at": "2026-09-24T21:55:00Z",
             "text": "day 353.\n\n%s, top moved to 6 October 2025." % UMSTELLUNG}]
    pruefe("vor dem post gilt sie als unerklaert", umstellung_erklaert([]), False)
    pruefe("danach als erklaert", umstellung_erklaert(raus), True)
    pruefe("ein fremder posttyp zaehlt dafuer nicht",
           umstellung_erklaert([{"key": "weekly-1", "text": UMSTELLUNG}]), False)

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

    # --- sperre 4: der zaehler waechst um genau 1 ---
    def lauf(zaehltag, schluss, log):
        return bauen([{"d": schluss, "btc": 84424.0}],
                     'var LAST_CLOSE = 84424, LAST_DATE = "%s";' % schluss,
                     zaehltag, 3, log)

    def gepostet(tag, n):
        return [{"id": "1", "key": "dayn-%s" % tag, "text": "day %d.\n\nrest" % n}]

    # normaler tag: +1, kein vermerk
    t1, _, p1 = lauf("2026-09-26", "2026-09-25", gepostet("2026-09-25", 354))
    pruefe("normaler tag geht raus", p1, None)
    pruefe("und zaehlt um genau eins weiter", t1.split("\n")[0], "day 355.")
    pruefe("ohne vermerk", "the last post read" in t1, False)

    # ausgefallener tag: +2 mit vermerk
    t2, _, p2 = lauf("2026-09-27", "2026-09-26", gepostet("2026-09-25", 354))
    pruefe("nach einem ausfall geht der post raus", p2, None)
    pruefe("die luecke steht im text", "no post yesterday." in t2, True)
    pruefe("und der vermerk nennt die vorige zahl",
           "the last post read 354." in t2, True)
    pruefe("die eigene zahl steht in zeile eins", t2.split("\n")[0], "day 356.")
    pruefe("auch mit vermerk passt der post in einen tweet", len(t2) <= 280, True)

    # zwei tage ausgefallen: der vermerk zaehlt sie
    t2b = lauf("2026-09-28", "2026-09-27", gepostet("2026-09-25", 354))[0]
    pruefe("zwei fehlende tage werden benannt",
           "no post for 2 days." in t2b, True)

    # zweimal derselbe tag: abbruch
    p3 = lauf("2026-09-26", "2026-09-25", gepostet("2026-09-25", 355))[2]
    pruefe("zweimal derselbe tag geht nicht raus", p3 is not None, True)
    pruefe("und sagt warum", "zweimal derselbe tag" in p3, True)
    pruefe("rueckwaerts auch nicht",
           "rueckwaerts" in lauf("2026-09-26", "2026-09-25",
                                 gepostet("2026-09-25", 400))[2], True)

    # der erste post ueberhaupt hat nichts zu vergleichen
    pruefe("leeres sperrlog haelt nichts an", lauf("2026-09-26", "2026-09-25", [])[2], None)
    pruefe("ein post ohne tageszahl im text wird nicht geraten",
           letzte_zahl([{"id": "1", "key": "dayn-2026-09-25", "text": "kaputt"}]), (None, None))
    pruefe("fremde eintraege zaehlen nicht mit",
           letzte_zahl([{"id": "1", "key": "dayn-2026-09-25", "text": "day 354."},
                        {"key": "weekly-2026-09-26", "text": "day 999."}]),
           (354, "2026-09-25"))

    # --- der umstellungstag selbst, aus echten daten ---
    echt = [{"id": "1", "key": "dayn-2026-09-22",
             "text": "day 350.\n\nbitcoin traded at 86,174 on 22 September 2026 (21:23 utc)."}]
    tu, _, pu = lauf("2026-09-24", "2026-09-23", echt)
    pruefe("der umstellungstag geht raus", pu, None)
    pruefe("er nennt beide regelaenderungen",
           ("counter now runs to today" in tu
            and "top moved to 6 October 2025" in tu), True)
    pruefe("und die luecke vom 23.09.", "no post yesterday." in tu, True)
    pruefe("350 kommt aus dem log, nicht aus dem quelltext",
           "the last post read 350." in tu, True)
    pruefe("353 kommt aus der rechnung", tu.split("\n")[0], "day 353.")
    pruefe("der umstellungstag passt in einen tweet", len(tu) <= 280, True)
    # der beweis, dass nichts festgeschrieben ist: anderes log, andere zahl
    anders = lauf("2026-09-24", "2026-09-23",
                  [{"id": "1", "key": "dayn-2026-09-21", "text": "day 349."}])[0]
    pruefe("eine andere vorgeschichte gibt einen anderen vermerk",
           "the last post read 349." in anders, True)
    # und am tag danach steht nichts mehr da
    danach = lauf("2026-09-25", "2026-09-24", gepostet("2026-09-24", 353))[0]
    pruefe("am tag nach der umstellung kein vermerk mehr",
           ("the last post read" in danach, danach.split("\n")[0]),
           (False, "day 354."))

    # --- die kollision: luecke UND umstellung sagen "no post yesterday" ---
    # naechsten monat faellt ein tag aus, an der zaehlung hat sich nichts
    # geaendert. dann steht GENAU EIN vermerk da, nicht zwei.
    erklaert = [{"id": "1", "key": "dayn-2026-09-24", "posted_at": "2026-09-24T21:55:00Z",
                 "text": "day 353.\n\n%s, top moved to 6 October 2025." % UMSTELLUNG},
                {"id": "1", "key": "dayn-2026-10-19", "posted_at": "2026-10-20T21:55:00Z",
                 "text": "day 379.\n\nrest"}]
    tk, _, pk = lauf("2026-10-22", "2026-10-21", erklaert)
    pruefe("sprung +2 ohne zaehlungsaenderung geht raus", pk, None)
    pruefe("und traegt genau einen lueckenvermerk", tk.count("no post"), 1)
    pruefe("die umstellung wird nicht wiederholt", UMSTELLUNG in tk, False)
    pruefe("der vermerk nennt die vorige zahl", "the last post read 379." in tk, True)
    pruefe("die zahl selbst stimmt", tk.split("\n")[0], "day 381.")

    # am umstellungstag fallen beide ursachen zusammen - auch dann einmal
    pruefe("auch am umstellungstag steht die luecke nur einmal",
           lauf("2026-09-24", "2026-09-23",
                [{"id": "1", "key": "dayn-2026-09-22", "posted_at": "2026-09-22T00:18:42Z",
                  "text": "day 350.\n\nrest"}])[0].count("no post"), 1)

    # --- der anker ist posted_at, nicht der schluesseltag ---
    # der schluessel traegt den PREIStag, und der liegt einen tag vor dem
    # zaehltag. mit ihm als anker haette ab dem 25.09. jeder post
    # "no post yesterday" getragen, obwohl keiner fehlt.
    nach_heute = [{"id": "1", "key": "dayn-2026-09-23", "posted_at": "2026-09-24T21:55:00Z",
                   "text": "day 353.\n\n%s, top moved to 6 October 2025." % UMSTELLUNG}]
    pruefe("posted_at ist der anker, nicht der schluessel",
           letzte_zahl(nach_heute), (353, "2026-09-24"))
    tm, _, pm = lauf("2026-09-25", "2026-09-24", nach_heute)
    pruefe("der tag nach der umstellung geht raus", pm, None)
    pruefe("und traegt gar keinen vermerk",
           ("no post" in tm, UMSTELLUNG in tm, "the last post read" in tm),
           (False, False, False))
    pruefe("er zaehlt einfach eins weiter", tm.split("\n")[0], "day 354.")
    pruefe("ohne posted_at faellt er auf den schluessel zurueck",
           letzte_zahl([{"id": "1", "key": "dayn-2026-09-23", "text": "day 353."}]),
           (353, "2026-09-23"))
    pruefe("und ein kaputtes posted_at auch",
           letzte_zahl([{"id": "1", "key": "dayn-2026-09-23", "posted_at": "spaeter",
                         "text": "day 353."}]), (353, "2026-09-23"))

    # --- nur bestaetigte posts zaehlen (entscheidung vom 25.09.2026) ---
    bestaetigt_354 = [{"id": "2103274283241738600", "key": "dayn-2026-09-24",
                       "posted_at": "2026-09-25T00:04:00Z", "text": "day 354.\n\nrest"}]
    for ohne in ({"key": "dayn-2026-09-25", "posted_at": "2026-09-26T00:01:00Z",
                  "text": "day 355.\n\nrest"},
                 {"id": "", "key": "dayn-2026-09-25", "posted_at": "2026-09-26T00:01:00Z",
                  "text": "day 355.\n\nrest"},
                 {"id": None, "key": "dayn-2026-09-25", "posted_at": "2026-09-26T00:01:00Z",
                  "text": "day 355.\n\nrest"}):
        pruefe("ein eintrag mit id=%r zaehlt nicht" % ohne.get("id", "fehlt"),
               letzte_zahl(bestaetigt_354 + [ohne]), (354, "2026-09-25"))
    # ohne den filter haette der lauf gegen die unbestaetigte 355 gemessen
    # und "zweimal derselbe tag" gemeldet, obwohl 355 nie draussen war.
    t_id, _, p_id = lauf("2026-09-26", "2026-09-25", bestaetigt_354 +
                         [{"key": "dayn-2026-09-25", "text": "day 355.\n\nrest",
                           "posted_at": "2026-09-26T00:01:00Z"}])
    pruefe("gegen den letzten BESTAETIGTEN post gemessen: 355 geht raus",
           (p_id, t_id.split("\n")[0]), (None, "day 355."))
    pruefe("ein sperrlog nur aus unbestaetigten eintraegen haelt nichts an",
           letzte_zahl([{"key": "dayn-2026-09-25", "text": "day 355."}]),
           (None, None))
    pruefe("eine marke in einem unbestaetigten eintrag erklaert nichts",
           umstellung_erklaert([{"key": "dayn-2026-09-25", "text": UMSTELLUNG}]),
           False)

    # --- entscheidung (a): die luecke 350 -> 354 wird nicht erklaert ---
    pruefe("350 vom 22.09. war nach alter regel gezaehlt",
           nach_alter_regel(350, "2026-09-22"), True)
    pruefe("354 vom 25.09. ist nach neuer regel gezaehlt",
           nach_alter_regel(354, "2026-09-25"), False)
    # die marke ging nie raus. ohne die regelpruefung haette der erste
    # ausfall im oktober die umstellung vom september angekuendigt.
    okt = bestaetigt_354 + [{"id": "9", "key": "dayn-2026-10-18",
                             "posted_at": "2026-10-19T23:40:00Z", "text": "day 378.\n\nrest"}]
    t_okt = lauf("2026-10-21", "2026-10-20", okt)[0]
    pruefe("ausfall im oktober ohne marke im log: nur der lueckenvermerk",
           t_okt.strip().split("\n")[-1],
           "no post yesterday. the last post read 378.")
    pruefe("die umstellung wird dort nicht angekuendigt", UMSTELLUNG in t_okt, False)
    pruefe("heute nacht nach 354: kein vermerk",
           "the last post read" in lauf("2026-09-26", "2026-09-25", bestaetigt_354)[0],
           False)

    # --- ein zeitpunkt fuer den ganzen lauf ---
    spaet = datetime.datetime(2026, 9, 24, 23, 59, 58, tzinfo=datetime.timezone.utc)
    zt, st = laufzeit(spaet)
    pruefe("um 23:59:58 utc: zaehltag und posted_at aus einem zeitpunkt",
           (zt, st), ("2026-09-24", "2026-09-24T23:59:58Z"))
    pruefe("posted_at faellt auf den zaehltag", st[:10], zt)
    pruefe("der zeitstempel geht an x_post.py mit",
           post_befehl("t", "dayn-2026-09-23", st)[-2:],
           ["--posted-at", "2026-09-24T23:59:58Z"])
    berlin = datetime.timezone(datetime.timedelta(hours=2))
    pruefe("ein zeitpunkt in anderer zone wird auf utc gebracht",
           laufzeit(datetime.datetime(2026, 9, 25, 1, 59, 58, tzinfo=berlin)),
           ("2026-09-24", "2026-09-24T23:59:58Z"))

    # der ganze weg um 23:59:58: post bauen, so loggen wie x_post.py es
    # tut, und dann den folgetag und den tag danach rechnen.
    vorher = [{"id": "1", "key": "dayn-2026-09-22", "posted_at": "2026-09-22T00:18:42Z",
               "text": "day 350.\n\nrest"}]
    heutig, schl, _ = lauf(zt, "2026-09-23", vorher)
    nachher = vorher + [log_eintrag(schl, "1", heutig, "dayn.png", st)]
    morgen = lauf("2026-09-25", "2026-09-24", nachher)[0]
    pruefe("post um 23:59:58, folgetag: kein falscher vermerk",
           (morgen.split("\n")[0], "no post" in morgen), ("day 354.", False))
    uebermorgen = lauf("2026-09-26", "2026-09-25", nachher)[0]
    pruefe("post um 23:59:58, ein tag fehlt: der vermerk ist da",
           "no post yesterday." in uebermorgen, True)

    # und der fehler, den das verhindert: zweites now() eine sekunde nach
    # mitternacht. die luecke rechnet dann 0 statt 1, der vermerk bleibt
    # leer - und sperre 4 haelt den post an, weil der zaehler um 2
    # springt ohne vermerk. das netz haelt, aber es kostet einen weiteren
    # tag, und die luecke waechst.
    zwei_uhren = vorher + [log_eintrag(schl, "1", heutig, "dayn.png",
                                        "2026-09-25T00:00:01Z")]
    _, _, p_uhren = lauf("2026-09-26", "2026-09-25", zwei_uhren)
    pruefe("mit zwei uhren waere der post angehalten worden (so war es)",
           p_uhren is not None and "ohne vermerk" in p_uhren, True)

    # --- die marke ueberlebt den weg durchs sperrlog ---
    # vorher kuerzte x_post.py den text auf 120 zeichen, die marke stand
    # bei 194. die zeile haette sich nie abgeschrieben.
    pruefe("die marke steht hinter zeichen 120", heutig.find(UMSTELLUNG) > 120, True)
    pruefe("und ist nach dem loggen trotzdem lesbar",
           umstellung_erklaert(nachher), True)
    pruefe("so dass sie sich beim naechsten sprung nicht wiederholt",
           UMSTELLUNG in uebermorgen, False)

    # --- der zaehltag ist heute, nicht der schlusstag ---
    # am 24.09. mit dem schluss vom 23.09.: 353, nicht 352.
    spaet = bauen([{"d": "2026-09-23", "btc": 84424.0}],
                  'var LAST_CLOSE = 84424, LAST_DATE = "2026-09-23";',
                  "2026-09-24", 3)
    pruefe("der zaehler laeuft bis heute", spaet[0].split("\n")[0], "day 353.")
    pruefe("der preis traegt trotzdem seinen eigenen tag",
           "on 23 September 2026 (21:23 utc)" in spaet[0], True)
    pruefe("die sperre haengt weiter am preistag", spaet[1], "dayn-2026-09-23")
    # zwei laeufe an zwei tagen mit demselben schluss zaehlen verschieden,
    # und genau das ist der punkt: der tag vergeht auch ohne neue kerze.
    frueh = bauen([{"d": "2026-09-23", "btc": 84424.0}],
                  'var LAST_CLOSE = 84424, LAST_DATE = "2026-09-23";',
                  "2026-09-23", 3)
    pruefe("derselbe schluss, ein tag spaeter, eine zahl hoeher",
           (frueh[0].split("\n")[0], spaet[0].split("\n")[0]),
           ("day 352.", "day 353."))

    # --- sperre 5: post und seite zaehlen denselben tag ---
    pruefe("die seite wird auf ihren zaehler gelesen",
           seite_tageszahl('<b id="d1">353</b>'), 353)
    pruefe("mit tausenderpunkt auch", seite_tageszahl('<b id="d1">1,353</b>'), 1353)
    pruefe("ohne stempel kein urteil", seite_tageszahl("<b>353</b>"), None)
    pruefe("ein anderer zaehler auf der seite postet nicht",
           bauen([{"d": "2026-09-23", "btc": 84424.0}],
                 'var LAST_CLOSE = 84424, LAST_DATE = "2026-09-23";'
                 '<b id="d1">352</b>', "2026-09-24", 3)[2] is not None, True)
    pruefe("derselbe zaehler postet",
           bauen([{"d": "2026-09-23", "btc": 84424.0}],
                 'var LAST_CLOSE = 84424, LAST_DATE = "2026-09-23";'
                 '<b id="d1">353</b>', "2026-09-24", 3)[2], None)

    # --- sperre 4: karte und text zaehlen denselben tag ---
    # das ist der fall, der einen widerspruch im selben tweet verhindert.
    for tag in ("2026-09-16", "2026-09-23", "2026-09-24"):
        txt, schluessel, _ = bauen([{"d": tag, "btc": 75608.0}],
                                   'var LAST_CLOSE = 75608, LAST_DATE = "%s";' % tag,
                                   tag, 3)
        karte, _ = dayn_grafik.zahlen(
            [{"d": TOP_DATE, "btc": TOP}, {"d": "2026-06-30", "btc": 58534.28}],
            [{"d": tag, "btc": 75608.0}], bis=tag)
        pruefe("karte und text zaehlen gleich am %s" % tag,
               karte["tage_hoch"], txt.split("\n")[0][len("day "):-1])
    pruefe("der zaehltag steckt im sperrschluessel",
           bauen([{"d": "2026-09-23", "btc": 75608.0}],
                 'var LAST_CLOSE = 75608, LAST_DATE = "2026-09-23";',
                 "2026-09-24", 3)[1][len("dayn-"):], "2026-09-23")

    # das Skript auf der Seite und dieses hier muessen dieselbe Zahl rechnen
    if os.path.exists(SEITE):
        with open(SEITE, encoding="utf-8") as fh:
            html = fh.read()
        m = re.search(r"var TOP = ([0-9.]+), TOP_DATE = \"(\d{4}-\d{2}-\d{2})\"", html)
        pruefe("seite traegt dieselben konstanten",
               (float(m.group(1)), m.group(2)) if m else None, (TOP, TOP_DATE))

    # die gesamtzahl kommt aus der fallliste, nicht aus dem kopf des
    # letzten, der einen fall ergaenzt hat. sie stand schon einmal auf
    # 22, waehrend 34 faelle liefen.
    print("%d von %d faellen falsch" % (schlecht, gezaehlt))
    return 1 if schlecht else 0


if __name__ == "__main__":
    sys.exit(main())
