#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""upgrade_report.py, Report-Typ "Upgrade Report" (PH-UR) im PulseHawk Measurement
Framework, Spezifikation v1.0 (Ben, 2.11.2026).

Rechnet M1 bis M7 aus reports/<slug>.csv und baut den Seiteninhalt. Der
gemeinsame Waechter (scripts/report_waechter.py) prueft vorher und nachher
alles, was fuer jeden Typ gilt, und baut die Seite nur, wenn alles gruen ist.

Kopfdaten: data/reports/<slug>.json mit "typ": "upgrade-report". Die messende
Sitzung liefert die CSV und ihre eigenen Werte unter "werte"; der Waechter
rechnet sie aus der CSV nach und vergleicht exakt.
"""

import csv
import hashlib
import io
import math
import re

from report_waechter import (SITE, E, betrag, ts, iso, lang, datum_lang, fenster, fenster_text,
                             wert_html, zitier_html)

# die quellenfelder, die der waechter unter d) prueft
QUELLEN_FELDER = (("aktivierungshoehe", "aktivierungshoehe"), ("ziel_vorher", "zielabstand vorher"),
                  ("ziel_nachher", "zielabstand nachher"))

METHODE = "1.0"                     # aktuelle version der rechenvorschrift
METHODE_PFAD = "/standard/upgrade-report/v1-0"   # jede version bleibt unter ihrem pfad abrufbar
VOR_S = 24 * 3600                   # fenster 24 h vor der aktivierungshoehe
NACH_S = 72 * 3600                  # bis 72 h danach
LUECKE_FAKTOR = 5                   # M2, abstaende ueber 5 x ziel
# M6 nach Bens Entscheidung vom 3.11.2026: das Mittel der Blockabstaende der
# letzten Stunde liegt innerhalb +-20 % des neuen Ziels T, stabil ab dem ersten
# Block, nach dem das 60 Minuten ohne Unterbrechung gilt. Dieselbe Rechnung
# macht report_v1.py in kaspa-pulse, Variante "mittel".
STABIL_FENSTER_S = 3600             # M6, gleitendes fenster 1 h
STABIL_HALTEN_S = 3600              # M6, 60 min ohne unterbrechung im band
STABIL_TOLERANZ = 0.20              # M6, innerhalb 20 % des ziels
# die proben, die der report zeigt. Die Wache probt auch nach 6 h, diese Probe
# bleibt in den Rohdaten (label plus_6h) und erscheint nicht in M5.
PROBEN = (("activation", 0), ("plus_24h", 24 * 3600), ("plus_72h", 72 * 3600))
PROBEN_ROH = PROBEN + (("plus_6h", 6 * 3600),)
PROBE_TOLERANZ_S = 3600             # M5, probe hoechstens 1 h neben ihrem zeitpunkt
CSV_SPALTEN = ["report_id", "method_version", "kind", "label", "height", "time_utc", "value"]
METRIKEN = [
    ("M1", "Block intervals",
     "p50, p90 and p99 of the block intervals, before and after the activation height, "
     "each against the value computed for an ideal chain at the target interval."),
    ("M2", "Longest gap",
     "The longest block interval and the number of intervals above five times the target."),
    ("M3", "Reorgs", "The number of reorgs and their maximum depth in blocks."),
    ("M4", "Chain split",
     "Heights with competing tips, the most tips at one height and how long the longest lasted."),
    ("M5", "Peers on pre-upgrade software",
     "The share of peers in our sample that run pre-upgrade software at activation, "
     "24 hours later and 72 hours later, with n."),
    ("M6", "Time to stable",
     "The time from the activation block until the mean of the block intervals over the last hour "
     "lies within 20 % of the new target and stays there for 60 minutes without a break."),
    ("M7", "First block at the activation height",
     "Its time and the gap to our own estimate published before activation."),
]


def rang(werte, zaehler, nenner=100):
    """perzentil nach dem naechsten rang: der wert an stelle ceil(q n) der
    sortierten liste, q = zaehler / nenner. ganzzahlig, ohne interpolation."""
    s = sorted(werte)
    k = -(-zaehler * len(s) // nenner)
    return s[max(k, 1) - 1]


def ideal(ziel, q):
    """perzentil einer idealen kette mit exponentiellen abstaenden, auf 0.1 s."""
    return round(-ziel * math.log(1 - q), 1)


def dauer_text(s):
    if s is None:
        return "not within the window"
    h, m = divmod(round(s / 60), 60)
    return ("%d h %d min" % (h, m)) if h else ("%d min" % m)


def prozent(alt, n):
    return "%.1f %%" % (100 * alt / n) if n else "no peers sampled"


def zeilen(text):
    """csv streng lesen. jede spalte hat ihr format, sonst ValueError."""
    r = csv.DictReader(io.StringIO(text))
    if r.fieldnames != CSV_SPALTEN:
        raise ValueError("csv-spalten %r, erwartet %r" % (r.fieldnames, CSV_SPALTEN))
    aus = []
    for i, z in enumerate(r, 2):
        art = z["kind"]
        if art not in ("block", "reorg", "tip", "peer"):
            raise ValueError("zeile %d, kind %r unbekannt" % (i, art))
        if art == "peer":
            if z["label"] not in dict(PROBEN_ROH) or z["height"] or z["value"] not in ("0", "1"):
                raise ValueError("zeile %d, peer braucht label %s, leere height, value 0 oder 1"
                                 % (i, "/".join(dict(PROBEN_ROH))))
        elif z["label"]:
            raise ValueError("zeile %d, label nur bei peer" % i)
        if art != "peer" and not re.fullmatch(r"\d+", z["height"]):
            raise ValueError("zeile %d, height keine ganze zahl" % i)
        if z["value"] and not re.fullmatch(r"-?\d+", z["value"]):
            raise ValueError("zeile %d, value keine ganze zahl" % i)
        if art in ("reorg", "tip") and not z["value"]:
            raise ValueError("zeile %d, %s braucht value" % (i, art))
        aus.append(dict(z, t=ts(z["time_utc"]),
                        h=int(z["height"]) if z["height"] else None,
                        v=int(z["value"]) if z["value"] else None))
    return aus


def rechnen(kopf, rows):
    """alle werte M1 bis M7 aus den csv-zeilen, nach spezifikation v1.0."""
    H = kopf["aktivierungshoehe"]["wert"]
    t_vor, t_nach = kopf["ziel_vorher"]["wert"], kopf["ziel_nachher"]["wert"]
    bl = sorted((z for z in rows if z["kind"] == "block"), key=lambda z: z["h"])
    zeit = {z["h"]: z["t"] for z in bl}
    if H not in zeit:
        raise ValueError("kein block auf der aktivierungshoehe %d in der csv" % H)
    ta = zeit[H]
    vor = [zeit[h] - zeit[h - 1] for h in sorted(zeit) if h < H and h - 1 in zeit]
    nach_paare = [(zeit[h], zeit[h] - zeit[h - 1]) for h in sorted(zeit) if h > H and h - 1 in zeit]
    nach = [a for _, a in nach_paare]

    def m1(ab, ziel):
        if not ab:
            return {"n": 0}
        return {"n": len(ab), "p50": rang(ab, 50), "p90": rang(ab, 90), "p99": rang(ab, 99),
                "p50_ideal": ideal(ziel, 0.5), "p90_ideal": ideal(ziel, 0.9),
                "p99_ideal": ideal(ziel, 0.99)}

    def m2(ab, ziel):
        if not ab:
            return {"n": 0}
        return {"n": len(ab), "laengste_s": max(ab),
                "ueber_5x": sum(1 for a in ab if a > LUECKE_FAKTOR * ziel),
                "schwelle_s": LUECKE_FAKTOR * ziel}

    reorgs = [z["v"] for z in rows if z["kind"] == "reorg"]
    tips = {}
    for z in rows:
        if z["kind"] == "tip":
            tips.setdefault(z["h"], []).append(z["v"])
    konk = {h: d for h, d in tips.items() if len(d) >= 2}
    proben = {}
    for name, _ in PROBEN:
        p = [z for z in rows if z["kind"] == "peer" and z["label"] == name]
        proben[name] = {"n": len(p), "alt": sum(z["v"] for z in p),
                        "von": min((z["t"] for z in p), default=None),
                        "bis": max((z["t"] for z in p), default=None)}
    # M6: fuer jeden block ab aktivierung + 1 h das mittel der abstaende der
    # bloecke in der stunde davor (zeit u mit t - 1 h < u <= t). Stabil ab dem
    # ersten block, ab dem jedes mittel bis 60 min spaeter im band liegt und die
    # daten diese 60 min ganz abdecken.
    lo, hi = t_nach * (1 - STABIL_TOLERANZ), t_nach * (1 + STABIL_TOLERANZ)
    punkte = sorted(nach_paare)
    verlauf = []
    for t, _ in punkte:
        if t < ta + STABIL_FENSTER_S:
            continue
        w60 = [a for u, a in punkte if t - STABIL_FENSTER_S < u <= t]
        verlauf.append((t, lo <= sum(w60) / len(w60) <= hi))
    stabil = None
    for i, (t, drin) in enumerate(verlauf):
        if not drin or verlauf[-1][0] < t + STABIL_HALTEN_S:
            continue
        if all(d for u, d in verlauf[i:] if u <= t + STABIL_HALTEN_S):
            stabil = t - ta
            break
    schaetz = ts(kopf["schaetzung"]["zeit_utc"])
    return {
        "M1": {"vorher": m1(vor, t_vor), "nachher": m1(nach, t_nach)},
        "M2": {"vorher": m2(vor, t_vor), "nachher": m2(nach, t_nach)},
        "M3": {"reorgs": len(reorgs), "max_tiefe": max(reorgs, default=0)},
        "M4": {"hoehen": len(konk), "max_tips": max((len(d) for d in konk.values()), default=0),
               "laengste_s": max((max(d) for d in konk.values()), default=0)},
        "M5": {k: {"n": v["n"], "alt": v["alt"]} for k, v in proben.items()},
        "M6": {"sekunden": stabil, "fenster": len(verlauf), "band_von_s": round(lo, 1),
               "band_bis_s": round(hi, 1)},
        "M7": {"zeit_utc": iso(ta), "abstand_s": ta - schaetz},
        "_fenster": {"von": ta - VOR_S, "bis": ta + NACH_S, "ta": ta,
                     "proben": {k: (v["von"], v["bis"]) for k, v in proben.items()}},
    }


def oeffentlich(w):
    return {k: v for k, v in w.items() if not k.startswith("_")}


def pruefe_plausibel(w, rows=None, kopf=None):
    """c) reihenfolge der perzentile, keine negativen zaehlungen, fenster."""
    f = []
    for teil in ("vorher", "nachher"):
        m = w["M1"][teil]
        if m.get("n") and not (m["p50"] <= m["p90"] <= m["p99"]):
            f.append(("c", "M1 %s, p50 %s, p90 %s, p99 %s nicht aufsteigend"
                      % (teil, m["p50"], m["p90"], m["p99"])))
    zaehl = [("M1 %s n" % t, w["M1"][t]["n"]) for t in ("vorher", "nachher")]
    zaehl += [("M2 %s n" % t, w["M2"][t]["n"]) for t in ("vorher", "nachher")]
    zaehl += [("M2 %s ueber_5x" % t, w["M2"][t].get("ueber_5x", 0)) for t in ("vorher", "nachher")]
    zaehl += [("M3 reorgs", w["M3"]["reorgs"]), ("M3 max_tiefe", w["M3"]["max_tiefe"]),
              ("M4 hoehen", w["M4"]["hoehen"]), ("M4 max_tips", w["M4"]["max_tips"]),
              ("M4 laengste_s", w["M4"]["laengste_s"])]
    for k, v in w["M5"].items():
        zaehl += [("M5 %s n" % k, v["n"]), ("M5 %s alt" % k, v["alt"])]
        if v["alt"] > v["n"]:
            f.append(("c", "M5 %s, %d alte peers bei n %d" % (k, v["alt"], v["n"])))
    for name, v in zaehl:
        if not isinstance(v, int) or v < 0:
            f.append(("c", "zaehlung %s ist %r" % (name, v)))
    if w["M6"]["sekunden"] is not None and w["M6"]["sekunden"] < STABIL_FENSTER_S:
        f.append(("c", "M6 %s s liegt vor dem ersten vollen 1-h-fenster" % w["M6"]["sekunden"]))
    if rows is not None:
        H = kopf["aktivierungshoehe"]["wert"]
        bl = sorted(z["h"] for z in rows if z["kind"] == "block")
        if H not in bl:
            f.append(("c", "kein block auf der aktivierungshoehe %d" % H))
            return f
        if bl != list(range(bl[0], bl[-1] + 1)):
            f.append(("c", "blockhoehen in der csv nicht lueckenlos"))
        ta = next(z["t"] for z in rows if z["kind"] == "block" and z["h"] == H)
        von, bis = ta - VOR_S, ta + NACH_S
        for z in rows:
            if not von <= z["t"] <= bis:
                f.append(("c", "%s auf hoehe %s um %s liegt ausserhalb des fensters %s"
                          % (z["kind"], z["height"] or "-", z["time_utc"], fenster(von, bis))))
                break
        if bl[0] >= H or bl[-1] <= H:
            f.append(("c", "fenster deckt die aktivierungshoehe nicht von beiden seiten"))
        for name, ab in PROBEN_ROH:
            p = [z["t"] for z in rows if z["kind"] == "peer" and z["label"] == name]
            if p and (min(p) < ta + ab - PROBE_TOLERANZ_S or max(p) > ta + ab + PROBE_TOLERANZ_S):
                f.append(("c", "peer-probe %s nicht innerhalb 1 h um aktivierung %+d h"
                          % (name, ab // 3600)))
        zeit = {z["h"]: z["t"] for z in rows if z["kind"] == "block"}
        for z in rows:
            if z["kind"] == "block" and z["v"] is not None and z["h"] - 1 in zeit \
                    and z["v"] != zeit[z["h"]] - zeit[z["h"] - 1]:
                f.append(("c", "block %d, value %d passt nicht zu den zeiten (%d)"
                          % (z["h"], z["v"], zeit[z["h"]] - zeit[z["h"] - 1])))
                break
        for z in rows:
            if z["report_id"] != kopf["id"] or z["method_version"] != kopf["methode"]:
                f.append(("c", "csv-zeile mit report_id %r oder method_version %r, erwartet %r und %r"
                          % (z["report_id"], z["method_version"], kopf["id"], kopf["methode"])))
                break
    return f


def seiten_werte(w):
    """alle (schluessel, kanonischer wert) die auf der seite stehen muessen."""
    aus = {}
    for t in ("vorher", "nachher"):
        m1 = w["M1"][t]
        if m1["n"]:
            for k in ("p50", "p90", "p99", "p50_ideal", "p90_ideal", "p99_ideal"):
                aus["M1.%s.%s" % (t, k)] = m1[k]
        m2 = w["M2"][t]
        if m2["n"]:
            for k in ("laengste_s", "ueber_5x", "schwelle_s"):
                aus["M2.%s.%s" % (t, k)] = m2[k]
    for k in ("reorgs", "max_tiefe"):
        aus["M3." + k] = w["M3"][k]
    for k in ("hoehen", "max_tips", "laengste_s"):
        aus["M4." + k] = w["M4"][k]
    for k, v in w["M5"].items():
        aus["M5.%s.alt" % k] = v["alt"]
    aus["M6.sekunden"] = w["M6"]["sekunden"]
    aus["M6.band_von_s"] = w["M6"]["band_von_s"]
    aus["M6.band_bis_s"] = w["M6"]["band_bis_s"]
    aus["M7.zeit_utc"] = w["M7"]["zeit_utc"]
    aus["M7.abstand_s"] = w["M7"]["abstand_s"]
    return aus


def body(kopf, w, csv_text):
    """der inhalt der report-seite. Ohne werte ein geruest mit M1 bis M7."""
    H = kopf["aktivierungshoehe"]["wert"]
    t_vor, t_nach = kopf["ziel_vorher"]["wert"], kopf["ziel_nachher"]["wert"]
    q = lambda feld: " and ".join('<a href="%s" rel="noopener">%s</a>' % (E(x["url"], quote=True), E(x["name"]))
                                  for x in kopf[feld]["quellen"])
    ziel_text = ("%d s to %d s" % (t_vor, t_nach)) if t_vor != t_nach else "%d s" % t_nach
    fakten = "".join('<div><dt>%s</dt><dd class="fv">%s</dd><dd class="fq">%s</dd></div>' % z for z in (
        ("Report ID", E(kopf["id"]), "fixed, cite it with the URL"),
        ("Method", "v%s" % E(kopf["methode"]), '<a href="%s">PulseHawk Upgrade Report, specification v%s</a>'
         % (METHODE_PFAD, E(kopf["methode"]))),
        ("Activation height", betrag(H), "source %s" % q("aktivierungshoehe")),
        ("Target interval", ziel_text, "source %s" % (q("ziel_vorher") if t_vor == t_nach else
                                                      "%s, then %s" % (q("ziel_vorher"), q("ziel_nachher")))),
        ("Window", "24 h before to 72 h after", "the activation block, in UTC"),
        ("Status", "measured" if w else "pending", "numbers from the CSV below" if w
         else "first numbers after block %s" % betrag(H)),
    ))
    teile = ['<section id="in-short" class="facts"><h2>The report in short</h2><dl>%s</dl></section>' % fakten]
    if kopf.get("hinweis"):
        teile.append("<p>%s</p>" % E(kopf["hinweis"]))
    if not w:
        s = kopf["schaetzung"]
        for mid, name, was in METRIKEN:
            # zu M7 gehoert unsere schaetzung, die vor der aktivierung feststeht
            extra = ("<p>Our estimate before activation is %s.</p>" % schaetz_text(s)
                     if mid == "M7" else "")
            teile.append('<section id="%s"><h2>%s %s</h2><p>%s</p>%s<p class="note">Not yet counted. '
                         'The numbers follow after block %s, from our own count.</p></section>'
                         % (mid.lower(), mid, name, was, extra, betrag(H)))
        teile.append('<section id="data"><h2>Data</h2><p>The CSV with every block, reorg, tip and '
                     'peer sample follows with the first numbers, with its sha256 and the method version.'
                     '</p></section>')
    else:
        f = w["_fenster"]
        f_vor, f_nach, f_alle = fenster(f["von"], f["ta"]), fenster(f["ta"], f["bis"]), fenster(f["von"], f["bis"])
        for t, ziel, fen, wort in (("vorher", t_vor, f_vor, "before"), ("nachher", t_nach, f_nach, "after")):
            m = w["M1"][t]
            if not m["n"]:
                continue
            zeilen_ = "".join(
                '<tr><td class="c">%s</td><td>%s</td><td>%s</td></tr>'
                % (k, wert_html("M1.%s.%s" % (t, k), m[k], "%s s" % m[k], "counted", m["n"], fen),
                   wert_html("M1.%s.%s_ideal" % (t, k), m[k + "_ideal"], "%s s" % m[k + "_ideal"],
                             "computed", m["n"], fen))
                for k in ("p50", "p90", "p99"))
            teile.append(
                '<section id="m1-%s"><h2>M1 Block intervals %s activation</h2>'
                '<div class="tablewrap"><table class="nums"><thead><tr><th scope="col">Interval</th>'
                '<th scope="col">Counted</th><th scope="col">Computed at %d s</th></tr></thead>'
                '<tbody>%s</tbody></table></div><p class="src">Window %s.</p></section>'
                % (wort, wort, ziel, zeilen_, fenster_text(fen)))
        def tabelle(sid, h2, zeilen_, fen_text, zusatz=""):
            """ein abschnitt mit einer tabelle wert und ergebnis, darunter das fenster."""
            rows_ = "".join('<tr><td class="c">%s</td><td>%s</td></tr>' % z for z in zeilen_)
            return ('<section id="%s"><h2>%s</h2><div class="tablewrap"><table class="nums"><thead><tr>'
                    '<th scope="col">Value</th><th scope="col">Result</th></tr></thead><tbody>%s</tbody>'
                    '</table></div>%s<p class="src">Window %s.</p></section>' % (sid, h2, rows_, zusatz, fen_text))

        for t, fen, wort in (("vorher", f_vor, "before"), ("nachher", f_nach, "after")):
            m = w["M2"][t]
            if not m["n"]:
                continue
            teile.append(tabelle("m2-" + wort, "M2 Longest gap %s activation" % wort, [
                ("Longest interval", wert_html("M2.%s.laengste_s" % t, m["laengste_s"],
                                               "%s s" % betrag(m["laengste_s"]), "counted", m["n"], fen)),
                ("Five times the target", wert_html("M2.%s.schwelle_s" % t, m["schwelle_s"],
                                                    "%d s" % m["schwelle_s"], "computed", m["n"], fen)),
                ("Intervals above five times the target", wert_html("M2.%s.ueber_5x" % t, m["ueber_5x"],
                                                                    betrag(m["ueber_5x"]), "counted", m["n"], fen)),
            ], fenster_text(fen)))
        n_rows = len([1 for _ in csv.DictReader(io.StringIO(csv_text))])
        teile.append(tabelle("m3", "M3 Reorgs", [
            ("Reorgs", wert_html("M3.reorgs", w["M3"]["reorgs"], betrag(w["M3"]["reorgs"]), "counted", n_rows, f_alle)),
            ("Maximum depth in blocks", wert_html("M3.max_tiefe", w["M3"]["max_tiefe"], betrag(w["M3"]["max_tiefe"]),
                                                  "counted", n_rows, f_alle)),
        ], fenster_text(f_alle)))
        teile.append(tabelle("m4", "M4 Chain split", [
            ("Heights with competing tips", wert_html("M4.hoehen", w["M4"]["hoehen"], betrag(w["M4"]["hoehen"]),
                                                      "counted", n_rows, f_alle)),
            ("Most tips at one height", wert_html("M4.max_tips", w["M4"]["max_tips"], betrag(w["M4"]["max_tips"]),
                                                  "counted", n_rows, f_alle)),
            ("Longest time with competing tips", wert_html("M4.laengste_s", w["M4"]["laengste_s"],
                                                           "%s s" % betrag(w["M4"]["laengste_s"]),
                                                           "counted", n_rows, f_alle)),
        ], fenster_text(f_alle)))
        zeilen5, fenster5 = [], []
        for name, ab in PROBEN:
            v = w["M5"][name]
            pv, pb = f["proben"][name]
            fen = fenster(pv, pb) if pv is not None else fenster(f["ta"] + ab, f["ta"] + ab)
            wort = {"activation": "At activation", "plus_24h": "Activation plus 24 h",
                    "plus_72h": "Activation plus 72 h"}[name]
            zeilen5.append(("%s, pre-upgrade share" % wort,
                            wert_html("M5.%s.alt" % name, v["alt"], prozent(v["alt"], v["n"]), "counted", v["n"], fen)))
            fenster5.append("sample %s %s" % ({"activation": "at activation", "plus_24h": "after 24 h",
                                                "plus_72h": "after 72 h"}[name], fenster_text(fen)))
        teile.append(
            '<section id="m5"><h2>M5 Peers on pre-upgrade software</h2><div class="tablewrap"><table class="nums">'
            '<thead><tr><th scope="col">Value</th><th scope="col">Result</th></tr></thead><tbody>%s</tbody></table></div>'
            '<p class="src">Share of the peers in our own sample, software version only, no addresses kept. '
            'Windows %s.</p></section>'
            % ("".join('<tr><td class="c">%s</td><td>%s</td></tr>' % z for z in zeilen5), ", ".join(fenster5)))
        m6 = w["M6"]
        teile.append(tabelle("m6", "M6 Time to stable", [
            ("Time to stable", wert_html("M6.sekunden", m6["sekunden"], dauer_text(m6["sekunden"]),
                                         "counted", m6["fenster"], f_nach)),
            ("Lower edge of the band, 20 %% below %d s" % t_nach,
             wert_html("M6.band_von_s", m6["band_von_s"], "%s s" % m6["band_von_s"], "computed", m6["fenster"], f_nach)),
            ("Upper edge of the band, 20 %% above %d s" % t_nach,
             wert_html("M6.band_bis_s", m6["band_bis_s"], "%s s" % m6["band_bis_s"], "computed", m6["fenster"], f_nach)),
        ], fenster_text(f_nach)))
        s = kopf["schaetzung"]
        teile.append(tabelle("m7", "M7 First block at the activation height", [
            ("Time of block %s" % betrag(H), wert_html("M7.zeit_utc", w["M7"]["zeit_utc"],
                                                       lang(ts(w["M7"]["zeit_utc"])), "counted", 1, f_alle)),
            ("Gap to our estimate", wert_html("M7.abstand_s", w["M7"]["abstand_s"], "%+d s" % w["M7"]["abstand_s"],
                                              "computed", 1, f_alle)),
        ], fenster_text(f_alle), "<p>Our estimate was %s.</p>" % schaetz_text(s)))
        sha = hashlib.sha256(csv_text.encode("utf-8")).hexdigest()
        teile.append(
            '<section id="data"><h2>Data</h2><p>%s, method v%s, %s rows.</p>'
            '<p class="src sha">sha256 <code>%s</code></p></section>'
            % ('<a href="/%s" download>Download the CSV</a>' % E(kopf["csv"], quote=True),
               E(kopf["methode"]), betrag(n_rows), sha))
    teile.append(zitier_html(kopf))
    teile.append('<p>Corrections to this report are dated and listed on %s.</p>'
                 % '<a href="/independence#corrections">our independence page</a>')
    return "\n".join(teile)


def schaetz_text(s):
    """unsere schaetzung fuer den aktivierungsblock, mit band und datum."""
    t = "%s, computed from our count of the block pace" % lang(ts(s["zeit_utc"]))
    if s.get("band_von_utc") and s.get("band_bis_utc"):
        t += ", with 9 in 10 of our draws between %s and %s" % (lang(ts(s["band_von_utc"])),
                                                                 lang(ts(s["band_bis_utc"])))
    return t + ", as of %s" % datum_lang(s["datum"])


def titel(kopf):
    return "%s %s upgrade report" % (kopf["chain"], kopf["upgrade"])


def seite(kopf, w, csv_text):
    """das seiten-dict fuer b2b_pages, ohne css (das setzt der waechter)."""
    titel = kopf["titel"]
    url = SITE + "/reports/" + kopf["slug"]
    ds = {"@type": "Dataset", "name": "%s, %s" % (titel, kopf["id"]), "identifier": kopf["id"],
          "description": ("PulseHawk Upgrade Report %s for %s %s on %s, method v%s. Measured values M1 to M7, "
                          "from 24 hours before to 72 hours after activation height %s."
                          % (kopf["id"], kopf["chain"], kopf["upgrade"], kopf["netz"], kopf["methode"],
                             betrag(kopf["aktivierungshoehe"]["wert"]))),
          "url": url, "creator": {"@id": SITE + "/#org"}, "isAccessibleForFree": True,
          "license": "https://creativecommons.org/licenses/by/4.0/",
          "version": kopf["methode"],
          "datePublished": kopf["veroeffentlicht"] + "T06:00:00+00:00",
          "dateModified": kopf["geaendert"] + "T06:00:00+00:00",
          "measurementTechnique": "PulseHawk Upgrade Report, specification v%s, %s%s"
                                  % (kopf["methode"], SITE, METHODE_PFAD),
          "variableMeasured": ["%s %s" % (m, n) for m, n, _ in METRIKEN]}
    if w:
        f = w["_fenster"]
        ds["temporalCoverage"] = fenster(f["von"], f["bis"])
        ds["distribution"] = {"@type": "DataDownload", "encodingFormat": "text/csv",
                              "contentUrl": SITE + "/" + kopf["csv"]}
    return dict(
        datei="reports/%s.html" % kopf["slug"], pfad="/reports/" + kopf["slug"],
        og=kopf.get("og", "report-" + kopf["slug"]), lastmod=kopf["geaendert"],
        title="%s | PulseHawk" % titel,
        desc=kopf["beschreibung"],
        h1=titel,
        lead=("PulseHawk Upgrade Report %s, method v%s. We measure %s %s on %s from 24 hours before "
              "to 72 hours after block %s, with seven fixed values and no grades."
              % (kopf["id"], kopf["methode"], kopf["chain"], kopf["upgrade"], kopf["netz"],
                 betrag(kopf["aktivierungshoehe"]["wert"]))),
        body=body(kopf, w, csv_text),
        faqs=[], schema=["ARTICLE:%s:%s" % (kopf["veroeffentlicht"], kopf["geaendert"]), ds],
        crumbs=[("Measurement Framework", "/standard/"), (titel, "/reports/" + kopf["slug"])],
        report=kopf["id"],
    )


def testkopf():
    q = lambda art, n, w: {"art": art, "name": n, "url": "https://github.com/test/%s" % n.replace(" ", "-"),
                           "wert": w, "geprueft": "2026-11-02"}
    return {
        "id": "PH-UR-2026-999", "typ": "upgrade-report", "slug": "test-chain-up1", "chain": "Testchain", "upgrade": "UP1",
        "netz": "mainnet", "methode": METHODE, "veroeffentlicht": "2026-11-02", "geaendert": "2026-11-02",
        "beschreibung": ("Upgrade report for the test chain, measured from 24 hours before to 72 hours "
                         "after activation, seven fixed values, each dated, with raw data."),
        "aktivierungshoehe": {"wert": 100000, "quellen": [q("protocol constant", "spec A", 100000),
                                                        q("release", "release B", 100000)]},
        "ziel_vorher": {"wert": 75, "quellen": [q("protocol constant", "spec C", 75), q("release", "release D", 75)]},
        "ziel_nachher": {"wert": 25, "quellen": [q("protocol constant", "spec E", 25), q("release", "release F", 25)]},
        "schaetzung": {"zeit_utc": "2026-11-06T02:30:00Z", "datum": "2026-11-04"},
        "csv": "reports/test-chain-up1.csv", "werte": None, "og": "zcash-nu7",
    }


def test_csv(kopf, ta=None):
    """ein sauberer datensatz, mit festem zufall: 24 h vor 75 s, 72 h nach 25 s."""
    import random
    zufall = random.Random(2026)
    ta = ta or ts("2026-11-06T02:40:00Z")
    H = kopf["aktivierungshoehe"]["wert"]
    rid, mv = kopf["id"], kopf["methode"]
    t, h, vor = ta, H, []
    while True:
        t -= max(1, int(zufall.expovariate(1 / 75)))
        h -= 1
        if t < ta - VOR_S + 10:
            break
        vor.append((h, t))
    bloecke = sorted(vor) + [(H, ta)]
    t, h = ta, H
    while True:
        t += max(1, int(zufall.expovariate(1 / 25)))
        h += 1
        if t > ta + NACH_S - 10:
            break
        bloecke.append((h, t))
    out = io.StringIO()
    wr = csv.writer(out, lineterminator="\n")
    wr.writerow(CSV_SPALTEN)
    vorige = None
    for h, t in bloecke:
        wr.writerow([rid, mv, "block", "", h, iso(t), "" if vorige is None else t - vorige])
        vorige = t
    wr.writerow([rid, mv, "reorg", "", H + 40, iso(ta + 1000), 1])
    wr.writerow([rid, mv, "tip", "", H + 40, iso(ta + 990), 12])
    wr.writerow([rid, mv, "tip", "", H + 40, iso(ta + 990), 9])
    alt = {"activation": 14, "plus_6h": 9, "plus_24h": 5, "plus_72h": 1}
    for name, ab in PROBEN_ROH:
        for i in range(40):
            wr.writerow([rid, mv, "peer", name, "", iso(ta + ab - i), 1 if i < alt[name] else 0])
    return out.getvalue()




# --- spezifikation --------------------------------------------------------
# Jede Aenderung der Rechenvorschrift erhoeht die Version (Ben, 2.11.2026).
# Eine alte Version bleibt unter /standard/upgrade-report/v<x>-<y> abrufbar.
# Wer eine neue Version anlegt, kopiert den Text der alten in einen eigenen
# Zweig von spezifikation_html und aendert nur den neuen.
VERSIONEN = [
    ("1.0", "2026-11-03", "First version, with the values M1 to M7."),
]


def versionspfad(v):
    return "/standard/upgrade-report/v" + v.replace(".", "-")


def spezifikation_html(version):
    """der text der spezifikation in genau dieser version."""
    if version != "1.0":
        raise ValueError("keine spezifikation v%s" % version)
    m = "".join("<li><b>%s %s.</b> %s</li>" % (k, n, d) for k, n, d in METRIKEN)
    log = "".join("<li><b>Version %s, %s.</b> %s</li>" % (v, datum_lang(d), t) for v, d, t in VERSIONEN)
    return """
