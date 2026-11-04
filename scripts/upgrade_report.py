#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""upgrade_report.py, Report-Typ "Upgrade Report" (PH-UR) im PulseHawk Measurement
Framework, Spezifikation v1.0 (Ben, 2.11. und 3.11.2026).

Rechnet M1 bis M7 aus reports/<slug>.csv und baut den Seiteninhalt. Der
gemeinsame Waechter (scripts/report_waechter.py) prueft vorher und nachher
alles, was fuer jeden Typ gilt, und baut die Seite nur, wenn alles gruen ist.

Die Rechnung folgt scripts/wache/report_v1.py in kaspa-pulse, Stand main nach
#245 (Ben, 3.11.2026): Perzentile mit linearer Interpolation auf 0.1 s, die
Mengen bei M1 und M2, die Fenstergrenze ueber die Hoehe, M3 getrennt vor und
nach als Verteilung nach Tiefe mit Kopfzahl ab Tiefe 2, M4 als Episoden des
Signals kettenspaltung, M5 als Anteil in Prozent beim Handschlag. Einzige
Abweichung bis zum Auftrag an die Zcash-Sitzung: M6 verlangt, dass die 60 min
ganz in den Daten liegen, und rechnet in ganzen Sekunden. Beide Staende
sollen bis 8.11.2026 gleich rechnen.

