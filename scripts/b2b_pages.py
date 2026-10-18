#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""b2b_pages.py, baut die Seiten der Messmarke PulseHawk.

WARUM ES DAS GIBT
Seit dem 15.10.2026 ist pulsehawk.io die B2B-Seite der Messmarke (Ben).
Zwoelf Seiten teilen sich Kopf, Leiste, Fuss, Schema und Zaehlung. Von Hand
gepflegt liefen die auseinander, also stehen sie hier an einer Stelle, und
dieses Skript schreibt fertiges, statisches HTML. Im Browser wird nichts
nachgeladen ausser Plausible; jede Zahl steht im Quelltext.

WAS ES NICHT ANFASST
Die alten Datenseiten (Bitcoin-Zyklus, what-if, markets) gehoeren dem
Seitenstempel, scripts/stamp_pages.py. Dieses Skript schreibt keine dieser
Dateien und keine Datei in data/ ausser es liest data/upgrades.json. Die
Stichtagswache kennt die neuen Seiten nicht und muss sie nicht kennen.

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
BREVO_FORM_URL = os.environ.get("BREVO_FORM_URL", "").strip()

ZCASH_OFFEN = True             # seit 18.10.2026, Endzahlen von Ben
ZCASH_PDF = "reports/zcash-nu7-sample-report.pdf"
ZCASH_CSV = "reports/zcash-nu7-block-times.csv"
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
                    "how blockchains behave under load, across all chains, on its "
                    "own nodes, with an open method, dated numbers and raw data."),
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

def lies_upgrades():
    pfad = os.path.join(REPO, "data", "upgrades.json")
    with open(pfad, encoding="utf-8") as fh:
        d = json.load(fh)
    # nur eintraege mit quelle, regel vom 16.10.2026
    return d, [e for e in d["entries"] if str(e.get("source", "")).startswith("https://")]


def kalender_tabelle(eintraege):
    def datum(e):
        if e.get("date"):
            return '<time datetime="%s">%s</time>' % (e["date"], lang(e["date"]))
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

