#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""b2b_pages.py, baut die Seiten der Messmarke PulseHawk.

WARUM ES DAS GIBT
Seit dem 15.10.2026 ist pulsehawk.io die B2B-Seite der Messmarke (Ben).
Zwoelf Seiten teilen sich Kopf, Leiste, Fuss, Schema und Zaehlung. Von Hand
gepflegt liefen die auseinander, also stehen sie hier an einer Stelle, und
dieses Skript schreibt fertiges, statisches HTML. Im Browser wird nichts
nachgeladen ausser Plausible; jede Zahl steht im Quelltext.

DIE ALTEN DATENSEITEN (Ben, 27.10.2026)
Die Bitcoin- und Marktseiten aus der frueheren DAY-Serie (Zyklus,
Drawdown, Dominanz, Gold, markets, what-if) und /archive leiten auf
/method weiter. GitHub Pages kann keinen HTTP-301 senden; die Weiterleitung
ist eine Seite mit meta refresh 0, canonical und noindex, wie die Kurzlinks
in kaspa-pulse. Dieses Skript schreibt sie (WEITERLEITUNGEN), sie stehen
nicht in der Sitemap, und keine Seite verlinkt sie. Der Seitenstempel und
der DAY-N-Lauf, die diese Seiten frueher beschrieben, sind stillgelegt.
In data/ schreibt dieses Skript nichts.

EINSTELLUNGEN AUS DER UMGEBUNG
  KONTAKT_MAIL    Empfaenger fuer Kontakt und mailto-Rueckfall
                  (Standard hello@pulsehawk.io)
  BREVO_FORM_URL  Action-URL des Brevo-Formulars. Leer heisst: das Formular
                  schickt per mailto. Die URL ist kein Geheimnis, sie steht
                  danach ohnehin im HTML. Schluessel gehoeren nie hierher.

SONNTAG 18.10.2026, ZCASH
  ZCASH_OFFEN auf True, dann ist /zcash-nu7 indexiert, in Sitemap und
  Leiste, und SAMPLE_URL zeigt auf den Musterbericht. Die Downloads
  erscheinen, sobald die Dateien unter reports/ liegen.

    python3 scripts/b2b_pages.py            # bauen und pruefen
    python3 scripts/b2b_pages.py --check    # nur pruefen
    python3 scripts/b2b_pages.py --og DIR   # og-vorlagen nach DIR
"""

import datetime
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SITE = "https://pulsehawk.io"

KONTAKT_MAIL = os.environ.get("KONTAKT_MAIL", "").strip() or "hello@pulsehawk.io"
# Brevo-Formular "PulseHawk contact", Liste PulseHawk Leads (#17), ohne
# Double-Opt-in (Ben, 17.10.2026). Die Action-URL ist kein Geheimnis, sie
# steht ohnehin im HTML. Aus der Umgebung ueberschreibbar, leer heisst mailto.
BREVO_FORM_URL_STANDARD = ("https://f926321f.sibforms.com/serve/MUIFAI2n0BTv1Y0_sa6l9ABLD6Y1dsCFy3mVr"
                           "IG6it6dG89b7R1QbENQtPLV1j5zwZa-zaKNhZi1nqHeLl_nC_FvellYmKM4RklEV1XtOLrN48X"
                           "bnZxFrXUhsv9zxPutHnBtu3sJfDYZnDbxdJjJMgrpNR-P32bYQrf6xGZbkVf3Ja8jNJQgGKj25"
                           "csrXcVwNA1Lhv1rfZTpzEd52Q==")
BREVO_FORM_URL = os.environ.get("BREVO_FORM_URL", BREVO_FORM_URL_STANDARD).strip()

ZCASH_OFFEN = True             # seit 18.10.2026, Endzahlen von Ben
ZCASH_PDF = "reports/zcash-nu7-sample-report.pdf"
# seit #29 (20.10.2026): die CSV liegt unter data/, byte-gleich mit
# kaspa-pulse messung/zcash-nu7, Commit e08fdd3. keine zweite unter reports/.
ZCASH_CSV = "data/zcash-nu7/zcash-nu7-testnet-intervals-2026-10-18.csv"
ZCASH_CSV_SHA256 = "c1cda3d79a470f5a8e508ebb8ba633dd4f3499eec79b5ecbba96b446dea603b6"
# bis Sonntag zeigt "See a sample report" auf den Aufbau eines Berichts
SAMPLE_URL = "/zcash-nu7" if ZCASH_OFFEN else "/method#sample-report"

STAND = "2026-10-16"          # stand der texte, fuer dateModified und sitemap
METHODE = "Method version 1, 16 October 2026"

MONATE = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def lang(iso):
    d = datetime.date.fromisoformat(iso)
    return "%d %s %d" % (d.day, MONATE[d.month - 1], d.year)


# --- preise, eine stelle -------------------------------------------------
# Dollar fest und rund, kein Wechselkurs zur Laufzeit (Ben, 16.10.2026).
PREISE = {
    "review": {"eur": 250, "usd": 290, "ab": False, "monat": False,
               "name": "Review"},
    "launch": {"eur": 2500, "usd": 2900, "ab": True, "monat": False,
               "name": "Launch measurement"},
    "ongoing": {"eur": 1500, "usd": 1750, "ab": True, "monat": True,
                "name": "Ongoing measurement"},
}
PREIS_STAND = "Prices as of October 2026, net, plus VAT where it applies. Invoices in euro."


def betrag(n):
    return "{:,}".format(n)


def preis_text(k):
    p = PREISE[k]
    t = "%s € ($%s)" % (betrag(p["eur"]), betrag(p["usd"]))
    if p["ab"]:
        t = "from " + t
    if p["monat"]:
        t += " per month"
    return t


# --- seiten --------------------------------------------------------------
# datei, pfad (kanonisch), title, description, h1, leiste-name
NAV = [
    ("/tps-verification", "TPS verification"),
    ("/launch-measurement", "Launch measurement"),
    ("/upgrade-monitoring", "Upgrade monitoring"),
    ("/upgrades", "Calendar"),
    ("/method", "Method"),
    ("/independence", "Independence"),
]
# die zcash-fallseite kommt mit ZCASH_OFFEN in die leiste (Ben, 16.10.2026)
if ZCASH_OFFEN:
    NAV.insert(4, ("/zcash-nu7", "Zcash NU7"))

ORG_ID = SITE + "/#org"
ORG = {
    "@type": "Organization",
    "@id": ORG_ID,
    "name": "PulseHawk",
    "url": SITE + "/",
    "logo": SITE + "/hawk.png",
    "email": KONTAKT_MAIL,
    "description": ("PulseHawk is an independent measurement brand. It measures "
                    "how blockchains behave under load, across all chains, with its own nodes "
                    "or header clients, an open method, dated numbers and raw data."),
    "parentOrganization": {
        "@type": "Organization",
        "name": "Vizora Digital UG (haftungsbeschränkt)",
        "address": {"@type": "PostalAddress", "streetAddress": "Marc-Chagall-Straße 54",
                    "postalCode": "40477", "addressLocality": "Düsseldorf",
                    "addressCountry": "DE"},
    },
    "sameAs": ["https://x.com/pulsehawkio", "https://kaspapulse.com"],
}

E = html.escape


def a(href, text, cls=""):
    extern = href.startswith("http")
    rel = ' rel="noopener"' if extern else ""
    c = ' class="%s"' % cls if cls else ""
    return '<a href="%s"%s%s>%s</a>' % (E(href, quote=True), c, rel, text)


def sample_button():
    return ('<p class="cta">%s</p>'
            % a(SAMPLE_URL, "See a sample report",
                "btn plausible-event-name=Sample+Report"))


def contact_button(text="Request a measurement"):
    return a("/contact", text, "btn ghost")


def faq_html(faqs):
    teile = []
    for q, ans in faqs:
        teile.append('<details><summary><h3>%s</h3></summary><p>%s</p></details>' % (q, ans))
    return '<section class="faq"><h2>Questions we get asked</h2>%s</section>' % "".join(teile)


def strip_tags(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def faq_schema(faqs):
    return {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": strip_tags(q),
         "acceptedAnswer": {"@type": "Answer", "text": strip_tags(ans)}}
        for q, ans in faqs]}


def box(best, nicht):
    li = lambda xs: "".join("<li>%s</li>" % x for x in xs)
    return ('<div class="fit"><div><h3>Best for</h3><ul>%s</ul></div>'
            '<div><h3>Not for</h3><ul>%s</ul></div></div>' % (li(best), li(nicht)))


def schritte(xs):
    return '<ol class="steps">%s</ol>' % "".join(
        "<li><b>%s</b> %s</li>" % (t, d) for t, d in xs)


def preis_block(k, zusatz=""):
    p = PREISE[k]
    return ('<div class="price"><div class="pl">%s</div><div class="pv">%s</div>'
            '<p>%s %s</p></div>' % (p["name"], preis_text(k), PREIS_STAND, zusatz))


def service_schema(name, pfad, desc, k):
    p = PREISE[k]
    spec = {"@type": "UnitPriceSpecification" if p["monat"] else "PriceSpecification",
            "price": p["eur"], "minPrice": p["eur"], "priceCurrency": "EUR",
            "valueAddedTaxIncluded": False}
    if p["monat"]:
        spec["unitCode"] = "MON"
        spec["referenceQuantity"] = {"@type": "QuantitativeValue", "value": 1, "unitCode": "MON"}
    return {"@type": "Service", "name": name, "serviceType": name,
            "url": SITE + pfad, "description": desc, "provider": {"@id": ORG_ID},
            "areaServed": "Worldwide",
            "offers": {"@type": "Offer", "url": SITE + pfad, "priceCurrency": "EUR",
                       "price": p["eur"], "priceSpecification": spec,
                       "availability": "https://schema.org/InStock"}}


def article_schema(seite, published, modified):
    return {"@type": "Article", "headline": seite["h1"], "description": seite["desc"],
            "url": SITE + seite["pfad"], "datePublished": published,
            "dateModified": modified, "inLanguage": "en",
            "author": {"@id": ORG_ID}, "publisher": {"@id": ORG_ID},
            "image": SITE + "/og/%s.png" % seite["og"]}


# --- kalender ------------------------------------------------------------

# --- zitate, "who cites our numbers?" (Ben, 23.10.2026) --------------------
# Fremde, oeffentliche Zitate unserer Zaehlungen aus data/citations.json. Die
# Liste waechst ohne Code: Eintrag ergaenzen, b2b_pages.py laufen lassen.
# Nur Text, keine Logos fremder Konten, kein Lob ueber uns ergaenzen.
ZITAT_FELDER = ("date", "source_name", "source_handle", "url", "network",
                "what_they_used", "quote", "our_page", "type", "tagged")
ZITAT_SATZ = ("Other teams use our counts in their own work. We list each public "
              "citation with its date.")
# type bestimmt den Linktext der Karte (Ergaenzung Ben, 23.10.2026)
ZITAT_TYPEN = {"article": "Read their article", "forum": "Read their forum post",
               "video": "Watch their video", "podcast": "Hear their podcast",
               "post": "Read their post"}
# Zaehler ueber dem Abschnitt erst ab so vielen Eintraegen (Ben, 23.10.2026)
ZITAT_ZAEHLER_AB = 3


def lies_zitate():
    """eintraege, neueste zuerst. bricht laut ab, wenn ein eintrag nicht passt,
    statt eine halbe karte zu bauen."""
    pfad = os.path.join(REPO, "data", "citations.json")
    if not os.path.exists(pfad):
        return []
    with open(pfad, encoding="utf-8") as fh:
        eintraege = json.load(fh)["entries"]
    for e in eintraege:
        fehlt = [k for k in ZITAT_FELDER if k not in e]
        if fehlt:
            raise SystemExit("citations.json, eintrag %r ohne %s" % (e.get("source_name"), fehlt))
        datetime.date.fromisoformat(e["date"])            # wirft bei falschem datum
        if not e["url"].startswith("https://"):
            raise SystemExit("citations.json, url ohne https bei %r" % e["source_name"])
        if len(e["quote"].split()) > 8:
            raise SystemExit("citations.json, zitat ueber 8 woerter bei %r" % e["source_name"])
        if e["our_page"] and not e["our_page"].startswith("/"):
            raise SystemExit("citations.json, our_page muss eine eigene seite sein (/...)")
        if e["type"] not in ZITAT_TYPEN:
            raise SystemExit("citations.json, type %r bei %r, erlaubt %s"
                             % (e["type"], e["source_name"], ", ".join(ZITAT_TYPEN)))
        if not isinstance(e["tagged"], bool):
            raise SystemExit("citations.json, tagged muss true oder false sein bei %r" % e["source_name"])
    return sorted(eintraege, key=lambda e: e["date"], reverse=True)


def zitat_karte(e):
    # fremde links in einem neuen tab
    links = [a(e["url"], ZITAT_TYPEN[e["type"]]).replace(' rel="noopener"',
                                                        ' target="_blank" rel="noopener"')]
    if e["our_page"]:
        links.append(a(e["our_page"], "Our measurement"))
    # what_they_used beginnt mit einem verb ("used ...", "linked ..."), die
    # karte setzt "They" davor
    satz = e["what_they_used"].strip().rstrip(".")
    # ohne handle (etwa ein forum) steht nur das netzwerk in der zeile
    herkunft = " · ".join(E(x) for x in (e["source_handle"], e["network"]) if x)
    # nur vorhandene klassen, damit die css der uebrigen seiten gleich bleibt
    return ('<div class="card"><span class="ct">%s, %s</span>'
            '<span class="src">%s</span>'
            '<span class="cd">They %s.<br><i>\u201c%s\u201d</i></span>'
            '<span class="cp">%s</span></div>'
            % (E(e["source_name"]), lang(e["date"]), herkunft,
               E(satz), E(e["quote"]), " · ".join(links)))


def zitat_abschnitt(eintraege, hoechstens=None, sid=""):
    if not eintraege:
        return ""
    zeige = eintraege[:hoechstens] if hoechstens else eintraege
    mehr = ""
    if hoechstens and len(eintraege) > hoechstens:
        mehr = '<p class="note">%s</p>' % a("/independence#cited-by", "All %d citations" % len(eintraege))
    # zaehler ueber der ueberschrift, erst ab ZITAT_ZAEHLER_AB eintraegen;
    # "since" ist der monat des aeltesten eintrags
    zaehler = ""
    if len(eintraege) >= ZITAT_ZAEHLER_AB:
        erster = datetime.date.fromisoformat(min(x["date"] for x in eintraege))
        zaehler = '<p class="kick">Cited %d times since %s %d</p>\n' % (
            len(eintraege), MONATE[erster.month - 1], erster.year)
    return ('<section%s>%s<h2>Who cites our numbers?</h2>\n<p>%s</p>\n<div class="cards">%s</div>\n%s</section>'
            % (' id="%s"' % sid if sid else "", zaehler, ZITAT_SATZ,
               "".join(zitat_karte(x) for x in zeige), mehr))


# --- "how to cite" (Ergaenzung Ben, 23.10.2026) ----------------------------
# Ein fertiger Zitiersatz unter der Hauptzahl jeder Messseite, mit Knopf
# "copy". Der Satz zeigt auf einen festen Anker an der Zahl. "counted" nur
# fuer eigene Zaehlungen (Textregel), die Methodenseite sagt "published".
# Kuenftige Fallseiten rufen zitier_kasten() genauso auf.
ZITIER_EINLADUNG = "Using our numbers? Tag @pulsehawkio and we add you to %s."


def zitier_satz(name, datum, ziel, verb="counted"):
    """ziel ist pfad mit anker, etwa "/zcash-nu7#mean"."""
    return "PulseHawk (@pulsehawkio), %s, %s %s, pulsehawk.io%s" % (name, verb, lang(datum), ziel)


def zitier_kasten(kid, name, datum, ziel, verb="counted", csv=""):
    """kid ist eine auf der seite eindeutige id, csv ein fertiger satz mit link."""
    return ('<div class="cite"><p class="ch">How to cite</p>'
            '<div class="cr"><code id="%s">%s</code>'
            '<button type="button" class="cb" data-copy="%s">copy</button>'
            '<span class="vh" aria-live="polite"></span></div>%s'
            '<p class="small">%s</p></div>'
            % (kid, E(zitier_satz(name, datum, ziel, verb)), kid,
               '<p class="small">%s</p>' % csv if csv else "",
               ZITIER_EINLADUNG % a("/independence#cited-by", "the list")))


def lies_upgrades():
    pfad = os.path.join(REPO, "data", "upgrades.json")
    with open(pfad, encoding="utf-8") as fh:
        d = json.load(fh)
    # nur eintraege mit quelle, regel vom 16.10.2026
    return d, [e for e in d["entries"] if str(e.get("source", "")).startswith("https://")]


def kalender_tabelle(eintraege):
    def datum(e):
        if e.get("date"):
            # date_estimate, das datum ist geschaetzt (etwa aus der hoehe), die
            # hoehe steht dann dahinter (Ben, 26.10.2026)
            t = '<time datetime="%s">%s</time>' % (e["date"], lang(e["date"]))
            if e.get("date_estimate"):
                t = "around " + t
                if e.get("height"):
                    t += ", block %s" % betrag(e["height"])
            return t
        # ohne datum, aber mit hoehe: die hoehe ist der termin, den das
        # projekt selbst nennt
        if e.get("height"):
            return "block %s" % betrag(e["height"])
        return "not set"

    def sortkey(e):
        return (e.get("date") or "9999-99-99", e["chain"], e["network"])

    zeilen = []
    for e in sorted(eintraege, key=sortkey):
        fall = a(e["case"], "case page") if e.get("case") and (
            ZCASH_OFFEN or "zcash" not in e["case"]) else ""
        zeilen.append(
            '<tr id="%s"><td class="c">%s</td><td>%s</td><td>%s</td><td>%s</td>'
            '<td>%s</td><td>%s</td><td>%s%s</td></tr>'
            % (E(e["id"]), E(e["chain"]), E(e["event"]), E(e["network"]), datum(e),
               E(e["status"]), a(e["source"], E(e.get("source_title") or "source")),
               "yes" if e.get("measured_by_us") else "no",
               (", " + fall) if fall else ""))
    return ('<div class="tablewrap"><table><thead><tr><th scope="col">Chain</th>'
            '<th scope="col">Event</th><th scope="col">Network</th><th scope="col">Date</th>'
            '<th scope="col">Status</th><th scope="col">Source</th>'
            '<th scope="col">Measured by us</th></tr></thead><tbody>%s</tbody></table></div>'
            % "".join(zeilen))


# --- die seiten ----------------------------------------------------------

# Bitcoin Cash Tempnet (Ben, 22.10.2026). Die Zahlen stammen aus der eigenen
# Zaehlung, kaspa-pulse messung/bch-tempnet, data/bch/tempnet-2026-10-21.json
# (Stand 0712804): bloecke 7572, median 43.0 s, erwartet 41.6 s, erster Block
# 2026-10-15 12:56:56 UTC, Stichtag 2026-10-21 10:00 UTC. Die Startseite baut
# nicht aus diesen Daten, deshalb stehen sie hier mit Quelle.
BCH_FALL = "cases/bitcoin-cash.html"


# --- startseite nach dem design-skill (Ben, 26.10.2026) ---------------------
# Richtung "One motif" aus .claude/skills/design-taste-frontend. Das Motiv
# ist ein Blockabstand als senkrechter Balken, genommen aus unserer eigenen
# Zcash-Zaehlung (CSV im Repo). Marke bleibt: Farben, Schriften, Falke. Die
# CSS und das Skript gelten nur fuer die Startseite (Klasse "home" am body),
# die uebrigen Seiten bleiben, wie sie sind.

PULS_FENSTER = 288      # bloecke im hero, um die laengste luecke der zaehlung


def puls_daten():
    """fenster aus der zcash-csv um die laengste luecke. liefert dict mit
    hoehe des ersten blocks, zeitstempeln und abstaenden."""
    import csv
    pfad = os.path.join(REPO, ZCASH_CSV)
    with open(pfad, encoding="utf-8") as fh:
        reihen = [(int(r["height"]), int(r["timestamp"]), int(r["interval_s"]))
                  for r in csv.DictReader(fh) if r["interval_s"]]
    i_max = max(range(len(reihen)), key=lambda i: reihen[i][2])
    start = max(0, i_max - PULS_FENSTER * 2 // 3)
    fenster = reihen[start:start + PULS_FENSTER]
    return {"bloecke": len(reihen) + 1, "fenster": fenster, "i_max": i_max - start}


def utc_text(ts):
    d = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
    return "%s, %02d:%02d UTC" % (lang(d.date().isoformat()), d.hour, d.minute)


def puls_satz(h, iv, ts):
    return "Block %s, %d s after its parent by timestamp, %s." % (betrag(h), iv, utc_text(ts))


def puls_figur():
    """hero: die echten abstaende als balken, wurzel-skala, mit regler."""
    d = puls_daten()
    f = d["fenster"]
    hoch = 300.0
    groesst = max(iv for _, _, iv in f)

    def y(iv):
        return hoch - (iv / groesst) ** 0.5 * (hoch - 8)

    pfad = "".join("M%d %.1fV300h3V%.1fZ" % (i * 4, y(iv), y(iv)) for i, (_, _, iv) in enumerate(f))
    h0, _, _ = f[0]
    hm, tsm, ivm = f[d["i_max"]]
    ziel = y(25)
    daten = json.dumps([[iv, ts] for _, ts, iv in f], separators=(",", ":"))
    return ("""<figure class="puls" data-ui>
