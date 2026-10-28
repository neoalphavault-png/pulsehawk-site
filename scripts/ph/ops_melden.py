#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ops_melden.py, Aufforderungen von Hand nach #moderator-only (Ben, 28.10.2026).

WARUM
Ben postet @pulsehawkio von Hand, genau drei Posts in der Woche. Ein Entwurf
in #ph-entwuerfe allein reicht nicht: Zu jedem Entwurf kommt eine
Aufforderung nach #moderator-only, die mit "📤 VON HAND" beginnt und Uhrzeit,
Plattform, direkten Link und alles zum Kopieren nennt.

Kleine Schwester von scripts/ops_melden.py in kaspa-pulse, hier nur mit der
Art "hand". Der Webhook kommt nur aus der Umgebung, DISCORD_WEBHOOK_OPS
(GitHub Secret), und erscheint nie in einer Ausgabe. Fehlt das Secret, geht
nichts raus, die Aufforderung steht dann nur im Job-Log.

Vor dem Senden wird der Posttext noch einmal gegen die Textregeln des
Entwurfs geprueft (kalender: ph_kalender_post.regel_funde, zcash:
ph_entwurf.regel_pruefen). Bei einem Verstoss geht keine Aufforderung raus.

    python3 scripts/ph/ops_melden.py --aufforderung zcash --zeit "nächster Mi oder Do 17:45" \\
        --post entwurf/text.txt
    python3 scripts/ph/ops_melden.py --aufforderung zcash ... --probe   # nur job-log
    python3 scripts/ph/ops_melden.py --selbsttest
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
VON_HAND = "📤 VON HAND"
ARTEN = {"hand": "DISCORD_WEBHOOK_OPS"}
KANAL = {"hand": "#moderator-only"}
GRENZE = 1990
UA = "pulsehawk-ops"
WEBHOOK = re.compile(r"https?://(?:\w+\.)?discord(?:app)?\.com/api/webhooks/\S+", re.I)

X_LINK = "https://x.com/compose/post"
# Uhrzeiten aus dem Auftrag vom 28.10.2026, wortgleich
ZEIT_KALENDER = "Mo 16:30"
ZEIT_ZCASH = "nächster Mi oder Do 17:45"
GRAFIK_KANAL = "#ph-entwuerfe"


class Fehler(Exception):
    pass


def sauber(text):
    """Kein Webhook und kein Wert des Secrets in einer Nachricht oder Ausgabe."""
    t = WEBHOOK.sub("[webhook]", str(text))
    for name in ARTEN.values():
        w = os.environ.get(name, "").strip()
        if w:
            t = t.replace(w, "[webhook]")
    return t


def regeln(quelle):
    """Die Regelpruefung des Entwurfs, als Funktion text -> liste der verstoesse.
    Der Kalender prueft Post und Antwort mit derselben Regel. Beim Zcash-Entwurf
    gibt es keine Antwort; seine Regel verlangt "counted", "utc" und den
    Methodenhinweis und gilt deshalb nur fuer den Post."""
    if quelle == "kalender":
        sys.path.insert(0, str(HIER.parent))
        import ph_kalender_post
        return ph_kalender_post.regel_funde
    if quelle == "zcash":
        sys.path.insert(0, str(HIER))
        import ph_entwurf
        return ph_entwurf.regel_pruefen
    raise Fehler("unbekannte quelle %r, erlaubt kalender oder zcash" % quelle)


def aufforderung(zeit, post, antwort="", grafik="", pruefe=None, pruefe_antwort=None):
    """Die Aufforderung fuer einen Entwurf. Kopf wie im Auftrag, darunter der
    vollstaendige Posttext, antwort.txt und wo die Grafik haengt. Mit pruefe
    (und pruefe_antwort) werden die Texte vorher geprueft; bei einem Verstoss
    Fehler, keine Aufforderung."""
    post, antwort = post.strip(), (antwort or "").strip()
    if not post:
        raise Fehler("kein posttext, keine aufforderung")
    for name, text, regel in (("post", post, pruefe), ("antwort", antwort, pruefe_antwort)):
        funde = regel(text) if (regel and text) else []
        if funde:
            raise Fehler("%s verstoesst gegen die textregeln, keine aufforderung: %s"
                         % (name, "; ".join(funde)))
    zeilen = ["%s %s, X @pulsehawkio, %s. Erst nach ✅ von Claude im Chat posten"
              % (VON_HAND, zeit, X_LINK),
              "", "Posttext", "```", post, "```"]
    if antwort:
        zeilen += ["antwort.txt (weitere Tags, als Antwort unter den Post)", "```", antwort, "```"]
    else:
        zeilen += ["antwort.txt ist leer, keine weiteren Tags."]
    zeilen.append("Die Grafik%s hängt im %s-Post von heute." % (" (%s)" % grafik if grafik else "",
                                                              GRAFIK_KANAL))
    t = "\n".join(zeilen)
    if len(t) > GRENZE:
        raise Fehler("aufforderung hat %d zeichen, discord erlaubt %d" % (len(t), GRENZE))
    return t


