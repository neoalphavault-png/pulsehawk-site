#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
x_post.py - ein Post auf X: Text plus ein Bild, optional eine Selbstantwort,
mit Sperre gegen Doppelposts. Nur Standardbibliothek (OAuth 1.0a HMAC-SHA1
von Hand, X API v2).

Stufe 3 der Automatisierung (pulse-studio/docs/stufe3-x.md). Zuerst fuer
Number of the Day in kaspa-pulse (@KaspaPulse-Konto, App "Kaspa Pulse Bot"),
dieselbe Datei liegt in pulse-studio/scripts/ fuer den 19:05-Post von
@pulsehawkio (dort mit eigenen Secrets gleichen Namens).

Secrets (Umgebung): X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET
(OAuth 1.0a, App mit Read and Write). Werden nie gedruckt.

Kosten (X pay-per-use, Stand 09/2026): 0,015 $ je Post, 0,20 $ je Post mit
Link. Deshalb: der Hauptpost traegt nie einen Link, der Link steht in der
Selbstantwort, und die gibt es nur, wenn sie einen Link enthaelt.

  python3 scripts/x_post.py --text "..." --image bild.png [--reply "..."] --key nod-2026-09-11
  python3 scripts/x_post.py --from-nod data/number-of-day.json --image graphics/number-of-day.png
  python3 scripts/x_post.py --text "counting test, ignore" --image bild.png --delete-after
  python3 scripts/x_post.py --delete 1234567890
  python3 scripts/x_post.py --selftest        # Signatur gegen den dokumentierten X-Testvektor

