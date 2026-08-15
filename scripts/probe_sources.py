#!/usr/bin/env python3
"""
pulsehawk - quellenpruefer

Beantwortet genau eine frage: welche kostenlosen, schluessellosen datenquellen
fuer gold, den s&p 500 und krypto antworten aus einer github action heraus?

Claude kann das nicht selbst pruefen, seine sandbox hat keinen netzzugang nach
aussen. Statt eine quelle zu versprechen, die vielleicht geht, misst dieses
skript es. Ein lauf, eine tabelle, danach wissen wir es.

Es postet nichts, es schreibt nichts ins repo. Es druckt nur.

    python3 scripts/probe_sources.py
"""

import json
import sys
import time
import urllib.error
import urllib.request

TIMEOUT = 25
# ohne echten user agent antworten yahoo und stooq oft gar nicht oder mit 403
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")


def get(url, accept="*/*"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        body = r.read()
    return r.status, body, (time.time() - t0) * 1000


# ---------------------------------------------------------------- proben

def probe_csv(url, want_cols):
    """erwartet eine csv mit kopfzeile. gibt die letzte datenzeile zurueck."""
    st, body, ms = get(url, "text/csv,*/*")
    text = body.decode("utf-8", "replace").strip()
    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) < 2:
        return False, "nur %d zeile(n), inhalt %r" % (len(lines), text[:70]), ms
    head = lines[0].lower()
    missing = [c for c in want_cols if c not in head]
    if missing:
        return False, "spalten fehlen %s, kopf %r" % (missing, lines[0][:70]), ms
    return True, "%d zeilen, letzte %s" % (len(lines) - 1, lines[-1][:52]), ms


def probe_yahoo(url):
    st, body, ms = get(url, "application/json")
    d = json.loads(body.decode("utf-8", "replace"))
    res = (d.get("chart") or {}).get("result") or []
    if not res:
        return False, "keine result-liste, %r" % str(d)[:70], ms
    r0 = res[0]
    ts = r0.get("timestamp") or []
    close = ((r0.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    vals = [c for c in close if c is not None]
    if not ts or not vals:
        return False, "leere zeitreihe", ms
    day = time.strftime("%Y-%m-%d", time.gmtime(ts[-1]))
    return True, "%d punkte, zuletzt %s = %.2f" % (len(vals), day, vals[-1]), ms


def probe_json(url, pick, label):
    st, body, ms = get(url, "application/json")
    d = json.loads(body.decode("utf-8", "replace"))
    v = pick(d)
    if v is None:
        return False, "wert nicht gefunden, %r" % str(d)[:70], ms
    return True, "%s = %s" % (label, v), ms


SOURCES = [
    # gold
    ("gold   stooq xauusd",
     lambda: probe_csv("https://stooq.com/q/d/l/?s=xauusd&i=d", ["date", "close"])),
    ("gold   yahoo GC=F",
     lambda: probe_yahoo("https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
                         "?range=6mo&interval=1d")),
    ("gold   coingecko pax-gold",
     lambda: probe_json("https://api.coingecko.com/api/v3/simple/price"
                        "?ids=pax-gold&vs_currencies=usd",
                        lambda d: (d.get("pax-gold") or {}).get("usd"), "paxg usd")),
    # aktien
    ("aktien stooq ^spx",
     lambda: probe_csv("https://stooq.com/q/d/l/?s=%5Espx&i=d", ["date", "close"])),
    ("aktien yahoo ^GSPC",
     lambda: probe_yahoo("https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC"
                         "?range=6mo&interval=1d")),
    # krypto, bekannt funktionierend, dient als kontrollgruppe
    ("krypto coingecko btc",
     lambda: probe_json("https://api.coingecko.com/api/v3/simple/price"
                        "?ids=bitcoin&vs_currencies=usd",
                        lambda d: (d.get("bitcoin") or {}).get("usd"), "btc usd")),
    ("krypto coingecko dominanz",
     lambda: probe_json("https://api.coingecko.com/api/v3/global",
                        lambda d: round(((d.get("data") or {})
                                         .get("market_cap_percentage") or {})
                                        .get("btc", 0), 2), "btc dominanz prozent")),
    ("krypto coingecko marktkap",
     lambda: probe_json("https://api.coingecko.com/api/v3/global",
                        lambda d: round(((d.get("data") or {})
                                         .get("total_market_cap") or {})
                                        .get("usd", 0) / 1e12, 3), "gesamt billionen usd")),
    # waehrung, fuer die euro-umrechnung
    ("fx     frankfurter eurusd",
     lambda: probe_json("https://api.frankfurter.app/latest?from=EUR&to=USD",
                        lambda d: (d.get("rates") or {}).get("USD"), "eurusd")),
]


def main():
    print("pulsehawk quellenpruefer")
    print("laufzeitpunkt %s utc\n" % time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
    ok_count = 0
    results = []
    for name, fn in SOURCES:
        try:
            ok, detail, ms = fn()
        except urllib.error.HTTPError as exc:
            ok, detail, ms = False, "HTTP %s" % exc.code, 0.0
        except Exception as exc:  # noqa: BLE001
            ok, detail, ms = False, "%s" % str(exc)[:60], 0.0
        results.append((ok, name, detail, ms))
        print("  %s %-26s %6.0f ms  %s"
              % ("OK  " if ok else "FEHL", name, ms, detail))
        if ok:
            ok_count += 1
        time.sleep(1.5)  # hoeflich bleiben, coingecko drosselt sonst

    print("\n%d von %d quellen haben geantwortet" % (ok_count, len(SOURCES)))
    for bereich, praefix in (("gold", "gold"), ("aktien", "aktien")):
        treffer = [n for ok, n, _, _ in results if ok and n.startswith(praefix)]
        if treffer:
            print("  %-7s nutzbar: %s" % (bereich, ", ".join(t.split()[1] for t in treffer)))
        else:
            print("  %-7s KEINE quelle, follow the money braucht hier eine loesung" % bereich)
    return 0


if __name__ == "__main__":
    sys.exit(main())