<h2 class="ph">Zcash testnet, block by block</h2>
<svg viewBox="0 0 %(w)d 300" preserveAspectRatio="none" role="img" aria-labelledby="puls-cap">
<path class="pz" d="M0 %(ziel).1fH%(w)d"/><path class="pb" d="%(pfad)s"/>
<rect class="pm" x="0" y="0" width="3" height="300" style="transform:translateX(%(xm)dpx)"/></svg>
<div class="pa"><span>Bar height, seconds since the block before</span><span>Dashed line, 25 s target</span></div>
<label class="pr" for="puls-r">Pick a block in the trace</label>
<input id="puls-r" type="range" min="0" max="%(n)d" value="%(im)d" aria-describedby="puls-o">
<output id="puls-o" for="puls-r">%(satz)s</output>
<figcaption id="puls-cap">Zcash testnet after NU7, %(anz)d consecutive blocks from %(h0)s, measured by us. The tallest bar is the longest gap of our whole count of %(bl)s blocks, %(ivm)d s at block %(hm)s on %(dm)s. The line marks the 25 s target.</figcaption>
<script type="application/json" id="puls-d">{"h0":%(h0j)d,"d":%(daten)s}</script>
</figure>""" % {"w": len(f) * 4, "ziel": ziel, "pfad": pfad, "xm": d["i_max"] * 4, "n": len(f) - 1,
                  "im": d["i_max"], "satz": E(puls_satz(hm, ivm, tsm)), "anz": len(f), "h0": betrag(h0),
                  "bl": betrag(d["bloecke"]), "ivm": ivm, "hm": betrag(hm),
                  "dm": lang(datetime.datetime.fromtimestamp(tsm, datetime.timezone.utc).date().isoformat()),
                  "h0j": h0, "daten": daten})


def zcash_fragment():
    zeilen = [("Mean", "23.68 s", "25 s"), ("Median", "17.0 s", "17.3 s"), ("p90", "52 s", "57.6 s"),
              ("p99", "109 s", "115.1 s"), ("Longest gap", "451 s", "about 284 s")]
    return ('<div class="frag" data-ui><table class="ft"><thead><tr><th scope="col">Block interval</th>'
            '<th scope="col">Measured</th><th scope="col">Ideal 25 s chain</th></tr></thead><tbody>%s</tbody></table>'
            '<p class="fs">Our count of 49,203 blocks, up to 18 October 2026, 06:00 UTC</p></div>'
            % "".join('<tr><th scope="row">%s</th><td>%s</td><td>%s</td></tr>' % z for z in zeilen))


def bch_fragment():
    # zahlen wie in der bch-karte, eigene zaehlung bis 21.10.2026
    return ('<div class="frag" data-ui><p class="fh">Median gap between blocks</p>'
            '<div class="fb"><span class="fbl">Measured</span><span class="fbb" style="width:100%%"></span><span class="fbv">43 s</span></div>'
            '<div class="fb"><span class="fbl">Expected</span><span class="fbb e" style="width:%.1f%%"></span><span class="fbv">41.6 s</span></div>'
            '<p class="fs">Our count of 7,572 blocks, 15 to 21 October 2026</p></div>' % (41.6 / 43 * 100))


def csv_fragment():
    pfad = os.path.join(REPO, ZCASH_CSV)
    with open(pfad, encoding="utf-8") as fh:
        kopf = [next(fh).rstrip("\n") for _ in range(6)]
    return ('<div class="frag csv" data-ui><pre><code>%s\n…</code></pre>'
            '<p class="fs">Raw data, 49,203 rows up to 18 October 2026, SHA-256 %s…</p>'
            '<p class="fs"><a class="plausible-event-name=CSV+Download" href="/%s" download>Download the CSV</a>, about 1 MB, licensed CC BY 4.0.</p></div>'
            % ("\n".join(E(z) for z in kopf), ZCASH_CSV_SHA256[:16], ZCASH_CSV))


def bch_kachel():
    text = ("The testnet for 1 minute blocks, counted from our own header client since "
            "activation on 15 October 2026. Up to 21 October, 7,572 blocks with a median "
            "gap of 43 s against 41.6 s expected.")
    fall = (' %s' % a("/cases/bitcoin-cash", "Read the Bitcoin Cash case")
            if os.path.exists(os.path.join(REPO, BCH_FALL)) else "")
    kasten = zitier_kasten("cite-bch", "Bitcoin Cash tempnet block intervals",
                           "2026-10-21", "/#bch-median")
    return ('<div class="tile w2" id="bch-median"><h3>Bitcoin Cash tempnet</h3><p>%s%s</p>%s%s</div>'
            % (text, fall, bch_fragment(), kasten))


def zitat_zeilen(eintraege, hoechstens=3):
    """startseite, zitate als zeilen, das zitat in satzgroesse links."""
    if not eintraege:
        return ""
    zeige = eintraege[:hoechstens]
    zaehler = ""
    if len(eintraege) >= ZITAT_ZAEHLER_AB:
        erster = datetime.date.fromisoformat(min(x["date"] for x in eintraege))
        zaehler = '<p class="kick">Cited %d times since %s %d</p>\n' % (
            len(eintraege), MONATE[erster.month - 1], erster.year)
    zeilen = []
    for e in zeige:
        links = [a(e["url"], ZITAT_TYPEN[e["type"]]).replace(' rel="noopener"', ' target="_blank" rel="noopener"')]
        if e["our_page"]:
            links.append(a(e["our_page"], "Our measurement"))
        herkunft = " · ".join(E(x) for x in (e["source_handle"], e["network"]) if x)
        zeilen.append('<div class="zr"><blockquote><p>“%s”</p></blockquote><div class="zm">'
                      '<p><b>%s</b>, %s</p><p>%s</p><p>They %s.</p><p>%s</p></div></div>'
                      % (E(e["quote"]), E(e["source_name"]), lang(e["date"]), herkunft,
                         E(e["what_they_used"].strip().rstrip(".")), " · ".join(links)))
    mehr = ""
    if len(eintraege) > hoechstens:
        mehr = '<p>%s</p>' % a("/independence#cited-by", "All %d citations" % len(eintraege))
    return ('<section class="zit">%s<h2>Who cites our numbers?</h2>\n<p class="sub">%s</p>\n%s\n%s</section>'
            % (zaehler, ZITAT_SATZ, "\n".join(zeilen), mehr))


def leistungen():
    reihen = [("/tps-verification", "TPS verification", "Claimed vs measured throughput, from our own measurement.", "Review " + preis_text("review")),
              ("/launch-measurement", "Launch measurement", "The first week after a testnet or mainnet launch, set against the week before.", preis_text("launch").capitalize()),
              ("/upgrade-monitoring", "Upgrade monitoring", "Block time, difficulty and orphaned blocks before and after a hard fork.", "Ongoing " + preis_text("ongoing"))]
    return "\n".join('<a class="lr" href="%s"><h3 class="ln">%s</h3><span class="ld">%s</span><span class="lp">%s</span></a>'
                     % r for r in reihen)


HOME_CSS = """
.home{--xl:clamp(34px,7.4vw,112px);--l:clamp(30px,3.6vw,52px);--m:clamp(22px,2.1vw,30px);--s:15px}
.home .wrap{max-width:1312px;padding:0 clamp(20px,3vw,48px)}
.home header.top{border-bottom:0}.home nav.main a{font-size:var(--s)}
.home footer.foot{border-top:0;background:var(--card);margin-top:0}.home footer.foot .wrap{font-size:var(--s)}
.home main{padding:clamp(24px,4vw,56px) 0 0}
.home main>.wrap{display:grid;grid-template-columns:minmax(0,7fr) minmax(0,5fr);column-gap:clamp(24px,4vw,64px)}
.home main>.wrap>*{grid-column:1/-1}
.home main>.wrap>.lead{grid-column:1}.home main>.wrap>.hero-acts{grid-column:2;align-self:end;justify-content:flex-end}
.home p,.home li{font-size:18px;color:var(--txt)}
.home h1{font-size:var(--xl);line-height:.98;letter-spacing:-.035em;max-width:none;text-wrap:balance}
.home .lead{font-size:20px;line-height:1.5;max-width:48ch;margin-top:clamp(20px,2.2vw,32px)}
.home h2{font-size:var(--l);line-height:1.04;letter-spacing:-.025em;margin:0 0 20px}
.home h3{font:800 var(--m)/1.15 Archivo,sans-serif;letter-spacing:-.02em;color:var(--txt);margin:0}
.home section{padding-top:clamp(88px,10vw,168px)}
.home .sub{color:var(--dim);max-width:52ch;margin-top:0}
.home .small,.home .fs{font-size:var(--s);color:var(--dim)}
.home a.btn,.home button{border-radius:0}
.home .btn{font-size:var(--s);padding:14px 22px;transition:transform .15s ease,background-color .15s ease,color .15s ease}
.home .btn:active{transform:scale(.97)}
.home .btn.ghost:hover{background:var(--teal);color:#06110E;filter:none}
.home .acts{display:flex;flex-wrap:wrap;gap:12px;margin-top:28px}.home .acts .btn{margin:0}
.puls{margin:clamp(36px,4vw,56px) 0 0;position:relative}
.puls .ph{font:600 var(--s) 'IBM Plex Sans',sans-serif;letter-spacing:0;color:var(--dim);margin:0 0 12px}
.puls svg{display:block;width:100%;height:clamp(160px,28vh,300px)}
.puls .pb{fill:var(--teal);transform-origin:50% 100%;animation:steigen .7s cubic-bezier(.2,.7,.2,1) both}
.puls .pz{stroke:var(--dim);stroke-width:1;stroke-dasharray:4 6;vector-effect:non-scaling-stroke;fill:none}
.puls .pm{fill:var(--txt);transition:transform .12s ease-out}
.puls .pa{display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 24px;font-size:var(--s);color:var(--dim);margin-top:8px}
.puls .pr{display:block;font-size:var(--s);color:var(--dim);margin-top:20px}
.puls input{width:100%;height:44px;accent-color:var(--teal);margin:4px 0;cursor:pointer}
.puls output{display:block;font-size:18px;color:var(--txt);font-variant-numeric:tabular-nums;min-height:3.2em}
.puls figcaption{font-size:var(--s);color:var(--dim);margin-top:8px;max-width:80ch}
@keyframes steigen{from{transform:scaleY(.02)}to{transform:none}}
.lst{margin-top:12px}
.lr{display:grid;grid-template-columns:4fr 6fr 3fr;gap:8px 32px;align-items:baseline;text-decoration:none;color:var(--txt);padding:22px 20px;margin:0 -20px;transition:background-color .2s ease}
.lr+.lr{margin-top:6px}
.lr:hover,.lr:focus-visible{background:var(--card)}
.lr .ln{padding-left:18px;position:relative}
.lr .ln:before{content:"";position:absolute;left:0;bottom:.15em;width:6px;height:.8em;background:var(--teal)}
.ld{font-size:18px;color:var(--dim)}.lp{font-size:18px;text-align:right;font-variant-numeric:tabular-nums}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.tile{background:var(--card);padding:clamp(20px,2.4vw,32px);display:flex;flex-direction:column;gap:14px;scroll-margin-top:16px}
.tile.w2{grid-column:span 2}.tile.acc{background:var(--teal)}
.tile.acc h2{color:#06110E;margin:0}.tile.acc p{color:#06110E}
.tile .big{font:800 var(--l)/1 Archivo,sans-serif;letter-spacing:-.03em;color:var(--txt);margin-top:4px}
.tile .big+.small{margin-top:-8px}
.tile p{margin:0}
.frag{background:var(--bg);border:1px solid var(--line);padding:18px 20px;min-height:200px;font-variant-numeric:tabular-nums}
.ft{min-width:0;font-size:15px}.ft th,.ft td{padding:7px 8px;color:var(--txt);text-align:right;font:inherit;text-transform:none;letter-spacing:0}
.ft th[scope=row],.ft thead th:first-child{text-align:left;color:var(--dim)}.ft thead th{color:var(--dim);border-bottom:1px solid var(--line)}
.ft td{border-bottom:1px solid var(--line)}.ft tr:last-child td,.ft tr:last-child th{border-bottom:0}
.frag .fh{font-size:15px;color:var(--dim)}
.fb{display:grid;grid-template-columns:5.5em 1fr 3.5em;gap:10px;align-items:center;margin-top:14px;font-size:15px}
.fbb{display:block;height:28px;background:var(--teal)}.fbb.e{background:var(--dim)}.fbv{text-align:right}
.frag pre{margin:0;overflow:hidden}.frag code{font:400 14px/1.6 var(--mono);color:var(--txt)}
.home .cite{background:var(--bg);border:0;margin-top:0;max-width:none}
.home .cite .ch{text-transform:none;letter-spacing:0;font:600 var(--s) 'IBM Plex Sans',sans-serif;color:var(--txt)}
.home .cite .cb{font:600 var(--s) 'IBM Plex Sans',sans-serif;border-radius:0;min-height:40px}
.home .cite code{font-size:var(--s)}.home .cite .small{font-size:var(--s)}
.zit .zr{display:grid;grid-template-columns:7fr 5fr;gap:16px 48px;padding:32px 0}
.zit .zr+.zr{padding-top:8px}
.zit blockquote p{font:800 var(--m)/1.15 Archivo,sans-serif;letter-spacing:-.02em;color:var(--txt);margin:0;max-width:24ch}
.zit .zm p{margin:0 0 6px;font-size:var(--s);color:var(--dim)}.zit .zm p:first-child{color:var(--txt)}
.home .kick{font:600 18px 'IBM Plex Sans',sans-serif;color:var(--teal);margin:0 0 10px}
.panel{background:var(--card);display:grid;grid-template-columns:5fr 6fr;gap:clamp(24px,4vw,64px);padding:clamp(24px,4vw,56px);align-items:start}
.panel h2{margin-top:0}
.stmt{display:grid;grid-template-columns:6fr 6fr;gap:24px clamp(24px,4vw,64px);align-items:start}
.stmt .gross{font:800 var(--m)/1.2 Archivo,sans-serif;letter-spacing:-.02em;color:var(--txt);margin-top:0;max-width:24ch}
.ende{display:grid;grid-template-columns:7fr 5fr;gap:24px clamp(24px,4vw,64px);align-items:end;padding-bottom:clamp(88px,10vw,168px)}
.ende h2{font-size:var(--xl);margin:0}
.mo .home main section>*,.mo .home .tile{opacity:0;transform:translateY(24px);transition:opacity .6s ease,transform .7s cubic-bezier(.2,.7,.2,1)}
.mo .home main section.in>*,.mo .home section.in .tile{opacity:1;transform:none}
.mo .home section.in>*:nth-child(2),.mo .home section.in .tile:nth-child(2){transition-delay:.07s}
.mo .home section.in>*:nth-child(3),.mo .home section.in .tile:nth-child(3){transition-delay:.14s}
.mo .home section.in>*:nth-child(4),.mo .home section.in .tile:nth-child(4){transition-delay:.21s}
.mo .home section.in>*:nth-child(n+5),.mo .home section.in .tile:nth-child(n+5){transition-delay:.28s}
.mo .home .tiles{opacity:1!important;transform:none!important}
@media (prefers-reduced-motion:reduce){.puls .pb{animation:none}.home *{transition:none!important}}
@media (max-width:900px){.home main>.wrap{grid-template-columns:1fr}.home main>.wrap>.hero-acts{grid-column:1;justify-content:flex-start}
.tiles{grid-template-columns:1fr 1fr}.lr{grid-template-columns:1fr;gap:6px}.lp{text-align:left}
.panel,.stmt,.ende,.zit .zr{grid-template-columns:1fr}}
@media (max-width:600px){.tiles{grid-template-columns:1fr}.tile.w2{grid-column:auto}.home p,.home li{font-size:17px}
.home header.top .wrap{padding-top:10px;padding-bottom:10px}}
"""

# regler im hero und die eintritte der abschnitte. ohne skript bleibt alles
# sichtbar und der regler zeigt die laengste luecke (vom server gesetzt).
HOME_JS = """
<script>
(function(){var r=document.getElementById('puls-r'),o=document.getElementById('puls-o'),m=document.querySelector('.puls .pm'),j=document.getElementById('puls-d');
if(r&&o&&m&&j){var D=JSON.parse(j.textContent),M=['January','February','March','April','May','June','July','August','September','October','November','December'];
var z=function(n){return String(n).replace(/\\B(?=(\\d{3})+(?!\\d))/g,',')},p=function(n){return n<10?'0'+n:n};
var s=function(){var i=+r.value,e=D.d[i],t=new Date(e[1]*1000),x='Block '+z(D.h0+i)+', '+e[0]+' s after its parent by timestamp, '+t.getUTCDate()+' '+M[t.getUTCMonth()]+' '+t.getUTCFullYear()+', '+p(t.getUTCHours())+':'+p(t.getUTCMinutes())+' UTC.';
o.textContent=x;r.setAttribute('aria-valuetext',x);m.style.transform='translateX('+(i*4)+'px)';};r.addEventListener('input',s);}
var d=document.documentElement;if(location.hash||!('IntersectionObserver' in window)||matchMedia('(prefers-reduced-motion: reduce)').matches)return;
var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}});},{rootMargin:'0px 0px -8% 0px'});
var ss=document.querySelectorAll('.home main section');d.classList.add('mo');for(var k=0;k<ss.length;k++)io.observe(ss[k]);})();
</script>"""


def seiten():
    S = []
    up_meta, up = lies_upgrades()
    up_stand = max([e.get("checked", STAND) for e in up] + [up_meta.get("updated", STAND)])

    # 1 startseite, nach dem design-skill (Ben, 26.10.2026). Gleiche Aussagen,
    # Preise und Zahlen wie vorher, neu angeordnet. CSS und Skript nur hier.
    S.append(dict(
        datei="index.html", pfad="/", og="home", lastmod="2026-10-26",
        title="Independent blockchain measurement | PulseHawk",
        desc=("PulseHawk does its own blockchain measurement under load, with own nodes or "
              "header clients. Dated numbers, raw data and an open method for upgrades."),
        h1="Blockchains, measured under load",
        lead=("Independent measurement for foundations, core teams and grant committees. "
              "We count blocks, transactions and confirmation times ourselves, and publish "
              "dated numbers with raw data."),
        body="""