def _text_fuer(art, text):
    if art not in ARTEN:
        raise Fehler("unbekannte art %r, erlaubt hand" % art)
    t = sauber(text).strip()
    if not t.startswith(VON_HAND):
        t = VON_HAND + "\n" + t
    return t[:GRENZE]


def _post(url, body, typ, timeout=60):
    req = urllib.request.Request(url, data=body, headers={"Content-Type": typ, "User-Agent": UA}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except urllib.error.URLError as exc:
        raise Fehler("discord nicht erreichbar (%s)" % type(exc.reason).__name__)


def senden(art, text, was="aufforderung", probe=False):
    """Schickt eine Nachricht der Art hand. Gibt den HTTP-Status zurueck, oder
    None, wenn das Secret fehlt oder probe gesetzt ist (dann steht sie nur im
    Job-Log)."""
    t = _text_fuer(art, text)
    if probe:
        print("[%s] probe, nicht an %s gesendet (%s):\n%s" % (art, KANAL[art], was, t))
        return None
    url = os.environ.get(ARTEN[art], "").strip()
    if not url:
        print("[%s] kein %s, nichts an %s gesendet, nur im job-log (%s):\n%s"
              % (art, ARTEN[art], KANAL[art], was, t))
        return None
    body = json.dumps({"content": t, "allowed_mentions": {"parse": []}}).encode()
    status = _post(url, body, "application/json")
    print("%s an %s, http %s" % (was, KANAL[art], status))
    if status >= 400:
        raise Fehler("%s an %s abgelehnt, http %s" % (was, KANAL[art], status))
    return status


def hand(text, was="aufforderung", probe=False):
    return senden("hand", text, was, probe)


def zusammenfassung(text):
    """Die Aufforderung auch in die Zusammenfassung des Laufs, wenn es eine gibt."""
    ziel = os.environ.get("GITHUB_STEP_SUMMARY")
    if ziel:
        with open(ziel, "a", encoding="utf-8") as fh:
            fh.write("## Aufforderung fuer #moderator-only\n````\n%s\n````\n" % sauber(text))


def selbsttest():
    f = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            f.append(name)

    alt = os.environ.get("DISCORD_WEBHOOK_OPS")
    gesendet = []
    global _post
    echt = _post

    def falsch(url, body, typ, timeout=60):
        gesendet.append((url, body, typ))
        return 204
    _post = falsch
    # testadresse erst zur laufzeit zusammengesetzt, keine webhook-adresse in der datei
    basis = "https://discord.com/api/" + "webhooks/"
    post = ("network upgrades in the next 14 days, from the pulsehawk calendar\n\n"
            "zcash nu7 on mainnet, around 6 november 2026\n\n@zcash\npulsehawk.io/upgrades")
    try:
        os.environ["DISCORD_WEBHOOK_OPS"] = basis + "1/hand-test"
        k = regeln("kalender")
        a = aufforderung(ZEIT_KALENDER, post, "also on the calendar @monero", "kalender.png", k, k)
        ok("kopf wortgleich mit dem auftrag", a.split("\n")[0] ==
           "📤 VON HAND Mo 16:30, X @pulsehawkio, https://x.com/compose/post. "
           "Erst nach ✅ von Claude im Chat posten")
        ok("vollstaendiger posttext drin", post in a)
        ok("antwort drin", "also on the calendar @monero" in a and "antwort.txt" in a)
        ok("hinweis auf die grafik", "hängt im #ph-entwuerfe-Post von heute" in a)
        ok("leere antwort sagt keine tags", "keine weiteren Tags" in aufforderung(ZEIT_KALENDER, post))
        ok("zcash-zeit wortgleich", aufforderung(ZEIT_ZCASH, post).startswith(
           "📤 VON HAND nächster Mi oder Do 17:45, X @pulsehawkio"))
        for name, schlecht in (("doppelpunkt", post.replace("days,", "days:")),
                               ("emoji", post + " \U0001F680"),
                               ("gross", post.replace("zcash", "Zcash")),
                               ("zu lang", post + " x" * 140)):
            try:
                aufforderung(ZEIT_KALENDER, schlecht, pruefe=regeln("kalender"))
                ok("regelverstoss %s stoppt die aufforderung" % name, False)
            except Fehler:
                ok("regelverstoss %s stoppt die aufforderung" % name, True)
        z = ("zcash nu7 testnet with 25 s blocks.\n"
             "we counted a median block interval of 17.0 s over 49,203 blocks, against 17.3 s computed "
             "for an ideal 25 s chain.\nthe longest gap was 451 s.\n"
             "window 4 oct 2026, 18:21 to 18 oct 2026, 05:59 utc, blocks 1 to 2.\nmethod on pulsehawk.io")
        ok("zcash-entwurf besteht die zcash-regeln", ZEIT_ZCASH in aufforderung(ZEIT_ZCASH, z, pruefe=regeln("zcash")))
        try:
            aufforderung(ZEIT_ZCASH, z.replace("computed", "expected"), pruefe=regeln("zcash"))
            ok("zcash-regel expected stoppt die aufforderung", False)
        except Fehler:
            ok("zcash-regel expected stoppt die aufforderung", True)
        try:
            aufforderung(ZEIT_KALENDER, post, "also on the calendar: @monero", pruefe=k, pruefe_antwort=k)
            ok("regelverstoss in der antwort stoppt die aufforderung", False)
        except Fehler:
            ok("regelverstoss in der antwort stoppt die aufforderung", True)
        ok("hand geht an den ops-webhook", hand(a) == 204 and gesendet[-1][0].endswith("hand-test"))
        inhalt = json.loads(gesendet[-1][1])
        ok("ein kopf, nicht doppelt", inhalt["content"].count(VON_HAND) == 1)
        ok("niemand wird angepingt", inhalt["allowed_mentions"] == {"parse": []})
        hand("leak " + os.environ["DISCORD_WEBHOOK_OPS"] + " und " + basis + "9/abc")
        inhalt = json.loads(gesendet[-1][1])["content"]
        ok("kein webhook im text", "hand-test" not in inhalt and "/9/abc" not in inhalt)
        ok("ohne kopf bekommt die nachricht einen", inhalt.startswith(VON_HAND))
        n = len(gesendet)
        ok("probe sendet nichts", hand(a, probe=True) is None and len(gesendet) == n)
        del os.environ["DISCORD_WEBHOOK_OPS"]
        ok("ohne secret nichts gesendet, nur job-log", hand(a) is None and len(gesendet) == n)
        try:
            senden("log", "x")
            ok("unbekannte art stoppt", False)
        except Fehler:
            ok("unbekannte art stoppt", True)
        try:
            aufforderung(ZEIT_KALENDER, "  ")
            ok("ohne posttext keine aufforderung", False)
        except Fehler:
            ok("ohne posttext keine aufforderung", True)
    finally:
        _post = echt
        if alt is None:
            os.environ.pop("DISCORD_WEBHOOK_OPS", None)
        else:
            os.environ["DISCORD_WEBHOOK_OPS"] = alt
    print("%d fehler" % len(f))
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--aufforderung", choices=("kalender", "zcash"), help="quelle des entwurfs")
    ap.add_argument("--zeit", help="wann posten, sonst die zeit der quelle")
    ap.add_argument("--post", help="datei mit dem posttext")
    ap.add_argument("--antwort", help="datei mit der antwort, darf fehlen oder leer sein")
    ap.add_argument("--grafik", default="", help="dateiname der grafik im entwurfspost")
    ap.add_argument("--probe", action="store_true", help="nicht senden, nur ins job-log")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if not (a.aufforderung and a.post):
        ap.error("--aufforderung und --post")
    zeit = a.zeit or {"kalender": ZEIT_KALENDER, "zcash": ZEIT_ZCASH}[a.aufforderung]
    antwort = ""
    if a.antwort and Path(a.antwort).exists():
        antwort = Path(a.antwort).read_text(encoding="utf-8")
    try:
        regel = regeln(a.aufforderung)
        text = aufforderung(zeit, Path(a.post).read_text(encoding="utf-8"), antwort, a.grafik,
                            regel, regel if a.aufforderung == "kalender" else None)
        zusammenfassung(text)
        hand(text, "aufforderung %s" % a.aufforderung, a.probe)
    except Fehler as exc:
        print(sauber(exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
