#!/usr/bin/env python3
"""ph_entwurf.py - Post-Entwurf fuer @pulsehawkio aus unserer Zaehlung.

Ben, 22.10.2026: nach jedem BCH-Tempnet-Lauf (mittwochs) und nach jeder
Zcash-CSV ein Entwurf mit Grafik in den privaten Discord-Kanal. Kein Posten
auf X. Mit --senden geht der Entwurf (Text und Grafik) an den Webhook aus der
Umgebungsvariable DISCORD_WEBHOOK_PH_DRAFTS (GitHub Secret). Die Adresse wird
nie gedruckt, auch nicht in Fehlermeldungen.

Inhalt: ein gezaehlter Wert mit Vergleich zur Vorwoche oder zum
Erwartungswert, eine Zeile Deutung, Fenster in UTC, "method on pulsehawk.io".
Grafik 1600 x 900 mit Fuss "Data from PulseHawk", im Wechsel zwei Layouts
(Verteilung der Blockabstaende, Verlauf) nach der Paritaet der ISO-Woche.

Textregeln (Abbruch bei Verstoss, vor jedem Senden geprueft): alles klein,
keine Gedankenstriche, Doppelpunkte (ausser in Uhrzeiten), Pfeile, Hashtags,
Emojis, keine Echtzeitwoerter, keine Preise, "counted" genau einmal und nur
im Satz mit unserem gezaehlten Wert, "computed" statt "expected" fuer Werte
aus der Zielzeit (Ben, 23.10.2026).

Dieselbe Datei liegt in kaspa-pulse (scripts/ph/) und pulsehawk-site
(scripts/ph/). Wer eine aendert, aendert beide.

  python3 scripts/ph/ph_entwurf.py --selbsttest
  python3 scripts/ph/ph_entwurf.py bch --json data/bch/tempnet-2026-10-21.json \
      --koepfe data/bch/tempnet-koepfe.csv.gz --aus entwurf
  python3 scripts/ph/ph_entwurf.py zcash --csv data/zcash-nu7/zcash-nu7-testnet-intervals-2026-10-18.csv --aus entwurf
"""
import argparse
import csv
import glob
import gzip
import json
import math
import os
import re
import statistics
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

# ------------------------------------------------------------------ regeln
ECHTZEIT = ["now", "live", "currently", "right now", "today", "tonight", "real time", "realtime",
            "at the moment", "as we speak", "this morning", "breaking"]
PREIS = ["$", "€", "£", "usd", "eur", "price", "prices", "priced", "market cap", "pump", "dump", "moon"]
VERBOTEN_ZEICHEN = {"–": "gedankenstrich", "—": "gedankenstrich", "→": "pfeil", "←": "pfeil",
                    "⇒": "pfeil", "#": "hashtag"}
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")


def regel_pruefen(text, wert_zeile_index=1):
    """Liefert eine Liste von Verstoessen (leer = in Ordnung)."""
    fehler = []
    if text != text.lower():
        fehler.append("nicht alles klein geschrieben")
    for z, art in VERBOTEN_ZEICHEN.items():
        if z in text:
            fehler.append(f"{art} ({z!r})")
    if re.search(r"\s-\s|->|<-|=>", text):
        fehler.append("gedankenstrich oder pfeil aus ascii")
    if re.search(r"(?<!\d):|:(?!\d)", text):
        fehler.append("doppelpunkt ausserhalb einer uhrzeit")
    if EMOJI.search(text):
        fehler.append("emoji")
    woerter = text.lower()
    for w in ECHTZEIT:
        if re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", woerter):
            fehler.append(f"echtzeitwort {w!r}")
    for w in PREIS:
        if (w in woerter) if not w.isalpha() else re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", woerter):
            fehler.append(f"preis {w!r}")
    zeilen = text.split("\n")
    treffer = [i for i, z in enumerate(zeilen) if re.search(r"(?<![a-z])counted(?![a-z])", z)]
    if len(treffer) != 1 or treffer[0] != wert_zeile_index:
        fehler.append("'counted' nicht genau einmal im satz mit unserem gezaehlten wert")
    if re.search(r"(?<![a-z])expect(ed|ation)?(?![a-z])", woerter):
        fehler.append("'expected' statt 'computed' fuer werte aus der zielzeit")
    if "method on pulsehawk.io" not in text:
        fehler.append("hinweis 'method on pulsehawk.io' fehlt")
    if "utc" not in text:
        fehler.append("fenster in utc fehlt")
    return fehler


