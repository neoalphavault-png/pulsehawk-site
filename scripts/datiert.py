#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datiert.py, die datierte Schicht von pulsehawk.io (Ben, 11.11.2026).

Leitregel: Die Seite ist entweder zeitlos oder automatisch aktuell. Eine Zahl
steht nur dann auf der Startseite, wenn sie aus einer Datei kommt, die eine
Veroeffentlichung sowieso aendert:

  data/reports.json        die Reports, der neueste ist der Aufmacher-Beleg
  data/measurements.json   die Messungen mit Wert, Fenster und Datum
  data/track-record.json   die gewerteten Prognosen und ihr interval score

Der Bau bricht ab, statt zu warnen, bei echten Fehlern:
  - einem Wert fehlt label, Fenster oder Veroeffentlichungsdatum,
  - die sha256 eines Reports passt nicht zu seiner CSV.

Ist der neueste Report aelter als FRISCH_TAGE Tage, baut die Startseite die
zeitlose Fassung (Ben, 11.11.2026, Teil 2): "Latest report" ohne Kopfzahl,
Messkacheln mit Werten aelter als die Grenze entfallen zugunsten eines Links
auf /reports/. Ein Bau fuer eine Korrektur scheitert daran nicht.

Die taegliche Pruefung (Workflow datiert-pruefung.yml) liest nur und meldet
nach #ops-log: gelb ab GELB_TAGE mit den Resttagen, rot ab FRISCH_TAGE.

    python3 scripts/datiert.py                      pruefen, wie der bau
    python3 scripts/datiert.py --pruefen [--melden] [--probe]
    python3 scripts/datiert.py --selbsttest