<p class="acts hero-acts">%s %s</p>
%s
<section><h2>What can we measure for you?</h2>
<p class="sub">We measure ourselves, with our own nodes or our own header clients, never from third party dashboards.</p>
<div class="lst">%s</div>
<p class="small">Custom scope, on request. %s</p>
</section>
<section><div class="tiles">
<div class="tile w2 acc"><h2>Which networks have we measured?</h2><p>We publish dated numbers, raw data and an open method.</p></div>
<div class="tile w2"><h3>Kaspa</h3><p>A network with a very high block rate, followed every day since August 2026 through our Kaspa media brand.</p><p>%s</p></div>
<div class="tile w2"><h3>Zcash NU7 on testnet</h3><div class="big">23.68 s</div><p class="small">Mean block interval, against a 25 s target</p><p>Network Upgrade 7 on the Zcash testnet, measured independently over 49,203 blocks up to 18 October 2026.</p>%s<p>%s</p></div>
%s
</div></section>
%s
<section><div class="panel"><div><h2>What is in a report?</h2>
<p>A short summary, the measurement window in UTC, charts, a table with median, p90 and p99, the method version and a CSV with every block we counted. Every number carries its date.</p>
<p class="acts">%s</p></div>
%s</div></section>
<section><div class="stmt"><h2>For foundations and grant committees</h2><div>
<p class="gross">A grant pays for the measurement, never for the result.</p>
<p>Ongoing measurement of a network works best as a public good. When a grant funds it, every result and its raw data are published openly, for the whole ecosystem, with the same method and the same rules as paid work.</p>
<p>The rules that make this hold are on our %s page. %s.</p>
</div></div></section>
<section class="ende"><h2>How do we start?</h2><div>
<p>Tell us the network, what you want measured and when. We reply from %s within one business day.</p>
<p class="acts">%s %s</p>
</div></section>
""" % (a("/contact", "Request a measurement", "btn"),
       a(SAMPLE_URL, "See a sample report", "btn ghost plausible-event-name=Sample+Report"),
       puls_figur(),
       leistungen(), PREIS_STAND,
       a("/cases/kaspa", "Read the Kaspa case"),
       zcash_fragment(), a("/zcash-nu7", "Read the Zcash NU7 case"),
       bch_kachel(),
       zitat_zeilen(lies_zitate(), hoechstens=3),
       a(SAMPLE_URL, "See a sample report", "btn ghost plausible-event-name=Sample+Report"),
       csv_fragment(),
       a("/independence", "independence"),
       a("/upgrade-monitoring", "How ongoing measurement works"),
       E(KONTAKT_MAIL), a("/contact", "Request a measurement", "btn"),
       a("mailto:" + KONTAKT_MAIL, E(KONTAKT_MAIL), "btn ghost")),
        faqs=[],
        schema=[],
        css=HOME_CSS, bodyclass="home", script=HOME_JS,
    ))

    # 2 tps
    tps_faq = [
        ("Why is measured TPS usually lower than claimed TPS?",
         "A claim often comes from a lab test with simple transfers on a few nodes close "
         "together. A public network carries mixed transactions over real distances. Both "
         "numbers can be honest, they just describe different conditions. We show both and name the conditions."),
        ("Can you verify a TPS claim on a network that is new to you?",
         "Yes. We set up our own node or header client for the job. The setup time is part of the agreed window."),
        ("Will the result be published?",
         "Yes. Results are published as measured. You see them before publication and can correct facts, not findings."),
    ]
    S.append(dict(
        datei="tps-verification.html", pfad="/tps-verification", og="tps-verification",
        title="TPS verification, claimed vs measured | PulseHawk",
        desc=("Independent TPS verification. We check a TPS claim against real network "
              "throughput in our own measurement and publish claimed vs measured, dated."),
        h1="Independent TPS verification, claimed vs measured",
        lead=("A TPS claim is a number from a test. We verify the TPS claim against what "
              "the network does in our own measurement, inside a dated window, and set real TPS vs "
              "claimed TPS side by side with the raw data."),
        body="""