def selbsttest():
    gut = ("bch tempnet 2027 with one minute blocks.\n"
           "we counted a median block interval of 43.0 s over 7,572 blocks, against 41.6 s computed.\n"
           "that is close to what an ideal 60 s chain shows.\n"
           "window 15 oct 2026, 12:56 to 21 oct 2026, 09:59 utc, blocks 327,989 to 335,560.\n"
           "method on pulsehawk.io")
    assert regel_pruefen(gut) == [], regel_pruefen(gut)
    schlecht = {
        "Gross": gut.replace("bch", "BCH"),
        "gedankenstrich": gut.replace("blocks.", "blocks – fast."),
        "ascii-strich": gut.replace("blocks.", "blocks - fast."),
        "doppelpunkt": gut.replace("window", "window:"),
        "pfeil": gut.replace("against", "→"),
        "hashtag": gut + " #bch",
        "emoji": gut + " \U0001F680",
        "now": gut.replace("with one", "now with one"),
        "live": gut.replace("with one", "live with one"),
        "preis": gut.replace("blocks.\nwe", "blocks at $300.\nwe"),
        "counted zweimal": gut.replace("that is close", "counted, that is close"),
        "counted fehlt": gut.replace("we counted", "we saw"),
        "ohne methode": gut.replace("method on pulsehawk.io", "more soon"),
        "expected": gut.replace("computed", "expected"),
    }
    for name, t in schlecht.items():
        assert regel_pruefen(t), f"selbsttest: {name} wurde nicht erkannt"
    # jede Art der Deutungszeile muss die Regeln halten, auch mit Wertung
    import random
    zufall = random.Random(2027)
    t, rows = 1_760_000_000, []
    for h in range(1, 30_000):
        t += int(zufall.expovariate(1 / 60)) + 1
        rows.append((h, t, rows and t - rows[-1][1] or 60))
    for art in DEUTUNGEN:
        for faktor in (1, 4):
            r2 = [(h, z, a * faktor) for h, z, a in rows]
            gewaehlt, satz = deutung(r2, 60.0, 600.0, "60 s", rows[-1][1], art)
            assert gewaehlt == art, f"selbsttest: deutung {art} nicht gewaehlt"
            zeilen = gut.split("\n")
            zeilen[2] = satz
            assert regel_pruefen("\n".join(zeilen)) == [], f"selbsttest: deutung {art} {satz!r}"
    print(f"selbsttest regeln: ok ({len(schlecht)} verstoesse erkannt, gutes beispiel sauber, "
          f"{len(DEUTUNGEN)} deutungen sauber)")


# ------------------------------------------------------------------ hilfen
def zahl(x, nk=0):
    return f"{x:,.{nk}f}"


def zeit(ts):
    d = datetime.fromtimestamp(ts, timezone.utc)
    return f"{d.day} {d.strftime('%b').lower()} {d.year}, {d:%H:%M}"


