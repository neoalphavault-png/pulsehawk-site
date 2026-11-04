#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""b2b_check.py, prueft die Seiten der Messmarke gegen die Textregeln.

Regeln vom 16.10.2026 (Ben), fuer sichtbaren Text:
  kein Gedankenstrich, kein Doppelpunkt, kein Pfeil (Uhrzeiten, Links und
  "|" im Title ausgenommen), "%" statt "percent", keine Echtzeit-Woerter,
  "PulseHawk" in einem Wort, kein deutsches "stand" (Ben, 2.11.2026),
  keine gemiedenen Suchbegriffe, keine
  Superlative aus der Liste, Saetze ueber das, was wir nicht tun, nur auf
  /method und /independence.
Dazu SEO: Title hoechstens 60 Zeichen, Description 140 bis 155, genau eine
H1, Abschnitte unter 250 Woertern, JSON-LD gueltig, FAQ-Schema nur mit
Fragen, die sichtbar dastehen, Canonical und og:image vorhanden, Plausible
auf jeder Seite. Und nie eine IP-Adresse im Quelltext.

Dazu ab 4.11.2026 (Ben): ein Absatz, der ein Upgrade, eine Aktivierung oder
eine Konsensregel einer Kette nennt, traegt die Spezifikationsnummer (ZIP,
CHIP, KIP, BIP, EIP, SIMD, BEP); eine vorhergesagte Upgrade-Zeit steht nur als
Blockhoehe plus "estimate"; Mess- und Report-Seiten tragen Methoden-IDs, eine
Zeile "Measurement uncertainty" und den Block "reproduce this".

    python3 scripts/b2b_check.py datei.html ...
    python3 scripts/b2b_check.py --selbsttest
