#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ph_kalender_post.py, montags ein X-Entwurf aus dem Upgrade-Kalender.

WAS ES TUT
Nimmt aus data/upgrades.json alle Eintraege mit Datum in den naechsten
14 Tagen und baut daraus
  post.txt     den Posttext, englisch, klein geschrieben, hoechstens 280
               Zeichen nach X-Zaehlung, je Eintrag Netzwerk, Ereignis und
               Datum, hoechstens 4 Handles im Haupttext
  antwort.txt  die uebrigen Handles fuer eine Antwort, leer wenn keine
  kalender.png die Grafik, 1600x900, Fuss "Data from PulseHawk · pulsehawk.io"

Es postet NICHT auf X (Ben, 22.10.2026). Mit --discord gehen Text, Antwort
und Grafik an einen privaten Discord-Kanal; Ben prueft und postet selbst.
Ohne Eintrag in 14 Tagen geht eine kurze Meldung statt eines Entwurfs.

TEXTREGELN IM POSTTEXT
Keine Gedankenstriche, keine Doppelpunkte, keine Pfeile, keine Hashtags,
keine Emojis, keine Echtzeit-Woerter (now, live, ...), keine Preise, alles
klein, hoechstens 280 Zeichen. Verstoesst ein Text dagegen, bricht das
Skript ab, statt etwas Falsches zu schicken.

SCHLUESSEL
Die Webhook-URL kommt nur aus der Umgebung, DISCORD_WEBHOOK_PH_DRAFTS
(GitHub Secret). Sie wird nie ausgegeben, auch nicht in Fehlermeldungen.

    python3 scripts/ph_kalender_post.py               # bauen nach graphics/kalender/
    python3 scripts/ph_kalender_post.py --heute 2026-11-02
    python3 scripts/ph_kalender_post.py --discord     # bauen und an discord
    python3 scripts/ph_kalender_post.py --selbsttest
