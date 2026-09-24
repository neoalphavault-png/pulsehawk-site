#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gold_in_baermaerkten.py, Messlauf: GLD und SPY ueber Bitcoins Zyklusfenster.

REINE MESSUNG. Druckt und rechnet, schreibt nichts, baut keine Seite.

FENSTER
Die bestaetigten acht Ankerpunkte. Baermarkt = Hoch bis Tief, Bullenmarkt
= Tief bis Hoch. Dazu der laufende Baermarkt ab 06.10.2025.

HANDELSTAGE
Bitcoin handelt taeglich, GLD und SPY nur an Boersentagen. Fuer jede
Fenstergrenze wird bei GLD und SPY der LETZTE HANDELSTAG AM ODER VOR dem
Stichtag genommen. Der Lauf zaehlt mit, wie oft das ein anderes Datum war,
und nennt jede Verschiebung einzeln.

ALLZEITHOCH
"Allzeithoch im Archiv" heisst: hoeher als jeder fruehere Schluss IM
ARCHIV. Die GLD-Reihe beginnt am 03.09.2010, frueheres gibt es hier nicht.
Ein echtes Allzeithoch von GLD kann davor gelegen haben.

    python3 mess/gold_in_baermaerkten.py
    python3 mess/gold_in_baermaerkten.py --selftest