<section><h2>How does a TPS verification work?</h2>
%s
</section>
<section><h2>What does it cost?</h2>
%s
<p>Longer windows or a measured testnet stress test are custom scope, on request.</p>
</section>
<section><h2>Is it the right fit?</h2>
%s
</section>
%s
<p class="cta">%s %s</p>
""" % (schritte([
            ("The claim.", "You send the TPS number and where it was published, a paper, a dashboard or a post."),
            ("The conditions.", "We write down what stands behind the claim, transaction type and size, number of nodes, network and date."),
            ("The measurement.", "We count ourselves, with our own node or header client, over an agreed window in UTC. Transactions per minute, blocks per second and confirmation time."),
            ("The note.", "You get a dated note with claimed and measured numbers next to each other, plus the CSV."),
        ]), preis_block("review"),
            box(["Teams that want to check their own TPS number before they publish it",
                 "Foundations and grant committees that need a neutral view of a claim",
                 "Exchanges and integrators that plan capacity"],
                ["Teams that need their code reviewed",
                 "Anyone who needs a number before the network runs",
                 "Questions about price or market"]),
            faq_html(tps_faq), sample_button(), contact_button()),
        faqs=tps_faq,
        schema=[service_schema("TPS verification", "/tps-verification",
                               "Claimed vs measured TPS from our own measurement, with dated raw data.", "review")],
    ))

    # 3 launch
    launch_faq = [
        ("Can you measure our testnet stress test?",
         "Yes. We watch the stress test with our own nodes or header clients and count what reaches the "
         "network. The load comes from your test, our part is the count."),
        ("How early should we book?",
         "Two weeks before launch is enough for most networks. That leaves time to set up our measurement and record the week before."),
        ("What if the launch date moves?",
         "The measurement moves with it. The price stays the same as long as the scope does."),
    ]
    S.append(dict(
        datei="launch-measurement.html", pfad="/launch-measurement", og="launch-measurement",
        title="Testnet and mainnet launch measurement | PulseHawk",
        desc=("Testnet stress test measurement and mainnet launch metrics. The first week "
              "after launch against the week before, from our own measurement, with raw data."),
        h1="Testnet and mainnet launch measurement",
        lead=("The first week after a launch shows how a network holds up under real "
              "load. We measure that week ourselves and set it against the week "
              "before, so your mainnet launch metrics come with a baseline."),
        body="""
<section><h2>What happens in the launch week?</h2>
%s
</section>
<section><h2>What do we count?</h2>
<p>Blocks per second and per minute, the block time distribution, transactions per minute, confirmation time, fees, stale and orphaned blocks and the propagation delay. The full list is in our %s.</p>
<p>For a new chain the week before is the last testnet week. For a testnet stress test measurement it is the quiet week before the test.</p>
</section>
<section><h2>What does it cost?</h2>
%s
</section>
<section><h2>Is it the right fit?</h2>
%s
</section>
%s
<p class="cta">%s %s</p>
""" % (schritte([
            ("Before.", "Our measurement runs from the week before launch and records a baseline."),
            ("Launch.", "We count through the first week after launch, block by block."),
            ("After.", "You get a before and after report with charts, the CSV and the method version."),
            ("Publication.", "Results are published as measured, after you have seen them."),
        ]), a("/method", "method"), preis_block("launch"),
            box(["Core teams launching a testnet or mainnet",
                 "Foundations that fund a launch and want an outside count",
                 "Teams planning a public testnet stress test"],
                ["Teams that need a code or security review",
                 "A count that has to stay private for good",
                 "Questions about price or market"]),
            faq_html(launch_faq), sample_button(), contact_button()),
        faqs=launch_faq,
        schema=[service_schema("Launch measurement", "/launch-measurement",
                               "The first week after a testnet or mainnet launch against the week before, from our own measurement.", "launch")],
    ))

    # 4 upgrade
    upg_faq = [
        ("How long before the upgrade should measurement start?",
         "Four weeks before activation gives a clean baseline. Shorter works too, the report then says how long the baseline was."),
        ("Do you cover the testnet activation as well?",
         "Yes, and it is often the better test, because problems show there first. Many teams book both."),
        ("Where can we see upcoming hard forks?",
         'In our <a href="/upgrades">network upgrade calendar</a>. Every entry links to its source.'),
    ]
    S.append(dict(
        datei="upgrade-monitoring.html", pfad="/upgrade-monitoring", og="upgrade-monitoring",
        title="Hard fork and network upgrade monitoring | PulseHawk",
        desc=("Hard fork monitoring from our own measurement. Block time, difficulty and orphaned "
              "blocks compared before and after a network upgrade, with dated raw data."),
        h1="Hard fork and network upgrade monitoring",
        lead=("A hard fork changes the rules a network runs on. Hard fork monitoring "
              "shows whether the change did what it set out to do. We measure block time, "
              "difficulty and orphaned blocks ourselves, before and after the upgrade."),
        body="""
<section><h2>What do we compare before and after the upgrade?</h2>
<ul class="list">
<li><b>Block time.</b> The distribution with median, p90, p99 and the longest gap between two blocks.</li>
<li><b>Difficulty.</b> How fast it follows a change in hashrate.</li>
<li><b>Stale and orphaned blocks.</b> How many valid blocks did not make the main chain.</li>
<li><b>Propagation.</b> The delay until a block reaches all of our measurement points.</li>
<li><b>Load.</b> Transactions per minute and fees.</li>
</ul>
<p>Every network upgrade before and after comparison uses two windows of the same length, both in UTC.</p>
</section>
<section><h2>How does ongoing measurement work?</h2>
%s
</section>
<section><h2>What does it cost?</h2>
%s
</section>
<section><h2>Is it the right fit?</h2>
%s
</section>
%s
<p class="cta">%s %s</p>
""" % (schritte([
            ("Baseline.", "Our measurement runs weeks before activation and records the old rules."),
            ("Activation.", "We follow the upgrade height block by block, on testnet and mainnet."),
            ("Monthly report.", "Each month you get a dated report with charts and the CSV."),
            ("Publication.", "Results are published as measured, after you have seen them."),
        ]), preis_block("ongoing", "A single upgrade without ongoing work is priced like a launch measurement."),
            box(["Core teams shipping a hard fork",
                 "Foundations and grant committees that track a network over time",
                 "Mining pools and exchanges that plan around an upgrade"],
                ["Teams that need their code reviewed",
                 "A one day snapshot",
                 "Questions about price or market"]),
            faq_html(upg_faq), sample_button(), contact_button()),
        faqs=upg_faq,
        schema=[service_schema("Upgrade monitoring", "/upgrade-monitoring",
                               "Block time, difficulty and orphaned blocks before and after a hard fork, from our own measurement.", "ongoing")],
    ))

    # 5 method
    m_faq = [
        ("What is a stale block rate?",
         "The share of valid blocks that did not end up in the main chain, in % of all "
         "blocks we saw in the window. If it rises after an upgrade, blocks reach parts of the network too late."),
        ("How do you measure propagation delay?",
         "Each of our measurement points records when a block first arrives. The gap between "
         "the first and the last point is the propagation delay for that block. We report median and p90 for the window."),
        ("Can we repeat your measurement?",
         "Yes. The method is on this page and the raw data is in the CSV. Two people with the same window should get the same numbers."),
    ]
    S.append(dict(
        datei="method.html", pfad="/method", og="method", lastmod="2026-10-23",
        title="How we measure blockchains | PulseHawk",
        desc=("Our open method. Block time distribution, stale block rate, propagation "
              "delay, confirmation time and fees, from our own measurement in dated windows."),
        h1="How we measure",
        lead=("Every number we publish comes from our own measurement, inside a stated window, "
              "with a method anyone can repeat. This page lists what we count, the rules we "
              "publish by and what falls outside our work. "
              '<span id="version">%s</span>.' % METHODE),
        body="""
%s
<section><h2>Where do the numbers come from?</h2>
<p>We measure ourselves, from full nodes we run or from our own header clients connected directly to network peers. Each report says which. We do not publish their addresses, hostnames or locations, so nobody can tune a network around our measurement.</p>
<p>Third party explorers serve as a cross check, never as the source of a published number.</p>
</section>
<section><h2>What is a measurement window?</h2>
<p>Each measurement has a fixed start and end in UTC, agreed before it starts. Before and after comparisons use two windows of the same length. Every published number names its window and the method version it was counted with.</p>
</section>
<section><h2>What do we count?</h2>
<ul class="list">
<li><b>Blocks per second and per minute.</b></li>
<li><b>Block time distribution.</b> Median, p90, p99 and the longest gap between two blocks.</li>
<li><b>Transactions per minute.</b></li>
<li><b>Confirmation and acceptance time.</b> From first sight of a transaction to its first block, and to the depth the network counts as final.</li>
<li><b>Fees.</b> Per transaction and per block.</li>
<li><b>Stale and orphaned blocks.</b> The stale block rate in %% of all blocks seen.</li>
<li><b>Propagation delay.</b> The gap between the first and the last of our measurement points to see a block.</li>
<li><b>Difficulty adjustment.</b> How fast difficulty follows a change in hashrate.</li>
</ul>
</section>
<section><h2>What are the rules we publish by?</h2>
<div class="rules">
<div><h3>No source, no number</h3><p>A number without its window and raw data does not get published. If we counted something ourselves, we show how.</p></div>
<div><h3>What happened, not why</h3><p>A chain shows what the network did. It does not show intent. We report blocks and transactions, readers draw their own conclusions.</p></div>
<div><h3>No price statements</h3><p>No price targets, no buy or sell calls, and no deals that would give us a reason for either.</p></div>
<div><h3>Public results stay free</h3><p>Published measurements and their raw data stay free to read and download.</p></div>
</div>
</section>
<section id="sample-report"><h2>What is in a report?</h2>
<ol class="steps">
<li><b>Summary.</b> The answer in a few sentences, with dates.</li>
<li><b>Window.</b> Start and end in UTC, network, node software versions.</li>
<li><b>Charts and tables.</b> Median, p90, p99 and the longest gap, before and after.</li>
<li><b>Method.</b> The method version used, with any deviation named.</li>
<li><b>Raw data.</b> A CSV with every block and timestamp we counted.</li>
</ol>
<p>%s</p>
</section>
<section><h2>What do we not do?</h2>
<p>We do not review or audit code. We do not audit security. We make no statements about prices. We do not run validators or mine for clients, and we never publish node IPs or hostnames.</p>
</section>
%s
<p class="cta">%s</p>
""" % (zitier_kasten("cite-method", "measurement method version 1", "2026-10-16",
                     "/method#version", verb="published"),
       "The first public sample report, Zcash NU7 on testnet, follows on 18 October 2026, 12:00 Berlin time."
       if not ZCASH_OFFEN else
       "The first public sample report is %s, published on 18 October 2026." % a("/zcash-nu7", "Zcash NU7 on testnet"),
       faq_html(m_faq), contact_button()),
        faqs=m_faq,
        schema=[],
    ))

    # 6 independence
    i_faq = [
        ("Can a client stop a result from being published?",
         "No. Clients see the result before publication and can correct facts, such as a "
         "wrong upgrade height or a node version. The findings stay as measured."),
        ("Do you accept payment in a client's token?",
         "Yes, and it is converted when it arrives. No one at PulseHawk holds a client's token, from offer to publication."),
        ("How can anyone check that a result is right?",
         "Every published number comes with its window, its method version and the raw data, so anyone can count again."),
    ]
    S.append(dict(
        datei="independence.html", pfad="/independence", og="independence", lastmod="2026-10-23",
        title="Our independence rules | PulseHawk",
        desc=("Four rules for every PulseHawk measurement. The price never depends on the "
              "result, no client tokens held, results published as measured, links named."),
        h1="How we stay independent",
        lead=("A measurement is only worth something if the result could have gone the "
              "other way. These four rules apply to every job, paid by a client or funded by a grant."),
        body="""