def quantil(s, q):
    s = sorted(s)
    pos = (len(s) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def layout_waehlen(wunsch, ende_ts):
    if wunsch in ("verteilung", "verlauf"):
        return wunsch
    woche = datetime.fromtimestamp(ende_ts, timezone.utc).isocalendar()[1]
    return "verteilung" if woche % 2 == 0 else "verlauf"


# Deutungszeile (Ben, 22.10.2026): nicht jede Woche gleich, sondern im Wechsel
# eine konkrete Beobachtung aus den Daten. Hoechstens eine Wertung, und nur wenn
# die Zahl sie traegt (Faktor 1,5 oder mehr gegen die ideale Kette).
DEUTUNGEN = ("vorwoche", "luecke", "alt_ziel", "p90")


def wertung(r):
    if r >= 1.5:
        return "well above"
    if r <= 1 / 1.5:
        return "well below"
    return None


def dauer(s):
    if s < 120:
        return f"{s} s"
    m = round(s / 60)
    if m < 60:
        return f"{m} min"
    return f"{m // 60} h" + (f" {m % 60} min" if m % 60 else "")


def prozent(x):
    return f"{x:.1f} %" if x >= 1 else f"{x:.2g} %" if x >= 0.001 else "under 0.001 %"


def deutung(rows, ziel_s, alt_ziel_s, kette, ende_ts, wunsch="auto", ohne_vorwoche=False, versatz=0,
            schwelle_text=None):
    """rows (hoehe, zeit, abstand_zum_vorgaenger). Liefert (art, satz).
    ohne_vorwoche, wenn die Wertzeile schon gegen den Lauf der Vorwoche vergleicht.
    Auswahl nach ISO-Woche des Fensterendes plus versatz je Kette, damit BCH und
    Zcash in derselben Woche nicht dieselbe Art zeigen."""
    ab = [a for _, _, a in rows]
    moeglich = []
    # Vorwoche aus denselben Daten: die letzten 7 Tage gegen die 7 davor
    w2 = [a for _, t, a in rows if ende_ts - 7 * 86400 < t <= ende_ts]
    w1 = [a for _, t, a in rows if ende_ts - 14 * 86400 < t <= ende_ts - 7 * 86400]
    if not ohne_vorwoche and rows[0][1] <= ende_ts - 13 * 86400 and len(w1) >= 100 and len(w2) >= 100:
        moeglich.append("vorwoche")
    moeglich += ["luecke", "alt_ziel", "p90"]
    if wunsch in DEUTUNGEN and wunsch in moeglich:
        art = wunsch
    else:
        woche = datetime.fromtimestamp(ende_ts, timezone.utc).isocalendar()[1]
        art = moeglich[(woche + versatz) % len(moeglich)]
    if art == "vorwoche":
        m1, m2 = statistics.median(w1), statistics.median(w2)
        if m1 == m2:
            return art, f"over the last seven days the median held at {zahl(m2, 1)} s, as in the seven days before."
        return art, (f"over the last seven days the median {'rose' if m2 > m1 else 'fell'} to {zahl(m2, 1)} s, "
                     f"from {zahl(m1, 1)} s in the seven days before.")
    if art == "luecke":
        h, t, a = max(rows, key=lambda r: r[2])
        d = datetime.fromtimestamp(t, timezone.utc)
        return art, (f"the longest gap was {dauer(a)}, before block {zahl(h)} on "
                     f"{d.day} {d.strftime('%b').lower()} at {d:%H:%M} utc.")
    if art == "alt_ziel":
        anteil = 100 * sum(1 for a in ab if a > alt_ziel_s) / len(ab)
        ideal = 100 * math.exp(-alt_ziel_s / ziel_s)
        w = wertung(anteil / ideal) if ideal > 0 else None
        name = schwelle_text or f"the old {zahl(alt_ziel_s)} s target"
        satz = f"the share of intervals longer than {name} was {prozent(anteil)}"
        if w:
            return art, f"{satz}, {w} the {prozent(ideal)} computed for an ideal {kette} chain."
        return art, f"{satz}, against {prozent(ideal)} computed for an ideal {kette} chain."
    p90, ideal = quantil(ab, 0.9), ziel_s * math.log(10)
    w = wertung(p90 / ideal)
    satz = f"the 90th percentile of intervals is {zahl(p90)} s"
    if w:
        return art, f"{satz}, {w} the {zahl(ideal)} s computed for an ideal {kette} chain."
    return art, f"{satz}, against {zahl(ideal)} s computed for an ideal {kette} chain."


# ------------------------------------------------------------------ grafik
FARBE = {"bg": "#080B0F", "txt": "#F2F5F4", "dim": "#A9B7B4", "teal": "#49EACB", "linie": "#1C2228",
         "zweit": "#F2B84B"}


def grafik(pfad, titel, untertitel, zeichne):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(16, 9), dpi=100, facecolor=FARBE["bg"])
    ax = fig.add_axes([0.07, 0.17, 0.88, 0.62], facecolor=FARBE["bg"])
    fig.text(0.07, 0.91, titel, color=FARBE["txt"], fontsize=30, fontweight="bold")
    fig.text(0.07, 0.855, untertitel, color=FARBE["dim"], fontsize=17)
    zeichne(ax)
    for s in ax.spines.values():
        s.set_color(FARBE["linie"])
    ax.tick_params(colors=FARBE["dim"], labelsize=14)
    ax.xaxis.label.set_color(FARBE["dim"])
    ax.yaxis.label.set_color(FARBE["dim"])
    ax.grid(color=FARBE["linie"], linewidth=1)
    ax.set_axisbelow(True)
    leg = ax.get_legend()
    if leg:
        leg.get_frame().set_facecolor(FARBE["bg"])
        leg.get_frame().set_edgecolor(FARBE["linie"])
        for t in leg.get_texts():
            t.set_color(FARBE["txt"])
    fig.text(0.07, 0.045, "Data from PulseHawk", color=FARBE["teal"], fontsize=16)
    fig.text(0.95, 0.045, "pulsehawk.io", color=FARBE["dim"], fontsize=16, ha="right")
    fig.savefig(pfad, facecolor=FARBE["bg"])
    plt.close(fig)
    from PIL import Image
    with Image.open(pfad) as im:
        assert im.size == (1600, 900), f"grafik hat {im.size}, erwartet 1600x900"


