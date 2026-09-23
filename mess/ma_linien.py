#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ma_linien.py, Messlauf ueber gleitende Durchschnitte aus data/history.json.

REINE MESSUNG, KEINE SEITE. Das Skript rechnet und druckt, sonst nichts.
Es schreibt keine Datei und veraendert das Archiv nicht.

DATIERUNG
Gerechnet wird auf der korrigierten Reihe. Die blockchain.com-Punkte sind
seit dem 22.09.2026 in scripts/history.py um einen Tag zurueckgesetzt
(bc_tag), das Archiv traegt diese Datierung. Der Lauf prueft das am Anfang
an drei Ankerpunkten nach und bricht ab, wenn er die alte Datierung
vorfindet, damit die Verschiebung nicht in eine neue Kennzahl wandert.

DEFINITIONEN, wie vorgegeben
  SMA200d  Mittel der letzten 200 TAGESschluesse, einschliesslich des Tages
  SMA50d   dasselbe mit 50
  Wochenschluss  der Schluss des SONNTAGS in UTC
  SMA200w  Mittel der letzten 200 WOCHENschluesse, nicht 1400 Tage
  darunter Tagesschluss < Durchschnitt, strikt kleiner
  Fuer einen Tag d gilt der SMA200w des juengsten Sonntags <= d. Die Linie
  springt also woechentlich und steht zwischen zwei Sonntagen still.

    python3 mess/ma_linien.py
    python3 mess/ma_linien.py --selftest