Sperre: data/x-post-log.json merkt sich je --key die Post-ID. Gleicher Key
noch einmal = nichts posten, Exit 0. Ist der Hauptpost drin, aber die
Antwort fehlt, wird beim naechsten Lauf nur die Antwort nachgeholt (montags
gilt das fuer beide Antworten einzeln).
Jeder Fehler bricht laut ab (Exit 1), es gibt keinen stillen Fallback.
"""
import argparse
import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

API = "https://api.x.com"
URL_TWEETS = API + "/2/tweets"
URL_MEDIA = API + "/2/media/upload"
TIMEOUT = 60
MAX_CHARS = 280
URL_WEIGHT = 23   # X zaehlt jede URL als 23 Zeichen (t.co)
LINK_RE = re.compile(r"(https?://\S+|\bwww\.\S+|\b[a-z0-9][a-z0-9-]*\.(?:com|io|org|net|de|xyz|html)(?:/\S*)?)", re.I)
ENV = ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")



# ---------------------------------------------------------------- OAuth 1.0a

def pct(s):
    """RFC 3986: alles ausser A-Z a-z 0-9 - . _ ~ wird kodiert."""
    return urllib.parse.quote(str(s), safe="")


def signature(method, url, params, consumer_secret, token_secret):
    pairs = sorted((pct(k), pct(v)) for k, v in params.items())
    param_str = "&".join("%s=%s" % kv for kv in pairs)
    base = "&".join([method.upper(), pct(url), pct(param_str)])
    key = "%s&%s" % (pct(consumer_secret), pct(token_secret))
    digest = hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def oauth_header(method, url, creds, extra_params=None, nonce=None, timestamp=None):
    """extra_params: Query- und Formularparameter (application/x-www-form-urlencoded),
    die in die Signatur gehoeren. JSON- und Multipart-Koerper gehoeren NICHT hinein."""
    oauth = {
        "oauth_consumer_key": creds["key"],
        "oauth_nonce": nonce or uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": timestamp or str(int(time.time())),
        "oauth_token": creds["token"],
        "oauth_version": "1.0",
    }
    allp = dict(extra_params or {})
    allp.update(oauth)
    oauth["oauth_signature"] = signature(method, url, allp, creds["secret"], creds["token_secret"])
    return "OAuth " + ", ".join('%s="%s"' % (pct(k), pct(v)) for k, v in sorted(oauth.items()))


def creds_from_env():
    vals = [os.environ.get(n, "").strip() for n in ENV]
    missing = [n for n, v in zip(ENV, vals) if not v]
    if missing:
        sys.exit("FEHLT: %s nicht gesetzt (Repo-Secrets, OAuth 1.0a Read and Write)" % ", ".join(missing))
    return {"key": vals[0], "secret": vals[1], "token": vals[2], "token_secret": vals[3]}


# ---------------------------------------------------------------- HTTP

def call(method, url, creds, json_body=None, multipart=None, query=None):
    """Ein signierter Aufruf. Gibt das JSON der Antwort zurueck oder bricht laut ab.
    Antworttexte werden gekuerzt gedruckt, Secrets nie."""
    full = url + ("?" + urllib.parse.urlencode(query) if query else "")
    headers = {"Authorization": oauth_header(method, url, creds, query),
               "User-Agent": "pulse-studio x_post/1.0"}
    data = None
    if json_body is not None:
        data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif multipart is not None:
        data, headers["Content-Type"] = multipart
    req = urllib.request.Request(full, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:800]
        raise RuntimeError("X antwortet HTTP %d auf %s %s: %s" % (e.code, method, url, body))


def multipart_body(fields, file_field, filename, blob, mime):
    boundary = "----kaspapulse" + uuid.uuid4().hex[:16]
    out = []
    for k, v in fields.items():
        out.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, k, v)).encode())
    out.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
                "Content-Type: %s\r\n\r\n" % (boundary, file_field, filename, mime)).encode())
    out.append(blob + b"\r\n")
    out.append(("--%s--\r\n" % boundary).encode())
    return b"".join(out), "multipart/form-data; boundary=%s" % boundary


# ---------------------------------------------------------------- X-Aufrufe

def upload_image(path, creds):
    with open(path, "rb") as fh:
        blob = fh.read()
    ext = os.path.splitext(path)[1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(ext.lstrip("."))
    if not mime:
        sys.exit("Bildformat nicht unterstuetzt: %s" % path)
    if len(blob) > 5 * 1024 * 1024:
        sys.exit("Bild groesser als 5 MB: %s" % path)
    body = multipart_body({"media_category": "tweet_image", "media_type": mime},
                          "media", os.path.basename(path), blob, mime)
    res = call("POST", URL_MEDIA, creds, multipart=body)
    d = res.get("data") or res
    media_id = d.get("id") or d.get("media_id_string") or d.get("media_id")
    if not media_id:
        raise RuntimeError("media upload ohne id: %s" % json.dumps(res)[:300])
    print("bild hochgeladen, media_id %s, %d kB" % (media_id, len(blob) // 1024))
    return str(media_id)


def post(text, creds, media_id=None, reply_to=None):
    body = {"text": text}
    if media_id:
        body["media"] = {"media_ids": [media_id]}
    if reply_to:
        body["reply"] = {"in_reply_to_tweet_id": str(reply_to)}
    res = call("POST", URL_TWEETS, creds, json_body=body)
    pid = (res.get("data") or {}).get("id")
    if not pid:
        raise RuntimeError("post ohne id: %s" % json.dumps(res)[:300])
    return str(pid)


def delete(post_id, creds):
    res = call("DELETE", URL_TWEETS + "/" + str(post_id), creds)
    ok = (res.get("data") or {}).get("deleted")
    if not ok:
        raise RuntimeError("loeschen fehlgeschlagen fuer %s: %s" % (post_id, json.dumps(res)[:300]))
    print("geloescht: %s" % post_id)


# ---------------------------------------------------------------- Regeln

def weighted_len(text):
    """Zeichen wie X sie zaehlt: jede URL 23, sonst je Zeichen eins."""
    n, pos = 0, 0
    for m in LINK_RE.finditer(text):
        n += len(text[pos:m.start()]) + URL_WEIGHT
        pos = m.end()
    return n + len(text[pos:])


def has_link(text):
    return bool(LINK_RE.search(text or ""))


def check_text(text, what):
    text = (text or "").strip()
    if not text:
        sys.exit("%s ist leer" % what)
    n = weighted_len(text)
    if n > MAX_CHARS:
        sys.exit("%s zu lang: %d von %d Zeichen (URLs zaehlen 23)" % (what, n, MAX_CHARS))
    return text


# ---------------------------------------------------------------- Montag

def berlin_offset(when):
    """Sommerzeit in Europe/Berlin ohne tzdata (gleiche Rechnung wie in
    yt_live_check.py): letzter Sonntag im Maerz bis letzter Sonntag im
    Oktober ist +02:00."""
    def last_sunday(year, month):
        d = dt.date(year, month, 31)
        return d - dt.timedelta(days=(d.weekday() + 1) % 7)
    y = when.year
    start = dt.datetime.combine(last_sunday(y, 3), dt.time(1), dt.timezone.utc)
    end = dt.datetime.combine(last_sunday(y, 10), dt.time(1), dt.timezone.utc)
    return dt.timedelta(hours=2) if start <= when < end else dt.timedelta(hours=1)


def berlin_today():
    now = dt.datetime.now(dt.timezone.utc)
    return (now + berlin_offset(now)).date()


def load_log(path):
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return []


def save_log(path, log):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def find(log, key):
    for e in log:
        if e.get("key") == key:
            return e
    return None


# ---------------------------------------------------------------- Ablauf

def run(args):
    if args.from_nod:
        with open(args.from_nod, encoding="utf-8") as fh:
            nod = json.load(fh)
        p = nod.get("post") or {}
        text = p.get("x", "")
        reply = p.get("reply", "")
        if not text:
            sys.exit("%s traegt keinen post.x" % args.from_nod)
        # Selbstantwort nur, wenn sie einen Link traegt (Bens Regel: der Link
        # steht nie im Hauptpost, und ohne Link braucht es keine Antwort).
        if reply and not has_link(reply):
            print("Selbstantwort ohne Link, wird nicht gepostet: %r" % reply[:80])
            reply = ""
        key = args.key or "nod-%s" % (nod.get("date") or dt.date.today().isoformat())
    else:
        text, reply, key = args.text, args.reply, args.key
    if not text:
        sys.exit("--text oder --from-nod fehlt")
    text = check_text(text, "Text")
    if has_link(text):
        print("HINWEIS: der Hauptpost traegt einen Link (0,20 $ statt 0,015 $).")
    if reply:
        reply = check_text(reply, "Selbstantwort")
    if args.delete_after:
        key = key or "test-%s" % dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    if not key:
        sys.exit("--key fehlt (Sperre gegen Doppelposts), z. B. nod-2026-09-11")

    log = load_log(args.log)
    entry = find(log, key)
    if entry and entry.get("id") and not args.delete_after:
        if reply and not entry.get("reply_id"):
            print("Hauptpost %s liegt schon vor (key %s), nur die Antwort fehlt noch." % (entry["id"], key))
        else:
            print("schon gepostet (key %s, id %s), nichts zu tun" % (key, entry["id"]))
            return 0

    if args.dry_run:
        print("DRY_RUN, das ginge raus (key %s):\n\n%s\n" % (key, text))
        if reply:
            print("Antwort:\n%s\n" % reply)
        print("Bild: %s, %d/%d Zeichen" % (args.image, weighted_len(text), MAX_CHARS))
        return 0

    creds = creds_from_env()
    if not entry or not entry.get("id"):
        media_id = upload_image(args.image, creds) if args.image else None
        pid = post(text, creds, media_id=media_id)
        entry = {"key": key, "id": pid, "posted_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                 "text": text[:120], "image": os.path.basename(args.image) if args.image else None}
        log.append(entry)
        save_log(args.log, log)          # sofort merken, bevor irgendetwas anderes passiert
        print("gepostet: %s (key %s)" % (pid, key))
    if reply and not entry.get("reply_id"):
        rid = post(reply, creds, reply_to=entry["id"])
        entry["reply_id"] = rid
        entry["reply_has_link"] = has_link(reply)
        save_log(args.log, log)
        print("Selbstantwort: %s%s" % (rid, " (mit Link)" if has_link(reply) else ""))
    if args.delete_after:
        for pid in [entry.get("reply_id"), entry.get("id")]:
            if pid:
                delete(pid, creds)
        entry["deleted"] = True
        save_log(args.log, log)
        print("Test beendet, beide Posts wieder geloescht.")
    return 0


def selftest():
    # Dokumentierter Testvektor aus der X-Entwicklerdoku ("Creating a signature").
    creds = {"key": "xvz1evFS4wEEPTGEFPHBog", "secret": "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw",
             "token": "370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb", "token_secret": "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE"}
    hdr = oauth_header("POST", "https://api.twitter.com/1.1/statuses/update.json", creds,
                       {"include_entities": "true", "status": "Hello Ladies + Gentlemen, a signed OAuth request!"},
                       nonce="kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg", timestamp="1318622958")
    want = 'oauth_signature="hCtSmYh%2BiHYCEqBWrE7C7hYmtUk%3D"'
    assert want in hdr, hdr
    assert weighted_len("see kaspapulse.com/kaspa-weekly.html now") == len("see ") + 23 + len(" now")
    assert has_link("priced on kaspapulse.com.") and not has_link("one kas buys 47 sats.")
    assert has_link("https://x.com/abc") and has_link("www.example.org")
    print("selftest ok: Signatur stimmt mit dem X-Testvektor ueberein, Link-Erkennung ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text")
    ap.add_argument("--reply", help="Selbstantwort (zweiter Post, antwortet auf den ersten)")
    ap.add_argument("--image", help="PNG/JPG bis 5 MB")
    ap.add_argument("--from-nod", help="data/number-of-day.json: post.x als Text, post.reply als Antwort (nur mit Link)")
    ap.add_argument("--key", help="Sperrschluessel, z. B. nod-2026-09-11")
    ap.add_argument("--log", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "x-post-log.json"))
    ap.add_argument("--delete", metavar="ID", help="einen Post loeschen und beenden")
    ap.add_argument("--delete-after", action="store_true", help="Testlauf: posten und sofort wieder loeschen")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.delete:
        delete(a.delete, creds_from_env())
        return 0
    return run(a)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print("FEHLER: %s" % exc, file=sys.stderr)
        sys.exit(1)