def zeichne_verteilung(abstaende, ziel_s, kette):
    def z(ax):
        obergrenze = quantil(abstaende, 0.995)
        breite = max(1, round(obergrenze / 60))
        kanten = list(range(0, int(obergrenze) + breite, breite))
        ax.hist([a for a in abstaende if 0 <= a <= kanten[-1]], bins=kanten, color=FARBE["teal"],
                alpha=0.85, label="counted intervals")
        n = len(abstaende)
        xs = [k + breite / 2 for k in kanten[:-1]]
        ys = [n * (math.exp(-(x - breite / 2) / ziel_s) - math.exp(-(x + breite / 2) / ziel_s)) for x in xs]
        ax.plot(xs, ys, color=FARBE["zweit"], linewidth=3, label=f"ideal {kette} chain")
        ax.set_xlabel("seconds between blocks", fontsize=15)
        ax.set_ylabel("blocks", fontsize=15)
        ax.legend(fontsize=14)
    return z


MIN_TAG = 100  # Tage mit weniger Bloecken sagen ueber den Median nichts


def tagesmediane(paare):
    """paare (zeitstempel, abstand) -> (tage, mediane, anzahl, ausgelassen) je UTC-Tag.
    Tage unter MIN_TAG Bloecken (Tempnet 15.10.: 9 Bloecke, Median 3.650 s) fallen
    aus der Grafik und werden im Untertitel genannt."""
    tage = {}
    for t, a in paare:
        tage.setdefault(datetime.fromtimestamp(t, timezone.utc).strftime("%m.%d"), []).append(a)
    k = [x for x in sorted(tage) if len(tage[x]) >= MIN_TAG]
    weg = [f"{x} with {len(tage[x])} blocks" for x in sorted(tage) if len(tage[x]) < MIN_TAG]
    return k, [statistics.median(tage[x]) for x in k], [len(tage[x]) for x in k], weg


def weg_satz(weg):
    return f", left out {' and '.join(weg)}" if weg else ""


def zeichne_verlauf(tage, mediane, anzahl, _weg, ziel_s, kette):
    """Median je UTC-Tag gegen den Median einer idealen Kette (ziel_s * ln 2).
    Der Median, weil ein Tag mit wenigen langen Abstaenden sonst alles erdrueckt
    (Tempnet 15.10.: 10 Bloecke, Mittel 3.585 s)."""
    ideal = ziel_s * math.log(2)

    def z(ax):
        ax.bar(range(len(tage)), mediane, color=FARBE["teal"], alpha=0.85, label="counted median per utc day")
        ax.axhline(ideal, color=FARBE["zweit"], linewidth=3, label=f"median of an ideal {kette} chain")
        if len(tage) > 16:
            # Mainnet 23.10.2026: 34 Tage, Beschriftungen liefen ineinander. Nur
            # jeder k-te Tag, die Blockzahl einmal als typischer Wert je Tag.
            k = math.ceil(len(tage) / 12)
            ax.set_xticks(range(0, len(tage), k))
            ax.set_xticklabels(tage[::k], fontsize=12)
            ax.set_xlabel(f"utc day, typically {statistics.median(anzahl):,.0f} blocks counted per day", fontsize=13)
        elif len(tage) > 8:  # sonst laufen die Beschriftungen ineinander
            ax.set_xticks(range(len(tage)))
            ax.set_xticklabels([f"{t}\n{n:,}" for t, n in zip(tage, anzahl)], fontsize=11)
            ax.set_xlabel("utc day and blocks counted that day", fontsize=13)
        else:
            ax.set_xticks(range(len(tage)))
            ax.set_xticklabels([f"{t}\n{n:,} blocks" for t, n in zip(tage, anzahl)], fontsize=12)
        ax.set_ylabel("seconds", fontsize=15)
        # Platz ueber den Balken, damit die Legende nichts verdeckt
        ax.set_ylim(0, max(max(mediane), ideal) * 1.35)
        ax.legend(fontsize=14, loc="upper right", ncol=2)
    return z