<section id="scope"><h2>What does an Upgrade Report measure?</h2>
<p>An Upgrade Report covers one network upgrade on one PoW or DAG chain. Its window runs from 24 hours before to 72 hours after the first block at the activation height. All times are in UTC. Block times are the timestamps in the block headers that our own listener or header client receives.</p>
<p>The target interval and the activation height each come from two independent sources, a protocol constant and a release. If the two differ, no report is built.</p>
</section>
<section id="values"><h2>Which values does every Upgrade Report carry?</h2>
<ul class="list">%s</ul>
</section>
<section id="rules"><h2>How are the values computed?</h2>
<ul class="list">
<li><b>Two sets of intervals.</b> The interval of a block is its time minus the time of the block before it. Blocks below the activation height form the set before activation, blocks above it the set after. The interval that ends at the activation block belongs to neither set.</li>
<li><b>Percentiles.</b> A percentile is the value at rank ceil(q × n) of the sorted intervals, without interpolation.</li>
<li><b>Ideal chain.</b> For a chain with exponential intervals at target T, p50 is T × ln 2, p90 is T × ln 10 and p99 is T × ln 100, rounded to 0.1 s. These values are computed.</li>
<li><b>Gaps.</b> M2 counts intervals strictly above five times the target.</li>
<li><b>Reorgs and tips.</b> A reorg is a switch of our listener to a competing branch, its depth the number of blocks replaced. A tip competes when another block at the same height reaches our listener, and lasts until one of them is abandoned.</li>
</ul>
</section>
<section id="peers-stable"><h2>How are peers and time to stable counted?</h2>
<ul class="list">
<li><b>Peer samples.</b> Our listener asks the peers it connects to for their software version. A peer counts as pre-upgrade when its version cannot follow the upgrade. The report shows three samples, at activation, after 24 hours and after 72 hours, each within one hour of its time. Further samples, such as one after 6 hours, stay in the raw data. Only the version is kept, no address.</li>
<li><b>Time to stable.</b> For every block from one hour after activation on, we take the mean of the intervals in the hour before it. That mean is in the band when it lies within 20 %% of the new target T. Time to stable is the time from the activation block to the first block from which the mean stays in the band for 60 minutes without a break. If no block does within the window, the report says so.</li>
<li><b>Our estimate.</b> M7 compares the time of the activation block with our own estimate, published before activation with its date.</li>
</ul>
</section>
<section id="data"><h2>What does the data file contain?</h2>
<p>Each report publishes one CSV with the columns report_id, method_version, kind, label, height, time_utc and value. A row of kind block holds a height, its header time and the interval to the block before. Rows of kind reorg hold the depth, rows of kind tip the duration in seconds, and rows of kind peer the sample label and 1 for pre-upgrade software or 0 for upgraded software.</p>
<p>The page shows the sha256 of the CSV. Every value on the page is computed again from that file before the page is built.</p>
</section>
<section id="changelog"><h2>Changelog</h2>
<ul class="list">%s</ul>
</section>""" % (m, log)