"""

import html
import json
import os
import re
import sys
from html.parser import HTMLParser

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ECHTZEIT = ("live", "right now", "real time", "real-time", "realtime", "currently",
            "at the moment")
GEMIEDEN = ("blockchain testing services", "smart contract audit", "security audit",
            "benchmark", "reviewed by", "audited by", "team of experts")
SUPERLATIV = ("best-in-class", "leading", "world-class", "unmatched", "revolutionary",
              "fastest", "most trusted", "cutting-edge", "the best ")
NICHT_TUN = re.compile(r"\bwe (do not|don't|never|make no)\b", re.I)
NICHT_TUN_ERLAUBT = ("method.html", "independence.html")

# Saetze beginnen nicht mit einer Ziffer (Ben, 18.10.2026). Geprueft wird
# Fliesstext: Absaetze, Listen, Ueberschriften, FAQ-Fragen und Kartentexte.
# Tabellenzellen, Chips und Quellenzeilen sind keine Saetze.
SATZ_BLOECKE = ("p", "li", "h1", "h2", "h3", "summary")
SATZ_KLASSEN = ("cd", "lead", "cr")
SATZ_AUSNAHMEN = ("src", "note")
RE_SATZ = re.compile(r"(?<=[.!?])\s+")

# Zitierkasten "How to cite" (Ben, 23.10.2026). Der Satz hat genau diese
# Form, sein Anker steht auf der Zielseite, der Knopf kopiert genau diesen
# Satz, und darunter steht der Einladungssatz.
RE_ZITIER = re.compile(r"PulseHawk \(@pulsehawkio\), [^,]+, (counted|published) "
                       r"\d{1,2} (January|February|March|April|May|June|July|August|"
                       r"September|October|November|December) \d{4}, "
                       r"pulsehawk\.io(/[a-z0-9/-]*)#([a-z0-9-]+)$")
EINLADUNG = "Using our numbers? Tag @pulsehawkio and we add you to the list."
# Upgrades und Konsensregeln nur mit Spezifikationsnummer im selben Absatz,
# Upgrade-Zeiten nur als Blockhoehe plus Schaetzung (Ben, 4.11.2026).
# Ein Absatz nennt ein Upgrade, wenn er eine Kette oder ein benanntes Upgrade
# zusammen mit einem Upgrade-Wort nennt (Aktivierung, Upgrade, Hardfork,
# Konsensregel). Allgemeine Saetze ueber Upgrades ohne Kette bleiben frei,
# ebenso Leiste, Fusszeile und Brotkrumen.
KETTEN = re.compile(r"\b(Zcash|Bitcoin Cash|BCH|Bitcoin|Kaspa|Ethereum|Solana|Litecoin|Monero|Cardano|"
                    r"Polkadot|Avalanche|Cosmos|Dogecoin|Tron|Ton|Sui|Aptos|Near)\b")
UPGRADE_WORT = re.compile(r"\b(activat\w*|upgrade\w*|hard ?forks?|soft ?forks?|consensus rules?|"
                          r"network upgrade)\b", re.I)
BENANNT = re.compile(r"\b(NU\d+|Crescendo|Taproot|SegWit|Pectra|Dencun|Shapella|Faster Blocks)\b")
RE_SPEZ = re.compile(r"\b(ZIP|CHIP|KIP|BIP|EIP|SIMD|BEP)[ -]?\d", re.I)
PROGNOSE = re.compile(r"\b(forecasts?|expected|expect|arrives?|will (activate|reach|arrive)|puts block|"
                      r"estimat\w*|draws)\b", re.I)
ZEITANGABE = re.compile(r"\b\d{1,2}:\d{2}\b|\b\d{1,2} (January|February|March|April|May|June|July|"
                        r"August|September|October|November|December)\b")
# mess- und report-seiten tragen methoden-ids, eine unsicherheitszeile und
# den block "reproduce this" (Ben, 4.11.2026)
MESS_SEITEN = ("zcash-nu7.html",)


def funde_spez(absaetze):
    f = []
    for text in absaetze:
        upgrade = (BENANNT.search(text) or KETTEN.search(text)) and UPGRADE_WORT.search(text)
        if upgrade and not RE_SPEZ.search(text):
            f.append("upgrade ohne spezifikationsnummer (ZIP, CHIP, KIP, BIP) im absatz '%s'" % text[:90])
        # eine vorhergesagte zeit fuer ein upgrade oder eine blockhoehe
        if PROGNOSE.search(text) and ZEITANGABE.search(text) and (upgrade or re.search(r"\bblock [\d,]{4,}", text)):
            if not re.search(r"\bblock [\d,]{4,}", text) or not re.search(r"estimat", text, re.I):
                f.append("upgrade-zeit ohne blockhoehe und 'estimate' im absatz '%s'" % text[:90])
    return f


def funde_messseite(roh):
    f = []
    if 'class="meth"' not in roh or "/method#ph-m-" not in roh:
        f.append("mess-seite ohne methoden-ids")
    if "Measurement uncertainty" not in roh:
        f.append("mess-seite ohne zeile measurement uncertainty")
    if 'id="reproduce"' not in roh:
        f.append("mess-seite ohne block reproduce this")
    return f


RE_ZEITPUNKT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$")


def ziel_datei(pfad):
    pfad = pfad.strip("/")
    return "index.html" if not pfad else pfad + ".html"


def funde_zitierkasten(roh):
    f = []
    ids = re.findall(r'\sid="([^"]+)"', roh)
    doppelt = sorted({i for i in ids if ids.count(i) > 1})
    if doppelt:
        f.append("id doppelt %s" % ", ".join(doppelt))
    kaesten = re.findall(r'<div class="cite">(.*?)</p></div>', roh, re.S)
    if roh.count('<div class="cite">') != len(kaesten):
        f.append("zitierkasten unvollstaendig")
    for k in kaesten:
        m = re.search(r'<code id="([^"]+)">([^<]*)</code><button type="button" class="cb" '
                      r'data-copy="([^"]+)">copy</button>', k)
        if not m or m.group(1) != m.group(3):
            f.append("zitierkasten ohne passenden knopf copy")
            continue
        satz = html.unescape(m.group(2))
        z = RE_ZITIER.match(satz)
        if not z:
            f.append("zitiersatz passt nicht zur form '%s'" % satz)
            continue
        ziel = os.path.join(REPO, ziel_datei(z.group(3)))
        if not os.path.exists(ziel):
            f.append("zitiersatz zeigt auf fehlende seite '%s'" % z.group(3))
        else:
            with open(ziel, encoding="utf-8") as fh:
                if ' id="%s"' % z.group(4) not in fh.read():
                    f.append("anker #%s fehlt auf %s" % (z.group(4), z.group(3)))
        if EINLADUNG not in re.sub(r"<[^>]+>", "", k):
            f.append("einladungssatz fehlt im zitierkasten")
    if kaesten and "data-copy" in roh and "navigator.clipboard" not in roh:
        f.append("kopier-skript fehlt")
    return f


class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stapel = []
        self.teile = []          # (tag-pfad, text)
        self.h1 = 0
        self.ld = []
        self.meta = {}
        self.links = {}
        self.title = ""
        self.abschnitte = [[]]
        self._ld = False
        self._title = False
        self.attrtext = []
        self.bloecke = []        # fliesstext je block, fuer die ziffernregel
        self.absaetze = []       # p, li und lead, fuer die upgrade-regeln
        self._block = []         # stapel offener bloecke: (tag, sammelt)

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag in ("br", "img", "input", "meta", "link"):
            if tag == "meta":
                k = d.get("name") or d.get("property")
                if k:
                    self.meta[k] = d.get("content", "")
            if tag == "link" and d.get("rel"):
                self.links[d["rel"]] = d.get("href", "")
            if tag == "img" and d.get("alt"):
                self.attrtext.append(d["alt"])
            if tag == "input" and d.get("placeholder"):
                self.attrtext.append(d["placeholder"])
            return
        self.stapel.append(tag)
        klassen = (d.get("class") or "").split()
        if tag in SATZ_BLOECKE or any(k in SATZ_KLASSEN for k in klassen):
            sammelt = not any(k in SATZ_AUSNAHMEN for k in klassen)
            rahmen = any(t in ("nav", "header", "footer") for t in self.stapel)
            self._block.append((tag, sammelt, [], (tag in ("p", "li") or "lead" in klassen) and not rahmen))
        if tag == "h1":
            self.h1 += 1
        if tag == "h2":
            self.abschnitte.append([])
        if tag == "script" and d.get("type") == "application/ld+json":
            self._ld = True
            self.ld.append("")
        if tag == "title":
            self._title = True
        if d.get("placeholder"):
            self.attrtext.append(d["placeholder"])

    def handle_endtag(self, tag):
        if self._block and self._block[-1][0] == tag:
            _, sammelt, teile, absatz = self._block.pop()
            text = re.sub(r"\s+", " ", "".join(teile)).strip()
            if sammelt and text:
                self.bloecke.append(text)
                if absatz:
                    self.absaetze.append(text)
        if tag in self.stapel:
            while self.stapel and self.stapel.pop() != tag:
                pass
        if tag == "script":
            self._ld = False
        if tag == "title":
            self._title = False

    def handle_data(self, data):
        if self._ld:
            self.ld[-1] += data
            return
        if self._title:
            self.title += data
            return
        if any(t in ("script", "style", "head") for t in self.stapel):
            return
        if self._block:
            self._block[-1][2].append(data)
        if data.strip():
            self.teile.append(data)
            self.abschnitte[-1].append(data)


def funde_text(text, datei):
    f = []
    t = text
    # uhrzeiten und links sind erlaubt
    t_ohne = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\b", "", t)
    t_ohne = re.sub(r"https?://\S+|mailto:\S+", "", t_ohne)
    for zeichen, name in (("—", "gedankenstrich"), ("–", "gedankenstrich"),
                          (" - ", "gedankenstrich"), ("→", "pfeil"), ("←", "pfeil"),
                          ("->", "pfeil"), ("=>", "pfeil"), (":", "doppelpunkt")):
        if zeichen in t_ohne:
            i = t_ohne.index(zeichen)
            f.append("%s in '%s'" % (name, t_ohne[max(0, i - 40):i + 20].strip()))
    low = t.lower()
    # "percentile" ist ein fachwort und bleibt, nur "percent" fuer % ist falsch
    if re.search(r"(?<![a-z])percent(?![a-z])", low):
        f.append("'percent' statt %")
    # "stand 28 October 2026" ist deutsch, englisch heisst es "as of" (Ben, 2.11.2026)
    m = re.search(r"(?<![a-z])stand(?![a-z])", low)
    if m:
        f.append("'stand' in '%s', englisch 'as of <datum>'" % t[max(0, m.start() - 30):m.end() + 25].strip())
    for w in ECHTZEIT:
        if re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(w), low):
            f.append("echtzeit-wort '%s'" % w)
    for w in GEMIEDEN:
        if w in low:
            f.append("gemiedener begriff '%s'" % w)
    for w in SUPERLATIV:
        if w in low:
            f.append("superlativ '%s'" % w.strip())
    # "PulseHawk" in einem wort; kleingeschrieben nur als domain oder handle
    for m in re.finditer(r"pulse\s?hawk", t, re.I):
        if m.group(0) == "PulseHawk":
            continue
        if re.match(r"pulsehawk(\.io|io)", t[m.start():m.start() + 12]):
            continue
        # die organisation auf github heisst so (github.com/pulsehawk/methods)
        if t[max(0, m.start() - 11):m.start()] == "github.com/":
            continue
        f.append("schreibweise '%s'" % m.group(0))
    if os.path.basename(datei) not in NICHT_TUN_ERLAUBT and NICHT_TUN.search(t):
        m = NICHT_TUN.search(t)
        f.append("'was wir nicht tun' ausserhalb von method/independence: '%s'"
                 % t[max(0, m.start() - 30):m.end() + 30])
    return f


def dicht(s):
    """ohne leerraum, damit ein link mitten im satz den vergleich nicht stoert."""
    return re.sub(r"\s+", "", s)


def pruefe(datei, roh=None):
    """funde fuer eine seite. Mit roh wird der html-text geprueft, bevor er auf
    der platte liegt (upgrade-report-waechter, Ben 2.11.2026)."""
    if roh is None:
        with open(os.path.join(REPO, datei), encoding="utf-8") as fh:
            roh = fh.read()
    p = Text()
    p.feed(roh)
    f = []
    sichtbar = " ".join(p.teile + p.attrtext)
    sichtbar = re.sub(r"\s+", " ", sichtbar)
    f += funde_text(sichtbar, datei)
    for block in p.bloecke:
        # abkuerzungen beenden keinen satz ("Art. 6 (1)(f) GDPR"), und eine
        # nummerierte ueberschrift ("1. Controller") ist kein satz
        block = re.sub(r"\b(Art|No|Jr|St|e\.g|i\.e)\. ", lambda m: m.group(1) + ".\u2060", block)
        block = re.sub(r"^\d+\.\s", "", block)
        for satz in RE_SATZ.split(block):
            if satz[:1].isdigit():
                f.append("satz beginnt mit ziffer '%s'" % satz[:60])
    f += funde_zitierkasten(roh)
    f += funde_spez(p.absaetze)
    rel = os.path.relpath(os.path.join(REPO, datei), REPO) if not os.path.isabs(datei) else os.path.relpath(datei, REPO)
    if rel in MESS_SEITEN or (rel.startswith("reports/") and rel.endswith(".html")):
        f += funde_messseite(roh)
    # Kaspa Pulse steht nirgends auf pulsehawk.io, auch nicht im schema oder in
    # einem link; die marken sind getrennt (Ben, 3.11.2026)
    m = re.search(r"kaspa[ _-]?pulse", roh, re.I)
    if m:
        f.append("kaspa pulse genannt '%s'" % roh[max(0, m.start() - 40):m.end() + 20].replace("\n", " "))
    # meta description und og-texte gelten als sichtbar
    desc = p.meta.get("description", "")
    f += ["description, " + x for x in funde_text(desc, datei)]
    titel = p.title.split("|")[0]
    f += ["title, " + x for x in funde_text(titel, datei)]
    if len(p.title) > 60:
        f.append("title %d zeichen" % len(p.title))
    noindex = "noindex" in p.meta.get("robots", "")
    if not (140 <= len(desc) <= 155) and not noindex:
        f.append("description %d zeichen" % len(desc))
    if p.h1 != 1:
        f.append("%d h1" % p.h1)
    for i, ab in enumerate(p.abschnitte[1:], 1):
        n = len(" ".join(ab).split())
        if n >= 250:
            f.append("abschnitt %d hat %d woerter" % (i, n))
    if not p.links.get("canonical", "").startswith("https://pulsehawk.io/"):
        f.append("canonical fehlt")
    og = p.meta.get("og:image", "")
    if not og:
        f.append("og:image fehlt")
    else:
        lokal = os.path.join(REPO, og.replace("https://pulsehawk.io/", ""))
        if not os.path.exists(lokal):
            f.append("og-bild fehlt auf platte %s" % og)
    if "plausible.io/js/pa-" not in roh or "plausible.init()" not in roh:
        f.append("plausible fehlt")
    if re.search(r"(?<![\d.])(\d{1,3}\.){3}\d{1,3}(?![\d.])", re.sub(r"<script type=\"application/ld\+json\">.*?</script>", "", roh, flags=re.S)):
        f.append("ip-adresse im quelltext")
    for blob in p.ld:
        try:
            d = json.loads(blob)
        except ValueError as exc:
            f.append("json-ld kaputt %s" % exc)
            continue
        for node in d.get("@graph", [d]):
            if node.get("@type") == "FAQPage":
                for q in node["mainEntity"]:
                    if dicht(q["name"]) not in dicht(sichtbar):
                        f.append("faq-frage nicht sichtbar '%s'" % q["name"])
                    if dicht(q["acceptedAnswer"]["text"]) not in dicht(sichtbar):
                        f.append("faq-antwort nicht sichtbar '%s'" % q["name"])
            for k in ("name", "description", "headline"):
                v = node.get(k)
                if isinstance(v, str):
                    f += ["schema %s, %s" % (k, x) for x in funde_text(v, datei)]
            # datum mit uhrzeit und zeitzone, sonst meldet googles rich results
            # test "ungueltiger datum/uhrzeit-wert" (Ben, 2.11.2026)
            for k in ("datePublished", "dateModified"):
                v = node.get(k)
                if v is not None and not RE_ZEITPUNKT.match(str(v)):
                    f.append("schema %s ohne uhrzeit und zeitzone '%s'" % (k, v))
    return f


SPEZ_FAELLE = [
    ("Zcash NU7 activates at block 3,543,405.", 1),
    ("Zcash NU7 activates at block 3,543,405, per ZIP 259.", 0),
    ("We measure a network before and after an upgrade.", 0),
    ("Kaspa runs at 10 blocks per second since the Crescendo hardfork.", 1),
    ("Kaspa runs at 10 blocks per second since the Crescendo hardfork, KIP-14.", 0),
    ("Our forecast puts the Zcash NU7 activation (ZIP 259) at 6 November 2026, 02:39 UTC.", 1),
    ("Our estimate puts block 3,543,405, the Zcash NU7 activation (ZIP 259), at 6 November 2026, 02:39 UTC.", 0),
    ("The median of 20,000 draws puts block 3,543,405 at 6 November 2026.", 1),
    ("Read the Zcash NU7 case", 0),
]


def selbsttest():
    """die regeln vom 4.11.2026 an festen faellen, dazu der waechter des track record."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import b2b_pages
    falsch = 0
    for text, n in SPEZ_FAELLE:
        k = len(funde_spez([text]))
        falsch += k != n
        print("  %s  %d funde, erwartet %d  %s" % ("ok  " if k == n else "FEHL", k, n, text[:70]))
    gut = {"id": "TR-T", "art": "estimate", "published": "2026-11-04", "url": "https://pulsehawk.io/x",
           "where": "x", "network": "Zcash mainnet, NU7 (ZIP 259)", "subject": "time of block 3,543,405",
           "estimate": {"value": "v", "band": "a to b", "as_of": "2026-11-02"}, "result": None,
           "deviation": None, "status": "open", "methods": ["PH-M-006"]}
    erg = {"value": "v", "label": "counted", "window": "w", "n": 5, "interval": "i"}
    faelle = [
        ("gut", gut, 0),
        ("ohne link", dict(gut, url=""), 1),
        ("ohne datum", dict(gut, published="4.11."), 1),
        ("in band ohne ergebnis", dict(gut, status="in band", deviation="+1 s"), 1),
        ("open mit ergebnis", dict(gut, result=erg), 1),
        ("in band mit ergebnis", dict(gut, status="in band", result=erg, deviation="+1 s"), 0),
        ("schaetzung ohne hoehe", dict(gut, subject="time of the upgrade"), 1),
        ("upgrade ohne zip", dict(gut, network="Zcash mainnet, NU7"), 1),
        ("unbekannte methode", dict(gut, methods=["PH-M-999"]), 1),
    ]
    for name, e, n in faelle:
        k = len(b2b_pages.pruefe_track_record([e]))
        falsch += k != n
        print("  %s  track record %s, %d funde, erwartet %d" % ("ok  " if k == n else "FEHL", name, k, n))
    print("%d von %d faellen falsch" % (falsch, len(SPEZ_FAELLE) + len(faelle)))
    return 1 if falsch else 0


def main(dateien):
    schlecht = 0
    for d in dateien:
        funde = pruefe(d)
        if funde:
            schlecht += 1
            print("  FEHL %-26s %s" % (d, "\n       ".ljust(34).join([""] + funde)))
        else:
            print("  ok   %s" % d)
    print("%d von %d seiten mit funden" % (schlecht, len(dateien)))
    return 1 if schlecht else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--selbsttest"]:
        sys.exit(selbsttest())
    sys.exit(main(sys.argv[1:]))
