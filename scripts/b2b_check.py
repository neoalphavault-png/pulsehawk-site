#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""b2b_check.py, prueft die Seiten der Messmarke gegen die Textregeln.

Regeln vom 16.10.2026 (Ben), fuer sichtbaren Text:
  kein Gedankenstrich, kein Doppelpunkt, kein Pfeil (Uhrzeiten, Links und
  "|" im Title ausgenommen), "%" statt "percent", keine Echtzeit-Woerter,
  "PulseHawk" in einem Wort, keine gemiedenen Suchbegriffe, keine
  Superlative aus der Liste, Saetze ueber das, was wir nicht tun, nur auf
  /method und /independence.
Dazu SEO: Title hoechstens 60 Zeichen, Description 140 bis 155, genau eine
H1, Abschnitte unter 250 Woertern, JSON-LD gueltig, FAQ-Schema nur mit
Fragen, die sichtbar dastehen, Canonical und og:image vorhanden, Plausible
auf jeder Seite. Und nie eine IP-Adresse im Quelltext.

    python3 scripts/b2b_check.py datei.html ...
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
    if "percent" in low:
        f.append("'percent' statt %")
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
        f.append("schreibweise '%s'" % m.group(0))
    if os.path.basename(datei) not in NICHT_TUN_ERLAUBT and NICHT_TUN.search(t):
        m = NICHT_TUN.search(t)
        f.append("'was wir nicht tun' ausserhalb von method/independence: '%s'"
                 % t[max(0, m.start() - 30):m.end() + 30])
    return f


def dicht(s):
    """ohne leerraum, damit ein link mitten im satz den vergleich nicht stoert."""
    return re.sub(r"\s+", "", s)


def pruefe(datei):
    pfad = os.path.join(REPO, datei)
    with open(pfad, encoding="utf-8") as fh:
        roh = fh.read()
    p = Text()
    p.feed(roh)
    f = []
    sichtbar = " ".join(p.teile + p.attrtext)
    sichtbar = re.sub(r"\s+", " ", sichtbar)
    f += funde_text(sichtbar, datei)
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
    if 'data-domain="pulsehawk.io"' not in roh:
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
    return f


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
    sys.exit(main(sys.argv[1:]))