def seiten():
    S = []
    up_meta, up = lies_upgrades()
    up_stand = max([e.get("checked", STAND) for e in up] + [up_meta.get("updated", STAND)])

    # 1 startseite
    S.append(dict(
        datei="index.html", pfad="/", og="home", lastmod="2026-10-18",
        title="Independent blockchain measurement | PulseHawk",
        desc=("PulseHawk measures blockchains under load on its own nodes. Dated "
              "numbers, raw data and an open method for TPS claims, launches and upgrades."),
        h1="Independent blockchain measurement under load",
        lead=("PulseHawk measures how blockchains behave under load. We run our own "
              "nodes, count blocks, transactions and confirmation times inside a fixed "
              "window, and publish dated numbers with the raw data. The method is open. "
              "We work for foundations, core teams and grant committees across all "
              "chains, around launches and network upgrades."),
        body="""
<ul class="chips"><li>Own nodes</li><li>Open method</li><li>Dated numbers</li><li>Raw data</li></ul>
<section><h2>What can we measure for you?</h2>
<div class="cards">
<a class="card" href="/tps-verification"><span class="ct">TPS verification</span><span class="cd">Claimed vs measured throughput, counted on our own node.</span><span class="cp">Review %s</span></a>
<a class="card" href="/launch-measurement"><span class="ct">Launch measurement</span><span class="cd">The first week after a testnet or mainnet launch, set against the week before.</span><span class="cp">%s</span></a>
<a class="card" href="/upgrade-monitoring"><span class="ct">Upgrade monitoring</span><span class="cd">Block time, difficulty and orphaned blocks before and after a hard fork.</span><span class="cp">Ongoing %s</span></a>
</div>
<p class="note">Custom scope, on request. %s</p>
</section>
<section><h2>Which networks have we measured?</h2>
<div class="cards two">
<a class="card" href="/zcash-nu7"><span class="ct">Zcash NU7 on testnet</span><span class="cd">Network Upgrade 7 on the Zcash testnet, measured independently over 49,203 blocks up to 18 October 2026. Mean block interval 23.68 s against a 25 s target.</span><span class="cp">Read the Zcash NU7 case</span></a>
<a class="card" href="/cases/kaspa"><span class="ct">Kaspa</span><span class="cd">A network with a very high block rate, followed every day since August 2026 through our Kaspa media brand.</span><span class="cp">Read the Kaspa case</span></a>
</div>
</section>
<section><h2>For foundations and grant committees</h2>
<p>Ongoing measurement of a network works best as a public good. When a grant funds it, every result and its raw data are published openly, for the whole ecosystem, with the same method and the same rules as paid work.</p>
<p>A grant pays for the measurement, never for the result. The rules that make this hold are on our %s page.</p>
<p>%s</p>
</section>
<section><h2>What does a blockchain performance measurement look like?</h2>
<p>A short summary, the measurement window in UTC, charts, a table with median, p90 and p99, the method version and a CSV with every block we counted. Every number carries its date.</p>
%s
</section>
<section><h2>How do we start?</h2>
<p>Tell us the network, what you want measured and when. Ben, the founder, answers personally.</p>
<p class="cta">%s %s</p>
</section>
""" % (preis_text("review"), preis_text("launch"), preis_text("ongoing"), PREIS_STAND,
       a("/independence", "independence"),
       a("/upgrade-monitoring", "How ongoing measurement works"),
       sample_button(), contact_button(),
       a("mailto:" + KONTAKT_MAIL, E(KONTAKT_MAIL), "btn ghost")),
        faqs=[],
        schema=[],
    ))

    # 2 tps
    tps_faq = [
        ("Why is measured TPS usually lower than claimed TPS?",
         "A claim often comes from a lab test with simple transfers on a few nodes close "
         "together. A public network carries mixed transactions over real distances. Both "
         "numbers can be honest, they just describe different conditions. We show both and name the conditions."),
        ("Can you verify a TPS claim on a network you have no node on yet?",
         "Yes. We set up our own node for the job. The time it needs to sync is part of the agreed window."),
        ("Will the result be published?",
         "Yes. Results are published as measured. You see them before publication and can correct facts, not findings."),
    ]
    S.append(dict(
        datei="tps-verification.html", pfad="/tps-verification", og="tps-verification",
        title="TPS verification, claimed vs measured | PulseHawk",
        desc=("Independent TPS verification. We check a TPS claim against real network "
              "throughput on our own node and publish claimed vs measured with dated raw data."),
        h1="Independent TPS verification, claimed vs measured",
        lead=("A TPS claim is a number from a test. We verify the TPS claim against what "
              "the network does on our own node, inside a dated window, and set real TPS vs "
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
            ("The measurement.", "We count on our own node over an agreed window in UTC. Transactions per minute, blocks per second and confirmation time."),
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
                               "Claimed vs measured TPS, counted on our own node, with dated raw data.", "review")],
    ))

    # 3 launch
    launch_faq = [
        ("Can you measure our testnet stress test?",
         "Yes. We watch the stress test from our own nodes and count what reaches the "
         "network. The load comes from your test, our part is the count."),
        ("How early should we book?",
         "Two weeks before launch is enough for most networks. That leaves time to sync our nodes and record the week before."),
        ("What if the launch date moves?",
         "The measurement moves with it. The price stays the same as long as the scope does."),
    ]
    S.append(dict(
        datei="launch-measurement.html", pfad="/launch-measurement", og="launch-measurement",
        title="Testnet and mainnet launch measurement | PulseHawk",
        desc=("Testnet stress test measurement and mainnet launch metrics. The first week "
              "after launch against the week before, counted on our own nodes, with raw data."),
        h1="Testnet and mainnet launch measurement",
        lead=("The first week after a launch shows how a network holds up under real "
              "load. We measure that week on our own nodes and set it against the week "
              "before, so your mainnet launch metrics come with a baseline."),
        body="""
<section><h2>What happens in the launch week?</h2>
%s
</section>
<section><h2>What do we count?</h2>
<p>Blocks per second and per minute, the block time distribution, transactions per minute, confirmation time, fees, stale and orphaned blocks and the delay between our nodes. The full list is in our %s.</p>
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
            ("Before.", "Our nodes run from the week before launch and record a baseline."),
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
                               "The first week after a testnet or mainnet launch against the week before, counted on our own nodes.", "launch")],
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
        desc=("Hard fork monitoring on our own nodes. Block time, difficulty and orphaned "
              "blocks compared before and after a network upgrade, with dated raw data."),
        h1="Hard fork and network upgrade monitoring",
        lead=("A hard fork changes the rules a network runs on. Hard fork monitoring "
              "shows whether the change did what it set out to do. We measure block time, "
              "difficulty and orphaned blocks on our own nodes, before and after the upgrade."),
        body="""
<section><h2>What do we compare before and after the upgrade?</h2>
<ul class="list">
<li><b>Block time.</b> The distribution with median, p90, p99 and the longest gap between two blocks.</li>
<li><b>Difficulty.</b> How fast it follows a change in hashrate.</li>
<li><b>Stale and orphaned blocks.</b> How many valid blocks did not make the main chain.</li>
<li><b>Propagation.</b> The delay until a block reaches all of our nodes.</li>
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
            ("Baseline.", "Our nodes run weeks before activation and record the old rules."),
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
                               "Block time, difficulty and orphaned blocks before and after a hard fork, counted on our own nodes.", "ongoing")],
    ))

    # 5 method
    m_faq = [
        ("What is a stale block rate?",
         "The share of valid blocks that did not end up in the main chain, in % of all "
         "blocks our nodes saw in the window. If it rises after an upgrade, blocks reach parts of the network too late."),
        ("How do you measure propagation delay?",
         "Each of our nodes records when a block first arrives. The gap between the first "
         "and the last node is the propagation delay for that block. We report median and p90 for the window."),
        ("Can we repeat your measurement?",
         "Yes. The method is on this page and the raw data is in the CSV. Two people with the same window should get the same numbers."),
    ]
    S.append(dict(
        datei="method.html", pfad="/method", og="method", lastmod="2026-10-18",
        title="How we measure blockchains | PulseHawk",
        desc=("Our open method. Block time distribution, stale block rate, propagation "
              "delay, confirmation time and fees, counted on our own nodes in dated windows."),
        h1="How we measure",
        lead=("Every number we publish comes from our own nodes, inside a stated window, "
              "with a method anyone can repeat. This page lists what we count, the rules we "
              "publish by and what falls outside our work. %s." % METHODE),
        body="""
<section><h2>Where do the numbers come from?</h2>
<p>From full nodes we run ourselves, on every network we measure, in more than one place. We do not publish their addresses, hostnames or locations, so nobody can tune a network around our measurement.</p>
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
<li><b>Propagation delay.</b> The gap between the first and the last of our nodes to see a block.</li>
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
""" % ("The first public sample report, Zcash NU7 on testnet, follows on 18 October 2026, 12:00 Berlin time."
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
        datei="independence.html", pfad="/independence", og="independence",
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
<p class="cta">%s</p>
""" % (a("https://kaspapulse.com", "kaspapulse.com"), faq_html(i_faq), contact_button()),
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
        datei="upgrades.html", pfad="/upgrades", og="upgrades", lastmod="2026-10-18",
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
<p class="note">%d entries, checked on %s. Measured by us means we measured that upgrade ourselves and a case page follows.</p>
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
    dl = []
    if pdf:
        dl.append(a("/" + ZCASH_PDF, "Download the sample report (PDF)",
                    "btn plausible-event-name=PDF+Download"))
    if csv:
        dl.append(a("/" + ZCASH_CSV, "Download block intervals (CSV)",
                    "btn ghost plausible-event-name=CSV+Download"))
    # ohne dateien keine leeren knoepfe; der abschnitt erscheint, sobald
    # eine der beiden dateien unter reports/ liegt
    downloads = ('<section><h2>Where is the raw data?</h2><p>The full report and every '
                 'block interval in the window, from our own measurement.</p>'
                 '<p class="cta">%s</p></section>' % " ".join(dl)) if dl else ""
    # wir betreiben keinen zcash-knoten: ein eigener header-client holt die
    # header per p2p (getheaders) direkt bei testnet-peers (Ben, 18.10.2026)
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
        datei="zcash-nu7.html", pfad="/zcash-nu7", og="zcash-nu7", lastmod="2026-10-18",
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
<tr><td class="c">Mean</td><td>23.68 s</td><td>25 s</td></tr>
<tr><td class="c">Median</td><td>17.0 s</td><td>17.3 s</td></tr>
<tr><td class="c">p90</td><td>52 s</td><td>57.6 s</td></tr>
<tr><td class="c">p99</td><td>109 s</td><td>115.1 s</td></tr>
<tr><td class="c">Over 75 s</td><td>3.59%%</td><td>4.98%%</td></tr>
<tr><td class="c">Over 150 s</td><td>0.203%%</td><td>0.248%%</td></tr>
<tr><td class="c">Longest gap</td><td>451 s</td><td>about 284 s</td></tr>
</tbody></table></div>
<p class="note">Expected means an ideal chain with a 25 s mean, where intervals follow an exponential distribution.</p>
%s
</section>
<section><h2>How often is a block slower than the old 75 s target?</h2>
<p>In 3.59%% of intervals, against 4.98%% for an ideal 25 s chain. Before NU7 the target itself was 75 s. Gaps over 150 s came in 0.203%% of intervals, against 0.248%% expected.</p>
<p>The longest gap was 451 s, longer than the roughly 284 s an ideal chain would show over the same number of blocks. No block timestamp went backwards.</p>
%s
</section>
<section><h2>How fast does difficulty follow hashrate?</h2>
<p>We found 6 jumps in hashrate of 2x or more. Difficulty caught up after a median of 960 blocks, about 2.7 hours as measured, and after 1,839 blocks at most.</p>
%s
</section>
<section><h2>How long do confirmations take?</h2>
<p>Thirty blocks at 25 s spanned a median of 730 s and a p99 of 1,187 s. For perfect 25 s blocks the p99 would be about 1,105 s, so the measured value sits above that, partly because of the hashrate jumps (1,154 s without the windows around them), and still well below the 1,409 s for ten blocks at 75 s.</p>
%s
</section>
<section><h2>How many blocks were orphaned?</h2>
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
""" % (quelle, quelle, quelle, quelle, a("/method", "How we measure"), downloads,
       faq_html(z_faq), contact_button("Request a measurement for your upgrade")),
        faqs=z_faq,
        schema=["ARTICLE:2026-10-18:2026-10-18", {
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
              "carries its date and is marked either measured, from our own nodes, or source, "
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
         "Ben reads every request and answers by email, with questions or a written offer."),
        ("Do I need a fixed budget?",
         "No. The range helps us suggest a scope, and not sure yet is a fine answer."),
    ]
    if BREVO_FORM_URL:
        # mit Brevo zaehlt der Tracker das Absenden ueber die Klasse, einmal,
        # ohne das Formular anzuhalten; der Browser schickt es selbst ab
        form_open = ('<form class="form plausible-event-name=Contact+Form" method="post" action="%s">'
                     % E(BREVO_FORM_URL, quote=True))
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
        desc=("Request an independent blockchain measurement. Tell us the network, what to "
              "measure, when and your budget range. The founder answers each request by email."),
        h1="Request a measurement",
        lead=("Four questions and your email. Tell us which network, what you want measured "
              "and when, and we answer with questions or an offer. You can also write to %s."
              % a("mailto:" + KONTAKT_MAIL, E(KONTAKT_MAIL))),
        body="""
<section><h2>What should we measure?</h2>
%s
<label for="f-network">Network</label>
<input id="f-network" name="NETWORK" type="text" required autocomplete="off" placeholder="Zcash testnet, Kaspa mainnet">
<label for="f-scope">What to measure</label>
<textarea id="f-scope" name="SCOPE" rows="4" required placeholder="A TPS claim, a launch week, an upcoming hard fork"></textarea>
<label for="f-when">When</label>
<input id="f-when" name="TIMING" type="text" required placeholder="Launch on 3 December 2026">
<label for="f-budget">Budget range</label>
<select id="f-budget" name="BUDGET" required><option value="">Choose a range</option>%s</select>
<label for="f-email">Your email</label>
<input id="f-email" name="EMAIL" type="email" required autocomplete="email">
<input type="text" name="email_address_check" value="" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true">
<input type="hidden" name="locale" value="en">
<button type="submit" class="btn">Send request</button>
<p class="small">We use your details only to answer this request. See %s.</p>
</form>
</section>
<section><h2>Who answers?</h2>
<div class="person"><img src="/hawk.png" alt="" width="48" height="51" loading="lazy"><div><b>Your contact</b><br>Ben, founder<br>%s · %s</div></div>
</section>
%s
""" % (form_open, "".join('<option>%s</option>' % b for b in budgets),
       a("/datenschutz.html", "privacy"),
       a("https://x.com/gokugalax", "x.com/gokugalax"),
       a("mailto:" + KONTAKT_MAIL, E(KONTAKT_MAIL)), faq_html(c_faq)),
        faqs=c_faq,
        schema=[],
        script=MAILTO_JS if not BREVO_FORM_URL else "",
    ))

    # 11 archive
    alt = [
        ("/bitcoin-halving-to-top.html", "The Bitcoin 4 year cycle, halving to top", "Four cycles counted in days from the halving to the cycle top."),
        ("/bitcoin-top-to-bottom.html", "The Bitcoin cycle bottom, how long after the top", "The three completed cycles from top to bottom, with the dates behind each."),
        ("/bitcoin-drawdown.html", "How far Bitcoin is below its all-time high", "The distance to the October 2025 top, recounted every day."),
        ("/bitcoin-bull-run-length.html", "How long Bitcoin bull runs last", "From each cycle low to the following top, counted in days."),
        ("/gold-in-bitcoin-bear-markets.html", "Does gold rise when Bitcoin falls?", "Gold and the S&amp;P 500 through every Bitcoin bear market."),
        ("/bitcoin-dominance.html", "Bitcoin dominance", "Bitcoin's share of the crypto market, from a daily record."),
        ("/markets.html", "Gold vs stocks vs bitcoin", "Three markets over the same seven calendar days."),
        ("/what-if.html", "What if you had bought bitcoin, gold or the S&amp;P 500?", "One buy, a monthly plan or a daily amount, from daily prices since 2010."),
    ]
    S.append(dict(
        datei="archive.html", pfad="/archive", og="archive",
        title="Archive, market data pages | PulseHawk",
        desc=("PulseHawk market data pages from 2026. Bitcoin cycle counts, drawdown, "
              "dominance, gold and stocks. Still online and still updated by the same scripts."),
        h1="Archive",
        lead=("PulseHawk began in August 2026 as a market data feed. These pages are from "
              "that time. They stay online at their addresses, and the same scripts still "
              "update their numbers every day."),
        body="""
<section><h2>Which pages are in the archive?</h2>
<div class="cards one">%s</div>
</section>
""" % "".join('<a class="card" href="%s"><span class="ct">%s</span><span class="cd">%s</span></a>'
              % (h, t, d) for h, t, d in alt),
        faqs=[],
        schema=[],
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
<p>If you send the contact form or write to us, we process your email address and what you tell us about your project, only to answer your request. When the form is sent through Brevo, a service of Brevo GmbH, Köpenicker Straße 126, 10179 Berlin, Germany, your entries are transmitted to and stored by Brevo on our behalf. Without Brevo, the form opens your own email program and nothing is sent until you send that email.</p>
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
.person{display:flex;gap:14px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;max-width:560px;color:var(--dim)}
.person b{color:var(--txt)}
address{font-style:normal;color:var(--dim);margin-top:10px}
footer.foot{border-top:1px solid var(--line);margin-top:56px}
footer.foot .wrap{display:flex;justify-content:space-between;gap:10px 20px;flex-wrap:wrap;padding-top:20px;padding-bottom:36px;font-size:13.5px;color:var(--dim)}
footer.foot a{color:var(--dim)}footer.foot a:hover{color:var(--teal)}
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
            ' · <a href="/archive">Archive</a> · <a href="/contact">Contact</a></div></div></footer>')


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
<style>{css}</style>
</head>
<body>
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
           ld=ld, css=re.sub(r"\n", "", CSS), kopf=kopfleiste(seite["pfad"]),
           crumbs=cr_html, h1=seite["h1"], lead=seite["lead"], body=seite["body"].strip(),
           fuss=fuss(), script=seite.get("script", ""))


# --- sitemap, robots, llms ----------------------------------------------

ALTE_SEITEN = ["bitcoin-halving-to-top.html", "bitcoin-top-to-bottom.html",
               "bitcoin-drawdown.html", "bitcoin-bull-run-length.html",
               "gold-in-bitcoin-bear-markets.html", "bitcoin-dominance.html",
               "markets.html", "what-if.html"]


def sitemap(S, alt_lastmod):
    zeilen = []
    for s in S:
        if s.get("noindex"):
            continue
        zeilen.append("  <url>\n    <loc>%s%s</loc>\n    <lastmod>%s</lastmod>\n  </url>"
                      % (SITE, s["pfad"], s.get("lastmod", STAND)))
    for d in ALTE_SEITEN:
        zeilen.append("  <url>\n    <loc>%s/%s</loc>\n    <lastmod>%s</lastmod>\n  </url>"
                      % (SITE, d, alt_lastmod.get(d, STAND)))
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
             "PulseHawk runs its own nodes, publishes an open method, dates every number "
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


def alt_lastmod():
    """letzter commit je alter seite, damit die sitemap nicht luegt."""
    import subprocess
    aus = {}
    for d in ALTE_SEITEN:
        try:
            r = subprocess.run(["git", "log", "-1", "--format=%cs", "--", d], cwd=REPO,
                               capture_output=True, text=True, timeout=20)
            if r.stdout.strip():
                aus[d] = r.stdout.strip()
        except Exception:                                   # noqa: BLE001
            pass
    return aus


def og_html(seite):
    return """<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}
body{{width:1200px;height:630px;overflow:hidden;background:#080B0F;background-image:radial-gradient(ellipse 80% 70% at 85% 10%,rgba(73,234,203,.16),transparent 60%)}}
.o{{padding:72px 80px;height:630px;display:flex;flex-direction:column;justify-content:space-between}}
.b{{display:flex;align-items:center;gap:18px;font:800 38px Archivo}} .b img{{width:64px;height:68px}}
.t{{font:800 66px/1.08 Archivo;color:#F2F5F4;max-width:1000px;letter-spacing:-1px}}
.s{{font:400 24px 'IBM Plex Mono';color:#49EACB}}
</style></head><body><div class="o"><div class="b"><img src="{repo}/hawk.png">PulseHawk</div>
<div class="t">{h1}</div><div class="s">own nodes · open method · dated numbers · raw data</div></div></body></html>
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
            fh.write(sitemap(S, alt_lastmod()))
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
