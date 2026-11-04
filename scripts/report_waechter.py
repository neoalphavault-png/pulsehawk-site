#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report_waechter.py, der gemeinsame Waechter fuer alle Report-Typen des
PulseHawk Measurement Framework (Ben, 2.11.2026).

Ein Report-Typ (etwa scripts/upgrade_report.py) rechnet seine Werte aus der
CSV und baut seinen Seiteninhalt. Alles andere steht einmal hier und gilt fuer
jeden Typ: Kopfdaten lesen, Report-ID, Quellen, die Pruefungen a) bis f), die
Seite mit "How to cite", die Meldung nach #ops-log und der Selbsttest g).

Eine Seite entsteht nur, wenn jede Pruefung gruen ist. Sonst bricht der Bau
ab, und die Meldung geht nach #ops-log (scripts/ph/ops_melden.py, Secret
DISCORD_WEBHOOK_LOG aus der Umgebung; fehlt es, steht sie nur im Job-Log).

  a) jeder Wert auf der Seite hat Kennzeichnung (counted, source, computed),
     Fenster in UTC und n, sichtbar neben dem Wert
  b) alle Werte werden aus der CSV neu gerechnet und muessen exakt mit den
     Werten der messenden Sitzung und mit den Werten auf der Seite stimmen
  c) Plausibilitaet des Typs (beim Upgrade Report p50 <= p90 <= p99, keine
     negativen Zaehlungen, Fenster passt zur Aktivierungshoehe), dazu die
     Report-ID nach dem Muster PH-<Praefix>-<Jahr>-<Nummer>
  d) Zielwerte wie Zielabstand und Aktivierungshoehe aus zwei unabhaengigen
     Quellen, einer Protokoll-Konstante und einem Release, Abweichung bricht ab
  e) keine IPs, Hostnamen, Peer-Adressen oder Schluessel in Seite und CSV
  f) Textregeln (b2b_check), dazu kein now oder live, keine Preise, nie "we offer"
  g) --selbsttest baut absichtlich falsche Testdaten, jede Pruefung muss einmal
     ausloesen, und ein sauberer Datensatz muss durchgehen

Kein Report geht ohne Pruefung durch Claude in den Merge.

    python3 scripts/report_waechter.py --selbsttest
    python3 scripts/report_waechter.py --pruefen            # alle reports, ohne zu schreiben
    python3 scripts/report_waechter.py --pruefen zcash-nu7