"""
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ARCHIV = os.path.join(REPO, "data", "history.json")

# unsere acht ankerpunkte
HOCHS = ["2013-12-04", "2017-12-16", "2021-11-08", "2025-10-06"]
TIEFS = ["2015-01-14", "2018-12-15", "2022-11-21", "2026-06-30"]
# 2013-12-04 stand nicht in der vorgabe, ist aber unser viertes zyklushoch
# und wird deshalb mitgerechnet und als solches ausgewiesen.
ANKER_VORGABE = {"2017-12-16", "2021-11-08", "2025-10-06",
                 "2015-01-14", "2018-12-15", "2022-11-21", "2026-06-30"}


def D(s):
    return datetime.date(*[int(x) for x in s.split("-")])


def iso(d):
    return d.isoformat()


def lade():
    with open(ARCHIV, "r", encoding="utf-8") as fh:
        rows = json.load(fh)
    return sorted((r["d"], float(r["btc"])) for r in rows
                  if isinstance(r, dict) and isinstance(r.get("d"), str)
                  and isinstance(r.get("btc"), (int, float)))


# --- nullter schritt ------------------------------------------------

def archivguete(reihe):
    tage = [d for d, _ in reihe]
    erster, letzter = tage[0], tage[-1]
    spanne = (D(letzter) - D(erster)).days + 1
    luecken = []
    for i in range(1, len(reihe)):
        dd = (D(tage[i]) - D(tage[i - 1])).days
        if dd > 1:
            luecken.append((tage[i - 1], tage[i], dd - 1))
    return dict(erster=erster, letzter=letzter, kalendertage=spanne,
                mit_wert=len(reihe), fehlend=spanne - len(reihe),
                luecken=luecken,
                lang=[x for x in luecken if x[2] > 3])


def datierung_pruefen(preis):
    """drei anker gegen die korrigierte datierung. bricht ab, wenn das
    archiv noch die alte traegt."""
    soll = {"2025-10-06": 124776.68, "2026-06-30": 58534.28,
            "2017-12-16": 19279.90}
    schlecht = [d for d, v in soll.items()
                if abs(preis.get(d, -1) - v) > 0.005]
    return schlecht


# --- gleitende durchschnitte ----------------------------------------

def sma(reihe, fenster):
    """{tag: mittel der letzten <fenster> werte einschliesslich des tages}.
    laeuft ueber eine rollende summe, der selbsttest rechnet gegen."""
    out = {}
    summe = 0.0
    for i, (d, v) in enumerate(reihe):
        summe += v
        if i >= fenster:
            summe -= reihe[i - fenster][1]
        if i >= fenster - 1:
            out[d] = summe / fenster
    return out


def wochenschluesse(reihe):
    """(sonntag, schluss) je kalenderwoche, chronologisch. nur echte
    sonntage, jeder hoechstens einmal."""
    return [(d, v) for d, v in reihe if D(d).weekday() == 6]


def sma_w(wochen, fenster):
    out = {}
    summe = 0.0
    for i, (d, v) in enumerate(wochen):
        summe += v
        if i >= fenster:
            summe -= wochen[i - fenster][1]
        if i >= fenster - 1:
            out[d] = summe / fenster
    return out


def linie_taeglich(reihe, wochenlinie):
    """traegt den woechentlichen wert auf die tage: fuer tag d gilt der
    wert des juengsten sonntags <= d. vor dem ersten sonntag: nichts."""
    sonntage = sorted(wochenlinie)
    out = {}
    j = -1
    for d, _ in reihe:
        while j + 1 < len(sonntage) and sonntage[j + 1] <= d:
            j += 1
        if j >= 0:
            out[d] = wochenlinie[sonntage[j]]
    return out


def strecken(reihe, linie):
    """zusammenhaengende strecken, in denen der schluss unter der linie
    liegt. liefert (von, bis, tage, tiefster abstand in prozent)."""
    out = []
    lauf = None
    for d, v in reihe:
        m = linie.get(d)
        if m is None:
            continue
        if v < m:
            ab = (v / m - 1.0) * 100.0
            if lauf is None:
                lauf = [d, d, 1, ab]
            else:
                lauf[1] = d
                lauf[2] += 1
                lauf[3] = min(lauf[3], ab)
        elif lauf is not None:
            out.append(tuple(lauf))
            lauf = None
    if lauf is not None:
        out.append(tuple(lauf))
    return out


def kreuzungen(s50, s200):
    """(tag, richtung) an jedem vorzeichenwechsel von s50 - s200.
    richtung 'hoch' = s50 steigt ueber s200, 'runter' = umgekehrt."""
    tage = sorted(set(s50) & set(s200))
    out = []
    vor = None
    for d in tage:
        diff = s50[d] - s200[d]
        if diff == 0:
            continue
        zeichen = 1 if diff > 0 else -1
        if vor is not None and zeichen != vor:
            out.append((d, "hoch" if zeichen > 0 else "runter"))
        vor = zeichen
    return out


# --- selbsttest -----------------------------------------------------

def selbsttest(reihe):
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

    # --- 1) SMA200d auf einem zweiten weg ---
    # der hauptweg laeuft ueber eine rollende summe. hier wird derselbe
    # tag aus den rohwerten neu aufgebaut: 200 tage rueckwaerts gehen,
    # die kurse einsammeln, summieren, teilen.
    stichtag = "2026-09-22"
    haupt = sma(reihe, 200)[stichtag]
    preis = dict(reihe)
    kurse = []
    tag = D(stichtag)
    while len(kurse) < 200:
        kurse.append(preis[iso(tag)])
        tag -= datetime.timedelta(days=1)
    zweiter = sum(kurse) / 200.0
    print("  SMA200d am %s" % stichtag)
    print("    rollende summe : %.6f" % haupt)
    print("    von hand        : %.6f" % zweiter)
    print("    erster / letzter einbezogener tag: %s / %s"
          % (iso(D(stichtag) - datetime.timedelta(days=199)), stichtag))
    pruefe("SMA200d auf zwei wegen gleich", round(haupt, 6), round(zweiter, 6))
    pruefe("es sind wirklich 200 kurse", len(kurse), 200)

    # --- 2) SMA200w auf einem zweiten weg ---
    wochen = wochenschluesse(reihe)
    wl = sma_w(wochen, 200)
    w_stichtag = max(wl)
    haupt_w = wl[w_stichtag]
    idx = [d for d, _ in wochen].index(w_stichtag)
    hand = [v for _, v in wochen[idx - 199:idx + 1]]
    zweiter_w = sum(hand) / 200.0
    print("  SMA200w am %s (sonntag)" % w_stichtag)
    print("    rollende summe : %.6f" % haupt_w)
    print("    von hand        : %.6f" % zweiter_w)
    print("    erster / letzter einbezogener sonntag: %s / %s"
          % (wochen[idx - 199][0], w_stichtag))
    pruefe("SMA200w auf zwei wegen gleich", round(haupt_w, 6), round(zweiter_w, 6))
    pruefe("es sind wirklich 200 wochen", len(hand), 200)

    # --- 3) wochenschluss-auswahl ---
    pruefe("nur sonntage", sorted(set(D(d).weekday() for d, _ in wochen)), [6])
    pruefe("kein sonntag doppelt", len(set(d for d, _ in wochen)), len(wochen))
    abstaende = set((D(wochen[i][0]) - D(wochen[i - 1][0])).days
                    for i in range(1, len(wochen)))
    pruefe("genau sieben tage zwischen zwei wochenschluessen", abstaende, {7})
    probe = [("2010-08-20", 1.0), ("2010-08-21", 2.0), ("2010-08-22", 3.0),
             ("2010-08-23", 4.0), ("2010-08-29", 5.0)]
    pruefe("aus einer woche genau der sonntag", wochenschluesse(probe),
           [("2010-08-22", 3.0), ("2010-08-29", 5.0)])
    pruefe("eine woche ohne sonntag liefert nichts",
           wochenschluesse([("2010-08-23", 4.0), ("2010-08-24", 5.0)]), [])

    # --- 4) kreuzungserkennung ---
    # gesetzte reihe: 50 startet unter 200, geht darueber, faellt zurueck.
    t = ["2020-01-0%d" % i for i in range(1, 8)]
    a = dict(zip(t, [1.0, 2.0, 3.0, 4.0, 3.0, 2.0, 1.0]))
    b = dict(zip(t, [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0]))
    # am 01-06 sind beide linien exakt gleich. ein gleichstand ist keine
    # kreuzung, er wird uebersprungen, und die kreuzung traegt den ersten
    # tag, an dem das neue verhaeltnis wirklich gilt: den 01-07.
    pruefe("ein hoch und ein runter", kreuzungen(a, b),
           [("2020-01-03", "hoch"), ("2020-01-07", "runter")])
    pruefe("gleichstand traegt keine kreuzung", a["2020-01-06"] - b["2020-01-06"], 0.0)
    pruefe("die kreuzung traegt den ersten tag mit echtem vorzeichen",
           a["2020-01-07"] - b["2020-01-07"] < 0, True)
    pruefe("beruehrung ohne wechsel zaehlt nicht",
           kreuzungen(dict(zip(t, [1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0])),
                      dict(zip(t, [2.0] * 7))), [])
    pruefe("ohne wechsel keine kreuzung",
           kreuzungen(dict(zip(t, [3.0] * 7)), dict(zip(t, [2.0] * 7))), [])

    # an einem bekannten datum: die kreuzung, die der lauf unten meldet,
    # muss sich am tag davor und danach im vorzeichen unterscheiden.
    s50, s200 = sma(reihe, 50), sma(reihe, 200)
    kr = kreuzungen(s50, s200)
    bekannt = kr[-1][0]
    alle = sorted(set(s50) & set(s200))
    i = alle.index(bekannt)
    vorher = s50[alle[i - 1]] - s200[alle[i - 1]]
    nachher = s50[bekannt] - s200[bekannt]
    print("  juengste kreuzung %s, richtung %s" % (kr[-1][0], kr[-1][1]))
    print("    differenz am vortag %s: %+.2f" % (alle[i - 1], vorher))
    print("    differenz am tag    %s: %+.2f" % (bekannt, nachher))
    pruefe("vorzeichen wechselt an der gemeldeten kreuzung",
           (vorher > 0, nachher > 0), (False, True) if kr[-1][1] == "hoch"
           else (True, False))

    # --- 5) strecken ---
    pruefe("strecke erkannt",
           strecken([("2020-01-01", 1.0), ("2020-01-02", 3.0),
                     ("2020-01-03", 1.0), ("2020-01-04", 1.0)],
                    {"2020-01-01": 2.0, "2020-01-02": 2.0,
                     "2020-01-03": 2.0, "2020-01-04": 2.0}),
           [("2020-01-01", "2020-01-01", 1, -50.0),
            ("2020-01-03", "2020-01-04", 2, -50.0)])
    pruefe("gleichstand ist nicht darunter",
           strecken([("2020-01-01", 2.0)], {"2020-01-01": 2.0}), [])

    print("\n%d von %d faellen falsch" % (schlecht, gezaehlt))
    return 1 if schlecht else 0


# --- bericht --------------------------------------------------------

def haupt(reihe):
    preis = dict(reihe)
    g = archivguete(reihe)
    print("=" * 66)
    print("NULLTER SCHRITT, ARCHIVGUETE")
    print("=" * 66)
    print("  erster btc-tag      %s" % g["erster"])
    print("  letzter btc-tag     %s" % g["letzter"])
    print("  kalendertage        %d" % g["kalendertage"])
    print("  tage mit schluss    %d" % g["mit_wert"])
    print("  fehlende tage       %d" % g["fehlend"])
    if g["luecken"]:
        print("  luecken:")
        for a, b, L in g["luecken"]:
            print("    %s -> %s  %d tag(e)" % (a, b, L))
    else:
        print("  luecken             keine, kalendertaeglich lueckenlos")
    if g["lang"]:
        print()
        print("  !!! LUECKE LAENGER ALS 3 TAGE, betroffene zeitraeume werden")
        print("  !!! NICHT gerechnet:")
        for a, b, L in g["lang"]:
            print("      %s -> %s  %d tage" % (a, b, L))
        return 1

    schlecht = datierung_pruefen(preis)
    print("  datierung           %s" % ("korrigiert (bc_tag) bestaetigt"
                                        if not schlecht
                                        else "ABWEICHUNG bei %s" % schlecht))
    if schlecht:
        return 1

    s200 = sma(reihe, 200)
    s50 = sma(reihe, 50)
    heute, kurs = reihe[-1]

    print()
    print("=" * 66)
    print("A) 200-TAGE-LINIE")
    print("=" * 66)
    print("  linie definiert ab  %s" % min(s200))
    # A1
    lauf = 0
    start = None
    for d, v in reversed(reihe):
        if d not in s200:
            break
        if v < s200[d]:
            lauf += 1
            start = d
        else:
            break
    if lauf:
        print("  A1  aktuelle strecke unter der linie: %d tage, seit %s"
              % (lauf, start))
    else:
        print("  A1  aktuelle strecke unter der linie: 0 tage")
        print("      der letzte schluss %s liegt UEBER der linie" % heute)
        unten = [d for d, v in reihe if d in s200 and v < s200[d]]
        if unten:
            letzte = strecken(reihe, s200)[-1]
            print("      juengste abgeschlossene strecke darunter: %s bis %s, "
                  "%d tage, tiefster abstand %.2f%%"
                  % (letzte[0], letzte[1], letzte[2], letzte[3]))
    # A2
    print()
    print("  A2  laengste zusammenhaengende strecke unter der linie je abstieg")
    print("      %-12s %-12s %-12s %-12s %6s %10s"
          % ("hoch", "tief", "von", "bis", "tage", "tiefster"))
    for hoch, tief in zip(HOCHS, TIEFS):
        fenster = [(d, v) for d, v in reihe if hoch <= d <= tief]
        st = strecken(fenster, s200)
        mark = "" if hoch in ANKER_VORGABE else "   (hoch nicht in der vorgabe)"
        if not st:
            print("      %-12s %-12s  keine strecke darunter%s" % (hoch, tief, mark))
            continue
        b = max(st, key=lambda x: x[2])
        print("      %-12s %-12s %-12s %-12s %6d %9.2f%%%s"
              % (hoch, tief, b[0], b[1], b[2], b[3], mark))
    # A3
    print()
    print("  A3  abstand kurs zu SMA200d am %s" % heute)
    print("      kurs   %s" % format(kurs, ",.2f"))
    print("      SMA200d %s" % format(s200[heute], ",.2f"))
    print("      abstand %+.2f%%" % ((kurs / s200[heute] - 1) * 100))

    print()
    print("=" * 66)
    print("B) 200-WOCHEN-LINIE")
    print("=" * 66)
    wochen = wochenschluesse(reihe)
    wl = sma_w(wochen, 200)
    erster_sonntag = min(wl)
    tl = linie_taeglich(reihe, wl)
    gueltig = [(d, v) for d, v in reihe if d in tl]
    print("  wochenschluesse im archiv   %d (erster %s, letzter %s)"
          % (len(wochen), wochen[0][0], wochen[-1][0]))
    print("  linie definiert ab sonntag  %s" % erster_sonntag)
    print("  tage mit definierter linie  %d (%s bis %s)"
          % (len(gueltig), gueltig[0][0], gueltig[-1][0]))
    unten = [(d, v) for d, v in gueltig if v < tl[d]]
    print()
    print("  B1  tage unter der linie    %d von %d = %.3f%%"
          % (len(unten), len(gueltig), len(unten) / len(gueltig) * 100))
    st = strecken(gueltig, tl)
    print()
    print("  B2  alle strecken darunter (%d)" % len(st))
    print("      %-12s %-12s %6s %10s" % ("von", "bis", "tage", "tiefster"))
    for a, b, n, ab in st:
        print("      %-12s %-12s %6d %9.2f%%" % (a, b, n, ab))
    print()
    print("  B3  letzter tag unter der linie  %s"
          % (unten[-1][0] if unten else "keiner"))
    print()
    print("  B4  abstand kurs zu SMA200w am %s" % heute)
    print("      kurs    %s" % format(kurs, ",.2f"))
    print("      SMA200w %s  (stand sonntag %s)"
          % (format(tl[heute], ",.2f"), max(d for d in wl if d <= heute)))
    print("      abstand %+.2f%%" % ((kurs / tl[heute] - 1) * 100))
    print()
    sonntage = sorted(wl)
    faelle = [(sonntage[i - 1], sonntage[i], wl[sonntage[i]] - wl[sonntage[i - 1]])
              for i in range(1, len(sonntage)) if wl[sonntage[i]] < wl[sonntage[i - 1]]]
    print("  B5  ist die SMA200w jemals von woche zu woche gefallen?")
    print("      geprueft: %d wochenschritte ab %s" % (len(sonntage) - 1, erster_sonntag))
    if faelle:
        print("      JA, %d schritte:" % len(faelle))
        for a, b, delta in faelle:
            print("        %s -> %s   %+.2f" % (a, b, delta))
    else:
        print("      NEIN. In keinem einzigen Wochenschritt ist die Linie")
        print("      gefallen. Die Linie ist definiert ab %s." % erster_sonntag)

    print()
    print("=" * 66)
    print("C) 50/200-KREUZUNGEN")
    print("=" * 66)
    kr = kreuzungen(s50, s200)
    print("  beide linien definiert ab   %s" % min(set(s50) & set(s200)))
    print()
    print("  C1  %-12s %s" % ("datum", "richtung"))
    for d, r in kr:
        print("      %-12s %s" % (d, "50 ueber 200" if r == "hoch"
                                  else "50 unter 200"))
    hoch_n = sum(1 for _, r in kr if r == "hoch")
    print()
    print("  C2  hoch (50 ueber 200)   %d" % hoch_n)
    print("      runter (50 unter 200) %d" % (len(kr) - hoch_n))
    print("      gesamt                %d" % len(kr))
    return 0


def main(argv):
    reihe = lade()
    if "--selftest" in argv:
        print("=" * 66)
        print("SELBSTTEST")
        print("=" * 66)
        return selbsttest(reihe)
    return haupt(reihe)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