# ------------------------------------------------------------------ quellen
def bch(args):
    r = json.load(open(args.json))
    B, A, E = r["bereich"], r["abstaende"], r["erwartung_abstaende"]
    stichtag = r["stichtag_utc"][:10]
    # Vorwoche: der juengste datierte Stand vor diesem
    alle = sorted(glob.glob(os.path.join(os.path.dirname(args.json), "tempnet-20*.json")))
    frueher = [p for p in alle if os.path.basename(p)[8:18] < stichtag]
    vor = json.load(open(frueher[-1])) if frueher else None
    med = float(A["median"])
    if vor:
        wert = (f"we counted a median block interval of {zahl(med, 1)} s over {zahl(B['bloecke'])} blocks, "
                f"against {zahl(float(vor['abstaende']['median']), 1)} s in our run a week earlier.")
    else:
        wert = (f"we counted a median block interval of {zahl(med, 1)} s over {zahl(B['bloecke'])} blocks, "
                f"against {zahl(E['median'], 1)} s computed for an ideal 60 s chain.")
    bis = int(datetime.strptime(B["bis_zeit_utc"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
    with gzip.open(args.koepfe, "rt") as f:
        zt = {int(z["hoehe"]): int(z["zeit"]) for z in csv.DictReader(f)}
    rows = [(h, zt[h], zt[h] - zt[h - 1]) for h in range(B["von_hoehe"] + 1, B["bis_hoehe"] + 1)]
    art, d = deutung(rows, 60.0, 600.0, "60 s", bis, args.deutung, ohne_vorwoche=bool(vor))
    text = "\n".join([
        "bch tempnet 2027 with one minute blocks.", wert, d,
        f"window {zeit(zt[B['von_hoehe']])} to {zeit(bis)} utc, blocks {zahl(B['von_hoehe'])} to {zahl(B['bis_hoehe'])}.",
        "method on pulsehawk.io"])
    layout = layout_waehlen(args.layout, bis)
    if layout == "verteilung":
        ab = [a for _, _, a in rows]
        zeichne = zeichne_verteilung(ab, 60.0, "60 s")
        titel, unter = "BCH tempnet, block intervals", f"{zahl(len(ab))} intervals counted against an ideal 60 s chain"
    else:
        tm = tagesmediane([(t, a) for _, t, a in rows])
        zeichne = zeichne_verlauf(*tm, 60.0, "60 s")
        titel, unter = "BCH tempnet, median interval per day", "days in utc from the fork block" + weg_satz(tm[3])
    return text, layout, titel, unter, zeichne, {"quelle": "bch", "stichtag": stichtag, "deutung": art}


def zcash(args):
    rows = []
    with open(args.csv) as f:
        for z in csv.DictReader(f):
            rows.append((int(z["height"]), int(z["timestamp"]), int(z["interval_s"]) if z["interval_s"] else None))
    ab = [r[2] for r in rows if r[2] is not None]
    med = statistics.median(ab)
    erw = 25 * math.log(2)
    von, bis = rows[0][1], rows[-1][1]
    art, d = deutung([r for r in rows if r[2] is not None], 25.0, 75.0, "25 s", bis, args.deutung, versatz=1)
    text = "\n".join([
        "zcash nu7 testnet with 25 s blocks.",
        f"we counted a median block interval of {zahl(med, 1)} s over {zahl(len(rows))} blocks, "
        f"against {zahl(erw, 1)} s computed for an ideal 25 s chain.",
        d,
        f"window {zeit(von)} to {zeit(bis)} utc, blocks {zahl(rows[0][0])} to {zahl(rows[-1][0])}.",
        "method on pulsehawk.io"])
    layout = layout_waehlen(args.layout, bis)
    if layout == "verteilung":
        zeichne = zeichne_verteilung(ab, 25.0, "25 s")
        titel, unter = "Zcash NU7 testnet, block intervals", f"{zahl(len(ab))} intervals counted against an ideal 25 s chain"
    else:
        tm = tagesmediane([(t, a) for h, t, a in rows if a is not None])
        zeichne = zeichne_verlauf(*tm, 25.0, "25 s")
        titel, unter = "Zcash NU7 testnet, median interval per day", "days in utc from the nu7 activation" + weg_satz(tm[3])
    return text, layout, titel, unter, zeichne, {"quelle": "zcash", "csv": os.path.basename(args.csv), "deutung": art}


def ts_aus(text):
    return int(datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())


def zcash_mainnet(args):
    """Stand aus scripts/zcash/mainnet_auswertung.py. Vor NU7 gegen 75 s mit der
    Vorhersage fuer die Aktivierungshoehe, ab NU7 gegen 25 s mit dem Einpendeln."""
    st = json.load(open(args.stand))
    nu7 = st["nu7_hoehe"]
    with gzip.open(args.koepfe, "rt") as f:
        zt = {int(z["hoehe"]): int(z["zeit"]) for z in csv.DictReader(f)}
    spitze = max(zt)
    nach_nu7 = spitze > nu7 + 100
    if nach_nu7:
        rows = [(h, zt[h], zt[h] - zt[h - 1]) for h in range(nu7 + 1, spitze + 1)]
        T, kette, schwelle, schwelle_text = 25.0, "25 s", 75.0, None
        kopf = "zcash mainnet with nu7 and 25 s blocks."
    else:
        rows = [(h, zt[h], zt[h] - zt[h - 1]) for h in sorted(zt) if h - 1 in zt and h < nu7]
        T, kette, schwelle, schwelle_text = 75.0, "75 s", 225.0, "225 s, three times the target"
        kopf = "zcash mainnet ahead of nu7 with 75 s blocks."
    ab = [a for _, _, a in rows]
    med = statistics.median(ab)
    von, bis = rows[0][1], rows[-1][1]
    # Vorwoche: juengster frueherer Stand derselben Phase, mindestens 5 Tage alt
    vor = None
    for pf in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(args.stand)), "stand-20*.json")), reverse=True):
        if os.path.abspath(pf) == os.path.abspath(args.stand):
            continue
        alt = json.load(open(pf))
        teil = alt.get("nach_nu7" if nach_nu7 else "vor_nu7")
        if teil and ts_aus(alt["bereich"]["bis_utc"]) <= bis - 5 * 86400:
            vor = teil["gezaehlt"]["median_s"]
            break
    if vor is not None:
        vergleich = f"against {zahl(vor, 1)} s in our run a week earlier."
    else:
        vergleich = f"against {zahl(T * math.log(2), 1)} s computed for an ideal {kette} chain."
    wert = f"we counted a median block interval of {zahl(med, 1)} s over {zahl(len(rows))} blocks, {vergleich}"
    art, d = deutung(rows, T, schwelle, kette, bis, args.deutung, ohne_vorwoche=vor is not None,
                     versatz=2, schwelle_text=schwelle_text)
    zeilen = [kopf, wert, d]
    v, e = st.get("vorhersage"), st.get("einpendeln")
    if not nach_nu7 and v and "median_utc" in v:
        zeilen.append(f"at the pace of the last {v['tempo_fenster_tage']} days block {zahl(nu7)} arrives around "
                      f"{zeit(ts_aus(v['median_utc']))} utc, in a 90 % band from {zeit(ts_aus(v['band_5_utc']))} "
                      f"to {zeit(ts_aus(v['band_95_utc']))}.")
    elif nach_nu7 and e:
        if e.get("eingependelt_ab_block"):
            zeilen.append(f"block times settled near 25 s after {zahl(e['bloecke_bis_eingependelt'])} blocks, "
                          f"about {zahl(e['stunden_bis_eingependelt'], 1)} hours after the first nu7 block.")
        else:
            zeilen.append(f"block times had not settled near 25 s within the first {zahl(e['bloecke_nach_nu7'])} blocks.")
    zeilen += [f"window {zeit(von)} to {zeit(bis)} utc, blocks {zahl(rows[0][0])} to {zahl(rows[-1][0])}.",
               "method on pulsehawk.io"]
    text = "\n".join(zeilen)
    layout = layout_waehlen(args.layout, bis)
    name = "Zcash mainnet with NU7" if nach_nu7 else "Zcash mainnet ahead of NU7"
    if layout == "verteilung":
        zeichne = zeichne_verteilung(ab, T, kette)
        titel, unter = f"{name}, block intervals", f"{zahl(len(ab))} intervals counted against an ideal {kette} chain"
    else:
        tm = tagesmediane([(t, a) for _, t, a in rows])
        zeichne = zeichne_verlauf(*tm, T, kette)
        titel = f"{name}, median interval per day"
        unter = ("days in utc from the nu7 activation" if nach_nu7 else "days in utc") + weg_satz(tm[3])
    return text, layout, titel, unter, zeichne, {"quelle": "zcash-mainnet", "phase": "nach_nu7" if nach_nu7 else "vor_nu7",
                                                 "stand": os.path.basename(args.stand), "deutung": art}