"""

import datetime
import glob
import hashlib
import html
import importlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SITE = "https://pulsehawk.io"
DATEN = os.path.join(REPO, "data", "reports")

# die report-typen des frameworks. Ein typ mit status active hat ein modul,
# das rechnet und den seiteninhalt baut; geplante typen haben nur ihren satz.
TYPEN = [
    {"slug": "upgrade-report", "name": "Upgrade Report", "praefix": "PH-UR", "status": "active",
     "version": "1.0", "modul": "upgrade_report",
     "satz": "Measures a network upgrade on a PoW or DAG chain, from 24 hours before to 72 hours "
             "after the activation height, with seven fixed values."},
    {"slug": "confirmation-depth", "name": "Confirmation Depth Report", "praefix": "PH-CD",
     "status": "planned", "version": None, "modul": None,
     "satz": "Measures how deep reorgs reach on a chain, as a basis for how many confirmations cover them."},
    {"slug": "network-baseline", "name": "Network Baseline", "praefix": "PH-NB", "status": "planned",
     "version": None, "modul": None,
     "satz": "Measures block intervals, gaps, reorgs and peer software of a chain over a period "
             "without an upgrade, as the reference for later reports."},
    {"slug": "load-test", "name": "Load Test Report", "praefix": "PH-LT", "status": "planned",
     "version": None, "modul": None,
     "satz": "Measures how block intervals and inclusion times of a chain behave while a known "
             "transaction load runs on a test network."},
    {"slug": "anchor-verification", "name": "Anchor Verification Report", "praefix": "PH-AV",
     "status": "planned", "version": None, "modul": None,
     "satz": "Checks independently whether data anchored on a chain is there, unchanged, at the "
             "stated height and transaction."},
]
TYP = {t["slug"]: t for t in TYPEN}

# feste kennungen der pruefverfahren, auf /method beschrieben (Ben, 4.11.2026).
# Jeder Report nennt die Kennungen, die er nutzt. Abgestimmt mit der Sitzung
# "Zcash NU7 Testnet Messung" (Vorschlag vom 4.11.2026, Antwort im Bericht).
VERFAHREN = [
    {"id": "PH-M-001", "name": "Block intervals from headers",
     "was": "Our own header client fetches block headers from network peers and checks hash linkage, proof of "
            "work from the difficulty bits and the checkpoints of the node software. Intervals are header time "
            "minus the header time of the block before.",
     "validierung": "Each run compares 500 block hashes with two independent peers. All 500 matched on Zcash "
                    "mainnet on 2 November 2026, and on the Bitcoin Cash tempnet with two different node "
                    "implementations on 28 October 2026."},
    {"id": "PH-M-002", "name": "Reorg depth from the listener",
     "was": "Our listener connects to peers without running a node, follows the tip from every announced block "
            "and logs each switch to another branch with its depth in blocks. The same listener raises the "
            "chain split signal.",
     "validierung": "Replayed on 29 October 2026 against our recording of the Zcash NU7 testnet of 17 October "
                    "2026, 776 chain blocks and 5 orphaned blocks of depth 1, with a reorg of depth 2 and a "
                    "chain split added on purpose. Every case was detected as set."},
    {"id": "PH-M-003", "name": "Peer protocol version at the handshake",
     "was": "Our listener reads the protocol version each peer sends in the version handshake and counts the "
            "peers below the minimum protocol version of an upgrade. Only the version is kept, no address.",
     "validierung": "Checked in the replay of 29 October 2026. There is no independent comparison yet."},
    {"id": "PH-M-004", "name": "Propagation from the listener",
     "was": "Our listener records the first announcement of every block in milliseconds and the spread between "
            "the first and the last peer that announced it.",
     "validierung": "Compared on 28 October 2026 with the public rufitnes/tempnet-data set for the Bitcoin Cash "
                    "tempnet. All 4,207 blocks matched by hash, and the first announcement differed from his "
                    "receive time by a median of 0.01 s."},
    {"id": "PH-M-005", "name": "Stale blocks after six confirmations",
     "was": "A block counts as stale when it was announced to our listener and is not in the chain six blocks "
            "later. The share is stale blocks over chain blocks plus stale blocks.",
     "validierung": "Compared on 28 October 2026 with the reorg events in rufitnes/tempnet-data. The two "
                    "measure different things, a node logs a reorg only when its own tip had moved. There is no "
                    "independent count of the same quantity yet."},
    {"id": "PH-M-006", "name": "Forecast of an activation time",
     "was": "From the block pace we counted over the last full UTC days, 20,000 draws give the median time at "
            "which a block height is reached and a 90 % band. Every forecast is published with its date and "
            "scored on our track record.",
     "validierung": "The first check against a real activation is Zcash NU7 (ZIP 259) on mainnet, listed on our track "
                    "record."},
]
VERFAHREN_ID = {v["id"] for v in VERFAHREN}
METHODS_REPO = "https://github.com/pulsehawk/methods"
METHODS_MD = METHODS_REPO + "/blob/main/METHODS.md"
REPORT_V1 = METHODS_REPO + "/blob/main/upgrade_report/report_v1.py"
# was davon schon in pulsehawk/methods steht (Antwort der Sitzung "Zcash NU7
# Testnet Messung", 4.11.2026): die rechnung aus den aufgezeichneten daten in
# upgrade_report/report_v1.py; kopf-client, wache und zuhoerer, die zaehlung
# der stale blocks und die prognose selbst folgen. "rechnung" True heisst, die
# rechnung steht in report_v1.py.
VERFAHREN_CODE = {"PH-M-001": True, "PH-M-002": True, "PH-M-003": True, "PH-M-004": True,
                  "PH-M-005": False, "PH-M-006": True}


def verfahren_html(ids):
    """die zeile mit den verwendeten kennungen, jede verlinkt auf /method."""
    return '<p class="meth">Methods used %s.</p>' % ", ".join(
        '<a href="/method#%s">%s</a>' % (i.lower(), i) for i in ids)


def reproduzieren_html(eintrag):
    """der block "reproduce this". Mit bestaetigten befehlen zeigt er drei:
    code holen, neu zaehlen, vergleichen. Solange die messende sitzung sie nicht
    bestaetigt hat, zeigt er nur den ersten und sagt, wann die anderen kommen,
    statt etwas zu zeigen, das nicht laeuft."""
    repo = '<a href="%s" rel="noopener">github.com/pulsehawk/methods</a>' % METHODS_REPO
    if eintrag.get("bestaetigt"):
        befehle, satz = eintrag["befehle"], ("The code is in %s. These three commands fetch it, count again "
                                             "and compare with the published values." % repo)
    else:
        befehle = eintrag["befehle"][:1]
        satz = ("The code is in %s. The command below fetches it. The commands to count again and compare "
                "follow %s." % (repo, eintrag["folgt"]))
    return ('<section id="reproduce" class="repro" data-bestaetigt="%s"><h2>Reproduce this</h2>'
            '<p>%s</p><pre id="repro-cmd">%s</pre><p><button type="button" class="cb" data-copy="repro-cmd">'
            'copy</button><span class="vh" aria-live="polite"></span></p></section>'
            % ("true" if eintrag.get("bestaetigt") else "false", satz, E("\n".join(befehle))))


def lies_reproduzieren(schluessel):
    """der eintrag aus data/reproduce.json, sonst nur der befehl zum holen."""
    with open(os.path.join(REPO, "data", "reproduce.json"), encoding="utf-8") as fh:
        alle_ = json.load(fh)["eintraege"]
    return alle_.get(schluessel) or {"bestaetigt": False, "folgt": "with the code",
                                     "befehle": ["git clone %s && cd methods" % METHODS_REPO]}
RE_ID = re.compile(r"^(PH-[A-Z]{2})-(\d{4})-(\d{3})$")

ARTEN_QUELLE = {"protocol constant", "release"}
KENNUNGEN = {"counted", "source", "computed"}

MONATE = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]

# die sieben festen messwerte, so stehen sie in der spezifikation und im report
class Rot(Exception):
    """eine oder mehrere pruefungen sind rot. funde ist eine liste (buchstabe, text)."""

    def __init__(self, funde):
        super().__init__("; ".join("%s) %s" % f for f in funde))
        self.funde = funde


# --- hilfen ---------------------------------------------------------------

E = html.escape


def betrag(x):
    return "{:,}".format(x)


def ts(text):
    """'2026-11-06T02:40:12Z' -> unix-sekunden."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", text or ""):
        raise ValueError("zeit nicht im format JJJJ-MM-TTThh:mm:ssZ: %r" % text)
    return int(datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
               .replace(tzinfo=datetime.timezone.utc).timestamp())


