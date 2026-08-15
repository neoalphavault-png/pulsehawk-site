#!/usr/bin/env python3
"""
pulsehawk - quellenpruefer, runde 2

Beantwortet genau eine frage: welche kostenlosen, schluessellosen datenquellen
fuer gold, aktien, krypto und waehrung antworten aus einer github action heraus?

Er postet nichts, schreibt nichts ins repo. Er druckt nur.

Stand nach runde 1 (15.08.2026, lauf im pulsehawk-site repo):
  laeuft   coingecko (btc, dominanz, marktkapitalisierung, pax-gold)
  laeuft   frankfurter (eurusd)
  gesperrt stooq, antwortet mit einer html-seite samt robots-meta
  gesperrt yahoo, HTTP 429 auf github-runner-adressen
  offen    aktien, dafuer gab es nach runde 1 gar keine quelle

Runde 2 prueft vor allem FRED, die zeitreihen-datenbank der federal reserve
st. louis. Sie liefert csv ohne schluessel und ist als behoerdenquelle auch
zitierfaehiger als ein finanzportal.

    python3 scripts/probe_sources.py
"""

import json
import sys
import time
import urllib.error
import urllib.request

TIMEOUT = 25
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s"


def get(url, accept="*/*"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        body = r.read()
    return r.status, body, (time.time() - t0) * 1000


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def probe_csv(url):
    """
    Toleranter csv-test. Egal wie die spalten heissen, gesucht wird die letzte
    zeile, deren zweites feld eine zahl ist. FRED schreibt an feiertagen einen
    punkt statt eines wertes, solche zeilen werden uebersprungen.
    """
    st, body, ms = get(url, "text/csv,*/*")
    text = body.decode("utf-8", "replace").strip()
    if text[:1] == "<":
        return False, "html statt csv, %r" % text[:56], ms
    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) < 2:
        return False, "nur %d zeile(n), %r" % (len(lines), text[:56]), ms
    letzte = None
    for line in reversed(lines[1:]):
        teile = [t.strip().strip('"') for t in line.split(",")]
        if len(teile) >= 2 and _num(teile[1]) is not None:
            letzte = (teile[0], _num(teile[1]))
            break
    if letzte is None:
        return False, "keine zeile mit zahl, kopf %r" % lines[0][:50], ms
    return True, "%d zeilen, zuletzt %s = %s" % (len(lines) - 1, letzte[0], letzte[1]), ms


def probe_yahoo(url):
    st, body, ms = get(url, "application/json")
    d = json.loads(body.decode("utf-8", "replace"))
    res = (d.get("chart") or {}).get("result") or []
    if not res:
        return False, "keine result-liste", ms
    r0 = res[0]
    ts = r0.get("timestamp") or []
    close = ((r0.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    vals = [c for c in close if c is not None]
    if not ts or not vals:
        return False, "leere zeitreihe", ms
    return True, "%d punkte, zuletzt %s = %.2f" % (
        len(vals), time.strftime("%Y-%m-%d", time.gmtime(ts[-1])), vals[-1]), ms


def probe_json(url, pick, label):
    st, body, ms = get(url, "application/json")
    d = json.loads(body.decode("utf-8", "replace"))
    v = pick(d)
    if v is None:
        return False, "wert nicht gefunden", ms
    return True, "%s = %s" % (label, v), ms


SOURCES = [
    # --- aktien, die offene luecke aus runde 1 -----------------------------
    ("aktien fred SP500",
     lambda: probe_csv(FRED % "SP500")),
    ("aktien fred NASDAQ100",
     lambda: probe_csv(FRED % "NASDAQ100")),
    ("aktien fred DJIA",
     lambda: probe_csv(FRED % "DJIA")),
    ("aktien fred WILL5000IND",
     lambda: probe_csv(FRED % "WILL5000IND")),
    ("aktien stooq leichtabruf",
     lambda: probe_csv("https://stooq.com/q/l/?s=%5Espx&f=sd2t2ohlcv&h&e=csv")),
    ("aktien stooq.pl leichtabruf",
     lambda: probe_csv("https://stooq.pl/q/l/?s=%5Espx&f=sd2t2ohlcv&h&e=csv")),
    ("aktien yahoo query2",
     lambda: probe_yahoo("https://query2.finance.yahoo.com/v8/finance/chart/%5EGSPC"
                         "?range=6mo&interval=1d")),
    # --- gold, zweite quelle zum gegenpruefen von pax-gold -----------------
    ("gold   fred goldpm",
     lambda: probe_csv(FRED % "GOLDPMGBD228NLBM")),
    ("gold   coingecko pax-gold",
     lambda: probe_json("https://api.coingecko.com/api/v3/simple/price"
                        "?ids=pax-gold&vs_currencies=usd",
                        lambda d: (d.get("pax-gold") or {}).get("usd"), "paxg usd")),
    # --- risikoappetit, kandidat fuer spaeter ------------------------------
    ("extra  fred VIXCLS",
     lambda: probe_csv(FRED % "VIXCLS")),
    # --- kontrollgruppe, lief in runde 1 ----------------------------------
    ("krypto coingecko dominanz",
     lambda: probe_json("https://api.coingecko.com/api/v3/global",
                        lambda d: round(((d.get("data") or {})
                                         .get("market_cap_percentage") or {})
                                        .get("btc", 0), 2), "btc dominanz prozent")),
    ("fx     frankfurter eurusd",
     lambda: probe_json("https://api.frankfurter.app/latest?from=EUR&to=USD",
                        lambda d: (d.get("rates") or {}).get("USD"), "eurusd")),
]


def main():
    print("pulsehawk quellenpruefer, runde 2")
    print("laufzeitpunkt %s utc\n" % time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
    results = []
    for name, fn in SOURCES:
        try:
            ok, detail, ms = fn()
        except urllib.error.HTTPError as exc:
            ok, detail, ms = False, "HTTP %s" % exc.code, 0.0
        except Exception as exc:  # noqa: BLE001
            ok, detail, ms = False, "%s" % str(exc)[:56], 0.0
        results.append((ok, name, detail))
        print("  %s %-28s %6.0f ms  %s"
              % ("OK  " if ok else "FEHL", name, ms, detail))
        time.sleep(1.2)

    print("\n%d von %d quellen haben geantwortet"
          % (sum(1 for ok, _, _ in results if ok), len(results)))
    for bereich in ("aktien", "gold"):
        treffer = [n.split(None, 1)[1].strip()
                   for ok, n, _ in results if ok and n.startswith(bereich)]
        if treffer:
            print("  %-7s nutzbar: %s" % (bereich, ", ".join(treffer)))
        else:
            print("  %-7s KEINE quelle. dann brauchen wir einen kostenlosen "
                  "api-schluessel" % bereich)
    return 0


if __name__ == "__main__":
    sys.exit(main())
