#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rueckschlaege.py, Messlauf: Rueckgaenge INNERHALB der Bullenmaerkte.

REINE MESSUNG. Rechnet und druckt, schreibt nichts, baut keine Seite.

DEFINITION, damit nichts wackelt
Eine Episode beginnt an einem LAUFENDEN HOCH und endet am tiefsten
Tagesschluss, bevor dieses Hoch wieder ueberboten wird. Die Episoden
ueberlappen sich dadurch nie und decken das Fenster luecken los ab.
  Tiefe  = Tief / Hoch - 1, auf Tagesschluessen
  Dauer  = Kalendertage vom Hoch zum Tief, also die Strecke ABWAERTS.
           Nicht die Zeit bis zur Erholung.
Gezaehlt wird eine Episode, wenn ihre Tiefe mindestens die Schwelle
erreicht. Die Schwelle ist ein Parameter, Vorgabe 20 Prozent.

Am rechten Rand des laufenden Aufstiegs kann eine Episode OFFEN sein,
also ihr Hoch noch nicht wieder erreicht. Solche Faelle sind mit einem
Stern markiert und in jeder Zaehlung enthalten.

DATEN
Archiv plus Tageslog ueber market_log.reihe_mit_logvorrang, also mit dem
Marktlog am rechten Rand. Korrigierte Datierung (bc_tag).

⚠️ DIESER IMPORT IST DER GRUND FUER DEN GROSSEN DIFF DES BRANCHES
Die Funktion liegt auf pages/gold-2026-09-24, deshalb wurde dieser Branch
am 24.09.2026 darauf gemergt. Ohne den Merge muesste hier die
Vorrangregel ein drittes Mal stehen, und genau das sollte die gemeinsame
Funktion beenden. Siehe mess/LIESMICH.md: der Unterbau ist Absicht und
gehoert nicht "aufgeraeumt".

    python3 mess/rueckschlaege.py
    python3 mess/rueckschlaege.py --schwelle 15
    python3 mess/rueckschlaege.py --selftest