"""

import argparse
import datetime
import html
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from x_post import weighted_len  # noqa: E402  dieselbe zaehlung wie beim posten

KALENDER = os.path.join(REPO, "data", "upgrades.json")
ZIEL = os.path.join(REPO, "graphics", "kalender")     # graphics/ ist gitignored
TAGE = 14
MAX_LEN = 280
MAX_HANDLES = 4
BREITE, HOEHE = 1600, 900
UEBERHANG = 260          # wie dayn_grafik: chromium rastert den unteren rand nicht
LINK = "pulsehawk.io/upgrades"
FUSS = "Data from PulseHawk · pulsehawk.io"
ENV_WEBHOOK = "DISCORD_WEBHOOK_PH_DRAFTS"

MONATE = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]


# --- textregeln ----------------------------------------------------------

STRICHE = ("—", "–", "‒", "―", "−", " - ", "--")
PFEILE = ("←", "↑", "→", "↓", "⇐", "⇒", "➜",
          "➔", "➡", "->", "=>", "<-")
ECHTZEIT = re.compile(r"\b(now|live|right now|real time|realtime|currently|"
                      r"at the moment)\b", re.I)
PREIS = re.compile(r"[$€£¥₿]|\b(price|prices|priced|usd|eur|usdt|"
                   r"usdc|market cap|ath)\b", re.I)


def ist_emoji(ch):
    o = ord(ch)
    return (o >= 0x1F000 or 0x2600 <= o <= 0x27BF or 0x2B00 <= o <= 0x2BFF
            or o in (0xFE0F, 0x200D, 0x20E3))


def regel_funde(text):
    """liste der verstoesse, leer heisst sauber."""
    f = []
    for z in STRICHE:
        if z in text:
            f.append("gedankenstrich %r" % z)
    if ":" in text:
        f.append("doppelpunkt")
    for z in PFEILE:
        if z in text:
            f.append("pfeil %r" % z)
    if "#" in text:
        f.append("hashtag")
    if any(ist_emoji(c) for c in text):
        f.append("emoji")
    m = ECHTZEIT.search(text)
    if m:
        f.append("echtzeit-wort %r" % m.group(0))
    m = PREIS.search(text)
    if m:
        f.append("preis %r" % m.group(0))
    if text != text.lower():
        f.append("nicht klein geschrieben")
    n = weighted_len(text)
    if n > MAX_LEN:
        f.append("%d zeichen, erlaubt %d" % (n, MAX_LEN))
    return f


# --- daten ----------------------------------------------------------------

def lade(pfad=KALENDER):
    with open(pfad, encoding="utf-8") as fh:
        return json.load(fh)["entries"]


def faellig(eintraege, heute, tage=TAGE):
    """eintraege mit datum von heute bis heute + tage, nach datum.
    eintraege ohne datum (not set, nur blockhoehe) gehoeren nicht hinein."""
    bis = heute + datetime.timedelta(days=tage)
    aus = []
    for e in eintraege:
        if not e.get("date"):
            continue
        d = datetime.date.fromisoformat(e["date"])
        if heute <= d <= bis:
            aus.append((d, e))
    aus.sort(key=lambda x: (x[0], x[1]["chain"], x[1]["network"]))
    return [e for _, e in aus]


def datum_text(iso):
    d = datetime.date.fromisoformat(iso)
    return "%d %s %d" % (d.day, MONATE[d.month - 1], d.year)


def zeile(e):
    """eine zeile je eintrag, netzwerk, ereignis und datum."""
    # x_event ist ein kurzer name fuer den post, wenn event zu lang ist
    # (Zcash "NU7" statt "NU7, Network Upgrade 7", Ben 26.10.2026)
    ereignis = re.sub(r"\s*,\s*", " ", e.get("x_event") or e["event"])
    # ein geschaetztes datum heisst "around" (date_estimate, Ben 26.10.2026)
    return ("%s %s on %s, %s%s" % (e["chain"], ereignis, e["network"],
                                   "around " if e.get("date_estimate") else "",
                                   datum_text(e["date"]))).lower()


def handles(eintraege):
    gesehen, aus = set(), []
    for e in eintraege:
        for h in e.get("x_handles") or []:
            h = h.strip()
            if not h:
                continue
            h = h if h.startswith("@") else "@" + h
            if h.lower() not in gesehen:
                gesehen.add(h.lower())
                aus.append(h.lower())
    return aus


def texte(eintraege, tage=TAGE):
    """(post, antwort). post passt immer in 280 zeichen: zu viele zeilen
    werden zu "and N more on the calendar" zusammengefasst."""
    kopf = "network upgrades in the next %d days, from the pulsehawk calendar" % tage
    hs = handles(eintraege)
    haupt, rest = hs[:MAX_HANDLES], hs[MAX_HANDLES:]
    zeilen = [zeile(e) for e in eintraege]
    for n in range(len(zeilen), 0, -1):
        teile = [kopf, ""] + zeilen[:n]
        if n < len(zeilen):
            teile.append("and %d more on the calendar" % (len(zeilen) - n))
        teile.append("")
        if haupt:
            teile.append(" ".join(haupt))
        teile.append(LINK)
        post = "\n".join(teile)
        if weighted_len(post) <= MAX_LEN:
            break
    antwort = ""
    if rest:
        antwort = "also on the calendar " + " ".join(rest)
        while weighted_len(antwort) > MAX_LEN and " " in antwort:
            antwort = antwort.rsplit(" ", 1)[0]
    return post, antwort


# --- grafik ---------------------------------------------------------------

def grafik_html(eintraege, heute, tage=TAGE):
    # farben und schriften wie auf pulsehawk.io (b2b_pages.py), hier fest gesetzt
    font = "file://" + os.path.join(REPO, "assets", "fonts")
    reihen = "".join(
        '<tr><td class="d">%s</td><td class="c">%s</td><td>%s</td><td class="n">%s</td></tr>'
        % (("around " if e.get("date_estimate") else "")
           + html.escape(datetime.date.fromisoformat(e["date"]).strftime("%-d %b %Y")),
           html.escape(e["chain"]), html.escape(e["event"]), html.escape(e["network"]))
        for e in eintraege[:7])
    mehr = ('<div class="mehr">and %d more on pulsehawk.io/upgrades</div>' % (len(eintraege) - 7)
            if len(eintraege) > 7 else "")
    bis = heute + datetime.timedelta(days=tage)
    return """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@font-face{font-family:Archivo;font-weight:800;src:url(%(f)s/archivo-latin-800-normal.woff2)}