def iso(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def lang(t):
    d = datetime.datetime.fromtimestamp(t, datetime.timezone.utc)
    return "%d %s %d, %02d:%02d UTC" % (d.day, MONATE[d.month - 1], d.year, d.hour, d.minute)


def datum_lang(iso_datum):
    d = datetime.date.fromisoformat(iso_datum)
    return "%d %s %d" % (d.day, MONATE[d.month - 1], d.year)


def fenster(von, bis):
    return "%s/%s" % (iso(von), iso(bis))


def fenster_text(f):
    von, bis = f.split("/")
    return "%s to %s" % (lang(ts(von)), lang(ts(bis)))


# --- daten lesen ----------------------------------------------------------

def lies_kopf(slug):
    with open(os.path.join(DATEN, slug + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def csv_pfad(kopf):
    return os.path.join(REPO, kopf["csv"]) if kopf.get("csv") else None


def lies_csv_text(kopf):
    p = csv_pfad(kopf)
    if not p:
        return None
    with open(p, encoding="utf-8", newline="") as fh:
        return fh.read()


# --- pruefungen -----------------------------------------------------------

RE_IP4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
RE_IP6 = re.compile(r"(?<![0-9A-Fa-f:])(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}(?![0-9A-Fa-f:])")
RE_HOSTPORT = re.compile(r"\b[a-z0-9.-]+\.[a-z]{2,}:\d{2,5}\b", re.I)
TLD = ("com|net|org|io|cash|dev|xyz|onion|local|lan|internal|info|co|app|cloud|network|"
       "de|uk|us|eu|ch|nl|fr|ru|cn|jp|me|sh|tech|ai|biz|host|server|node")
RE_HOST = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:%s)\b" % TLD, re.I)
# hosts, die die seite selbst nennt: eigene domain, quellen, schema, analytics
HOSTS_ERLAUBT = {"pulsehawk.io", "github.com", "zips.z.cash", "x.com", "schema.org",
                 "creativecommons.org", "plausible.io", "z.cash"}


def funde_e(text, wo):
    f = []
    for m in RE_IP4.finditer(text):
        if all(int(x) <= 255 for x in m.group(0).split(".")):
            f.append(("e", "ip-adresse in %s '%s'" % (wo, m.group(0))))
    for m in RE_IP6.finditer(text):
        g = m.group(0)
        # uhrzeiten (02:40:12) sind keine adressen, eine ip6 hat hex-buchstaben oder ::
        if "::" in g or re.search(r"[A-Fa-f]", g):
            f.append(("e", "ip6-adresse in %s '%s'" % (wo, g)))
    for m in RE_HOSTPORT.finditer(text):
        f.append(("e", "peer-adresse in %s '%s'" % (wo, m.group(0))))
    for m in RE_HOST.finditer(text):
        h = m.group(0).lower()
        if not any(h == e or h.endswith("." + e) for e in HOSTS_ERLAUBT):
            f.append(("e", "hostname in %s '%s'" % (wo, h)))
    sys.path.insert(0, HERE)
    import secret_scan
    for art, muster in secret_scan.MUSTER:
        if re.search(muster, text):
            f.append(("e", "%s in %s" % (art, wo)))
    return f


def pruefe_quellen(kopf, felder):
    """d) zwei unabhaengige quellen, eine protokoll-konstante und ein release,
    fuer jedes feld, das der report-typ als zielwert nennt."""
    f = []
    for feld, name in felder:
        e = kopf.get(feld) or {}
        q = e.get("quellen") or []
        if len(q) < 2:
            f.append(("d", "%s hat %d quelle(n), noetig sind zwei" % (name, len(q))))
            continue
        arten = {x.get("art") for x in q}
        if not ARTEN_QUELLE <= arten:
            f.append(("d", "%s braucht eine protokoll-konstante und ein release, hat %s"
                      % (name, sorted(a for a in arten if a))))
        if len({x.get("url") for x in q}) < len(q):
            f.append(("d", "%s, zwei quellen mit derselben url" % name))
        for x in q:
            if x.get("wert") != e.get("wert"):
                f.append(("d", "%s weicht ab, %s sagt %r, report sagt %r"
                          % (name, x.get("name"), x.get("wert"), e.get("wert"))))
            if not x.get("geprueft") or not x.get("url"):
                f.append(("d", "%s, quelle %s ohne url oder pruefdatum" % (name, x.get("name"))))
    return f


def vergleiche(a, b, pfad="werte"):
    """b) exakter vergleich, liefert die abweichenden stellen."""
    if isinstance(a, dict) and isinstance(b, dict):
        aus = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                aus.append("%s.%s fehlt %s" % (pfad, k, "in der csv-rechnung" if k not in b else "bei der sitzung"))
            else:
                aus += vergleiche(a[k], b[k], pfad + "." + k)
        return aus
    if type(a) is not type(b) or a != b:
        return ["%s, sitzung %r, csv %r" % (pfad, a, b)]
    return []


# --- seite ----------------------------------------------------------------

def wert_html(m, v, text, kennung, n, fen):
    """ein wert mit seiner kennzeichnung. data-v ist der kanonische wert, den
    der waechter mit der neu gerechneten zahl vergleicht."""
    return ('<span class="mv" data-m="%s" data-v="%s" data-k="%s" data-n="%d" data-f="%s">%s</span>'
            '<span class="mk">%s, n %s</span>'
            % (m, E(json.dumps(v), quote=True), kennung, n, fen, text, kennung, betrag(n)))


def zitier_texte(kopf):
    """klartext und bibtex mit id, titel, datum, url und methodenversion."""
    url = SITE + "/reports/" + kopf["slug"]
    titel = kopf["titel"]
    typname = TYP[kopf["typ"]]["name"]
    datum = kopf["geaendert"]
    klar = ("PulseHawk, %s, %s, method v%s, version of %s, %s"
            % (titel, kopf["id"], kopf["methode"], datum_lang(datum), url))
    bib = ("@misc{%s,\n  author = {{PulseHawk}},\n  title = {%s},\n  number = {%s},\n"
           "  year = {%s},\n  date = {%s},\n  url = {%s},\n  note = {PulseHawk %s, method v%s}\n}"
           % (kopf["id"], titel, kopf["id"], datum[:4], datum, url, typname, kopf["methode"]))
    return klar, bib


def zitier_html(kopf):
    klar, bib = zitier_texte(kopf)
    return ('<section id="cite"><h2>How to cite</h2><div class="rcite">'
            '<p>Plain text</p><pre id="cite-text">%s</pre>'
            '<p><button type="button" class="cb" data-copy="cite-text">copy</button>'
            '<span class="vh" aria-live="polite"></span></p>'
            '<p>BibTeX</p><pre id="cite-bibtex">%s</pre>'
            '<p><button type="button" class="cb" data-copy="cite-bibtex">copy</button>'
            '<span class="vh" aria-live="polite"></span></p></div></section>' % (E(klar), E(bib)))


REPORT_CSS = """
.rcite pre{background:var(--card);border-radius:10px;padding:14px 16px;overflow-x:auto;white-space:pre-wrap;
word-break:break-word;font:400 13.5px/1.55 var(--mono);color:var(--txt);margin-top:6px}
.rcite p{margin-top:14px}
.mk{display:block;font-size:12.5px;color:var(--dim)}
.mv{font-weight:600;color:var(--txt)}
.unc{font-size:13px;color:var(--dim);margin-top:8px}
.repro pre{background:var(--card);border-radius:10px;padding:14px 16px;overflow-x:auto;white-space:pre-wrap;
word-break:break-word;font:400 13.5px/1.55 var(--mono);color:var(--txt);margin-top:6px}
.sha code{word-break:break-all;overflow-wrap:anywhere}
"""


# --- waechter -------------------------------------------------------------

RE_WERT = re.compile(r'<span class="mv" ([^>]*)>(.*?)</span>(<span class="mk">(.*?)</span>)?', re.S)


def attrs(s):
    return {k: html.unescape(v) for k, v in re.findall(r'([a-z-]+)="([^"]*)"', s)}


def pruefe_id(kopf):
    """c) feste report-id PH-<praefix>-<jahr>-<nummer>, praefix passend zum typ."""
    typ = TYP.get(kopf.get("typ"))
    if not typ or typ["status"] != "active":
        return [("c", "report-typ %r unbekannt oder nicht aktiv" % kopf.get("typ"))]
    m = RE_ID.match(kopf.get("id") or "")
    if not m:
        return [("c", "report-id %r passt nicht zum muster PH-XX-JJJJ-NNN" % kopf.get("id"))]
    f = []
    if m.group(1) != typ["praefix"]:
        f.append(("c", "report-id %s, praefix %s passt nicht zu %s" % (kopf["id"], m.group(1), typ["praefix"])))
    if m.group(2) != kopf.get("veroeffentlicht", "")[:4]:
        f.append(("c", "report-id %s, jahr passt nicht zur veroeffentlichung %s"
                  % (kopf["id"], kopf.get("veroeffentlicht"))))
    if kopf.get("methode") != typ["version"]:
        f.append(("c", "methode v%s, die spezifikation von %s steht auf v%s"
                  % (kopf.get("methode"), typ["name"], typ["version"])))
    return f


def modul(kopf):
    return importlib.import_module(TYP[kopf["typ"]]["modul"])


def pruefe_seite_html(roh, soll, datei):
    """a), b) auf der seite, e) und f)."""
    f = []
    gefunden = {}
    for m in RE_WERT.finditer(roh):
        a = attrs(m.group(1))
        key = a.get("data-m", "?")
        if a.get("data-k") not in KENNUNGEN:
            f.append(("a", "%s ohne kennzeichnung counted, source oder computed" % key))
        if not re.fullmatch(r"\d+", a.get("data-n", "")):
            f.append(("a", "%s ohne n" % key))
        fen = a.get("data-f", "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", fen):
            f.append(("a", "%s ohne fenster in utc" % key))
        elif (fenster_text(fen) if fen.split("/")[0] != fen.split("/")[1] else lang(ts(fen.split("/")[0]))) \
                not in html.unescape(re.sub(r"<[^>]+>", "", roh)):
            f.append(("a", "%s, fenster %s steht nicht sichtbar auf der seite" % (key, fen)))
        sichtbar = m.group(4) or ""
        if a.get("data-k") and a.get("data-n") and sichtbar != "%s, n %s" % (a["data-k"], betrag(int(a["data-n"]))
                                                                           if a["data-n"].isdigit() else ""):
            f.append(("a", "%s, kennzeichnung und n stehen nicht sichtbar neben dem wert" % key))
        try:
            gefunden[key] = json.loads(a.get("data-v", ""))
        except ValueError:
            f.append(("b", "%s, wert auf der seite unlesbar" % key))
    if soll is not None:
        for k in sorted(set(soll) | set(gefunden)):
            if k not in gefunden:
                f.append(("b", "%s fehlt auf der seite" % k))
            elif k not in soll:
                f.append(("b", "%s steht auf der seite, ist aber kein messwert" % k))
            elif type(soll[k]) is not type(gefunden[k]) or soll[k] != gefunden[k]:
                f.append(("b", "%s, seite %r, csv %r" % (k, gefunden[k], soll[k])))
    elif gefunden:
        f.append(("b", "geruest ohne csv zeigt %d messwerte" % len(gefunden)))
    # css und skripte sind keine inhalte, das json-ld schon
    inhalt = re.sub(r"<style.*?</style>|<script(?![^>]*application/ld\+json).*?</script>", " ", roh, flags=re.S)
    f += funde_e(inhalt, "seite")
    sys.path.insert(0, HERE)
    import b2b_check
    f += [("f", x) for x in b2b_check.pruefe(datei, roh)]
    text = html.unescape(re.sub(r"<style.*?</style>|<script.*?</script>|<[^>]+>", " ", roh, flags=re.S))
    for muster, name in ((r"(?<![a-z])now(?![a-z])", "now"), (r"(?<![a-z])live(?![a-z])", "live"),
                         (r"\bwe offer\b", "we offer"),
                         (r"[$€£¥₿]|(?<![a-z])(price|prices|priced|usd|eur|usdt|usdc|market cap)(?![a-z])", "preis")):
        mm = re.search(muster, text, re.I)
        if mm:
            f.append(("f", "%s im text '%s'" % (name, text[max(0, mm.start() - 30):mm.end() + 20].strip())))
    return f


def pruefe_verfahren_unsicherheit(roh):
    """a) jeder abschnitt eines messwerts nennt seine verfahrenskennungen und hat
    eine zeile "Measurement uncertainty"; die kennungen gibt es auf /method; der
    block "reproduce this" steht auf der seite (Ben, 4.11.2026)."""
    f = []
    for m in re.finditer(r'<section id="(m\d[^"]*)">(.*?)</section>', roh, re.S):
        sid, inhalt = m.group(1), m.group(2)
        ids = re.findall(r"PH-M-\d{3}", re.sub(r"<[^>]+>", "", inhalt))
        if not ids:
            f.append(("a", "abschnitt %s ohne verfahrenskennung" % sid))
        for i in ids:
            if i not in VERFAHREN_ID:
                f.append(("a", "abschnitt %s nennt unbekannte kennung %s" % (sid, i)))
        if "Measurement uncertainty" not in inhalt:
            f.append(("a", "abschnitt %s ohne zeile measurement uncertainty" % sid))
    if 'id="reproduce"' not in roh:
        f.append(("a", "block reproduce this fehlt"))
    return f


def pruefe_report(kopf, csv_text, render, css=""):
    """alle pruefungen fuer einen report. Liefert (seiten-dict, werte) oder wirft Rot."""
    f = pruefe_id(kopf)
    if f:
        raise Rot(f)
    sys.path.insert(0, HERE)
    m = modul(kopf)
    f = pruefe_quellen(kopf, m.QUELLEN_FELDER)
    w = None
    rows = None
    if (kopf.get("werte") is None) != (csv_text is None):
        f.append(("b", "werte und csv gehoeren zusammen, eines fehlt"))
    if csv_text is not None:
        f += funde_e(csv_text, "csv")
        try:
            rows = m.zeilen(csv_text)
        except ValueError as exc:
            f.append(("c", "csv unlesbar, %s" % exc))
    if rows is not None and not any(x[0] == "d" for x in f):
        try:
            w = m.rechnen(kopf, rows)
        except ValueError as exc:
            f.append(("c", str(exc)))
        if w is not None:
            if isinstance(kopf.get("werte"), dict):
                try:
                    f += m.pruefe_plausibel(kopf["werte"])
                except (KeyError, TypeError) as exc:
                    f.append(("b", "werte der sitzung unvollstaendig, %s" % exc))
            f += m.pruefe_plausibel(m.oeffentlich(w), rows, kopf)
            f += [("b", x) for x in vergleiche(kopf.get("werte"), m.oeffentlich(w))]
    if f:
        raise Rot(f)
    kopf = dict(kopf, titel=m.titel(kopf))
    s = m.seite(kopf, w, csv_text)
    s["css"] = css + REPORT_CSS
    roh = render(s)
    f = pruefe_seite_html(roh, m.seiten_werte(w) if w else None, s["datei"])
    f += pruefe_verfahren_unsicherheit(roh)
    if f:
        raise Rot(f)
    return s, w


def melden(kopf, rot):
    """nach #ops-log, ohne den bau weiterlaufen zu lassen."""
    sys.path.insert(0, os.path.join(HERE, "ph"))
    import ops_melden
    text = ("report %s (%s) nicht gebaut, pruefungen rot\n%s"
            % (kopf.get("id"), kopf.get("slug"), "\n".join("%s) %s" % x for x in rot.funde[:20])))
    try:
        ops_melden.log(text, was="report")
    except ops_melden.Fehler as exc:
        print("meldung an #ops-log gescheitert, %s" % ops_melden.sauber(exc))


def alle(render, css=""):
    """alle reports unter data/reports. Ein roter report haelt den ganzen bau an."""
    aus = []
    for pfad in sorted(glob.glob(os.path.join(DATEN, "*.json"))):
        kopf = lies_kopf(os.path.splitext(os.path.basename(pfad))[0])
        try:
            s, _ = pruefe_report(kopf, lies_csv_text(kopf), render, css)
        except Rot as rot:
            melden(kopf, rot)
            raise SystemExit("report %s nicht gebaut\n%s"
                             % (kopf.get("id"), "\n".join("  %s) %s" % x for x in rot.funde)))
        aus.append(s)
    return aus


# --- selbsttest -----------------------------------------------------------

def _kette(ur, kopf, text):
    """kette, aktivierungshoehe und kopfzeit aus einer roh-csv, fuer den selbsttest."""
    rows = ur.zeilen(text)
    kette = {z["h"]: int(z["t"]) for z in rows if z["kind"] == "block"}
    akt = kopf["aktivierungshoehe"]["wert"]
    return kette, akt, kette[akt]


def selbsttest():
    sys.path.insert(0, HERE)
    sys.path.insert(0, os.path.join(HERE, "ph"))
    import b2b_pages
    import ops_melden
    import upgrade_report as ur
    gemeldet = []
    echt_log = ops_melden.log
    ops_melden.log = lambda text, was="", probe=False: gemeldet.append(text)
    schlecht, gezaehlt, ausgeloest = 0, 0, set()

    def ok(name, bed):
        nonlocal schlecht, gezaehlt
        gezaehlt += 1
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            schlecht += 1

    def lauf(kopf, csv_text, render=None):
        return pruefe_report(kopf, csv_text, render or b2b_pages.render)

    def rot(name, buchstabe, kopf, csv_text, render=None):
        try:
            lauf(kopf, csv_text, render)
            ok("%s) %s loest aus" % (buchstabe, name), False)
        except Rot as r:
            treffer = any(x[0] == buchstabe for x in r.funde)
            if treffer:
                ausgeloest.add(buchstabe)
            ok("%s) %s loest aus" % (buchstabe, name), treffer)

    try:
        kopf = ur.testkopf()
        text = ur.test_csv(kopf)
        w = ur.oeffentlich(ur.rechnen(kopf, ur.zeilen(text)))
        gut = dict(kopf, werte=w)
        s, ww = lauf(gut, text)
        kz = ww["kz"]
        ok("sauberer datensatz geht durch", s["datei"] == "reports/test-chain-up1.html")
        ok("M1 nach der aktivierung hat werte", kz["p50_nach"]["n"] > 10000)
        ok("perzentil mit linearer interpolation", ur.quantil([1, 2, 3, 4], 0.5) == 2.5
           and ur.quantil([10, 20], 0.9) == 19.0 and ur.r(ur.quantil([1, 2, 4], 0.99)) == 4.0)
        ok("modell bei 25 s, p50 17.3 s", kz["p50_nach_modell"]["wert"] == 17.3)
        ok("abstand des aktivierungsblocks gehoert zu nach", kz["p50_nach"]["n"]
           == len([h for h in ur.grenzen(*_kette(ur, kopf, text))[1]]))
        ok("M3 verteilung und kopfzahl ab tiefe 2", (kz["reorgs_ab_tiefe_2_vor"]["wert"],
           kz["reorgs_tiefe_1_vor"]["wert"], kz["reorgs_tiefe_3_plus_nach"]["wert"]) == (1, 2, 1))
        ok("M4 episoden, offene episode endet am fenster", kz["kettenspaltung_dauer_nach"]["n"] == 3)
        ok("M5 anteil in prozent, probe nach 6 h nicht im report",
           w["peers_unter_min_protokoll_aktivierung"]["wert"] == "35.0"
           and not any("plus_6h" in k for k in w) and ",peer,plus_6h," in text)
        ok("M6 stabil in ganzen sekunden, nach der ersten vollen stunde",
           re.fullmatch(r"\d+", w["zeit_bis_stabil"]["wert"]) and int(w["zeit_bis_stabil"]["wert"]) >= 3600)
        roh = b2b_pages.render(s)
        ok("jeder wert steht mit kennung auf der seite", roh.count('class="mv"') == len(ur.seiten_werte(ww)))
        ok("zitierblock mit id und bibtex", "@misc{PH-UR-2026-999," in roh and "method v1.0" in roh)
        ok("sha256 der csv auf der seite", hashlib.sha256(text.encode()).hexdigest() in roh)

        # geruest ohne zahlen geht durch
        g = dict(kopf, csv=None, werte=None)
        s, _ = lauf(g, None)
        roh = b2b_pages.render(s)
        ok("geruest ohne zahlen geht durch", 'class="mv"' not in roh and "Not yet counted" in roh)

        # a) kennzeichnung, fenster und n
        def ohne(attr):
            return lambda seite_: b2b_pages.render(seite_).replace(attr, "data-x", 1)
        rot("wert ohne kennung", "a", gut, text, ohne("data-k"))
        rot("wert ohne n", "a", gut, text, lambda s_: re.sub(r'data-n="\d+"', 'data-n=""', b2b_pages.render(s_), count=1))
        rot("wert ohne fenster", "a", gut, text, ohne("data-f"))
        rot("abschnitt ohne unsicherheitszeile", "a", gut, text,
            lambda s_: b2b_pages.render(s_).replace('<p class="unc">Measurement uncertainty', '<p class="unc">Unsicher', 1))
        rot("unbekannte verfahrenskennung", "a", gut, text,
            lambda s_: b2b_pages.render(s_).replace(">PH-M-001</a>", ">PH-M-999</a>", 1))
        rot("block reproduce this fehlt", "a", gut, text,
            lambda s_: b2b_pages.render(s_).replace('id="reproduce"', 'id="nachrechnen"', 1))
        rot("kennung nicht sichtbar", "a", gut, text,
            lambda s_: b2b_pages.render(s_).replace('<span class="mk">', '<span class="mx">', 1))
        # b) neu rechnen
        w2 = json.loads(json.dumps(w))
        w2["p90_nach"]["wert"] = str(round(float(w2["p90_nach"]["wert"]) + 0.1, 1))
        rot("sitzung meldet anderes p90", "b", dict(kopf, werte=w2), text)
        w2n = json.loads(json.dumps(w))
        w2n["reorgs_tiefe_1_vor"]["n"] = "99"
        rot("sitzung meldet anderes n", "b", dict(kopf, werte=w2n), text)
        rot("seite zeigt anderen wert", "b", gut, text,
            lambda s_: b2b_pages.render(s_).replace('data-m="reorgs_ab_tiefe_2_vor" data-v="&quot;1&quot;"',
                                                    'data-m="reorgs_ab_tiefe_2_vor" data-v="&quot;0&quot;"'))
        rot("csv ohne werte", "b", dict(kopf, werte=None), text)
        w6 = json.loads(json.dumps(w))
        w6["zeit_bis_stabil"]["wert"] = str(int(w6["zeit_bis_stabil"]["wert"]) + 60)
        rot("sitzung meldet andere zeit bis stabil", "b", dict(kopf, werte=w6), text)
        w6m = json.loads(json.dumps(w))
        w6m["zeit_bis_stabil"]["wert"] = str(round(int(w6m["zeit_bis_stabil"]["wert"]) / 60, 1))
        rot("sitzung meldet zeit bis stabil in minuten", "b", dict(kopf, werte=w6m), text)
        rot("geruest zeigt messwerte", "b", dict(kopf, csv=None, werte=None), None,
            lambda s_: b2b_pages.render(s_).replace("</main>", wert_html("reorg_max_tiefe_vor", "0", "0", "counted", 1,
                                                                         "2026-11-06T00:00:00Z/2026-11-06T01:00:00Z")
                                                     + "</main>"))
        # c) plausibel und fenster
        w3 = json.loads(json.dumps(w))
        w3["p50_vor"]["wert"] = str(float(w3["p99_vor"]["wert"]) + 1)
        rot("p50 groesser als p99", "c", dict(kopf, werte=w3), text)
        w4 = json.loads(json.dumps(w))
        w4["reorgs_tiefe_1_nach"]["wert"] = "-1"
        rot("negative zaehlung", "c", dict(kopf, werte=w4), text)
        zl = text.split("\n")
        bl = [z for z in zl if ",block," in z]
        rot("block vor dem fenster fehlt", "c", gut, "\n".join(z for z in zl if z != bl[0]))
        rot("fenster nach der aktivierung unvollstaendig", "c", gut, "\n".join(z for z in zl if z not in bl[-400:]))
        ohne_h = "\n".join(z for z in zl if not re.search(r",block,,%d," % kopf["aktivierungshoehe"]["wert"], z))
        rot("block auf der aktivierungshoehe fehlt", "c", gut, ohne_h)
        rot("csv mit fremder spalte", "c", gut, text.replace("report_id,", "report,", 1))
        rot("blockhoehen mit luecke", "c", gut, "\n".join(z for z in zl if z != bl[len(bl) // 2]))
        rot("report-id mit falschem praefix", "c", dict(gut, id="PH-CD-2026-999"), text)
        rot("report-id mit falschem jahr", "c", dict(gut, id="PH-UR-2025-999"), text)
        # d) zwei quellen
        k2 = json.loads(json.dumps(gut))
        k2["aktivierungshoehe"]["quellen"][1]["wert"] = 100001
        rot("release nennt andere hoehe", "d", k2, text)
        k3 = json.loads(json.dumps(gut))
        k3["ziel_nachher"]["quellen"] = k3["ziel_nachher"]["quellen"][:1]
        rot("zielabstand mit einer quelle", "d", k3, text)
        k4 = json.loads(json.dumps(gut))
        k4["ziel_vorher"]["quellen"][1]["art"] = "protocol constant"
        rot("zwei protokoll-konstanten, kein release", "d", k4, text)
        # e) adressen und schluessel
        rot("ip-adresse im hinweis", "e", dict(gut, hinweis="Peer 203.0.113.7 answered first."), text)
        rot("hostname im hinweis", "e", dict(gut, hinweis="Our node runs on zebra1.example.net here."), text)
        rot("peer-adresse in der csv", "e", gut,
            text + "PH-UR-2026-999,1.0,peer,activation,,2026-11-06T02:40:00Z,0 seed.example.org:8233\n")
        rot("schluessel im hinweis", "e", dict(gut, hinweis="ghp_" + "A1b2C3d4" * 5), text)
        # f) textregeln
        rot("gedankenstrich", "f", dict(gut, hinweis="Fast blocks – as planned."), text)
        rot("now", "f", dict(gut, hinweis="Blocks arrive every 25 s now."), text)
        rot("we offer", "f", dict(gut, hinweis="For this chain we offer more."), text)
        rot("preis", "f", dict(gut, hinweis="The token traded at $40 that day."), text)
        rot("doppelpunkt", "f", dict(gut, hinweis="Result: as computed."), text)

        # g) die meldung nach #ops-log
        gemeldet.clear()
        try:
            lauf(k2, text)
        except Rot as r:
            melden(k2, r)
        ok("rote pruefung geht nach #ops-log", gemeldet and "nicht gebaut" in gemeldet[-1])
        for b_ in "abcdef":
            ok("pruefung %s) mindestens einmal ausgeloest" % b_, b_ in ausgeloest)
    finally:
        ops_melden.log = echt_log
    print("%d von %d faellen falsch" % (schlecht, gezaehlt))
    return 1 if schlecht else 0


def main(argv):
    if "--selbsttest" in argv:
        return selbsttest()
    if "--pruefen" in argv:
        sys.path.insert(0, HERE)
        import b2b_pages
        rest = [a for a in argv if not a.startswith("--")]
        pfade = ([os.path.join(DATEN, r + ".json") for r in rest] if rest
                 else sorted(glob.glob(os.path.join(DATEN, "*.json"))))
        rc = 0
        for p in pfade:
            kopf = lies_kopf(os.path.splitext(os.path.basename(p))[0])
            try:
                _, w = pruefe_report(kopf, lies_csv_text(kopf), b2b_pages.render)
                print("ok   %s %s, %s" % (kopf["id"], kopf["slug"], "gemessen" if w else "geruest"))
            except Rot as r:
                rc = 1
                print("ROT  %s %s" % (kopf["id"], kopf["slug"]))
                for x in r.funde:
                    print("     %s) %s" % x)
        return rc
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