<section><h2>What are the rules?</h2>
<ol class="rules-list">
<li>Our price never depends on the result.</li>
<li>No one at PulseHawk holds a client's token, from offer to publication. Payments in a client's own token are converted when they arrive.</li>
<li>Results are published as measured. Clients see them before publication and can correct facts, not findings.</li>
<li>The same team runs Kaspa Pulse, a Kaspa media brand at %s.</li>
</ol>
</section>
<section><h2>Why does the price never depend on the result?</h2>
<p>The price is set in the offer, before the first block is counted. A good result costs the same as a bad one, and there is no bonus for either. That is the only way a client can trust a number they like, and a reader can trust a number the client paid for.</p>
</section>
<section><h2>What does the Kaspa Pulse link mean?</h2>
<p>Kaspa Pulse publishes on-chain and market data about Kaspa. When we measure Kaspa, every report names that link on its first page, so readers can weigh it themselves.</p>
</section>
<section><h2>What do we not do?</h2>
<p>We do not hold a client's token, we do not change findings after a client has seen them, and we do not sell placement in our calendar or on our case pages.</p>
</section>
%s
%s
<p class="cta">%s</p>
""" % (a("https://kaspapulse.com", "kaspapulse.com"),
       zitat_abschnitt(lies_zitate(), sid="cited-by"), faq_html(i_faq), contact_button()),
        faqs=i_faq,
        schema=[],
    ))

    # 7 upgrades
    u_faq = [
        ("Why does an upgrade show not set?",
         "Because the project has not announced a date or block height yet. The calendar only shows dates the project itself has published."),
        ("How often is the calendar updated?",
         "When a source changes. The date each entry was checked is part of the data, and the page shows when it last changed."),
    ]
    S.append(dict(
        datei="upgrades.html", pfad="/upgrades", og="upgrades", lastmod=up_stand,
        title="Network upgrade calendar | PulseHawk",
        desc=("Network upgrade calendar with upcoming hard forks across chains. Testnet and "
              "mainnet dates, status and the official source for every single entry."),
        h1="Network upgrade calendar",
        lead=("Upcoming hard forks and network upgrades across chains, each with the "
              "official source it comes from. A date shows as not set until the project "
              "announces one. Last checked on %s." % lang(up_stand)),
        body="""
<section><h2>Which upgrades are coming?</h2>
%s
<p class="note">%d entries, checked on %s. Around marks an estimated date, for example from an announced block height. Measured by us means we measured that upgrade ourselves and a case page follows.</p>
</section>
<section><h2>How does an upgrade get on this calendar?</h2>
<p>Only with a source from the project itself, a specification, release notes or an official announcement. Each source was checked on the date stated above, and a changed date replaces the old one on the same row.</p>
</section>
<section><h2>Want an upgrade measured?</h2>
<p>We compare block time, difficulty and orphaned blocks before and after activation. See %s.</p>
</section>
%s
<p class="cta">%s</p>
""" % (kalender_tabelle(up), len(up), lang(up_stand),
       a("/upgrade-monitoring", "upgrade monitoring"), faq_html(u_faq), contact_button()),
        faqs=u_faq,
        schema=["ARTICLE:2026-10-16:%s" % up_stand],
    ))

    # 8 zcash nu7, endzahlen vom 18.10.2026 (Ben). Alle Zahlen sind eigene
    # Messung; "expected" ist eine ideale Kette mit 25 s Mittel (Exponential-
    # verteilung): Median 25 ln2, p90 25 ln10, p99 25 ln100, ueber 75 s e^-3,
    # ueber 150 s e^-6, laengste Luecke etwa 25 (ln n + 0,577).
    pdf = os.path.exists(os.path.join(REPO, ZCASH_PDF))
    csv = os.path.exists(os.path.join(REPO, ZCASH_CSV))
    # Abschnitt aus #29, hier im Generator, damit ein Neubau ihn nicht loescht.
    # Darunter die Lizenzzeile (Ben, 22.10.2026). Die CSV selbst bleibt reine
    # Daten mit einer Spaltenzeile, ohne Kopftext.
    dl_teile = []
    if csv:
        dl_teile.append(
            '<p>The file comes from our own header client, which fetched every block header '
            'directly from testnet peers over P2P, checked the hash linkage and the proof of '
            'work against nBits, and compared 500 hashes with two further Zebra peers. It does '
            'not check block contents or Equihash solutions, and it does not come from nodes '
            'of our own.</p>\n<ul class="list">\n'
            '<li><b>height</b> is the block height on the Zcash testnet, from 4,465,026 to '
            '4,514,228.</li>\n'
            '<li><b>timestamp</b> is the block header timestamp in Unix seconds, which count '
            'in UTC.</li>\n'
            '<li><b>interval_s</b> is that timestamp minus the timestamp of the parent block, '
            'in seconds. It stays empty for 4,465,026, because the first counted interval is '
            'that of 4,465,027.</li>\n</ul>\n'
            '<p class="cta"><a class="btn plausible-event-name=CSV+Download" href="/%s" '
            'download>Download CSV, 49,203 blocks, about 1 MB</a></p>\n'
            '<p class="small">Data from PulseHawk, licensed CC BY 4.0. Cite as PulseHawk '
            '(2026), Zcash NU7 testnet block intervals, cut-off 18 October 2026.</p>\n'
            '<p class="src" style="overflow-wrap:anywhere">Our own measurement, Zcash NU7 '
            'testnet, headers from testnet peers, blocks 4,465,026 to 4,514,228, snapshot 18 '
            'October 2026, 06:00 UTC. SHA-256 %s.</p>' % (ZCASH_CSV, ZCASH_CSV_SHA256))
    if pdf:
        dl_teile.append('<p class="cta">%s</p>' % a("/" + ZCASH_PDF, "Download the sample report (PDF)",
                                                   "btn plausible-event-name=PDF+Download"))
    downloads = ('<section id="download"><h2>Download the raw intervals</h2>\n%s\n</section>'
                 % "\n".join(dl_teile)) if dl_teile else ""
    # CSV-zeile im zitierkasten, mit derselben klasse wie der download-knopf,
    # damit Plausible sie als CSV Download zaehlt
    z_csv = ('<a class="plausible-event-name=CSV+Download" href="/%s" download>Download the CSV</a>, '
             '49,203 blocks up to 18 October 2026, licensed CC BY 4.0.' % ZCASH_CSV) if csv else ""
    quelle = ('<p class="src">Our own measurement, Zcash NU7 testnet, headers from testnet '
              'peers, blocks 4,465,026 to 4,514,228, snapshot 18 October 2026, 06:00 UTC.</p>')
    z_faq = [
        ("Is the Zcash NU7 testnet producing 25 second blocks?",
         "Yes, close to it. Up to 18 October 2026, 06:00 UTC the mean block interval was "
         "23.68 s over 49,203 blocks, and median, p90 and p99 sat a few seconds below an "
         "ideal 25 s chain."),
        ("Do shorter blocks mean more orphaned blocks?",
         "In our listener window on 17 October 2026, 14:51 to 20:21 UTC, 5 of 780 announced "
         "blocks did not land in the chain, 0.64%, each at depth 1."),
        ("How many confirmations match the old 10 at 75 s?",
         "Thirty blocks at 25 s take the same 750 s on average as ten blocks at 75 s. Measured, "
         "they spanned a median of 730 s and a p99 of 1,187 s, well below the 1,409 s for ten "
         "blocks at 75 s."),
    ]
    S.append(dict(
        datei="zcash-nu7.html", pfad="/zcash-nu7", og="zcash-nu7", lastmod="2026-10-23",
        title="Zcash NU7 on testnet, block times measured | PulseHawk",
        desc=("Zcash testnet after NU7, block times measured independently from testnet "
              "headers. Mean 23.68 s vs 25 s over 49,203 blocks, p90, p99, longest gap."),
        h1="Zcash NU7 on testnet, block times measured",
        lead=("Yes, the Zcash testnet after NU7 runs close to 25 second blocks. Over the 49,203 "
              "testnet blocks since activation the mean interval was 23.68 s against the 25 s target, and the "
              "spread stayed close to an ideal 25 s chain, apart from one gap of 451 s. Measured "
              "independently up to 18 October 2026, 06:00 UTC, with 500 of 500 sampled hashes "
              "matching two Zebra peers."),
        body="""
<section><h2>Does NU7 hit 25 second blocks on testnet?</h2>
<p>Yes. The mean interval was 23.68 s, so blocks came about 5%% faster than the target. The median of 17.0 s is what a 25 s chain should show, because most blocks arrive early and a few arrive late.</p>
<div class="tablewrap"><table class="nums"><thead><tr><th scope="col">Block interval</th><th scope="col">Measured</th><th scope="col">Expected at 25 s</th></tr></thead><tbody>
<tr id="mean"><td class="c">Mean</td><td>23.68 s</td><td>25 s</td></tr>
<tr id="median"><td class="c">Median</td><td>17.0 s</td><td>17.3 s</td></tr>
<tr id="p90"><td class="c">p90</td><td>52 s</td><td>57.6 s</td></tr>
<tr id="p99"><td class="c">p99</td><td>109 s</td><td>115.1 s</td></tr>
<tr id="over-75s"><td class="c">Over 75 s</td><td>3.59%%</td><td>4.98%%</td></tr>
<tr id="over-150s"><td class="c">Over 150 s</td><td>0.203%%</td><td>0.248%%</td></tr>
<tr id="longest-gap"><td class="c">Longest gap</td><td>451 s</td><td>about 284 s</td></tr>
</tbody></table></div>
<p class="note">Expected means an ideal chain with a 25 s mean, where intervals follow an exponential distribution.</p>
%s
%s
</section>
<section id="slow-blocks"><h2>How often is a block slower than the old 75 s target?</h2>
<p>In 3.59%% of intervals, against 4.98%% for an ideal 25 s chain. Before NU7 the target itself was 75 s. Gaps over 150 s came in 0.203%% of intervals, against 0.248%% expected.</p>
<p>The longest gap was 451 s, longer than the roughly 284 s an ideal chain would show over the same number of blocks. No block timestamp went backwards.</p>
%s
</section>
<section id="difficulty"><h2>How fast does difficulty follow hashrate?</h2>
<p>We found 6 hashrate jumps of 2x or more, and 5 of them caught up. The other one was followed by the next jump 200 blocks later, before it could catch up. For those five the difficulty came within ±15 %% of the new level after a median of 960 blocks, or about 2.7 hours when measured in time, and the longest catch-up took 1,839 blocks.</p>
%s
</section>
<section id="confirmations"><h2>How long do confirmations take?</h2>
<p>Thirty blocks at 25 s spanned a median of 730 s and a p99 of 1,187 s. For perfect 25 s blocks the p99 would be about 1,105 s, so the measured value sits above that, partly because of the hashrate jumps (1,154 s without the windows around them), and still well below the 1,409 s for ten blocks at 75 s.</p>
%s
</section>
<section id="orphaned"><h2>How many blocks were orphaned?</h2>
<p>From 17 October 2026, 14:51 to 20:21 UTC our listener recorded every block announced to it. Five of the 780 did not land in the chain, 0.64%%, and each of them at depth 1.</p>
<p class="src">Our own listener, Zcash NU7 testnet, window 17 October 2026, 14:51 to 20:21 UTC.</p>
</section>
<section><h2>How we measured</h2>
<p>Our own header client followed the Zcash testnet from the NU7 activation at block 4,465,026 to block 4,514,228, the snapshot of 18 October 2026, 06:00 UTC, fetching headers directly from testnet peers and checking hash linkage and proof of work. That is 49,203 blocks. We checked 500 of them against two Zebra peers, and all 500 hashes matched, so we saw no fork in the blocks we compared.</p>
<p>Intervals come from consecutive block timestamps. Method in %s, version 1.</p>
</section>
%s
%s
<p class="cta">%s</p>
""" % (quelle, zitier_kasten("cite-zcash", "Zcash NU7 testnet block intervals", "2026-10-18",
                            "/zcash-nu7#mean", csv=z_csv),
       quelle, quelle, quelle, a("/method", "How we measure"), downloads,
       faq_html(z_faq), contact_button("Request a measurement for your upgrade")),
        faqs=z_faq,
        schema=["ARTICLE:2026-10-18:2026-10-23", {
            "@type": "Dataset",
            "name": "Zcash NU7 testnet block intervals",
            "description": ("Block intervals on the Zcash testnet from the NU7 activation at "
                            "block 4,465,026 to block 4,514,228, 49,203 blocks, measured by "
                            "PulseHawk from testnet block headers, snapshot 18 October 2026 06.00 UTC. Mean, "
                            "median, p90, p99, share over 75 s and 150 s, longest gap, "
                            "difficulty response and orphaned blocks."),
            "url": SITE + "/zcash-nu7",
            "creator": {"@id": ORG_ID},
            "isAccessibleForFree": True,
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "datePublished": "2026-10-18",
            "temporalCoverage": "../2026-10-18T06:00:00Z",
            "measurementTechnique": ("Own header client fetching headers directly from testnet "
                                     "peers over P2P, hash linkage and proof of work checked, "
                                     "timestamps of consecutive blocks, 500 hashes compared "
                                     "with two Zebra peers"),
            "variableMeasured": ["block interval", "difficulty", "orphaned blocks"],
            "keywords": ["zcash nu7 block time", "zcash 25 second blocks", "nu7 testnet"],
            # die CSV erst, wenn sie unter reports/ liegt
            **({"distribution": {"@type": "DataDownload", "encodingFormat": "text/csv",
                                 "contentUrl": SITE + "/" + ZCASH_CSV}} if csv else {}),
        }],
        noindex=not ZCASH_OFFEN,
    ))

    # 9 kaspa
    k_faq = [
        ("Is Kaspa Pulse part of PulseHawk?",
         "The same team runs both. Kaspa Pulse is a media brand for Kaspa, PulseHawk measures networks across all chains."),
        ("Can we book a Kaspa measurement?",
         "Yes, under the same rules as any other network. The link to Kaspa Pulse is named on the report."),
    ]
    S.append(dict(
        datei="cases/kaspa.html", pfad="/cases/kaspa", og="kaspa",
        title="Kaspa network measurements | PulseHawk",
        desc=("Kaspa block rate and fees against new issuance, every number dated and marked "
              "as our own measurement or as a series we take over, with links to raw data."),
        h1="Kaspa network measurements",
        lead=("Kaspa is the network we have followed longest, every day since August 2026, "
              "through our media brand Kaspa Pulse at kaspapulse.com. Every number on this page "
              "carries its date and is marked either measured, by us, or source, "
              "a series we take over and name."),
        body="""
