#!/usr/bin/env python3
"""
pulsehawk - quellenpruefer, runde 3

Beantwortet genau eine frage: worauf koennen wir FOLLOW THE MONEY bauen?

Er postet nichts, schreibt nichts ins repo, und er druckt den schluessel
niemals. Er sagt nur, ob einer gesetzt ist.

Stand nach zwei runden (15.08.2026, laeufe im pulsehawk-site repo):
  laeuft   coingecko (btc, dominanz, marktkapitalisierung, pax-gold)
  laeuft   frankfurter (eurusd)
  gesperrt stooq, html statt csv und HTTP 404 auf den leichtabruf
  gesperrt yahoo, HTTP 429 auf beiden hosts
  gesperrt fred, sechs von sechs reihen laufen in den timeout
  ergebnis fuer aktien gibt es keinen schluessellosen weg

Runde 3 prueft deshalb twelve data mit dem hinterlegten schluessel. Getestet
wird bewusst ETFs statt indizes. Ein index ist eine rechengroesse, ein ETF ist
ein topf mit echtem geld darin, und "wo sitzt das geld" ist die frage des
formats.

    TWELVEDATA_API_KEY=... python3 scripts/probe_sources.py
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 25
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")
TD_KEY = os.environ.get("TWELVEDATA_API_KEY", "").strip()
TD = "https://api.twelvedata.com"


def get(url, accept="*/*"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        body = r.read()
    return r.status, body, (time.time() - t0) * 1000


def _hide(text):
    """sicherheitsnetz. falls der schluessel je in eine meldung geraet."""
    return text.replace(TD_KEY, "***") if TD_KEY else text


# ---------------------------------------------------------------- twelvedata

def td_quote(symbol):
    """letzter kurs plus tagesveraenderung. ein credit."""
    if not TD_KEY:
        return False, "kein schluessel gesetzt", 0.0
    url = "%s/quote?symbol=%s&apikey=%s" % (TD, urllib.parse.quote(symbol), TD_KEY)
    st, body, ms = get(url, "application/json")
    d = json.loads(body.decode("utf-8", "replace"))
    if str(d.get("status", "")).lower() == "error":
        return False, _hide(str(d.get("message", ""))[:74]), ms
    close = d.get("close") or d.get("price")
    if close is None:
        return False, _hide(str(d)[:74]), ms
    chg = d.get("percent_change")
    return True, "%s = %s%s" % (d.get("symbol", symbol), close,
                                ("  tag %s%%" % chg) if chg else ""), ms


def td_series(symbol, points=90):
    """zeitreihe, das braucht die grafik wirklich. prueft laenge und rand."""
    if not TD_KEY:
        return False, "kein schluessel gesetzt", 0.0
    url = ("%s/time_series?symbol=%s&interval=1day&outputsize=%d&apikey=%s"
           % (TD, urllib.parse.quote(symbol), points, TD_KEY))
    st, body, ms = get(url, "application/json")
    d = json.loads(body.decode("utf-8", "replace"))
    if str(d.get("status", "")).lower() == "error":
        return False, _hide(str(d.get("message", ""))[:74]), ms
    vals = d.get("values") or []
    if len(vals) < 2:
        return False, "nur %d punkte" % len(vals), ms
    neu, alt = vals[0], vals[-1]
    return True, "%d punkte, %s bis %s, zuletzt %s" % (
        len(vals), alt.get("datetime"), neu.get("datetime"), neu.get("close")), ms


# ---------------------------------------------------------------- keyless

def probe_json(url, pick, label):
    st, body, ms = get(url, "application/json")
    d = json.loads(body.decode("utf-8", "replace"))
    v = pick(d)
    if v is None:
        return False, "wert nicht gefunden", ms
    return True, "%s = %s" % (label, v), ms


SOURCES = [
    # --- die luecke, aktien --------------------------------------------
    ("aktien td SPY reihe",      lambda: td_series("SPY")),
    ("aktien td SPY kurs",       lambda: td_quote("SPY")),
    ("aktien td QQQ kurs",       lambda: td_quote("QQQ")),
    ("aktien td SPX index",      lambda: td_quote("SPX")),
    # --- gold, zweite quelle neben pax-gold ------------------------------
    ("gold   td GLD reihe",      lambda: td_series("GLD")),
    ("gold   td XAU/USD kurs",   lambda: td_quote("XAU/USD")),
    ("gold   coingecko pax-gold",
     lambda: probe_json("https://api.coingecko.com/api/v3/simple/price"
                        "?ids=pax-gold&vs_currencies=usd",
                        lambda d: (d.get("pax-gold") or {}).get("usd"), "paxg usd")),
    # --- krypto und waehrung, laufen bereits -----------------------------
    ("krypto td BTC/USD reihe",  lambda: td_series("BTC/USD")),
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
    print("pulsehawk quellenpruefer, runde 3")
    print("laufzeitpunkt %s utc" % time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
    print("twelvedata schluessel %s\n"
          % ("gesetzt, %d zeichen" % len(TD_KEY) if TD_KEY else "FEHLT"))

    results = []
    for name, fn in SOURCES:
        try:
            ok, detail, ms = fn()
        except urllib.error.HTTPError as exc:
            ok, detail, ms = False, "HTTP %s" % exc.code, 0.0
        except Exception as exc:  # noqa: BLE001
            ok, detail, ms = False, _hide(str(exc))[:60], 0.0
        results.append((ok, name, detail))
        print("  %s %-26s %6.0f ms  %s"
              % ("OK  " if ok else "FEHL", name, ms, detail))
        # twelvedata basic erlaubt 8 credits pro minute, deshalb nur dort
        # bremsen. die schluessellosen quellen brauchen das nicht.
        time.sleep(8 if " td " in name else 1)

    print("\n%d von %d quellen haben geantwortet"
          % (sum(1 for ok, _, _ in results if ok), len(results)))
    for bereich in ("aktien", "gold", "krypto"):
        treffer = [n.split(None, 1)[1].strip()
                   for ok, n, _ in results if ok and n.startswith(bereich)]
        print("  %-7s %s" % (bereich,
                             ("nutzbar: " + ", ".join(treffer)) if treffer
                             else "KEINE quelle"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