"""

import datetime
import hashlib
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# die schwellen stehen hier allein, damit sie sich aendern lassen (Ben, 11.11.2026)
FRISCH_TAGE = 21     # danach baut die startseite die zeitlose fassung, die pruefung meldet rot
GELB_TAGE = 14       # ab hier meldet die taegliche pruefung gelb mit den resttagen

REPORTS = "data/reports.json"
MESSUNGEN = "data/measurements.json"
TRACK = "data/track-record.json"
LABELS = {"counted", "computed", "source"}
MONATE = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
E = html.escape


class Abbruch(SystemExit):
    """der bau bricht ab, mit klarer meldung und exit-code 1."""

    def __init__(self, funde):
        self.funde = funde
        super().__init__("datierte schicht, bau abgebrochen\n  " + "\n  ".join(funde))


def heute():
    """das datum des baus in utc. PH_HEUTE=JJJJ-MM-TT setzt es fuer proben und
    selbsttests, etwa um die zeitlose fassung zu zeigen; im normalen bau leer."""
    if os.environ.get("PH_HEUTE"):
        return iso_datum(os.environ["PH_HEUTE"])
    return datetime.datetime.now(datetime.timezone.utc).date()


def iso_datum(s):
    return datetime.date.fromisoformat(str(s))


def zeit(s):
    return datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def lang(d):
    d = iso_datum(d) if not isinstance(d, datetime.date) else d
    return "%d %s %d" % (d.day, MONATE[d.month - 1], d.year)


def fenster_text(f):
    """'15 October 2026, 12:56 UTC to 11 November 2026, 09:58 UTC'; ein fenster
    aus ganzen tagen (from_date, to_date) ohne uhrzeit."""
    if f.get("from_date"):
        a, b = iso_datum(f["from_date"]), iso_datum(f["to_date"])
        return "%s to %s" % (lang(a), lang(b))
    a, b = zeit(f["from_utc"]), zeit(f["to_utc"])
    return "%s, %s UTC to %s, %s UTC" % (lang(a.date()), a.strftime("%H:%M"), lang(b.date()), b.strftime("%H:%M"))


def dauer_text(s):
    s = int(round(s))
    h, rest = divmod(s, 3600)
    m, sek = divmod(rest, 60)
    return " ".join((["%d h" % h] if h else []) + (["%d min" % m] if h or m else []) + ["%d s" % sek])


def lade(pfad, repo=REPO):
    with open(os.path.join(repo, pfad), encoding="utf-8") as fh:
        return json.load(fh)


# --- pruefen -------------------------------------------------------------

def pruefe_reports(reps, tag, repo=REPO):
    f = []
    if not reps:
        return ["data/reports.json hat keinen report"]
    for r in reps:
        rid = r.get("id", "?")
        for k in ("id", "network", "title", "window", "published", "method_version", "path", "csv", "csv_sha256"):
            if not r.get(k):
                f.append("%s ohne %s" % (rid, k))
        try:
            iso_datum(r.get("published"))
        except (TypeError, ValueError):
            f.append("%s ohne gueltiges veroeffentlichungsdatum" % rid)
            continue
        w = r.get("window") or {}
        try:
            if zeit(w["from_utc"]) >= zeit(w["to_utc"]):
                f.append("%s fenster leer" % rid)
        except (KeyError, TypeError, ValueError):
            f.append("%s ohne fenster from_utc und to_utc" % rid)
        csv = os.path.join(repo, str(r.get("csv", "")).lstrip("/"))
        if not os.path.isfile(csv):
            f.append("%s csv fehlt %s" % (rid, r.get("csv")))
        elif hashlib.sha256(open(csv, "rb").read()).hexdigest() != r.get("csv_sha256"):
            f.append("%s sha256 passt nicht zu %s" % (rid, r.get("csv")))
    # das alter ist kein fehler mehr, es schaltet auf die zeitlose fassung (Ben, 11.11.2026)
    return f


def alter_tage(tag=None, repo=REPO):
    """alter des neuesten reports in tagen."""
    return ((tag or heute()) - iso_datum(neuester_report(repo)["published"])).days


def zeitlos(tag=None, repo=REPO):
    """True, wenn die startseite die zeitlose fassung baut."""
    return alter_tage(tag, repo) > FRISCH_TAGE


def frisch(datum, tag=None):
    """ein wert gilt als frisch, solange er nicht aelter als die grenze ist."""
    return ((tag or heute()) - iso_datum(datum)).days <= FRISCH_TAGE


def stufe(tag=None, repo=REPO):
    """gruen, gelb oder rot fuer die taegliche pruefung, mit alter und resttagen."""
    alter = alter_tage(tag, repo)
    rest = FRISCH_TAGE - alter
    if alter >= FRISCH_TAGE:
        return "rot", alter, rest
    if alter >= GELB_TAGE:
        return "gelb", alter, rest
    return "gruen", alter, rest


def pruefe_messungen(mes):
    f = []
    for m in mes:
        mid = m.get("id", "?")
        try:
            iso_datum(m.get("published"))
        except (TypeError, ValueError):
            f.append("messung %s ohne veroeffentlichungsdatum" % mid)
        if m.get("value") is not None:
            if m.get("label") not in LABELS:
                f.append("messung %s wert ohne label counted, computed oder source" % mid)
            w = m.get("window") or {}
            if m.get("label") == "source":
                if not m.get("checked"):
                    f.append("messung %s quellwert ohne pruefdatum" % mid)
            elif not ((w.get("from_utc") and w.get("to_utc")) or (w.get("from_date") and w.get("to_date"))):
                f.append("messung %s wert ohne fenster" % mid)
            c = m.get("compare")
            if c and c.get("label") not in LABELS:
                f.append("messung %s vergleichswert ohne label" % mid)
        elif not (m.get("window") or m.get("checked")):
            f.append("messung %s ohne fenster oder pruefdatum" % mid)
    return f


def interval_score(e):
    """Gneiting und Raftery (2007) fuer ein zentrales band mit niveau 1 - alpha:
    breite plus 2/alpha mal der abstand, wenn der wert ausserhalb liegt.
    In sekunden. None, wenn die prognose noch offen ist."""
    s, r = e.get("estimate") or {}, e.get("result") or {}
    if not (s.get("band_utc") and r.get("value_utc") and s.get("band_level")):
        return None
    lo, hi = (zeit(x).timestamp() for x in s["band_utc"])
    y = zeit(r["value_utc"]).timestamp()
    alpha = 1 - s["band_level"] / 100.0
    return (hi - lo) + (2 / alpha) * max(0.0, lo - y) + (2 / alpha) * max(0.0, y - hi)


def prognosen(track):
    """die gewerteten prognosen mit score, fuer startseite und /track-record."""
    gew = [e for e in track["entries"] if e.get("art") == "estimate" and e.get("status") in ("in band", "outside")]
    f = []
    for e in gew:
        if interval_score(e) is None:
            f.append("%s gewertet, aber ohne value_utc, band_utc oder band_level" % e["id"])
    if not track.get("updated"):
        f.append("data/track-record.json ohne updated")
    return gew, f


def alles_pruefen(tag=None, repo=REPO):
    tag = tag or heute()
    reps = lade(REPORTS, repo)["reports"]
    mes = lade(MESSUNGEN, repo)["measurements"]
    gew, f_tr = prognosen(lade(TRACK, repo))
    return pruefe_reports(reps, tag, repo) + pruefe_messungen(mes) + f_tr


def oder_abbruch(tag=None, repo=REPO):
    f = alles_pruefen(tag, repo)
    if f:
        raise Abbruch(f)


# --- html ----------------------------------------------------------------

def neuester_report(repo=REPO):
    return max(lade(REPORTS, repo)["reports"], key=lambda r: r["published"])


def stand(label, fenster=None, published=None, checked=None):
    """die sichtbare stand-zeile, ohne sie gilt eine zahl als fehler."""
    teile = []
    if fenster:
        teile.append("%s over %s" % (label, fenster_text(fenster)))
    elif checked:
        teile.append("%s, checked %s" % (label, lang(checked)))
    if published:
        teile.append("published %s" % lang(published))
    return '<p class="dstand">%s</p>' % E(", ".join(teile))


def headline(r, repo=REPO):
    h = r.get("headline")
    if not h:
        return ""
    kopf = lade("data/reports/%s.json" % h["slug"], repo)
    werte = kopf.get("werte") or {}
    if h["key"] not in werte:
        return ""
    w, n = werte[h["key"]]["wert"], werte[h["key"]]["n"]
    what = E(h["what"])
    satz = "%s, %s s counted, n %s" % (what[:1].upper() + what[1:], w,
                                       "{:,}".format(int(n)) if str(n).isdigit() else E(str(n)))
    if h.get("model_key") in werte:
        satz += ", against %s s computed %s" % (werte[h["model_key"]]["wert"], E(h.get("model_what", "")))
    return '<div class="dwert">%s s</div><p>%s.</p>' % (w, satz)


def report_karte(r, link, repo=REPO, ohne_zahl=False):
    """mit ohne_zahl die zeitlose fassung: titel, kennung und link, keine kopfzahl."""
    if ohne_zahl:
        return ('<div class="drep"><p class="dkick">Latest report, %s</p><h3>%s</h3><p>%s, %s.</p>'
                '<p>%s.</p></div>'
                % (E(r["id"]), link(r["path"], E(r["title"])), E(r["network"]), E(r.get("subject", "")),
                   link(r["path"], "Read the report with its window, date and raw data")))
    return ('<div class="drep dz"><p class="dkick">Latest report, %s</p><h3>%s</h3><p>%s, %s.</p>%s%s'
            '<p class="dmeta">Method v%s. %s, sha256 <code>%s…</code>.</p></div>'
            % (E(r["id"]), link(r["path"], E(r["title"])), E(r["network"]), E(r.get("subject", "")),
               headline(r, repo), stand("counted", r["window"], r["published"]), E(r["method_version"]),
               link(r["csv"], "Download the CSV"), E(r["csv_sha256"][:16])))


def messung_karte(m, link):
    wert = ""
    if m.get("value") is not None:
        vergleich = ""
        c = m.get("compare")
        if c:
            vergleich = "<p>Against %s, %s, %s.</p>" % (E(c["value"]), E(c["label"]), E(c["what"]))
        wert = ('<div class="dwert">%s</div><p>%s, %s%s.</p>%s'
                % (E(m["value"]), E(m["subject"]), E(m["label"]),
                   (", n %s" % "{:,}".format(m["n"])) if m.get("n") else "", vergleich))
    else:
        wert = "<p>%s.</p>" % E(m["subject"])
    st = stand(m["label"], m.get("window"), m.get("published"), m.get("checked"))
    mehr = "<p>%s</p>" % link(m["path"], E(m.get("link_text") or "Read more")) if m.get("path") else ""
    return ('<div class="dkarte dz" id="%s"><h3>%s</h3>%s<p class="small">%s.</p>%s%s</div>'
            % (E(m["id"]), E(m["network"]), wert, E(m["how"][:1].upper() + m["how"][1:]), st, mehr))


def prognose_block(track, link):
    gew, _ = prognosen(track)
    if not gew:
        return ""
    drin = sum(e["status"] == "in band" for e in gew)
    scores = [interval_score(e) for e in gew]
    mittel = sum(scores) / len(scores)
    stufen = sorted({e["estimate"]["band_level"] for e in gew})
    erst = min(e["published"] for e in gew)
    letzt = max(e["published"] for e in gew)
    zahl = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}
    wort = lambda n: zahl.get(n, "{:,}".format(n))
    return ('<section class="dprog" id="forecasts"><h2>Forecasts, scored in public</h2>'
            '<p>We publish activation times before they happen, dated and with a band, and score every '
            'forecast against the block afterwards, misses included.</p>'
            '<div class="dz"><div class="dwert">%d of %d</div>'
            '<p>Our %s forecasts landed inside their %s band, counted. Mean interval score %s, computed, lower is better.</p>'
            '%s</div><p>%s</p></section>'
            % (drin, len(gew), wort(len(gew)), " and ".join("%d%%" % s for s in stufen),
               dauer_text(mittel),
               '<p class="dstand">Forecasts published %s to %s, scored against the counted block, '
               'published %s</p>' % (lang(erst), lang(letzt), lang(track["updated"])),
               link("/track-record", "Every forecast and its score on our track record")))


# --- selbsttest ----------------------------------------------------------

def selbsttest():
    import tempfile
    import shutil
    falsch = 0
    anzahl = 10
    with tempfile.TemporaryDirectory() as tmp:
        for d in ("data", "data/reports", "reports"):
            os.makedirs(os.path.join(tmp, d), exist_ok=True)
        for p in (REPORTS, MESSUNGEN, TRACK):
            shutil.copy(os.path.join(REPO, p), os.path.join(tmp, p))
        for r in lade(REPORTS)["reports"]:
            ziel = os.path.join(tmp, r["csv"].lstrip("/"))
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            shutil.copy(os.path.join(REPO, r["csv"].lstrip("/")), ziel)
        neu = iso_datum(neuester_report()["published"])
        T = datetime.timedelta
        # das alter bricht nicht ab, es schaltet auf die zeitlose fassung und
        # stuft die taegliche pruefung (Ben, 11.11.2026, teil 2)
        faelle = [
            ("am tag der veroeffentlichung", neu, False, "gruen"),
            ("ein tag vor gelb", neu + T(days=GELB_TAGE - 1), False, "gruen"),
            ("ab gelb", neu + T(days=GELB_TAGE), False, "gelb"),
            ("genau an der grenze", neu + T(days=FRISCH_TAGE), False, "rot"),
            ("einen tag drueber", neu + T(days=FRISCH_TAGE + 1), True, "rot"),
        ]
        for name, tag, soll_zl, soll_st in faelle:
            fe = len(pruefe_reports(lade(REPORTS, tmp)["reports"], tag, tmp))
            zl, st = zeitlos(tag, tmp), stufe(tag, tmp)[0]
            ok = fe == 0 and zl == soll_zl and st == soll_st
            falsch += not ok
            print("  %s  %s, %d fehler, zeitlos %s, stufe %s, erwartet 0, %s, %s"
                  % ("ok  " if ok else "FEHL", name, fe, zl, st, soll_zl, soll_st))
        mes = lade(MESSUNGEN, tmp)["measurements"]
        ohne = [dict(mes[0], published=None)] + mes[1:]
        k = len(pruefe_messungen(ohne))
        falsch += k != 1
        print("  %s  messung ohne datum, %d funde, erwartet 1" % ("ok  " if k == 1 else "FEHL", k))
        ohne_f = [dict(mes[0], window=None)] + mes[1:]
        k = len(pruefe_messungen(ohne_f))
        falsch += k != 1
        print("  %s  wert ohne fenster, %d funde, erwartet 1" % ("ok  " if k == 1 else "FEHL", k))
        reps = lade(REPORTS, tmp)["reports"]
        kaputt = [dict(reps[0], csv_sha256="0" * 64)]
        k = len(pruefe_reports(kaputt, neu, tmp))
        falsch += k != 1
        print("  %s  falsche sha256, %d funde, erwartet 1" % ("ok  " if k == 1 else "FEHL", k))
    # interval score, zwei faelle von hand
    e_in = {"estimate": {"band_utc": ["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"], "band_level": 90},
            "result": {"value_utc": "2026-01-01T00:30:00Z"}}
    e_aus = {"estimate": {"band_utc": ["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"], "band_level": 90},
             "result": {"value_utc": "2026-01-01T01:01:00Z"}}
    for name, e, soll in (("im band, nur die breite", e_in, 3600.0), ("60 s drueber, 20 x 60 s strafe", e_aus, 4800.0)):
        ist = interval_score(e)
        falsch += abs(ist - soll) > 1e-6
        print("  %s  interval score %s, %.0f s, erwartet %.0f s" % ("ok  " if abs(ist - soll) < 1e-6 else "FEHL", name, ist, soll))
    print("%d von %d faellen falsch" % (falsch, anzahl))
    return 1 if falsch else 0


def pruefen(melden=False, probe=False, tag=None, repo=REPO):
    """die taegliche pruefung: liest nur, baut nichts, schreibt nichts.
    Meldet gelb und rot nach #ops-log, ebenso echte fehler. Exit 1 bei rot
    oder fehler, sonst 0."""
    fehler = alles_pruefen(tag, repo)
    neu = neuester_report(repo)
    st, alter, rest = stufe(tag, repo)
    if fehler:
        text = ("pulsehawk.io frische ROT, die datierte schicht hat fehler, der naechste bau bricht ab:\n- "
                + "\n- ".join(fehler))
        st = "rot"
    elif st == "rot":
        text = ("pulsehawk.io frische ROT: neuester report %s ist %d tage alt (veroeffentlicht %s), die grenze "
                "ist %d tage. Die startseite baut die zeitlose fassung ohne kopfzahl. Neuen report in "
                "data/reports.json eintragen." % (neu["id"], alter, neu["published"], FRISCH_TAGE))
    elif st == "gelb":
        text = ("pulsehawk.io frische GELB: neuester report %s ist %d tage alt (veroeffentlicht %s), noch %d "
                "tage bis zur grenze von %d tagen." % (neu["id"], alter, neu["published"], rest, FRISCH_TAGE))
    else:
        text = ("pulsehawk.io frische gruen: neuester report %s ist %d tage alt, noch %d tage bis zur grenze."
                % (neu["id"], alter, rest))
    print("stufe=%s alter=%d rest=%d report=%s" % (st, alter, rest, neu["id"]))
    print(text)
    if melden and st != "gruen":
        sys.path.insert(0, os.path.join(HERE, "ph"))
        import ops_melden
        ops_melden.log(text, was="frische", probe=probe)
    return 1 if st == "rot" else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--selbsttest"]:
        sys.exit(selbsttest())
    if sys.argv[1:2] == ["--pruefen"]:
        tag_ = iso_datum(sys.argv[sys.argv.index("--heute") + 1]) if "--heute" in sys.argv else None
        sys.exit(pruefen(melden="--melden" in sys.argv, probe="--probe" in sys.argv, tag=tag_))
    try:
        oder_abbruch()
    except Abbruch as exc:
        print(exc)
        sys.exit(1)
    print("datierte schicht ok, neuester report %s vom %s, grenze %d tage"
          % (neuester_report()["id"], neuester_report()["published"], FRISCH_TAGE))