<section><h2>How fast does Kaspa produce blocks?</h2>
<p>Kaspa runs at 10 blocks per second since the Crescendo upgrade in 2025. At that rate a block time distribution is counted in tenths of a second, and the longest gap matters more than the median.</p>
<p class="src">Source %s, protocol block rate, checked 16 October 2026.</p>
</section>
<section><h2>How do fees compare with new issuance?</h2>
<p>In the 30 days from 12 September to 11 October 2026, Kaspalytics counted 68,493 KAS in transaction fees. In the same 30 days the emission schedule created 55,848,455 new KAS, about 815 times the fees.</p>
<p class="src">Source Kaspalytics for the fees, a series taken over in the Kaspa Pulse daily log of 12 October 2026, %s. New coins from the emission schedule, arithmetic, not a count.</p>
</section>
<!-- PLATZ FUER DEN TESTNET-STURM 11.10.2026, bewusst leer (Ben, 16.10.2026).
     Nur mit Quelle: Zaehlbericht vom 11.10., 07:30 bis 12:29 UTC, zwei eigene Knoten,
     auf kaspa-pulse messung/tn10-zaehler. Stand 16.10.2026 liegt dort kein Bericht,
     nur Zaehler und Fenster. Dann als section "What happened on the Kaspa testnet on
     11 October 2026?", jede Zahl mit "measured" und dem Bericht als Quelle. -->
<section><h2>Where can I follow Kaspa?</h2>
<p>Daily numbers, the weekly reading and the cheat sheet are on %s. PulseHawk measures Kaspa under the same %s as every other network.</p>
</section>
%s
<p class="cta">%s %s</p>
""" % (a("https://kaspapulse.com/kaspa-hashrate.html", "kaspapulse.com, Kaspa hashrate page"),
       a("https://github.com/neoalphavault-png/kaspa-pulse/blob/main/data/tagesgrafik-log.json", "raw data"),
       a("https://kaspapulse.com", "kaspapulse.com"), a("/independence", "rules"),
       faq_html(k_faq), sample_button(), contact_button()),
        faqs=k_faq,
        schema=["ARTICLE:2026-10-16:2026-10-16"],
        crumbs=[("Kaspa", "/cases/kaspa")],
    ))

    # 10 contact
    c_faq = [
        ("What happens after I send the form?",
         "We reply from hello@pulsehawk.io within one business day, with questions or a written offer."),
        ("Do I need a fixed budget?",
         "No. The range helps us suggest a scope, and not sure yet is a fine answer."),
    ]
    if BREVO_FORM_URL:
        # mit Brevo zaehlt der Tracker das Absenden ueber die Klasse, genau
        # einmal. BREVO_JS schickt das Formular per fetch und zeigt die
        # Erfolgsmeldung hier auf der Seite, statt auf eine Brevo-Seite zu
        # wechseln. Es meldet selbst kein Ereignis, sonst zaehlte es doppelt.
        form_open = ('<form id="kontakt" class="form plausible-event-name=Contact+Form" method="post" '
                     'action="%s" data-brevo>' % E(BREVO_FORM_URL, quote=True))
    else:
        # ohne Brevo traegt das Formular KEINE Klasse: MAILTO_JS haelt das
        # Absenden an, meldet "Contact Form" selbst und oeffnet das
        # Mailprogramm. Klasse und eigener Aufruf zusammen zaehlten doppelt.
        form_open = ('<form class="form" method="post" '
                     'enctype="text/plain" action="mailto:%s?subject=Measurement%%20request" '
                     'data-mailto="%s">' % (E(KONTAKT_MAIL), E(KONTAKT_MAIL)))
    budgets = ["Under 1,000 €", "1,000 to 2,500 €", "2,500 to 5,000 €",
               "5,000 to 15,000 €", "Over 15,000 €", "Not sure yet"]
    S.append(dict(
        datei="contact.html", pfad="/contact", og="contact",
        title="Request a measurement | PulseHawk",
        desc=("Request an independent blockchain measurement. Tell us network, scope, timing "
              "and budget. We reply to each request by email within one business day."),
        h1="Request a measurement",
        lead=("Four questions and your email. Tell us which network, what you want measured "
              "and when, and we answer with questions or an offer. You can also write to %s."
              % a("mailto:" + KONTAKT_MAIL, E(KONTAKT_MAIL))),
        body="""