Die messende Sitzung liefert ihre Messwert-CSV; scripts/report_import.py macht
daraus "werte" in data/reports/<slug>.json und die Roh-CSV im PH-Format.
Der Waechter rechnet alles aus der Roh-CSV nach und vergleicht Wert und n
jeder Kennzahl exakt, als Text, so wie csv.writer sie schreibt.
"""

import bisect
import csv
import datetime
import hashlib
import io
import math
import re

from report_waechter import (SITE, E, betrag, lang, datum_lang, fenster, fenster_text,
                             wert_html, zitier_html, verfahren_html, reproduzieren_html, lies_reproduzieren)
import unsicherheit

# die pruefverfahren je messwert, beschrieben auf /method (Ben, 4.11.2026)
VERFAHREN_JE_M = {"M1": ["PH-M-001"], "M2": ["PH-M-001"], "M3": ["PH-M-002"], "M4": ["PH-M-002"],
                  "M5": ["PH-M-003"], "M6": ["PH-M-001"], "M7": ["PH-M-001", "PH-M-006"]}
# die zeile "measurement uncertainty" je messwert, solange es keine zahlen gibt
UNSICHER = {
    "M1": "a 95 % interval for each percentile from the rank statistics, computed, plus the 1 s resolution of "
          "header times, which miners set.",
    "M2": "the longest gap is a single counted value with no sampling interval. Header times resolve to 1 s and "
          "are set by miners.",
    "M3": "a count with no sampling interval. It depends on our listener staying connected, and any gap in "
          "coverage is named in the report.",
    "M4": "a duration from the arrival times at our listener, which resolve to 1 s. It depends on the listener "
          "staying connected.",
    "M5": "a 95 % Wilson interval for each share, computed from n.",
    "M6": "header times resolve to 1 s and the band edges are computed exactly. The first block that stays in "
          "the band can move by one block when header times run backwards.",
    "M7": "the header time is set by the miner and resolves to 1 s. Our estimate carries its own 90 % band.",
}

# die quellenfelder, die der waechter unter d) prueft
QUELLEN_FELDER = (("aktivierungshoehe", "aktivierungshoehe"), ("ziel_vorher", "zielabstand vorher"),
                  ("ziel_nachher", "zielabstand nachher"))

METHODE = "1.0"                     # aktuelle version der rechenvorschrift
METHODE_PFAD = "/standard/upgrade-report/v1-0"   # jede version bleibt unter ihrem pfad abrufbar
VOR_H, NACH_H = 24, 72              # fenster um die kopfzeit des aktivierungsblocks
LUECKE_FAKTOR = 5                   # M2, abstaende ueber 5 x ziel
KOPF_TIEFE = 2                      # M3, kopfzahl ab dieser tiefe
STABIL_FENSTER_S = 3600             # M6, gleitendes fenster 1 h
STABIL_HALTEN_S = 3600              # M6, 60 min ohne unterbrechung im band
STABIL_TOLERANZ = 0.20              # M6, innerhalb 20 % des ziels
# die proben der wache in stunden nach der aktivierung; der report zeigt 0,
# 24 und 72 h, die probe nach 6 h bleibt in den rohdaten (Ben, 3.11.2026)
PROBEN_H = (0, 6, 24, 72)
PROBEN_REPORT_H = (0, 24, 72)
PROBE_LABEL = {0: "activation", 6: "plus_6h", 24: "plus_24h", 72: "plus_72h"}
SPLIT_STUFEN = ("alarm", "entwarnung")
CSV_SPALTEN = ["report_id", "method_version", "kind", "label", "height", "time_utc", "value"]
TEILE = (("vor", "before"), ("nach", "after"))

METRIKEN = [
    ("M1", "Block intervals",
     "p50, p90 and p99 of the block intervals, before and after the activation height, "
     "each against the value computed for an ideal chain at the target interval."),
    ("M2", "Longest gap",
     "The longest block interval and the number of intervals above five times the target, "
     "before and after the activation height."),
    ("M3", "Reorgs",
     "Every switch of our listener's tip to another branch, before and after activation, as a "
     "distribution by depth, with the number of switches of depth 2 or more as the headline."),
    ("M4", "Chain split",
     "Episodes of the chain split signal before and after activation, their total duration and "
     "the longest one."),
    ("M5", "Peers on pre-upgrade software",
     "The share of peers below the minimum protocol version of the upgrade, at the handshake with "
     "our listener, at activation, 24 hours later and 72 hours later, with n."),
    ("M6", "Time to stable",
     "The time from the activation block until the mean of the block intervals over the last hour "
     "lies within 20 % of the new target and stays there for 60 minutes without a break."),
    ("M7", "First block at the activation height",
     "Its header time and the gap to our own estimate published before activation."),
]


def kennzahlen():
    """die kennzahlen, die der report zeigt und der waechter vergleicht, in
    den namen der messwert-csv von report_v1.py."""
    k = []
    for teil, _ in TEILE:
        for nm in ("p50", "p90", "p99"):
            k += ["%s_%s" % (nm, teil), "%s_%s_modell" % (nm, teil)]
        k += ["laengste_luecke_" + teil, "luecken_ueber_5x_ziel_" + teil]
    for teil, _ in TEILE:
        k += ["reorgs_ab_tiefe_%d_%s" % (KOPF_TIEFE, teil), "reorgs_tiefe_1_" + teil,
              "reorgs_tiefe_2_" + teil, "reorgs_tiefe_3_plus_" + teil, "reorg_max_tiefe_" + teil,
              "kettenspaltung_dauer_" + teil, "kettenspaltung_laengste_" + teil]
    for h in PROBEN_REPORT_H:
        k.append(probe_kennzahl(h))
    k += ["zeit_bis_stabil", "erster_block_kopfzeit", "kopfzeit_minus_schaetzung"]
    return k


def probe_kennzahl(h):
    return "peers_unter_min_protokoll_" + ("aktivierung" if h == 0 else "aktivierung_plus_%dh" % h)


# --- wie report_v1.py ------------------------------------------------------

def quantil(s, q):
    s = sorted(s)
    if not s:
        return None
    pos = (len(s) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def r(x, n=1):
    return "" if x is None else round(x, n)


def ts(text):
    """wie wache_kern.ts: iso-zeit mit Z oder +00:00 in sekunden, als float."""
    return datetime.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def utc(t):
    """wie wache_kern.utc."""
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def iso(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def grenzen(kette, akt, t_akt):
    """vor: bloecke unter der aktivierungshoehe ab dem ersten mit kopfzeit ab
    t_akt - 24 h; nach: ab der aktivierungshoehe bis vor den ersten block mit
    kopfzeit ab t_akt + 72 h. Abgegrenzt ueber die hoehe."""
    hoehen = sorted(kette)
    vor = [h for h in hoehen if h < akt]
    a = next((i for i, h in enumerate(vor) if kette[h] >= t_akt - VOR_H * 3600), None)
    vor = vor[a:] if a is not None else []
    nach = [h for h in hoehen if h >= akt]
    e = next((i for i, h in enumerate(nach) if kette[h] >= t_akt + NACH_H * 3600), None)
    nach = nach[:e] if e is not None else nach
    return vor, nach


def abstaende(kette, hoehen):
    return [(h, kette[h] - kette[h - 1]) for h in hoehen if h - 1 in kette]


# --- csv lesen -------------------------------------------------------------

RE_ZEIT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def zeilen(text):
    """roh-csv streng lesen. jede spalte hat ihr format, sonst ValueError."""
    r_ = csv.DictReader(io.StringIO(text))
    if r_.fieldnames != CSV_SPALTEN:
        raise ValueError("csv-spalten %r, erwartet %r" % (r_.fieldnames, CSV_SPALTEN))
    aus = []
    labels = set(PROBE_LABEL.values())
    for i, z in enumerate(r_, 2):
        art, lab, hoehe, wert = z["kind"], z["label"], z["height"], z["value"]
        if not RE_ZEIT.fullmatch(z["time_utc"]):
            raise ValueError("zeile %d, time_utc nicht JJJJ-MM-TTThh:mm:ssZ" % i)
        if hoehe and not re.fullmatch(r"\d+", hoehe):
            raise ValueError("zeile %d, height keine ganze zahl" % i)
        if wert and not re.fullmatch(r"-?\d+", wert):
            raise ValueError("zeile %d, value keine ganze zahl" % i)
        ok = {"block": not lab and hoehe,
              "meta": lab == "log" and wert == "1",
              "reorg": not lab and wert and int(wert) >= 1,
              "split": lab in SPLIT_STUFEN,
              "peer": lab in labels and not hoehe and wert in ("0", "1")}
        if art not in ok:
            raise ValueError("zeile %d, kind %r unbekannt" % (i, art))
        if not ok[art]:
            raise ValueError("zeile %d, %s mit label %r, height %r, value %r passt nicht zum format"
                             % (i, art, lab, hoehe, wert))
        aus.append(dict(z, t=ts(z["time_utc"]), h=int(hoehe) if hoehe else None,
                        v=int(wert) if wert else None))
    return aus


# --- neu rechnen -----------------------------------------------------------

def rechnen(kopf, rows):
    """alle kennzahlen aus den zeilen der roh-csv, wie report_v1.py.
    Liefert {"kz": {kennzahl: {wert, n, von, bis, art}}, "_fenster": ...}."""
    akt = kopf["aktivierungshoehe"]["wert"]
    ziel_vor, ziel_nach = kopf["ziel_vorher"]["wert"], kopf["ziel_nachher"]["wert"]
    kette = {z["h"]: int(z["t"]) for z in rows if z["kind"] == "block"}
    if akt not in kette:
        raise ValueError("kein block auf der aktivierungshoehe %d in der csv" % akt)
    t_akt = kette[akt]
    vor, nach = grenzen(kette, akt, t_akt)
    kz = {}

    def setz(k, wert, n, von, bis, art="counted"):
        kz[k] = {"wert": wert, "n": n, "von": von, "bis": bis, "art": art}

    fenster_ = {}
    for teil, hoehen, ziel in (("vor", vor, ziel_vor), ("nach", nach, ziel_nach)):
        if not hoehen:
            continue
        ab = abstaende(kette, hoehen)
        w = [x for _, x in ab]
        von, bis = kette[hoehen[0]], kette[hoehen[-1]]
        fenster_[teil] = (von, bis, ab, ziel)
        n = len(w)
        for q, nm, faktor in ((0.5, "p50", math.log(2)), (0.9, "p90", math.log(10)), (0.99, "p99", math.log(100))):
            setz("%s_%s" % (nm, teil), r(quantil(w, q)), n, von, bis)
            setz("%s_%s_modell" % (nm, teil), r(faktor * ziel), "", von, bis, "computed")
        setz("laengste_luecke_" + teil, max(x for _, x in ab), n, von, bis)
        setz("luecken_ueber_5x_ziel_" + teil, sum(1 for x in w if x > LUECKE_FAKTOR * ziel), n, von, bis)

    # M3 und M4 aus dem log der wache, nach der ankunftszeit
    hat_log = any(z["kind"] == "meta" for z in rows)
    log = [z for z in rows if z["kind"] in ("reorg", "split")]
    for teil, (von, bis, ab, _) in fenster_.items():
        bis_log = bis + 1  # die letzte sekunde des fensters mitnehmen
        if not hat_log:
            setz("reorgs_%s" % teil, "fehlt", "", von, bis)
            setz("kettenspaltung_dauer_" + teil, "fehlt", "", von, bis)
            continue
        tiefen = [z["v"] for z in log if z["kind"] == "reorg" and von <= z["t"] < bis_log]
        setz("reorgs_ab_tiefe_%d_%s" % (KOPF_TIEFE, teil), sum(1 for x in tiefen if x >= KOPF_TIEFE),
             len(ab), von, bis)
        for name_t, pruef in (("1", lambda x: x == 1), ("2", lambda x: x == 2), ("3_plus", lambda x: x >= 3)):
            setz("reorgs_tiefe_%s_%s" % (name_t, teil), sum(1 for x in tiefen if pruef(x)), len(tiefen), von, bis)
        setz("reorg_max_tiefe_" + teil, max(tiefen) if tiefen else 0, len(tiefen), von, bis)
        eps, start = [], None
        for z in log:
            if z["kind"] != "split":
                continue
            if z["label"] == "alarm" and start is None:
                start = z["t"]
            elif z["label"] == "entwarnung" and start is not None:
                eps.append((start, z["t"]))
                start = None
        if start is not None:
            eps.append((start, bis))
        eps = [(max(a, von), min(b, bis)) for a, b in eps if b > von and a < bis]
        setz("kettenspaltung_dauer_" + teil, round(sum(b - a for a, b in eps)), len(eps), von, bis)
        setz("kettenspaltung_laengste_" + teil, round(max((b - a for a, b in eps), default=0)), len(eps), von, bis)

    # M5 proben beim handschlag
    proben = {}
    for h in PROBEN_H:
        p = [z for z in rows if z["kind"] == "peer" and z["label"] == PROBE_LABEL[h]]
        if not p:
            setz(probe_kennzahl(h), "fehlt", "", "", "")
            continue
        alt = sum(z["v"] for z in p)
        t_p = min(z["t"] for z in p)
        proben[h] = t_p
        setz(probe_kennzahl(h), round(100 * alt / len(p), 1), len(p), t_p, t_p)

    # M6 zeit bis stabil, nach den kopfzeiten
    if "nach" in fenster_:
        von, bis, ab, ziel = fenster_["nach"]
        punkte = sorted((kette[h], x) for h, x in ab)
        zeiten = [t for t, _ in punkte]
        verlauf = []
        for i, (t, _) in enumerate(punkte):
            if t < von + STABIL_FENSTER_S:
                continue
            a = bisect.bisect_right(zeiten, t - STABIL_FENSTER_S)
            w60 = [x for _, x in punkte[a:i + 1]]
            verlauf.append((t, sum(w60) / len(w60)))
        lo, hi = ziel * (1 - STABIL_TOLERANZ), ziel * (1 + STABIL_TOLERANZ)
        drin = [lo <= m <= hi for _, m in verlauf]
        stabil = None
        for i, (t, _) in enumerate(verlauf):
            if not drin[i]:
                continue
            j = i
            while j < len(verlauf) and verlauf[j][0] <= t + STABIL_HALTEN_S and drin[j]:
                j += 1
            # anders als report_v1.py nach #245: die 60 min muessen ganz in den
            # daten liegen (Ben, 3.11.2026), also ein zeitpunkt danach existieren
            if j < len(verlauf) and verlauf[j][0] > t + STABIL_HALTEN_S:
                stabil = t
                break
        setz("zeit_bis_stabil", int(stabil - von) if stabil is not None else "nie", len(verlauf), von, bis)

    # M7 erster block auf der aktivierungshoehe
    schaetzung = ts(kopf["schaetzung"]["zeit_utc"])
    setz("erster_block_kopfzeit", utc(t_akt), 1, t_akt, t_akt)
    setz("kopfzeit_minus_schaetzung", round(t_akt - schaetzung), 1, t_akt, t_akt, "computed")
    return {"kz": kz, "_fenster": {"t_akt": t_akt, "teile": {t: (f[0], f[1]) for t, f in fenster_.items()},
                                   "abstaende": {t: [a for _, a in f[2]] for t, f in fenster_.items()},
                                   "proben_zahl": {h: (sum(z["v"] for z in rows if z["kind"] == "peer"
                                                           and z["label"] == PROBE_LABEL[h]),
                                                       sum(1 for z in rows if z["kind"] == "peer"
                                                           and z["label"] == PROBE_LABEL[h])) for h in PROBEN_H},
                                   "proben": proben, "ziel": {"vor": ziel_vor, "nach": ziel_nach},
                                   "von": min(kette[h] for h in vor + nach) if vor or nach else t_akt,
                                   "bis": max(kette[h] for h in vor + nach) if vor or nach else t_akt}}


def kanon(x):
    """so, wie csv.writer den wert schreibt."""
    return "" if x is None else str(x)


def oeffentlich(w):
    """die werte, die die messende sitzung ebenso liefert: wert und n als text."""
    return {k: {"wert": kanon(w["kz"][k]["wert"]), "n": kanon(w["kz"][k]["n"])}
            for k in kennzahlen() if k in w["kz"]}


def zahl(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def pruefe_plausibel(werte, rows=None, kopf=None):
    """c) reihenfolge der perzentile, keine negativen zaehlungen, fenster und
    vollstaendigkeit der roh-csv. werte ist {kennzahl: {wert, n}} als text."""
    f = []
    for teil, _ in TEILE:
        p = [zahl((werte.get("%s_%s" % (nm, teil)) or {}).get("wert")) for nm in ("p50", "p90", "p99")]
        if None not in p and not p[0] <= p[1] <= p[2]:
            f.append(("c", "M1 %s, p50 %s, p90 %s, p99 %s nicht aufsteigend" % (teil, p[0], p[1], p[2])))
    for k, v in werte.items():
        for feld in ("wert", "n"):
            x = v.get(feld, "")
            if x in ("", "fehlt", "nie") or k == "erster_block_kopfzeit" and feld == "wert":
                continue
            if k == "kopfzeit_minus_schaetzung" and feld == "wert":
                if not re.fullmatch(r"-?\d+", x):
                    f.append(("c", "%s %s ist %r" % (k, feld, x)))
                continue
            z = zahl(x)
            if z is None or z < 0:
                f.append(("c", "zaehlung %s %s ist %r" % (k, feld, x)))
        if k.startswith("peers_unter") and zahl(v.get("wert")) is not None and zahl(v["wert"]) > 100:
            f.append(("c", "%s ueber 100 %%" % k))
    if rows is not None:
        akt = kopf["aktivierungshoehe"]["wert"]
        kette = {z["h"]: z["t"] for z in rows if z["kind"] == "block"}
        hoehen = sorted(kette)
        if akt not in kette:
            f.append(("c", "kein block auf der aktivierungshoehe %d" % akt))
            return f
        if hoehen != list(range(hoehen[0], hoehen[-1] + 1)):
            f.append(("c", "blockhoehen in der csv nicht lueckenlos"))
        t_akt = kette[akt]
        if kette[hoehen[0]] >= t_akt - VOR_H * 3600:
            f.append(("c", "csv beginnt erst am fenster, der block davor (kopfzeit vor %s) fehlt"
                      % utc(t_akt - VOR_H * 3600)))
        if not any(t >= t_akt + NACH_H * 3600 for h, t in kette.items() if h > akt):
            f.append(("c", "fenster unvollstaendig, kein block mit kopfzeit ab %s" % utc(t_akt + NACH_H * 3600)))
        for z in rows:
            if z["kind"] == "block" and z["v"] is not None and z["h"] - 1 in kette \
                    and z["v"] != kette[z["h"]] - kette[z["h"] - 1]:
                f.append(("c", "block %d, value %d passt nicht zu den zeiten" % (z["h"], z["v"])))
                break
        for z in rows:
            if z["report_id"] != kopf["id"] or z["method_version"] != kopf["methode"]:
                f.append(("c", "csv-zeile mit report_id %r oder method_version %r, erwartet %r und %r"
                          % (z["report_id"], z["method_version"], kopf["id"], kopf["methode"])))
                break
    return f


# --- seite -----------------------------------------------------------------

def seiten_werte(w):
    """kennzahl -> kanonischer wert, so steht er in data-v auf der seite."""
    return {k: kanon(w["kz"][k]["wert"]) for k in kennzahlen() if k in w["kz"]}


def schaetz_text(s):
    """unsere schaetzung fuer den aktivierungsblock, mit band und datum."""
    t = "%s, computed from our count of the block pace" % lang(ts(s["zeit_utc"]))
    if s.get("band_von_utc") and s.get("band_bis_utc"):
        t += ", with 9 in 10 of our draws between %s and %s" % (lang(ts(s["band_von_utc"])),
                                                                 lang(ts(s["band_bis_utc"])))
    return t + ", as of %s" % datum_lang(s["datum"])


def dauer_text(s):
    h, m = divmod(round(s / 60), 60)
    return ("%d h %d min" % (h, m)) if h else ("%d min" % m)


def anzeige(k, x):
    """der sichtbare text zu einem kanonischen wert."""
    if x in ("fehlt", ""):
        return "missing"
    if x == "nie":
        return "not within the window"
    if k.startswith("peers_unter"):
        return "%s %%" % x
    if k == "zeit_bis_stabil":
        return "%s s, %s" % (betrag(int(x)), dauer_text(int(x)))
    if k == "erster_block_kopfzeit":
        return lang(ts(x.replace(" ", "T") + "Z"))
    if k == "kopfzeit_minus_schaetzung":
        return "%+d s" % int(x)
    if k.startswith(("p50", "p90", "p99", "laengste_luecke", "kettenspaltung")):
        return "%s s" % (betrag(int(x)) if re.fullmatch(r"\d+", x) else x)
    return betrag(int(x)) if re.fullmatch(r"\d+", x) else x


def zelle(w, k, n_ersatz=1, fen=None):
    """ein wert mit kennung, n und fenster fuer die seite."""
    e = w["kz"][k]
    n = e["n"] if isinstance(e["n"], int) else n_ersatz
    if fen is None:
        fen = fenster(e["von"], e["bis"]) if e["von"] != "" else fenster(w["_fenster"]["t_akt"], w["_fenster"]["t_akt"])
    return wert_html(k, kanon(e["wert"]), anzeige(k, kanon(e["wert"])), e["art"], n, fen)


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
        ("Window", "24 h before to 72 h after", "the activation block, cut by height, in UTC"),
        ("Status", "measured" if w else "pending", "numbers from the CSV below" if w
         else "first numbers after block %s" % betrag(H)),
    ))
    teile = ['<section id="in-short" class="facts"><h2>The report in short</h2><dl>%s</dl></section>' % fakten]
    if kopf.get("hinweis"):
        teile.append("<p>%s</p>" % E(kopf["hinweis"]))
    s = kopf["schaetzung"]
    if not w:
        for mid, name, was in METRIKEN:
            # zu M7 gehoert unsere schaetzung, die vor der aktivierung feststeht
            extra = ("<p>Our estimate before activation is %s.</p>" % schaetz_text(s)
                     if mid == "M7" else "")
            teile.append('<section id="%s"><h2>%s %s</h2><p>%s</p>%s<p class="note">Not yet counted. '
                         'The numbers follow after block %s, from our own count.</p>%s'
                         '<p class="unc">Measurement uncertainty, %s</p></section>'
                         % (mid.lower(), mid, name, was, extra, betrag(H), verfahren_html(VERFAHREN_JE_M[mid]),
                            UNSICHER[mid]))
        teile.append('<section id="data"><h2>Data</h2><p>The CSV with every block, reorg, chain split '
                     'signal and peer sample follows with the first numbers, with its sha256 and the method '
                     'version.</p></section>')
    else:
        fw = w["_fenster"]
        teil_fen = {t: fenster(*fw["teile"][t]) for t in fw["teile"]}

        def tabelle(sid, h2, kopfzeile, zeilen_, fussnote, mid=None, unsicher=None):
            rows_ = "".join("<tr><td class=\"c\">%s</td>%s</tr>" % (z[0], "".join("<td>%s</td>" % c for c in z[1:]))
                            for z in zeilen_)
            th = "".join('<th scope="col">%s</th>' % x for x in kopfzeile)
            mid = mid or sid[:2].upper()
            return ('<section id="%s"><h2>%s</h2><div class="tablewrap"><table class="nums"><thead><tr>%s</tr>'
                    '</thead><tbody>%s</tbody></table></div><p class="src">%s</p>%s'
                    '<p class="unc">Measurement uncertainty, %s</p></section>'
                    % (sid, h2, th, rows_, fussnote, verfahren_html(VERFAHREN_JE_M[mid]),
                       unsicher or UNSICHER[mid]))

        def pi_text(teil):
            ab = fw["abstaende"].get(teil) or []
            teile_ = []
            for nm, q in (("p50", 0.5), ("p90", 0.9), ("p99", 0.99)):
                iv = unsicherheit.perzentil_intervall(ab, q)
                if iv:
                    teile_.append("%s %s to %s s" % (nm, betrag(iv[0]), betrag(iv[1])))
            return ("95 %% intervals from the rank statistics, computed, %s. Header times resolve to 1 s."
                    % ", ".join(teile_)) if teile_ else UNSICHER["M1"]

        def wilson_text():
            teile_ = []
            for h in PROBEN_REPORT_H:
                alt, n = fw["proben_zahl"].get(h, (0, 0))
                iv = unsicherheit.anteil_intervall(alt, n)
                if iv:
                    teile_.append("%s %.1f to %.1f %%" % ("at activation" if h == 0 else "after %d h" % h, iv[0], iv[1]))
            return ("95 %% Wilson intervals, computed, %s." % ", ".join(teile_)) if teile_ else UNSICHER["M5"]

        fen_satz = "Windows, before activation %s, after activation %s." % (
            fenster_text(teil_fen["vor"]) if "vor" in teil_fen else "none",
            fenster_text(teil_fen["nach"]) if "nach" in teil_fen else "none")
        hat = lambda k: k in w["kz"]
        for teil, wort in TEILE:
            if not hat("p50_" + teil):
                continue
            ziel = fw["ziel"][teil]
            n = w["kz"]["p50_" + teil]["n"]
            teile.append(tabelle(
                "m1-" + wort, "M1 Block intervals %s activation" % wort, ("Interval", "Counted", "Computed at %d s" % ziel),
                [(nm, zelle(w, "%s_%s" % (nm, teil)), zelle(w, "%s_%s_modell" % (nm, teil), n))
                 for nm in ("p50", "p90", "p99")],
                "Window %s. Header times, linear interpolation." % fenster_text(teil_fen[teil]),
                "M1", pi_text(teil)))
        teile.append(tabelle(
            "m2", "M2 Longest gap", ("Value", "Before activation", "After activation"),
            [("Longest interval",) + tuple(zelle(w, "laengste_luecke_" + t) if hat("laengste_luecke_" + t) else "none"
                                           for t, _ in TEILE),
             ("Intervals above five times the target",)
             + tuple(zelle(w, "luecken_ueber_5x_ziel_" + t) if hat("luecken_ueber_5x_ziel_" + t) else "none"
                     for t, _ in TEILE)],
            fen_satz + " Five times the target is %d s before and %d s after activation." % (5 * t_vor, 5 * t_nach)))
        m3 = [("Switches of depth %d or more" % KOPF_TIEFE, "reorgs_ab_tiefe_%d_" % KOPF_TIEFE),
              ("Switches of depth 1", "reorgs_tiefe_1_"), ("Switches of depth 2", "reorgs_tiefe_2_"),
              ("Switches of depth 3 or more", "reorgs_tiefe_3_plus_"), ("Maximum depth in blocks", "reorg_max_tiefe_")]
        teile.append(tabelle(
            "m3", "M3 Reorgs", ("Value", "Before activation", "After activation"),
            [(name,) + tuple(zelle(w, pre + t) if hat(pre + t) else "missing" for t, _ in TEILE) for name, pre in m3],
            fen_satz + " Arrival time at our listener."))
        sp = kopf.get("kettenspaltung") or {}
        teile.append(tabelle(
            "m4", "M4 Chain split", ("Value", "Before activation", "After activation"),
            [("Total duration of chain split episodes",)
             + tuple(zelle(w, "kettenspaltung_dauer_" + t) if hat("kettenspaltung_dauer_" + t) else "missing"
                     for t, _ in TEILE),
             ("Longest episode",)
             + tuple(zelle(w, "kettenspaltung_laengste_" + t) if hat("kettenspaltung_laengste_" + t) else "missing"
                     for t, _ in TEILE)],
            fen_satz + " An episode runs from the alarm to the all clear of the signal, two branches from the "
            "activation height, each seen by at least %s peers and both deeper than %s blocks. Arrival time at our "
            "listener." % (sp.get("min_peers", "the stated number of"), sp.get("min_tiefe", "the stated number of"))))
        m5 = []
        for h in PROBEN_REPORT_H:
            k = probe_kennzahl(h)
            wort = "At activation" if h == 0 else "Activation plus %d h" % h
            m5.append((wort, zelle(w, k), ("sampled %s" % lang(fw["proben"][h])) if h in fw["proben"] else "not sampled"))
        teile.append(tabelle(
            "m5", "M5 Peers on pre-upgrade software", ("Sample", "Share below the minimum protocol", "Time"), m5,
            "Share of the peers at the handshake with our listener, protocol version only, no addresses kept. "
            "The sample after 6 h stays in the raw data.", "M5", wilson_text()))
        teile.append(tabelle(
            "m6", "M6 Time to stable", ("Value", "Result"),
            [("Time from the activation block", zelle(w, "zeit_bis_stabil"))] if hat("zeit_bis_stabil") else [],
            "Window %s. Band %s s to %s s, 20 %% around the target of %d s, computed. Header times."
            % (fenster_text(teil_fen["nach"]) if "nach" in teil_fen else "none",
               r(t_nach * (1 - STABIL_TOLERANZ)), r(t_nach * (1 + STABIL_TOLERANZ)), t_nach)))
        teile.append(tabelle(
            "m7", "M7 First block at the activation height", ("Value", "Result"),
            [("Header time of block %s" % betrag(H), zelle(w, "erster_block_kopfzeit")),
             ("Gap to our estimate", zelle(w, "kopfzeit_minus_schaetzung"))],
            "Window %s. Our estimate was %s." % (fenster_text(fenster(fw["t_akt"], fw["t_akt"])), schaetz_text(s))))
        sha = hashlib.sha256(csv_text.encode("utf-8")).hexdigest()
        n_rows = len([1 for _ in csv.DictReader(io.StringIO(csv_text))])
        teile.append(
            '<section id="data"><h2>Data</h2><p>%s, method v%s, %s rows.</p>'
            '<p class="src sha">sha256 <code>%s</code></p></section>'
            % ('<a href="/%s" download>Download the CSV</a>' % E(kopf["csv"], quote=True),
               E(kopf["methode"]), betrag(n_rows), sha))
    teile.append(reproduzieren_html(lies_reproduzieren("reports/" + kopf["slug"])))
    teile.append(zitier_html(kopf))
    teile.append('<p>Corrections to this report are dated and listed on %s.</p>'
                 % '<a href="/corrections">our corrections page</a>')
    return "\n".join(teile)


def titel(kopf):
    return "%s %s upgrade report" % (kopf["chain"], kopf["upgrade"])


def seite(kopf, w, csv_text):
    """das seiten-dict fuer b2b_pages, ohne css (das setzt der waechter)."""
    titel_ = kopf["titel"]
    url = SITE + "/reports/" + kopf["slug"]
    ds = {"@type": "Dataset", "name": "%s, %s" % (titel_, kopf["id"]), "identifier": kopf["id"],
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
        fw = w["_fenster"]
        ds["temporalCoverage"] = "%s/%s" % (iso(fw["von"]), iso(fw["bis"]))
        ds["distribution"] = {"@type": "DataDownload", "encodingFormat": "text/csv",
                              "contentUrl": SITE + "/" + kopf["csv"]}
    return dict(
        datei="reports/%s.html" % kopf["slug"], pfad="/reports/" + kopf["slug"],
        og=kopf.get("og", "report-" + kopf["slug"]), lastmod=kopf["geaendert"],
        title="%s | PulseHawk" % titel_,
        desc=kopf["beschreibung"],
        h1=titel_,
        # die spezifikation steht im selben absatz wie das upgrade (Ben, 4.11.2026)
        lead=("PulseHawk Upgrade Report %s, method v%s. We measure %s %s (%s) on %s from 24 hours before "
              "to 72 hours after block %s, the activation height, with seven fixed values and no grades."
              % (kopf["id"], kopf["methode"], kopf["chain"], kopf["upgrade"],
                 next(q["name"] for q in kopf["aktivierungshoehe"]["quellen"] if q["art"] == "protocol constant"),
                 kopf["netz"], betrag(kopf["aktivierungshoehe"]["wert"]))),
        body=body(kopf, w, csv_text),
        faqs=[], schema=["ARTICLE:%s:%s" % (kopf["veroeffentlicht"], kopf["geaendert"]), ds],
        crumbs=[("Measurement Framework", "/standard/"), (titel_, "/reports/" + kopf["slug"])],
        report=kopf["id"],
    )


# --- testdaten -------------------------------------------------------------
# Ein szenario ist das gemeinsame modell der testdaten: daraus schreibt
# ph_csv() die roh-csv, und upgrade_report_probe.py dieselben daten im format
# der wache (koepfe, log, zustand), damit report_v1.py sie rechnen kann.

def testkopf():
    q = lambda art, n, w: {"art": art, "name": n, "url": "https://github.com/test/%s" % n.replace(" ", "-"),
                           "wert": w, "geprueft": "2026-11-03"}
    return {
        "id": "PH-UR-2026-999", "typ": "upgrade-report", "slug": "test-chain-up1", "chain": "Testchain",
        "upgrade": "UP1", "netz": "mainnet", "methode": METHODE, "veroeffentlicht": "2026-11-03",
        "geaendert": "2026-11-03",
        "beschreibung": ("Upgrade report for the test chain, measured from 24 hours before to 72 hours "
                         "after activation, seven fixed values, each dated, with raw data."),
        "aktivierungshoehe": {"wert": 100000, "quellen": [q("protocol constant", "spec A", 100000),
                                                        q("release", "release B", 100000)]},
        "ziel_vorher": {"wert": 75, "quellen": [q("protocol constant", "spec C", 75), q("release", "release D", 75)]},
        "ziel_nachher": {"wert": 25, "quellen": [q("protocol constant", "spec E", 25), q("release", "release F", 25)]},
        "schaetzung": {"zeit_utc": "2026-11-06T02:30:00Z", "datum": "2026-11-04",
                       "band_von_utc": "2026-11-06T00:20:00Z", "band_bis_utc": "2026-11-06T04:50:00Z"},
        "kettenspaltung": {"min_peers": 2, "min_tiefe": 2}, "min_protokoll": 170190,
        "csv": "reports/test-chain-up1.csv", "werte": None, "og": "zcash-nu7",
    }


def testszenario(kopf, saat=2026):
    """kette, log und proben mit festem zufall, wie sie die wache haette."""
    import random
    zufall = random.Random(saat)
    H = kopf["aktivierungshoehe"]["wert"]
    t_akt = int(ts("2026-11-06T02:40:00Z"))
    kette, t, h = {H: t_akt}, t_akt, H
    while t > t_akt - 27 * 3600:                         # etwas mehr als 24 h davor
        t -= max(1, int(zufall.expovariate(1 / 75)))
        h -= 1
        kette[h] = t
    t, h = t_akt, H
    while t < t_akt + 73 * 3600:                         # etwas mehr als 72 h danach
        # in der ersten stunde nach nu7 langsamer, die schwierigkeit pendelt sich ein
        mittel = 60 if t < t_akt + 1800 else 25
        t += max(1, int(zufall.expovariate(1 / mittel)))
        h += 1
        kette[h] = t
    # ein paar kopfzeiten, die rueckwaerts laufen, wie im echten netz
    for hh in (H - 300, H + 500, H + 4000):
        kette[hh] = kette[hh - 1] - 3
    log = []

    def eintrag(t_, hoehe, signal, wert, schwelle, stufe):
        log.append({"utc": utc(t_), "hoehe": hoehe, "signal": signal, "wert": wert,
                    "schwelle": schwelle, "stufe": stufe})
    for dt, tiefe in ((-20 * 3600, 1), (-5 * 3600, 2), (-3600, 1), (600, 1), (2000, 3), (9000, 1),
                      (40000, 2), (200000, 1)):
        eintrag(t_akt + dt, H + dt // 25, "reorg_gesehen", tiefe, 2, "info")
    eintrag(t_akt - 30 * 3600, H - 1400, "blockpause", 700, 600, "hinweis")
    for a, b in ((-26 * 3600, -23 * 3600), (300, 1500), (7200, 7300), (250000, None)):
        eintrag(t_akt + a, H, "kettenspaltung", 3, 2, "alarm")
        if b is not None:
            eintrag(t_akt + b, H, "kettenspaltung", 0, 2, "entwarnung")
    log.sort(key=lambda x: x["utc"])
    proben = {}
    for stunde, alt, n in ((0, 14, 40), (6, 9, 38), (24, 5, 41), (72, 1, 39)):
        versionen = {"170140": alt, "170190": n - alt}
        proben[str(stunde)] = {"utc": utc(t_akt + stunde * 3600 + 30), "peers": n, "vor_upgrade": alt,
                               "anteil_prozent": round(100 * alt / n, 1), "hoehe": None, "versionen": versionen}
    return {"kette": kette, "log": log, "proben": proben, "hat_log": True,
            "min_protokoll": kopf.get("min_protokoll", 170190)}


def ph_csv(szenario, kopf):
    """die roh-csv im PH-format aus einem szenario oder aus den daten der wache.
    Bloecke vom block vor dem fenster bis zum ersten block ab t_akt + 72 h."""
    kette, akt = szenario["kette"], kopf["aktivierungshoehe"]["wert"]
    t_akt = kette[akt]
    vor, nach = grenzen(kette, akt, t_akt)
    erste = (vor or nach)[0] - 1
    schnitt = next((h for h in sorted(kette) if h > akt and kette[h] >= t_akt + NACH_H * 3600), max(kette))
    rid, mv = kopf["id"], kopf["methode"]
    out = io.StringIO()
    wr = csv.writer(out, lineterminator="\n")
    wr.writerow(CSV_SPALTEN)
    for h in range(erste, schnitt + 1):
        wr.writerow([rid, mv, "block", "", h, iso(kette[h]), kette[h] - kette[h - 1] if h > erste else ""])
    if szenario.get("hat_log"):
        wr.writerow([rid, mv, "meta", "log", "", iso(t_akt), 1])
    for z in szenario["log"]:
        zeit = z["utc"].replace(" ", "T") + "Z"
        hoehe = z["hoehe"] if z["hoehe"] not in (None, "") else ""
        if z["signal"] == "reorg_gesehen":
            wr.writerow([rid, mv, "reorg", "", hoehe, zeit, int(float(z["wert"]))])
        elif z["signal"] == "kettenspaltung" and z["stufe"] in SPLIT_STUFEN:
            wr.writerow([rid, mv, "split", z["stufe"], hoehe, zeit, int(float(z["wert"])) if z["wert"] != "" else ""])
    for stunde in PROBEN_H:
        p = szenario["proben"].get(str(stunde))
        if not p:
            continue
        zeit = p["utc"].replace(" ", "T") + "Z"
        for version, anzahl in sorted(p["versionen"].items()):
            for _ in range(int(anzahl)):
                wr.writerow([rid, mv, "peer", PROBE_LABEL[stunde], "", zeit,
                             1 if int(version) < szenario["min_protokoll"] else 0])
    return out.getvalue()


def test_csv(kopf):
    return ph_csv(testszenario(kopf), kopf)


# --- spezifikation ---------------------------------------------------------
# Jede Aenderung der Rechenvorschrift erhoeht die Version (Ben, 2.11.2026).
# Eine alte Version bleibt unter /standard/upgrade-report/v<x>-<y> abrufbar.
# Wer eine neue Version anlegt, kopiert den Text der alten in einen eigenen
# Zweig von spezifikation_html und aendert nur den neuen. v1.0 ist noch nicht
# veroeffentlicht; die Fassung vom 3.11.2026 folgt report_v1.py (Ben).
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
<p>An Upgrade Report covers one network upgrade on one PoW or DAG chain, from 24 hours before to 72 hours after the activation block. All times are in UTC. The activation time is the header time of the block at the activation height.</p>
<p>The target interval and the activation height each come from two independent sources, a protocol constant and a release. If the two differ, no report is built.</p>
</section>
<section id="values"><h2>Which values does every Upgrade Report carry?</h2>
<ul class="list">%s</ul>
</section>
<section id="window"><h2>How is the window cut?</h2>
<ul class="list">
<li><b>By height.</b> Header times need not rise from block to block, so the window is cut by height. The set before activation starts at the first block below the activation height whose header time is at least 24 hours before the activation time. The set after activation starts at the activation block and ends before the first block whose header time is at least 72 hours after it.</li>
<li><b>Intervals.</b> The interval of a block is its header time minus the header time of the block before it. Every block of a set counts, so the first interval of a set reaches back to the block just before it, and the interval of the activation block belongs to the set after activation.</li>
<li><b>Time basis.</b> M1, M2 and M6 use header times. M3 and M4 use the arrival time at our listener. M3 and M4 count from the first header time of a set to the last one, including that last second.</li>
</ul>
</section>
<section id="rules"><h2>How are the values computed?</h2>
<ul class="list">
<li><b>Percentiles.</b> Linear interpolation between the two nearest ranks of the sorted intervals, at position (n minus 1) × q, rounded to 0.1 s.</li>
<li><b>Ideal chain.</b> For a chain with exponential intervals at target T, p50 is T × ln 2, p90 is T × ln 10 and p99 is T × ln 100, rounded to 0.1 s. These values are computed.</li>
<li><b>Gaps.</b> M2 counts intervals strictly above five times the target of the set.</li>
<li><b>Reorgs.</b> Every switch of our listener's tip to another branch counts, with its depth in blocks. M3 gives the number of switches of depth 2 or more, the distribution by depth 1, 2 and 3 or more, and the maximum depth.</li>
<li><b>Chain split.</b> The chain split signal raises an alarm when two branches from the activation height are each seen by at least a stated number of peers and both are deeper than a stated number of blocks. An episode runs from the alarm to the all clear, cut to the set. M4 gives the total duration and the longest episode in seconds.</li>
</ul>
</section>
<section id="peers-stable"><h2>How are peers and time to stable counted?</h2>
<ul class="list">
<li><b>Peer samples.</b> Our listener reads the protocol version that each peer it connects to sends in the handshake. A peer counts as pre-upgrade when its version is below the minimum protocol version of the upgrade. The share is given in %% of n, rounded to 0.1. The report shows the samples at activation, after 24 hours and after 72 hours. Further samples, such as one after 6 hours, stay in the raw data. Only the version is kept, no address.</li>
<li><b>Time to stable.</b> For every block of the set after activation whose header time is at least one hour after the activation time, we take the mean of the intervals of the blocks in the hour up to it. That mean is in the band when it lies within 20 %% of the new target T. Time to stable is the time in whole seconds from the activation block to the first block from which the mean stays in the band for 60 minutes without a break, with the data covering those 60 minutes. If no block does within the window, the report says so.</li>
<li><b>Our estimate.</b> M7 gives the header time of the activation block and its gap to our own estimate in whole seconds, published before activation with its date.</li>
</ul>
</section>
<section id="data"><h2>What does the data file contain?</h2>
<p>Each report publishes one CSV with the columns report_id, method_version, kind, label, height, time_utc and value. Rows of kind block run from the block before the window to the first block after it, each with its header time and interval. Rows of kind reorg hold the depth, rows of kind split the alarm or all clear of the chain split signal, rows of kind peer the sample and 1 for a peer below the minimum protocol or 0 above it, and one row of kind meta says that the listener log is complete.</p>
<p>The page shows the sha256 of the CSV. Every value on the page is computed again from that file before the page is built.</p>
</section>
<section id="changelog"><h2>Changelog</h2>
<ul class="list">%s</ul>
</section>""" % (m, log)