"""
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ARCHIV = os.path.join(REPO, "data", "history.json")

HOCHS = ["2013-12-04", "2017-12-16", "2021-11-08", "2025-10-06"]
TIEFS = ["2015-01-14", "2018-12-15", "2022-11-21", "2026-06-30"]


def D(s):
    return datetime.date(*[int(x) for x in s.split("-")])


def lade(feld):
    with open(ARCHIV, "r", encoding="utf-8") as fh:
        rows = json.load(fh)
    return sorted((r["d"], float(r[feld])) for r in rows
                  if isinstance(r, dict) and isinstance(r.get("d"), str)
                  and isinstance(r.get(feld), (int, float)))


def am_oder_vor(reihe, tag):
    """(datum, wert) am stichtag, sonst der letzte handelstag davor."""
    tref = None
    for d, v in reihe:
        if d > tag:
            break
        tref = (d, v)
    return tref


def proz(neu, alt):
    return (float(neu) / float(alt) - 1.0) * 100.0


def athe(reihe):
    """die tage, an denen die reihe ein neues hoch im archiv setzt.
    strikt groesser als jeder fruehere schluss."""
    out = []
    hoch = None
    for d, v in reihe:
        if hoch is None or v > hoch:
            hoch = v
            out.append((d, v))
    return out


def fenster(reihe, von, bis):
    """(vondatum, vonwert, bisdatum, biswert, prozent, verschiebungen)"""
    a = am_oder_vor(reihe, von)
    b = am_oder_vor(reihe, bis)
    if not a or not b:
        return None
    versatz = []
    if a[0] != von:
        versatz.append(("start", von, a[0], (D(von) - D(a[0])).days))
    if b[0] != bis:
        versatz.append(("ende", bis, b[0], (D(bis) - D(b[0])).days))
    return (a[0], a[1], b[0], b[1], proz(b[1], a[1]), versatz)


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

    probe = [("2020-01-02", 10.0), ("2020-01-03", 11.0), ("2020-01-06", 12.0)]
    pruefe("genauer treffer", am_oder_vor(probe, "2020-01-03"), ("2020-01-03", 11.0))
    # 4. und 5. januar 2020 sind samstag und sonntag
    pruefe("wochenende faellt auf den freitag",
           am_oder_vor(probe, "2020-01-05"), ("2020-01-03", 11.0))
    pruefe("vor dem ersten handelstag nichts",
           am_oder_vor(probe, "2019-12-31"), None)
    pruefe("nach dem letzten der letzte",
           am_oder_vor(probe, "2030-01-01"), ("2020-01-06", 12.0))

    pruefe("prozent", round(proz(110.0, 100.0), 6), 10.0)
    pruefe("prozent nach unten", round(proz(90.0, 100.0), 6), -10.0)

    pruefe("neue hochs",
           [d for d, _ in athe([("a", 1.0), ("b", 2.0), ("c", 1.5), ("d", 2.0),
                                ("e", 2.5)])],
           ["a", "b", "e"])
    pruefe("gleichstand ist kein neues hoch",
           [d for d, _ in athe([("a", 1.0), ("b", 1.0)])], ["a"])

    f = fenster(probe, "2020-01-01", "2020-01-05")
    pruefe("fenster ohne startwert", f, None)
    f = fenster(probe, "2020-01-03", "2020-01-05")
    pruefe("fenster rechnet auf die handelstage", (f[0], f[2]),
           ("2020-01-03", "2020-01-03"))
    pruefe("und meldet die verschiebung am ende",
           f[5], [("ende", "2020-01-05", "2020-01-03", 2)])

    # gegenprobe auf den echten daten: ein fenster von hand
    gld = lade("gld")
    g = dict(gld)
    a = am_oder_vor(gld, "2021-11-08")
    b = am_oder_vor(gld, "2022-11-21")
    hand = (g[b[0]] / g[a[0]] - 1) * 100
    lauf = fenster(gld, "2021-11-08", "2022-11-21")[4]
    print("  GLD 2021-11-08 bis 2022-11-21")
    print("    start %s = %.4f, ende %s = %.4f" % (a[0], a[1], b[0], b[1]))
    print("    aus der funktion : %.6f%%" % lauf)
    print("    von hand         : %.6f%%" % hand)
    pruefe("fenster auf zwei wegen gleich", round(lauf, 9), round(hand, 9))

    print("\n%d von %d faellen falsch" % (schlecht, gezaehlt))
    return 1 if schlecht else 0


def zeile(name, von, bis, reihen, versatz_sammler):
    teile = []
    for feld in ("gld", "spy"):
        f = fenster(reihen[feld], von, bis)
        if f is None:
            teile.append(None)
            continue
        teile.append(f)
        for v in f[5]:
            versatz_sammler.append((name, feld) + v)
    b = fenster(reihen["btc"], von, bis)
    return b, teile


def haupt():
    reihen = {f: lade(f) for f in ("btc", "gld", "spy")}
    letzter_btc = reihen["btc"][-1][0]
    ende_laufend = letzter_btc

    print("=" * 74)
    print("DATENLAGE")
    print("=" * 74)
    for f in ("btc", "gld", "spy"):
        r = reihen[f]
        print("  %-4s %s .. %s   %d werte" % (f, r[0][0], r[-1][0], len(r)))
    print("  gld und spy handeln nur an boersentagen, btc taeglich.")
    print("  das laufende fenster endet am letzten btc-tag, %s." % ende_laufend)
    print()

    gld_hochs = athe(reihen["gld"])
    versatz = []

    for titel, paare in (
            ("BAERMAERKTE, hoch bis tief", list(zip(HOCHS, TIEFS))
             + [("2025-10-06", ende_laufend)]),
            ("BULLENMAERKTE, tief bis hoch", list(zip(TIEFS[:-1], HOCHS[1:]))
             + [("2026-06-30", ende_laufend)])):
        print("=" * 74)
        print(titel)
        print("=" * 74)
        print("  %-24s %9s %9s %9s  %s"
              % ("fenster", "BTC", "GLD", "SPY", "gld-allzeithochs im fenster"))
        for von, bis in paare:
            laufend = (bis == ende_laufend)
            b, (g, s) = zeile("%s..%s" % (von, bis), von, bis, reihen, versatz)
            hochs = [d for d, _ in gld_hochs if von <= d <= bis]
            wenn = ("%d, letztes %s" % (len(hochs), hochs[-1])) if hochs else "keins"
            print("  %-24s %+8.1f%% %+8.1f%% %+8.1f%%  %s"
                  % ("%s..%s%s" % (von, bis, " *" if laufend else ""),
                     b[4], g[4], s[4], wenn))
        print()

    print("=" * 74)
    print("HANDELSTAGE, jede verschiebung einzeln")
    print("=" * 74)
    print("  %d von %d grenzen lagen nicht auf einem boersentag"
          % (len(versatz), 2 * 2 * (len(HOCHS) + 1 + len(TIEFS))))
    print("  %-26s %-4s %-6s %-12s %-12s %s"
          % ("fenster", "feld", "rand", "stichtag", "genommen", "tage frueher"))
    for name, feld, rand, soll, ist, n in versatz:
        print("  %-26s %-4s %-6s %-12s %-12s %d" % (name, feld, rand, soll, ist, n))
    print()

    print("=" * 74)
    print("GLD-ALLZEITHOCHS IM ARCHIV, alle")
    print("=" * 74)
    print("  gesamt %d, erstes %s, letztes %s"
          % (len(gld_hochs), gld_hochs[0][0], gld_hochs[-1][0]))
    print("  hoechster schluss im archiv: %s am %s"
          % (format(gld_hochs[-1][1], ",.2f"), gld_hochs[-1][0]))
    jahre = {}
    for d, _ in gld_hochs:
        jahre[d[:4]] = jahre.get(d[:4], 0) + 1
    print("  je jahr: %s" % ", ".join("%s:%d" % kv for kv in sorted(jahre.items())))
    return 0


def main(argv):
    if "--selftest" in argv:
        print("=" * 74)
        print("SELBSTTEST")
        print("=" * 74)
        return selbsttest()
    return haupt()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