@font-face{font-family:Plex;font-weight:400;src:url(%(f)s/ibm-plex-sans-latin-400-normal.woff2)}
@font-face{font-family:Plex;font-weight:600;src:url(%(f)s/ibm-plex-sans-latin-600-normal.woff2)}
@font-face{font-family:Mono;font-weight:400;src:url(%(f)s/ibm-plex-mono-latin-400-normal.woff2)}
*{margin:0;padding:0;box-sizing:border-box}
body{width:%(w)dpx;height:%(h)dpx;overflow:hidden;background:#080B0F;color:#F2F5F4;font-family:Plex,sans-serif;
background-image:radial-gradient(ellipse 80%% 70%% at 85%% 5%%,rgba(73,234,203,.14),transparent 60%%)}
.k{width:%(w)dpx;height:%(h)dpx;padding:64px 80px 56px;display:flex;flex-direction:column}
.marke{display:flex;align-items:center;gap:16px;font:800 34px Archivo}.marke img{width:52px;height:55px}
h1{font:800 64px/1.1 Archivo;margin-top:44px;letter-spacing:-1px}
.sub{font:400 24px Mono;color:#49EACB;margin-top:14px}
table{border-collapse:collapse;margin-top:36px;width:100%%;font-size:28px}
td{padding:14px 18px 14px 0;border-bottom:1px solid #1C2228;color:#A9B7B4;vertical-align:top}
td.d{font-family:Mono;color:#49EACB;white-space:nowrap;width:330px;padding-right:32px}td.c{color:#F2F5F4;font-weight:600;width:250px}
td.n{text-align:right;white-space:nowrap}
.mehr{font-size:24px;color:#A9B7B4;margin-top:16px}
.fuss{margin-top:auto;font:400 22px Mono;color:#A9B7B4;border-top:1px solid #1C2228;padding-top:20px}
</style></head><body><div class="k">
<div class="marke"><img src="file://%(logo)s">PulseHawk</div>
<h1>Network upgrades, next %(t)d days</h1>
<div class="sub">%(von)s to %(bis)s, each with its official source</div>
<table>%(reihen)s</table>%(mehr)s
<div class="fuss">%(fuss)s</div>
</div></body></html>""" % {
        "f": font, "w": BREITE, "h": HOEHE, "logo": os.path.join(REPO, "hawk.png"),
        "t": tage, "von": heute.strftime("%-d %b %Y"), "bis": bis.strftime("%-d %b %Y"),
        "reihen": reihen, "mehr": mehr, "fuss": html.escape(FUSS)}


def grafik(eintraege, heute, ziel):
    import dayn_grafik                       # renderer und zuschnitt wie bei day n
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    quelle = ziel + ".html"
    with open(quelle, "w", encoding="utf-8") as fh:
        fh.write(grafik_html(eintraege, heute))
    r = subprocess.run([dayn_grafik.chrome(), "--headless", "--disable-gpu", "--no-sandbox",
                        "--hide-scrollbars", "--force-device-scale-factor=1",
                        "--virtual-time-budget=4000",
                        "--window-size=%d,%d" % (BREITE, HOEHE + UEBERHANG),
                        "--screenshot=" + ziel, "file://" + quelle], capture_output=True)
    if not os.path.exists(ziel):
        raise RuntimeError("chromium hat nichts geschrieben: %s" % r.stderr.decode()[-300:])
    os.remove(quelle)
    dayn_grafik.zuschneiden(ziel, BREITE, HOEHE)
    return ziel


# --- discord --------------------------------------------------------------

def discord_senden(inhalt, dateien=()):
    """eine nachricht an den privaten entwurfskanal. die url kommt nur aus der
    umgebung und erscheint nirgends in der ausgabe."""
    url = os.environ.get(ENV_WEBHOOK, "").strip()
    if not url:
        raise SystemExit("%s fehlt in der umgebung, nichts gesendet" % ENV_WEBHOOK)
    grenze = "----ph" + uuid.uuid4().hex
    teile = []
    nutz = {"content": inhalt[:2000], "allowed_mentions": {"parse": []}}
    teile.append(('--%s\r\nContent-Disposition: form-data; name="payload_json"\r\n'
                  'Content-Type: application/json\r\n\r\n' % grenze).encode()
                 + json.dumps(nutz).encode() + b"\r\n")
    for i, (name, pfad, mime) in enumerate(dateien):
        with open(pfad, "rb") as fh:
            blob = fh.read()
        teile.append(('--%s\r\nContent-Disposition: form-data; name="files[%d]"; '
                      'filename="%s"\r\nContent-Type: %s\r\n\r\n'
                      % (grenze, i, name, mime)).encode() + blob + b"\r\n")
    teile.append(("--%s--\r\n" % grenze).encode())
    req = urllib.request.Request(url, data=b"".join(teile), method="POST", headers={
        "Content-Type": "multipart/form-data; boundary=" + grenze,
        "User-Agent": "pulsehawk-kalender/1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            code = r.status
    except urllib.error.HTTPError as exc:
        raise SystemExit("discord antwortete mit http %d, nichts gesendet" % exc.code)
    except urllib.error.URLError as exc:
        raise SystemExit("discord nicht erreichbar (%s)" % type(exc.reason).__name__)
    print("an discord gesendet, http %d" % code)


# --- lauf -----------------------------------------------------------------

def lauf(heute, an_discord, ziel=ZIEL, pfad=KALENDER):
    eintraege = faellig(lade(pfad), heute)
    woche = heute.strftime("%Y-%m-%d")
    if not eintraege:
        meldung = ("kalender, woche ab %s. in den naechsten %d tagen steht kein eintrag "
                   "mit datum im kalender, also kein entwurf." % (woche, TAGE))
        print(meldung)
        if an_discord:
            discord_senden(meldung)
        return 0
    post, antwort = texte(eintraege)
    for name, text in (("post", post), ("antwort", antwort)):
        funde = regel_funde(text) if text else []
        if funde:
            print("FEHL %s verstoesst gegen die textregeln: %s" % (name, "; ".join(funde)))
            print(text)
            return 1
    os.makedirs(ziel, exist_ok=True)
    with open(os.path.join(ziel, "post.txt"), "w", encoding="utf-8") as fh:
        fh.write(post + "\n")
    with open(os.path.join(ziel, "antwort.txt"), "w", encoding="utf-8") as fh:
        fh.write(antwort + ("\n" if antwort else ""))
    png = grafik(eintraege, heute, os.path.join(ziel, "kalender.png"))
    print(post)
    print("--- antwort ---\n" + (antwort or "(keine)"))
    print("--- %d zeichen, %d eintraege, grafik %s" % (weighted_len(post), len(eintraege), png))
    if an_discord:
        inhalt = ("x-entwurf aus dem kalender, woche ab %s. bitte pruefen, nicht automatisch "
                  "gepostet.\n\npost (%d zeichen)\n```\n%s\n```\nantwort\n```\n%s\n```"
                  % (woche, weighted_len(post), post, antwort or "(keine)"))
        dateien = [("kalender.png", png, "image/png"),
                   ("post.txt", os.path.join(ziel, "post.txt"), "text/plain")]
        if antwort:                       # leere anhaenge lehnt discord ab
            dateien.append(("antwort.txt", os.path.join(ziel, "antwort.txt"), "text/plain"))
        discord_senden(inhalt, dateien)
    return 0


# --- selbsttest -----------------------------------------------------------

def selbsttest():
    schlecht = gezaehlt = 0

    def pruefe(name, ist, soll):
        nonlocal schlecht, gezaehlt
        gezaehlt += 1
        if ist != soll:
            schlecht += 1
            print("  FEHL %s\n    ist  %r\n    soll %r" % (name, ist, soll))
        else:
            print("  ok   %s" % name)

    gut = "network upgrades in the next 14 days\n\nzcash nu7 on mainnet, 5 november 2026\n@zcash\npulsehawk.io/upgrades"
    pruefe("sauberer text ohne funde", regel_funde(gut), [])
    for name, schlecht_text, stichwort in (
            ("gedankenstrich", gut + " — x", "gedankenstrich"),
            ("halbgeviert", gut + " – x", "gedankenstrich"),
            ("strich mit leerzeichen", gut + " - x", "gedankenstrich"),
            ("doppelpunkt", gut.replace("days", "days:"), "doppelpunkt"),
            ("pfeil", gut + " →", "pfeil"),
            ("ascii-pfeil", gut + " ->", "pfeil"),
            ("hashtag", gut + " #zcash", "hashtag"),
            ("emoji", gut + " \U0001F680", "emoji"),
            ("emoji zeichen", gut + " ⚡", "emoji"),
            ("now", gut + " out now", "echtzeit"),
            ("live", gut + " live", "echtzeit"),
            ("preis", gut + " at $40", "preis"),
            ("preiswort", gut + " price", "preis"),
            ("gross", gut.replace("zcash", "Zcash"), "klein"),
            ("zu lang", gut + " x" * 140, "zeichen")):
        pruefe("regel faengt %s" % name,
               any(stichwort in f for f in regel_funde(schlecht_text)), True)
    pruefe("bindestrich im namen ist kein gedankenstrich",
           regel_funde("solana alpenglow simd-0326 on mainnet, 1 november 2026"), [])
    pruefe("link zaehlt 23", weighted_len("a " + LINK), 2 + 23)

    heute = datetime.date(2026, 11, 2)
    def e(i, chain, d, hs, net="mainnet"):
        return {"id": "t%d" % i, "chain": chain, "event": "Upgrade %d, part" % i,
                "network": net, "date": d, "x_handles": hs}
    probe = [e(1, "Zcash", "2026-11-05", ["@Zcash", "@ZcashFoundation"]),
             e(2, "Ethereum", "2026-11-10", ["@ethereum"]),
             e(3, "Monero", "2026-11-16", ["@monero"]),          # tag 14, noch drin
             e(4, "Solana", "2026-11-17", ["@solana"]),          # tag 15, nicht mehr
             e(5, "Avalanche", "2026-11-01", ["@avax"]),         # gestern
             e(6, "Litecoin", None, ["@litecoin"]),             # ohne datum
             e(7, "Kaspa", "2026-11-03", ["@kaspaunchained", "@zcash"], "testnet")]
    f = faellig(probe, heute)
    pruefe("faellig nimmt tag 0 bis 14, nach datum",
           [x["id"] for x in f], ["t7", "t1", "t2", "t3"])
    post, antwort = texte(f)
    pruefe("post hat keine regelverstoesse", regel_funde(post), [])
    # vier lange zeilen passen nicht alle, der rest wird zusammengefasst
    pruefe("post nennt die ersten und fasst den rest zusammen",
           ("kaspa" in post, "zcash" in post, "and 2 more on the calendar" in post), (True, True, True))
    pruefe("post hoechstens 4 handles", len(re.findall(r"@\w+", post)), 4)
    pruefe("handles ohne doppelte, in datumsfolge", handles(f),
           ["@kaspaunchained", "@zcash", "@zcashfoundation", "@ethereum", "@monero"])
    pruefe("rest in der antwort", antwort, "also on the calendar @monero")
    pruefe("datum ausgeschrieben", zeile(f[1]), "zcash upgrade 1 part on mainnet, 5 november 2026")
    pruefe("x_event ersetzt event im post", zeile(dict(f[1], x_event="U1")),
           "zcash u1 on mainnet, 5 november 2026")
    pruefe("geschaetztes datum heisst around", zeile(dict(f[1], date_estimate=True)),
           "zcash upgrade 1 part on mainnet, around 5 november 2026")
    pruefe("around auch in der grafik",
           "around 5 Nov 2026" in grafik_html([dict(f[1], date_estimate=True)], heute), True)
    viele = [e(10 + i, "Chain%d" % i, "2026-11-%02d" % (3 + i % 10), []) for i in range(20)]
    post_v, _ = texte(faellig(viele, heute))
    pruefe("viele eintraege bleiben unter 280", weighted_len(post_v) <= MAX_LEN, True)
    pruefe("viele eintraege fassen den rest zusammen", "more on the calendar" in post_v, True)
    pruefe("zusammengefasster text ist sauber", regel_funde(post_v), [])
    pruefe("ohne handles keine antwort", texte(faellig(viele, heute))[1], "")

    # der echte kalender: jeder eintrag muss eine regelkonforme zeile ergeben
    echt = lade()
    for x in echt:
        x = dict(x, date=x.get("date") or "2026-11-05")
        pruefe("echter eintrag %s ergibt saubere zeile" % x["id"], regel_funde(zeile(x)), [])
    pruefe("echter kalender hat x_handles je eintrag", all("x_handles" in x for x in echt), True)
    post_e, antw_e = texte([dict(x, date="2026-11-05") for x in echt])
    pruefe("echter kalender als ein post ist sauber", regel_funde(post_e), [])
    pruefe("echte antwort ist sauber", regel_funde(antw_e) if antw_e else [], [])

    # der lauf: ohne eintraege eine meldung, keine grafik, kein abbruch
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        leer = os.path.join(tmp, "leer.json")
        with open(leer, "w") as fh:
            json.dump({"entries": [e(1, "Zcash", "2027-06-01", [])]}, fh)
        pruefe("ohne eintrag kein abbruch", lauf(heute, False, os.path.join(tmp, "out"), leer), 0)
        pruefe("ohne eintrag keine dateien", os.path.exists(os.path.join(tmp, "out")), False)
        # ein verstoss im kalender fuehrt zum abbruch, nicht zu einem entwurf
        boese = os.path.join(tmp, "boese.json")
        with open(boese, "w") as fh:
            json.dump({"entries": [dict(e(1, "Zcash", "2026-11-05", []), event="NU7: live now")]}, fh)
        pruefe("regelverstoss bricht ab", lauf(heute, False, os.path.join(tmp, "b"), boese), 1)
        pruefe("nach abbruch keine dateien", os.path.exists(os.path.join(tmp, "b")), False)
        # grafik nur, wenn ein renderer da ist (der github-laeufer hat google-chrome)
        try:
            import dayn_grafik
            dayn_grafik.chrome()
            da = True
        except Exception:                                     # noqa: BLE001
            da = False
        if da:
            gut_json = os.path.join(tmp, "gut.json")
            with open(gut_json, "w") as fh:
                json.dump({"entries": probe}, fh)
            pruefe("lauf mit eintraegen", lauf(heute, False, os.path.join(tmp, "g"), gut_json), 0)
            w, h, _, _ = dayn_grafik.png_lesen(os.path.join(tmp, "g", "kalender.png"))
            pruefe("grafik ist 1600x900", (w, h), (BREITE, HOEHE))
            pruefe("post.txt geschrieben", os.path.exists(os.path.join(tmp, "g", "post.txt")), True)
            pruefe("fuss steht in der grafik", FUSS in grafik_html(f, heute), True)

    print("%d von %d faellen falsch" % (schlecht, gezaehlt))
    return 1 if schlecht else 0


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--discord", action="store_true", help="an den privaten entwurfskanal")
    ap.add_argument("--heute", help="YYYY-MM-DD, sonst heute in utc")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    heute = (datetime.date.fromisoformat(a.heute) if a.heute
             else datetime.datetime.now(datetime.timezone.utc).date())
    return lauf(heute, a.discord)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