def senden(aus, text, meta):
    """Text und grafik.png als ein Discord-Beitrag. Gedruckt wird nur der Status."""
    hook = os.environ.get("DISCORD_WEBHOOK_PH_DRAFTS", "").strip()
    if not hook.startswith(("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/")):
        print("DISCORD_WEBHOOK_PH_DRAFTS fehlt oder ist keine Discord-Webhook-Adresse", file=sys.stderr)
        sys.exit(1)
    kopf = f"entwurf fuer @pulsehawkio, {meta['quelle']}, layout {meta['layout']}, nicht gepostet"
    inhalt = f"{kopf}\n```\n{text}\n```"
    grenze = "----ph" + uuid.uuid4().hex
    teile = []

    def feld(name, wert, dateiname=None, typ=None):
        k = f'Content-Disposition: form-data; name="{name}"'
        if dateiname:
            k += f'; filename="{dateiname}"'
        if typ:
            k += f"\r\nContent-Type: {typ}"
        teile.append(f"--{grenze}\r\n{k}\r\n\r\n".encode() + wert + b"\r\n")
    feld("payload_json", json.dumps({"content": inhalt, "allowed_mentions": {"parse": []}}).encode(),
         typ="application/json")
    with open(os.path.join(aus, "grafik.png"), "rb") as f:
        feld("files[0]", f.read(), f"pulsehawk-{meta['quelle']}-{meta['layout']}.png", "image/png")
    body = b"".join(teile) + f"--{grenze}--\r\n".encode()
    req = urllib.request.Request(hook, data=body, headers={
        "Content-Type": f"multipart/form-data; boundary={grenze}", "User-Agent": "pulsehawk-entwurf/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print(f"entwurf an discord geschickt, http {r.status}")
    except urllib.error.HTTPError as e:
        print(f"discord lehnt ab, http {e.code}", file=sys.stderr)
        sys.exit(1)
    except (urllib.error.URLError, OSError) as e:
        print(f"discord nicht erreicht, {type(e).__name__}", file=sys.stderr)
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", action="store_true")
    sub = ap.add_subparsers(dest="quelle")
    for name in ("bch", "zcash", "zcash-mainnet"):
        p = sub.add_parser(name)
        p.add_argument("--aus", required=True, help="Ausgabeverzeichnis")
        p.add_argument("--layout", default="auto", choices=["auto", "verteilung", "verlauf"])
        p.add_argument("--deutung", default="auto", choices=("auto",) + DEUTUNGEN)
        p.add_argument("--senden", action="store_true", help="an DISCORD_WEBHOOK_PH_DRAFTS schicken")
        if name == "bch":
            p.add_argument("--json", required=True)
            p.add_argument("--koepfe", required=True)
        elif name == "zcash-mainnet":
            p.add_argument("--stand", required=True, help="stand-JJJJ-MM-TT.json aus mainnet_auswertung.py")
            p.add_argument("--koepfe", required=True)
        else:
            p.add_argument("--csv", required=True)
    args = ap.parse_args()
    selbsttest()
    if args.selbsttest or not args.quelle:
        return
    text, layout, titel, unter, zeichne, meta = {"bch": bch, "zcash": zcash, "zcash-mainnet": zcash_mainnet}[args.quelle](args)
    fehler = regel_pruefen(text)
    if fehler:
        print("regelverstoss, kein entwurf:", "; ".join(fehler), file=sys.stderr)
        sys.exit(1)
    os.makedirs(args.aus, exist_ok=True)
    grafik(os.path.join(args.aus, "grafik.png"), titel, unter, zeichne)
    with open(os.path.join(args.aus, "text.txt"), "w") as f:
        f.write(text + "\n")
    meta.update({"layout": layout, "zeichen": len(text)})
    with open(os.path.join(args.aus, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(text)
    print(json.dumps(meta))
    if args.senden:
        senden(args.aus, text, meta)


if __name__ == "__main__":
    main()