<section><h2>What should we measure?</h2>
%s
<label for="f-network">Network</label>
<input id="f-network" name="NETWORK" type="text" maxlength="200" required autocomplete="off" placeholder="Zcash testnet, Kaspa mainnet">
<label for="f-scope">What to measure</label>
<textarea id="f-scope" name="SCOPE" rows="4" maxlength="200" required placeholder="A TPS claim, a launch week, an upcoming hard fork"></textarea>
<label for="f-when">When</label>
<input id="f-when" name="TIMING" type="text" maxlength="200" required placeholder="Launch on 3 December 2026">
<label for="f-budget">Budget range</label>
<select id="f-budget" name="BUDGET" required><option value="">Choose a range</option>%s</select>
<label for="f-email">Your email</label>
<input id="f-email" name="EMAIL" type="email" required autocomplete="email">
<input type="text" name="email_address_check" value="" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true">
<input type="hidden" name="locale" value="en">
<input type="hidden" name="html_type" value="simple">
<button type="submit" class="btn">Send request</button>
<p class="small">We use your details only to answer this request. See %s.</p>
</form>
<div id="f-ok" class="okmsg" role="status" tabindex="-1" hidden><b>Thank you.</b> Your request has arrived. We reply from %s within one business day.</div>
<p id="f-err" class="errmsg" role="alert" hidden>Your request did not go through. Please try again or write to %s.</p>
</section>
<section><h2>Who is your contact?</h2>
<div class="person"><img src="/hawk.png" alt="" width="48" height="51" loading="lazy"><div><b>Your contact</b><br>Ben, founder<br>%s · %s</div></div>
</section>
%s
""" % (form_open, "".join('<option>%s</option>' % b for b in budgets),
       a("/datenschutz.html", "privacy"), E(KONTAKT_MAIL), a("mailto:" + KONTAKT_MAIL, E(KONTAKT_MAIL)),
       a("https://x.com/gokugalax", "x.com/gokugalax"),
       a("mailto:" + KONTAKT_MAIL, E(KONTAKT_MAIL)), faq_html(c_faq)),
        faqs=c_faq,
        schema=[],
        script=BREVO_JS if BREVO_FORM_URL else MAILTO_JS,
    ))

    # 12/13 rechtliches, inhalt wie bisher, absender pulsehawk.io
    S.append(dict(
        datei="impressum.html", pfad="/impressum.html", og="home",
        title="Impressum, legal notice | PulseHawk",
        desc="Legal notice for pulsehawk.io under Section 5 DDG. Vizora Digital UG, Düsseldorf.",
        h1="Legal notice",
        lead="Impressum, information required under German law, Section 5 DDG.",
        body=IMPRESSUM % {"mail": a("mailto:" + KONTAKT_MAIL, E(KONTAKT_MAIL))},
        faqs=[], schema=[], noindex=True, legal=True,
    ))
    S.append(dict(
        datei="datenschutz.html", pfad="/datenschutz.html", og="home",
        title="Datenschutz, privacy policy | PulseHawk",
        desc="Privacy policy for pulsehawk.io. Hosting, contact form, cookieless Plausible analytics.",
        h1="Privacy policy",
        lead="Datenschutzerklärung. Last updated on 16 October 2026.",
        body=DATENSCHUTZ % {"mail": a("mailto:" + KONTAKT_MAIL, E(KONTAKT_MAIL))},
        faqs=[], schema=[], noindex=True, legal=True,
    ))
    return S


MAILTO_JS = """
<script>
(function(){var f=document.querySelector('form[data-mailto]');if(!f)return;
f.addEventListener('submit',function(e){e.preventDefault();if(!f.reportValidity())return;
var g=function(n){var x=f.elements[n];return x?x.value:'';};
if(window.plausible)window.plausible('Contact Form');
var b='Network '+g('NETWORK')+'\\nWhat to measure '+g('SCOPE')+'\\nWhen '+g('TIMING')+'\\nBudget '+g('BUDGET')+'\\nEmail '+g('EMAIL');
location.href='mailto:'+f.getAttribute('data-mailto')+'?subject='+encodeURIComponent('Measurement request')+'&body='+encodeURIComponent(b);});})();
</script>"""

# Brevo per fetch an die Action-URL mit isAjax=1, wie Brevos eigenes
# Formularskript. Erfolg, wenn die Antwort lesbar ist und nicht
# success false meldet. Bei einem Fehler bleibt das Formular stehen und
# nennt die Mailadresse; es wird nie ein zweites Mal von selbst geschickt,
# damit kein Kontakt doppelt ankommt. Ohne fetch schickt der Browser das
# Formular klassisch ab (dann mit Brevos eigener Seite).
BREVO_JS = """
<script>
(function(){var f=document.querySelector('form[data-brevo]');if(!f||!window.fetch||!window.URLSearchParams)return;
var ok=document.getElementById('f-ok'),err=document.getElementById('f-err'),btn=f.querySelector('button[type=submit]');
f.addEventListener('submit',function(e){e.preventDefault();if(btn.disabled)return;btn.disabled=true;err.hidden=true;
var u=f.action+(f.action.indexOf('?')<0?'?':'&')+'isAjax=1';
fetch(u,{method:'POST',body:new URLSearchParams(new FormData(f)),mode:'cors',credentials:'omit'})
.then(function(r){return r.text().then(function(t){var j=null;try{j=JSON.parse(t)}catch(x){}if(!r.ok||(j&&j.success===false))throw new Error('brevo');});})
.then(function(){f.hidden=true;ok.hidden=false;ok.focus();},function(){err.hidden=false;btn.disabled=false;});});})();
</script>"""

# Knopf "copy" im zitierkasten. Erst die Clipboard-API (Chrome, Safari ab
# 13.1, im Klick selbst aufgerufen), sonst ein unsichtbares Textfeld mit
# execCommand. Klappt beides nicht, bleibt der Satz markiert zum Kopieren.
KOPIER_JS = """
<script>
(function(){var bs=document.querySelectorAll('button[data-copy]');
function zeig(b,ok){var s=b.parentNode.querySelector('.vh');b.textContent=ok?'copied':'copy';if(s)s.textContent=ok?'Copied to clipboard':'';if(ok)setTimeout(function(){zeig(b,false)},2000)}
function mark(c){var r=document.createRange();r.selectNodeContents(c);var g=window.getSelection();g.removeAllRanges();g.addRange(r)}
function alt(t,b,c){var x=document.createElement('textarea'),ok=false;x.value=t;x.setAttribute('readonly','');x.style.cssText='position:fixed;top:0;left:0;opacity:0';document.body.appendChild(x);x.select();x.setSelectionRange(0,t.length);try{ok=document.execCommand('copy')}catch(e){}document.body.removeChild(x);b.focus();if(ok)zeig(b,true);else mark(c)}
for(var i=0;i<bs.length;i++)bs[i].addEventListener('click',function(){var b=this,c=document.getElementById(b.getAttribute('data-copy')),t=c.textContent;
if(navigator.clipboard&&navigator.clipboard.writeText&&window.isSecureContext){navigator.clipboard.writeText(t).then(function(){zeig(b,true)},function(){alt(t,b,c)})}else alt(t,b,c)})})();
</script>"""

IMPRESSUM = """
<section><h2>Site operator</h2>
<address><b>Vizora Digital UG (haftungsbeschränkt)</b><br>Marc-Chagall-Straße 54<br>40477 Düsseldorf<br>Germany</address>
<p>PulseHawk is a brand of Vizora Digital UG (haftungsbeschränkt).</p>
</section>
<section><h2>Represented by</h2><p>Managing Director Benjamin Alkanli</p></section>
<section><h2>Contact</h2><p>Email %(mail)s</p></section>
<section><h2>Commercial register</h2>
<p>Registered in the German commercial register (Handelsregister).<br>Register court Amtsgericht Düsseldorf<br>Registration number HRB 112321</p></section>
<section><h2>VAT ID</h2><p>VAT identification number pursuant to Section 27a of the German VAT Act (UStG) DE461539305</p></section>
<section><h2>Responsible for content, Section 18 (2) MStV</h2><p>Benjamin Alkanli<br>Marc-Chagall-Straße 54<br>40477 Düsseldorf, Germany</p></section>
<section><h2>EU dispute resolution</h2>
<p>The European Commission provides a platform for online dispute resolution at <a href="https://ec.europa.eu/consumers/odr/" rel="noopener">ec.europa.eu/consumers/odr</a>. We are neither willing nor obliged to participate in dispute resolution proceedings before a consumer arbitration board.</p></section>
<section><h2>Liability for content</h2>
<p>As a service provider, we are responsible for our own content on these pages in accordance with general law. However, we are not obliged to monitor transmitted or stored third party information or to investigate circumstances that indicate illegal activity. Obligations to remove or block the use of information under general law remain unaffected.</p></section>
<section><h2>Liability for links</h2>
<p>This site contains links to external third party websites over whose content we have no control. We therefore cannot accept any liability for such external content. The respective provider or operator of the linked pages is always responsible for their content.</p></section>
<section><h2>Copyright</h2>
<p>The content and works created by the site operator on these pages are subject to German copyright law. Reproduction, editing, distribution and any kind of use beyond the limits of copyright law require the written consent of the respective author or creator.</p></section>
<section><h2>No investment advice</h2>
<p>All content on pulsehawk.io is provided for informational purposes only. It does not constitute financial, investment, legal or tax advice, and it is not a recommendation to buy or sell any asset.</p></section>
"""

DATENSCHUTZ = """
<section><h2>1. Controller</h2>
<address><b>Vizora Digital UG (haftungsbeschränkt)</b><br>Marc-Chagall-Straße 54<br>40477 Düsseldorf, Germany<br>Email %(mail)s</address>
<p>pulsehawk.io is the site of PulseHawk, a brand of Vizora Digital UG that measures how blockchains behave under load. This policy explains what personal data is processed when you use it, under the EU General Data Protection Regulation (GDPR).</p>
</section>
<section><h2>2. Hosting on GitHub Pages</h2>
<p>This website is hosted on GitHub Pages, a service of GitHub, Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, USA. When you visit the site, GitHub collects technically necessary data, in particular your IP address, in server logs in order to deliver the website and keep the service secure. We have no access to these logs and do not analyze them.</p>
<p>Legal basis is Art. 6 (1)(f) GDPR, our legitimate interest in providing the website securely and efficiently. GitHub is certified under the EU U.S. Data Privacy Framework. More in the <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement" rel="noopener">GitHub Privacy Statement</a>.</p>
</section>
<section><h2>3. Analytics with Plausible, without cookies</h2>
<p>We count visits with Plausible Analytics, a service of Plausible Insights OÜ, Västriku tn 2, 50403 Tartu, Estonia. Plausible runs on servers in the EU, sets no cookies and stores no personal data. Your IP address is only used to form a daily changing anonymous identifier and is not stored. No data is shared with third parties or used for advertising, and visitors cannot be identified or followed across websites.</p>
<p>We count page views and a few events, a click on See a sample report, a download of a PDF or CSV file, a sent contact form and a click on a link to another website. Legal basis is Art. 6 (1)(f) GDPR, our legitimate interest in knowing which pages are used. More in the <a href="https://plausible.io/data-policy" rel="noopener">Plausible data policy</a>.</p>
</section>
<section><h2>4. Contact form and email</h2>
<p>If you send the contact form or write to us, we process your email address and what you tell us about your project, only to answer your request. The contact form is sent through Brevo, a service of Brevo GmbH, Köpenicker Straße 126, 10179 Berlin, Germany, which transmits and stores your entries on our behalf in our contact list.</p>
<p>Legal basis is Art. 6 (1)(b) GDPR, steps prior to entering into a contract, and Art. 6 (1)(f) GDPR. We delete the data when the request is closed and no retention duty applies. More in the <a href="https://www.brevo.com/legal/privacypolicy/" rel="noopener">Brevo privacy policy</a>.</p>
</section>
<section><h2>5. Fonts</h2>
<p>All fonts are served from pulsehawk.io itself. No request goes to a font provider.</p>
</section>
<section><h2>6. SSL encryption</h2>
<p>This website uses SSL/TLS encryption. Data you send to us cannot be read by third parties in transit.</p>
</section>
<section><h2>7. Cookies</h2>
<p>This website uses <b>no cookies</b>.</p>
</section>
<section><h2>8. Your rights</h2>
<p>Regarding your personal data, you have the right to access (Art. 15 GDPR), rectification (Art. 16 GDPR), erasure (Art. 17 GDPR), restriction of processing (Art. 18 GDPR), data portability (Art. 20 GDPR), to object to processing (Art. 21 GDPR) and to withdraw consent with effect for the future (Art. 7 (3) GDPR). To exercise any of these rights, email %(mail)s.</p>
</section>
<section><h2>9. Right to lodge a complaint</h2>
<p>You have the right to lodge a complaint with a data protection supervisory authority. The authority responsible for us is the State Commissioner for Data Protection and Freedom of Information of North Rhine Westphalia (LDI NRW), <a href="https://www.ldi.nrw.de" rel="noopener">www.ldi.nrw.de</a>. You may also contact the supervisory authority of your own EU member state.</p>
</section>
<section><h2>10. Changes</h2>
<p>We may update this privacy policy if the legal situation or this website changes. The version published here always applies.</p>
</section>
"""


# --- gestalt -------------------------------------------------------------

CSS = """
@font-face{font-family:Archivo;font-weight:800;font-style:normal;font-display:swap;src:url(/assets/fonts/archivo-latin-800-normal.woff2) format('woff2')}
@font-face{font-family:'IBM Plex Sans';font-weight:400;font-style:normal;font-display:swap;src:url(/assets/fonts/ibm-plex-sans-latin-400-normal.woff2) format('woff2')}
@font-face{font-family:'IBM Plex Sans';font-weight:600;font-style:normal;font-display:swap;src:url(/assets/fonts/ibm-plex-sans-latin-600-normal.woff2) format('woff2')}
@font-face{font-family:'IBM Plex Mono';font-weight:400;font-style:normal;font-display:swap;src:url(/assets/fonts/ibm-plex-mono-latin-400-normal.woff2) format('woff2')}
:root{--bg:#080B0F;--card:#0D1116;--line:#1C2228;--txt:#F2F5F4;--dim:#A9B7B4;--teal:#49EACB;--mono:'IBM Plex Mono',ui-monospace,Menlo,monospace}
*{box-sizing:border-box;margin:0;padding:0}
[hidden]{display:none!important}
html{-webkit-text-size-adjust:100%}
body{background:var(--bg);color:var(--txt);font:400 16px/1.6 'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',sans-serif}
a{color:var(--teal)}
a:focus-visible,summary:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:2px solid var(--teal);outline-offset:2px}
.skip{position:absolute;left:-9999px}.skip:focus{left:16px;top:8px;background:var(--teal);color:#080B0F;padding:6px 10px;z-index:9}
.wrap{max-width:860px;margin:0 auto;padding:0 20px}
header.top{border-bottom:1px solid var(--line)}
header.top .wrap{display:flex;align-items:center;justify-content:space-between;gap:16px;padding-top:14px;padding-bottom:14px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--txt);font:800 20px/1 Archivo,sans-serif;letter-spacing:.2px}
.brand img{width:30px;height:32px}
nav.main ul{list-style:none;display:flex;gap:4px 16px;flex-wrap:wrap}
nav.main a{color:var(--dim);text-decoration:none;font-size:14px;padding:6px 0;display:inline-block}
nav.main a:hover,nav.main a[aria-current]{color:var(--teal)}
nav.main a.nc{color:var(--teal);font-weight:600}
main{padding:44px 0 24px}
.crumbs{font-size:13px;color:var(--dim);margin-bottom:18px}.crumbs a{color:var(--dim)}
h1{font:800 clamp(30px,5.4vw,46px)/1.12 Archivo,sans-serif;letter-spacing:-.5px;max-width:20ch}
.lead{font-size:18px;line-height:1.6;color:var(--txt);margin-top:18px;max-width:64ch}
h2{font:800 23px/1.25 Archivo,sans-serif;margin:46px 0 14px;letter-spacing:-.2px}
h3{font-size:16px;font-weight:600;color:var(--txt)}
p{color:var(--dim);margin-top:12px;max-width:68ch}
p b,li b{color:var(--txt);font-weight:600}
.note,.src,.small{font-size:14px}
.src{font-family:var(--mono);font-size:12.5px;color:var(--dim)}
.chips{list-style:none;display:flex;flex-wrap:wrap;gap:8px;margin-top:24px}
.chips li{font:400 13px var(--mono);color:var(--teal);border:1px solid rgba(73,234,203,.35);border-radius:999px;padding:5px 12px}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px}
.cards.two{grid-template-columns:repeat(2,1fr)}.cards.one{grid-template-columns:1fr}
.card{display:flex;flex-direction:column;gap:8px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;text-decoration:none}
.card:hover{border-color:rgba(73,234,203,.5)}
.ct{font-weight:600;color:var(--txt);font-size:16px}.cd{color:var(--dim);font-size:14.5px;line-height:1.55;flex:1}
.cp{font:400 13px var(--mono);color:var(--teal)}
.btn{display:inline-block;background:var(--teal);color:#06110E;font-weight:600;text-decoration:none;border-radius:8px;padding:11px 18px;font-size:15px;border:1px solid var(--teal);cursor:pointer;font-family:inherit;margin:4px 8px 4px 0}
.btn:hover{filter:brightness(1.08)}
.btn.ghost{background:transparent;color:var(--teal)}
.btn.off{opacity:.55;cursor:default}
.cta{margin-top:22px}
.steps,.list,.rules-list{margin:12px 0 0 22px;color:var(--dim)}
.steps li,.list li,.rules-list li{margin-top:8px;max-width:68ch}
.rules-list li{color:var(--txt);font-size:17px;padding-left:4px}
.rules{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px}
.rules>div,.price,.fit>div{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.rules p{font-size:14.5px;margin-top:6px}
.price{border-color:rgba(73,234,203,.4)}.pl{font:400 12px var(--mono);color:var(--dim);text-transform:uppercase;letter-spacing:1px}
.pv{font:800 26px/1.2 Archivo,sans-serif;margin-top:6px}.price p{font-size:14px}
.fit{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.fit ul{margin:8px 0 0 18px;color:var(--dim);font-size:14.5px}.fit li{margin-top:6px}
.faq details{border-top:1px solid var(--line);padding:12px 0}
.faq details:last-child{border-bottom:1px solid var(--line)}
.faq summary{cursor:pointer;list-style:none}.faq summary::-webkit-details-marker{display:none}
.faq summary h3{display:inline;font-size:16px}
.faq summary::after{content:"+";float:right;color:var(--teal);font-family:var(--mono)}
.faq details[open] summary::after{content:"\\2212"}
.tablewrap{overflow-x:auto;margin-top:14px;border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;width:100%;font-size:14px;min-width:720px}
th{font:400 12px var(--mono);color:var(--dim);text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);text-transform:uppercase;letter-spacing:.5px}
td{padding:11px 12px;border-bottom:1px solid var(--line);color:var(--dim);vertical-align:top}
td.c{color:var(--txt);font-weight:600}tr:last-child td{border-bottom:0}
table.nums{min-width:0}
.form{display:grid;gap:6px;max-width:560px;margin-top:8px}
.form label{font-size:14px;color:var(--txt);margin-top:10px;font-weight:600}
.form input,.form select,.form textarea{background:var(--card);color:var(--txt);border:1px solid #2A333B;border-radius:8px;padding:11px 12px;font:inherit;width:100%}
.form textarea{resize:vertical}.form ::placeholder{color:#7E8C89}
.form .btn{justify-self:start;margin-top:16px}
.hp{position:absolute;left:-9999px;width:1px;height:1px;opacity:0}
.okmsg{background:var(--card);border:1px solid rgba(73,234,203,.5);border-radius:12px;padding:16px 18px;max-width:560px;color:var(--dim);margin-top:8px}.okmsg b{color:var(--teal)}
.errmsg{color:#FFB4A8;font-size:14.5px}
.person{display:flex;gap:14px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;max-width:560px;color:var(--dim)}
.person b{color:var(--txt)}
address{font-style:normal;color:var(--dim);margin-top:10px}
footer.foot{border-top:1px solid var(--line);margin-top:56px}
footer.foot .wrap{display:flex;justify-content:space-between;gap:10px 20px;flex-wrap:wrap;padding-top:20px;padding-bottom:36px;font-size:13.5px;color:var(--dim)}
footer.foot a{color:var(--dim)}footer.foot a:hover{color:var(--teal)}
.cite{background:var(--card);border:1px solid rgba(73,234,203,.4);border-radius:12px;padding:14px 16px;margin-top:16px;max-width:68ch}
.card .cite{margin-top:4px;background:var(--bg)}.card.wide{grid-column:1/-1}
.cite .ch{margin:0;font:400 12px var(--mono);color:var(--dim);text-transform:uppercase;letter-spacing:1px}
.cr{display:flex;gap:12px;align-items:flex-start;margin-top:8px}
.cr code{flex:1;font:400 14px/1.5 var(--mono);color:var(--txt);overflow-wrap:anywhere}
.cb{flex:none;background:transparent;color:var(--teal);border:1px solid var(--teal);border-radius:6px;padding:4px 12px;min-height:32px;font:400 13px var(--mono);cursor:pointer}
.cb:hover{background:rgba(73,234,203,.1)}
.cite .small{margin-top:8px}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.kick{margin-top:46px;font:400 13px var(--mono);color:var(--teal)}.kick+h2{margin-top:6px}
[id]{scroll-margin-top:16px}
tr:target td{background:rgba(73,234,203,.08)}.card:target{border-color:var(--teal)}
@media (max-width:760px){.cards,.cards.two,.rules,.fit{grid-template-columns:1fr}
nav.main{width:100%;overflow-x:auto}nav.main ul{flex-wrap:nowrap;white-space:nowrap;gap:16px;padding-bottom:4px}
main{padding-top:30px}.lead{font-size:17px}}
"""

# Snippet von Plausible fuer pulsehawk.io, genau so wie ausgegeben (Ben,
# 17.10.2026). Es bleiben die vier eigenen Ereignisse, die automatische
# Formular- und Downloaderfassung in Plausible bleibt aus (Ben), sonst
# zaehlte doppelt:
#   Sample Report  Klasse plausible-event-name=Sample+Report am Knopf
#   PDF Download   Klasse am Download-Link auf /zcash-nu7
#   CSV Download   Klasse am Download-Link auf /zcash-nu7
#   Contact Form   mit Brevo die Klasse am <form>, ohne Brevo MAILTO_JS
# Der Tracker wertet die Klassen immer aus, auch ohne Schalter im Dashboard.
PLAUSIBLE = """<!-- Privacy-friendly analytics by Plausible -->
<script async src="https://plausible.io/js/pa-XESlUIPQAsUi8GQsRqS55.js"></script>
<script>
  window.plausible=window.plausible||function(){(plausible.q=plausible.q||[]).push(arguments)},plausible.init=plausible.init||function(i){plausible.o=i||{}};
  plausible.init()
</script>"""


def fuss():
    return ('<footer class="foot"><div class="wrap"><div>PulseHawk, a Vizora Digital UG brand · '
            'Kaspa coverage at <a href="https://kaspapulse.com" rel="noopener">kaspapulse.com</a></div>'
            '<div><a href="/impressum.html">Impressum</a> · <a href="/datenschutz.html">Datenschutz</a>'
            ' · <a href="/contact">Contact</a></div></div></footer>')


def kopfleiste(pfad):
    teile = []
    for href, name in NAV:
        cur = ' aria-current="page"' if href == pfad else ""
        teile.append('<li><a href="%s"%s>%s</a></li>' % (href, cur, name))
    cur = ' aria-current="page"' if pfad == "/contact" else ""
    teile.append('<li><a class="nc" href="/contact"%s>Contact</a></li>' % cur)
    return ('<header class="top"><div class="wrap"><a class="brand" href="/">'
            '<img src="/hawk.png" alt="" width="30" height="32">PulseHawk</a>'
            '<nav class="main" aria-label="Main"><ul>%s</ul></nav></div></header>'
            % "".join(teile))


def crumbs(seite):
    if seite["pfad"] == "/":
        return "", None
    kette = [("Home", "/")] + seite.get("crumbs", [(seite["h1"], seite["pfad"])])
    html_ = '<nav class="crumbs" aria-label="Breadcrumb">%s</nav>' % " · ".join(
        a(h, E(n)) if i < len(kette) - 1 else '<span aria-current="page">%s</span>' % E(n)
        for i, (n, h) in enumerate(kette))
    schema = {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n,
         "item": SITE + ("/" if h == "/" else h)} for i, (n, h) in enumerate(kette)]}
    return html_, schema


def render(seite):
    can = SITE + seite["pfad"]
    og = SITE + "/og/%s.png" % seite["og"]
    graph = [ORG]
    for s in seite["schema"]:
        if isinstance(s, str) and s.startswith("ARTICLE:"):
            _, pub, mod = s.split(":")
            graph.append(article_schema(seite, pub, mod))
        else:
            graph.append(s)
    if seite["faqs"]:
        graph.append(faq_schema(seite["faqs"]))
    cr_html, cr_schema = crumbs(seite)
    if cr_schema and not seite.get("legal"):
        graph.append(cr_schema)
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph},
                    ensure_ascii=False, indent=1)
    robots = "noindex, follow" if seite.get("noindex") else "index, follow, max-image-preview:large"
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{can}">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="preload" href="/assets/fonts/archivo-latin-800-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/ibm-plex-sans-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<meta name="theme-color" content="#080B0F">
<meta property="og:type" content="website">
<meta property="og:site_name" content="PulseHawk">
<meta property="og:title" content="{ogtitle}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{can}">
<meta property="og:image" content="{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@pulsehawkio">
{plausible}
<script type="application/ld+json">
{ld}
</script>
<style>{css}{css2}</style>
</head>
<body{bk}>
<a class="skip" href="#inhalt">Skip to content</a>
{kopf}
<main id="inhalt"><div class="wrap">
{crumbs}
<h1>{h1}</h1>
<p class="lead">{lead}</p>
{body}
</div></main>
{fuss}{script}
</body>
</html>
""".format(title=E(seite["title"]), desc=E(seite["desc"], quote=True), robots=robots,
           can=can, og=og, ogtitle=E(seite["h1"], quote=True), plausible=PLAUSIBLE,
           ld=ld, css=re.sub(r"\n", "", CSS), css2=re.sub(r"\n", "", seite.get("css", "")),
           bk=' class="%s"' % seite["bodyclass"] if seite.get("bodyclass") else "", kopf=kopfleiste(seite["pfad"]),
           crumbs=cr_html, h1=seite["h1"], lead=seite["lead"], body=seite["body"].strip(),
           fuss=fuss(), script=seite.get("script", "") + (
               KOPIER_JS if "data-copy=" in seite["body"] + seite["lead"] else ""))


# --- sitemap, robots, llms ----------------------------------------------

# alte seiten, die auf /method weiterleiten (Ben, 27.10.2026). nicht in der
# sitemap, von keiner seite verlinkt.
WEITERLEITUNGEN = {d: "/method" for d in (
    "bitcoin-halving-to-top.html", "bitcoin-top-to-bottom.html",
    "bitcoin-drawdown.html", "bitcoin-bull-run-length.html",
    "gold-in-bitcoin-bear-markets.html", "bitcoin-dominance.html",
    "markets.html", "what-if.html", "archive.html")}


def weiterleitung_html(ziel):
    """wie die kurzlinks in kaspa-pulse: meta refresh 0, canonical, noindex,
    ohne javascript, ein link fuer alle, die keine weiterleitung folgen."""
    url = SITE + ziel
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="robots" content="noindex, follow">
<meta http-equiv="refresh" content="0; url=%(z)s">
<link rel="canonical" href="%(u)s">
<title>PulseHawk, how we measure</title>
<!--
  Weiterleitung, gebaut von scripts/b2b_pages.py (WEITERLEITUNGEN). Nicht von
  Hand aendern. Die Seite stammt aus der frueheren DAY-Serie und leitet seit
  dem 27.10.2026 auf %(z)s weiter (Ben). Nicht in der sitemap.xml.
-->
</head>
<body><a href="%(z)s">PulseHawk, how we measure</a></body>
</html>
""" % {"z": ziel, "u": url}


def sitemap(S):
    zeilen = []
    for s in S:
        if s.get("noindex"):
            continue
        zeilen.append("  <url>\n    <loc>%s%s</loc>\n    <lastmod>%s</lastmod>\n  </url>"
                      % (SITE, s["pfad"], s.get("lastmod", STAND)))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n'
            % "\n".join(zeilen))


ROBOTS = """User-agent: *
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

Sitemap: https://pulsehawk.io/sitemap.xml
"""


def llms(S):
    teile = ["# PulseHawk", "",
             "> Independent blockchain measurement under load, across all chains. "
             "PulseHawk does its own measurement with its own nodes or header clients, publishes an open method, dates every number "
             "and releases the raw data. A brand of Vizora Digital UG (haftungsbeschränkt), "
             "Düsseldorf, Germany. Kaspa coverage at https://kaspapulse.com.", "",
             "Services and prices (net, plus VAT where it applies, invoiced in euro, as of October 2026)",
             "- TPS verification, review %s" % preis_text("review"),
             "- Launch measurement %s" % preis_text("launch"),
             "- Upgrade monitoring, ongoing measurement %s" % preis_text("ongoing"),
             "- Custom scope, on request", "", "## Pages", ""]
    for s in S:
        if s.get("noindex"):
            continue
        teile.append("- [%s](%s%s): %s" % (s["h1"], SITE, s["pfad"], s["desc"]))
    teile += ["", "## Contact", "", "- %s" % KONTAKT_MAIL, "- https://x.com/pulsehawkio", ""]
    return "\n".join(teile)


def og_html(seite):
    return """<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}
body{{width:1200px;height:630px;overflow:hidden;background:#080B0F;background-image:radial-gradient(ellipse 80% 70% at 85% 10%,rgba(73,234,203,.16),transparent 60%)}}
.o{{padding:72px 80px;height:630px;display:flex;flex-direction:column;justify-content:space-between}}
.b{{display:flex;align-items:center;gap:18px;font:800 38px Archivo}} .b img{{width:64px;height:68px}}
.t{{font:800 66px/1.08 Archivo;color:#F2F5F4;max-width:1000px;letter-spacing:-1px;text-wrap:balance}}
.s{{font:400 24px 'IBM Plex Mono';color:#49EACB}}
</style></head><body><div class="o"><div class="b"><img src="{repo}/hawk.png">PulseHawk</div>
<div class="t">{h1}</div><div class="s">own measurement · open method · dated numbers · raw data</div></div></body></html>
""".format(css=CSS.replace("url(/assets", "url(%s/assets" % REPO), repo=REPO, h1=seite["h1"])


# --- pruefung ------------------------------------------------------------

def main(argv):
    S = seiten()
    if "--og" in argv:
        ziel = argv[argv.index("--og") + 1]
        os.makedirs(ziel, exist_ok=True)
        fertig = set()
        for s in S:
            if s["og"] in fertig or s.get("legal"):
                continue
            fertig.add(s["og"])
            with open(os.path.join(ziel, s["og"] + ".html"), "w", encoding="utf-8") as fh:
                fh.write(og_html(s))
        print("og-vorlagen in %s" % ziel)
        return 0
    if "--check" not in argv:
        for s in S:
            pfad = os.path.join(REPO, s["datei"])
            os.makedirs(os.path.dirname(pfad), exist_ok=True)
            with open(pfad, "w", encoding="utf-8") as fh:
                fh.write(render(s))
        with open(os.path.join(REPO, "sitemap.xml"), "w", encoding="utf-8") as fh:
            fh.write(sitemap(S))
        for d, ziel in sorted(WEITERLEITUNGEN.items()):
            with open(os.path.join(REPO, d), "w", encoding="utf-8") as fh:
                fh.write(weiterleitung_html(ziel))
        # keine seite darf eine weitergeleitete adresse verlinken
        for s_ in S:
            roh = render(s_)
            for d in WEITERLEITUNGEN:
                for form in ('href="/%s"' % d, 'href="/%s"' % d[:-5], 'href="%s/%s"' % (SITE, d),
                             'href="%s/%s"' % (SITE, d[:-5])):
                    if form in roh:
                        raise SystemExit("%s verlinkt %s" % (s_["datei"], form))
        with open(os.path.join(REPO, "robots.txt"), "w", encoding="utf-8") as fh:
            fh.write(ROBOTS)
        with open(os.path.join(REPO, "llms.txt"), "w", encoding="utf-8") as fh:
            fh.write(llms(S))
        print("%d seiten geschrieben" % len(S))
    sys.path.insert(0, HERE)
    import b2b_check
    return b2b_check.main([s["datei"] for s in S])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