"""
import datetime
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
from market_log import reihe_mit_logvorrang  # noqa: E402

# tief -> hoch, unsere bestaetigten anker. das letzte paar ist offen.
AUFSTIEGE = [("2015-01-14", "2017-12-16"),
             ("2018-12-15", "2021-11-08"),
             ("2022-11-21", "2025-10-06"),
             ("2026-06-30", None)]


def D(s):
    return datetime.date(*[int(x) for x in s.split("-")])


def lade():
    with open(os.path.join(REPO, "data", "history.json"), encoding="utf-8") as fh:
        archiv = json.load(fh)
    with open(os.path.join(REPO, "data", "market-log.json"), encoding="utf-8") as fh:
        log = json.load(fh)
    return reihe_mit_logvorrang("btc", archiv=archiv, log=log)


def fenster(reihe, von, bis):
    return [(d, v) for d, v in reihe if von <= d and (bis is None or d <= bis)]


def rueckschlaege(reihe, schwelle):
    """(hoch, tief, tiefe_prozent, tage, erholt) je episode ab schwelle."""
    if len(reihe) < 2:
        return []
    out = []
    hd, hv = reihe[0]
    td, tv = reihe[0]
    for d, v in reihe[1:]:
        if v >= hv:
            tiefe = (tv / hv - 1.0) * 100.0
            if -tiefe >= schwelle:
                out.append((hd, td, tiefe, (D(td) - D(hd)).days, True))
            hd, hv = d, v
            td, tv = d, v
        elif v < tv:
            td, tv = d, v
    tiefe = (tv / hv - 1.0) * 100.0
    if -tiefe >= schwelle:
        out.append((hd, td, tiefe, (D(td) - D(hd)).days, False))
    return out


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

    # 100 -> 70 (-30%) -> 120 -> 90 (-25%) -> 130
    r = [("2020-01-01", 100.0), ("2020-01-05", 70.0), ("2020-01-10", 120.0),
         ("2020-01-15", 90.0), ("2020-01-20", 130.0)]
    e = rueckschlaege(r, 20.0)
    pruefe("zwei episoden", len(e), 2)
    pruefe("erste: hoch, tief, tiefe, tage",
           (e[0][0], e[0][1], round(e[0][2], 4), e[0][3]),
           ("2020-01-01", "2020-01-05", -30.0, 4))
    pruefe("zweite rechnet gegen das NEUE hoch",
           (e[1][0], round(e[1][2], 4)), ("2020-01-10", -25.0))
    pruefe("beide sind erholt", [x[4] for x in e], [True, True])
    # schwelle greift
    pruefe("bei 26 prozent bleibt eine", len(rueckschlaege(r, 26.0)), 1)
    pruefe("bei 31 prozent bleibt keine", rueckschlaege(r, 31.0), [])
    pruefe("genau auf der schwelle zaehlt mit", len(rueckschlaege(r, 30.0)), 1)

    # offene episode am rand
    r2 = [("2020-01-01", 100.0), ("2020-01-10", 60.0)]
    e2 = rueckschlaege(r2, 20.0)
    pruefe("offene episode wird gemeldet",
           (len(e2), e2[0][4], round(e2[0][2], 4)), (1, False, -40.0))
    # ein zwischentief, das spaeter unterboten wird, zaehlt nur einmal
    r3 = [("2020-01-01", 100.0), ("2020-01-05", 80.0), ("2020-01-06", 85.0),
          ("2020-01-09", 60.0), ("2020-01-20", 110.0)]
    e3 = rueckschlaege(r3, 20.0)
    pruefe("eine episode bis zum tiefsten punkt",
           (len(e3), e3[0][1], round(e3[0][2], 4)), (1, "2020-01-09", -40.0))
    # eine reihe, die nur steigt
    pruefe("ohne rueckgang nichts",
           rueckschlaege([("a", 1.0), ("b", 2.0), ("c", 3.0)], 20.0), [])
    pruefe("zu kurze reihe", rueckschlaege([("a", 1.0)], 20.0), [])

    # fenster schneidet richtig
    pruefe("fenster mit beiden raendern",
           fenster([("2020-01-01", 1.0), ("2020-01-02", 2.0), ("2020-01-03", 3.0)],
                   "2020-01-02", "2020-01-03"),
           [("2020-01-02", 2.0), ("2020-01-03", 3.0)])
    pruefe("offenes fenster laeuft bis zum ende",
           len(fenster([("2020-01-01", 1.0), ("2020-01-02", 2.0)], "2020-01-01", None)), 2)

    print("\n%d von %d faellen falsch" % (schlecht, gezaehlt))
    return 1 if schlecht else 0


def tabelle(reihe, schwelle, zeigen=True):
    alle = []
    for von, bis in AUFSTIEGE:
        f = fenster(reihe, von, bis)
        e = rueckschlaege(f, schwelle)
        alle.append((von, bis or f[-1][0], f, e))
    if not zeigen:
        return alle
    for von, bis, f, e in alle:
        offen = " (laufend)" if (von, None) in [(a, b) for a, b in AUFSTIEGE] else ""
        print("  %s bis %s%s, %d tage im fenster, %d rueckschlaege ab %g%%"
              % (von, bis, offen, len(f), len(e), schwelle))
        if e:
            print("      %-12s %-12s %9s %6s" % ("von", "bis", "tiefe", "tage"))
            for hd, td, tiefe, tage, erholt in e:
                print("      %-12s %-12s %8.2f%% %6d%s"
                      % (hd, td, tiefe, tage, "" if erholt else "   *offen"))
        print()
    return alle


def haupt(schwelle):
    reihe = lade()
    print("=" * 70)
    print("DATENLAGE")
    print("=" * 70)
    print("  btc %s .. %s, %d tage (archiv + tageslog, log am rechten rand)"
          % (reihe[0][0], reihe[-1][0], len(reihe)))
    print("  schwelle %g%%, definition siehe kopf der datei" % schwelle)
    print()
    print("=" * 70)
    print("RUECKSCHLAEGE JE AUFSTIEG, schwelle %g%%" % schwelle)
    print("=" * 70)
    alle = tabelle(reihe, schwelle)

    flach = [x for _, _, _, e in alle for x in e]
    print("=" * 70)
    print("ZUSAMMEN, schwelle %g%%" % schwelle)
    print("=" * 70)
    print("  episoden gesamt            %d" % len(flach))
    if flach:
        tiefen = sorted(x[2] for x in flach)
        tage = sorted(x[3] for x in flach)
        print("  tiefe   median %7.2f%%   von %7.2f%% bis %7.2f%%   spanne %.2f punkte"
              % (statistics.median(tiefen), min(tiefen), max(tiefen),
                 max(tiefen) - min(tiefen)))
        print("  dauer   median %4d tage   von %d bis %d tage"
              % (statistics.median(tage), min(tage), max(tage)))
        jahre = {}
        for hd, _, _, _, _ in flach:
            jahre[hd[:4]] = jahre.get(hd[:4], 0) + 1
        print("  je kalenderjahr des HOCHS: %s"
              % ", ".join("%s:%d" % kv for kv in sorted(jahre.items())))
        jahre2 = {}
        for _, td, _, _, _ in flach:
            jahre2[td[:4]] = jahre2.get(td[:4], 0) + 1
        print("  je kalenderjahr des TIEFS: %s"
              % ", ".join("%s:%d" % kv for kv in sorted(jahre2.items())))
    print()
    print("=" * 70)
    print("WIE SEHR HAENGT DAS AN DER SCHWELLE")
    print("=" * 70)
    print("  %-9s %-9s %-9s %-9s %-9s %s"
          % ("schwelle", "2015-17", "2018-21", "2022-25", "2026-", "gesamt"))
    for sch in (15.0, 20.0, 25.0):
        z = [len(e) for _, _, _, e in tabelle(reihe, sch, zeigen=False)]
        print("  %-9s %-9d %-9d %-9d %-9d %d" % ("%g%%" % sch, z[0], z[1], z[2], z[3], sum(z)))
    print()
    for sch in (15.0, 20.0, 25.0):
        f = [x for _, _, _, e in tabelle(reihe, sch, zeigen=False) for x in e]
        if f:
            t = sorted(x[2] for x in f)
            print("  %g%%: %d episoden, tiefe median %.2f%%, von %.2f%% bis %.2f%%"
                  % (sch, len(f), statistics.median(t), min(t), max(t)))
    return 0


def main(argv):
    if "--selftest" in argv:
        print("=" * 70)
        print("SELBSTTEST")
        print("=" * 70)
        return selbsttest()
    sch = 20.0
    if "--schwelle" in argv:
        sch = float(argv[argv.index("--schwelle") + 1])
    return haupt(sch)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
