#!/usr/bin/env python3
"""
pulsehawk - marktlogger

Er schreibt jeden tag eine zeile in data/market-log.json. Aus diesen zeilen
wachsen zwei dinge, die wir sonst nie bekommen wuerden.

  1. die altcoin-reihe. coingecko liefert dominanz und gesamtmarktkapital
     nur als tageswert, ohne historie. wer sie haben will, muss sie selbst
     mitschreiben. jeder tag den wir nicht loggen, fehlt spaeter fuer immer.
  2. eine sauber nach kalendertagen ausgerichtete reihe fuer FOLLOW THE MONEY.
     twelve data und coingecko liefern gleich viele punkte ueber verschiedene
     zeitraeume, weil krypto sieben tage die woche handelt. wir speichern
     deshalb pro kalendertag, nicht pro datenpunkt.

Er postet nichts und er druckt den schluessel niemals.

    python3 scripts/market_log.py            taeglicher lauf
    python3 scripts/market_log.py --backfill einmalig, holt 90 tage historie
    python3 scripts/market_log.py --selftest rechnet ohne netz
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LOG = os.path.join(REPO, "data", "market-log.json")

TIMEOUT = 25
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")
TD_KEY = os.environ.get("TWELVEDATA_API_KEY", "").strip()
TD = "https://api.twelvedata.com"
CG = "https://api.coingecko.com/api/v3"

# die vier sprossen der risikoleiter. gold, aktien, bitcoin, altcoins.
# eth steht so lange fuer die oberste sprosse, bis unsere eigene
# dominanzreihe lang genug ist, um daraus den altcoin-anteil zu rechnen.
FIELDS = ["gld", "spy", "btc", "eth", "btc_dom", "total_mcap"]


def _hide(text):
    """sicherheitsnetz. falls der schluessel je in eine meldung geraet."""
    return text.replace(TD_KEY, "***") if TD_KEY else text


def get_json(url, accept="application/json"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


# ------------------------------------------------------------------ speicher

def load_log(path=LOG):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else []


def merge(rows, new_rows):
    """
    fuegt zeilen ein und ueberschreibt dabei nur die felder, die wirklich
    einen wert haben. so kann der taegliche lauf eine zeile ergaenzen, die
    der backfill angelegt hat, ohne sie kaputtzumachen.
    """
    by_day = {r["d"]: dict(r) for r in rows}
    for new in new_rows:
        day = new.get("d")
        if not day:
            continue
        cur = by_day.setdefault(day, {"d": day})
        for key in FIELDS:
            val = new.get(key)
            if val is not None:
                cur[key] = val
    out = []
    for day in sorted(by_day):
        row = {"d": day}
        for key in FIELDS:
            if by_day[day].get(key) is not None:
                row[key] = by_day[day][key]
        out.append(row)
    return out


def save_log(rows, path=LOG):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
        fh.write("\n")


# ------------------------------------------------------------------- quellen

def td_series(symbol, points):
    """tagesschlusskurse von twelve data. ein credit."""
    if not TD_KEY:
        raise RuntimeError("kein twelvedata schluessel gesetzt")
    url = ("%s/time_series?symbol=%s&interval=1day&outputsize=%d&apikey=%s"
           % (TD, urllib.parse.quote(symbol), points, TD_KEY))
    data = get_json(url)
    if str(data.get("status", "")).lower() == "error":
        raise RuntimeError(_hide(str(data.get("message", ""))[:120]))
    out = {}
    for row in data.get("values") or []:
        day = (row.get("datetime") or "")[:10]
        close = row.get("close")
        if day and close is not None:
            out[day] = round(float(close), 4)
    if not out:
        raise RuntimeError("keine werte fuer %s" % symbol)
    return out


def cg_chart(coin, days):
    """tageswerte von coingecko. der zeitstempel ist millisekunden utc."""
    url = "%s/coins/%s/market_chart?vs_currency=usd&days=%d" % (CG, coin, days)
    data = get_json(url)
    out = {}
    for stamp, price in data.get("prices") or []:
        day = time.strftime("%Y-%m-%d", time.gmtime(stamp / 1000.0))
        out[day] = round(float(price), 6)  # der spaetere wert des tages gewinnt
    if not out:
        raise RuntimeError("keine werte fuer %s" % coin)
    return out


def cg_global():
    """dominanz und gesamtmarktkapital. gibt es nur als tageswert."""
    data = (get_json("%s/global" % CG) or {}).get("data") or {}
    dom = (data.get("market_cap_percentage") or {}).get("btc")
    total = (data.get("total_market_cap") or {}).get("usd")
    return (round(float(dom), 3) if dom is not None else None,
            round(float(total)) if total is not None else None)


def cg_price(ids):
    url = "%s/simple/price?ids=%s&vs_currencies=usd" % (CG, ",".join(ids))
    data = get_json(url)
    return {k: (v or {}).get("usd") for k, v in data.items()}


# --------------------------------------------------------------------- laeufe

def today():
    return time.strftime("%Y-%m-%d", time.gmtime())


def run_backfill(days=90):
    """
    einmalig. holt so viel historie, wie die quellen hergeben.
    dominanz und gesamtmarktkapital fehlen hier bewusst, die gibt es
    rueckwirkend nicht. sie kommen ab dem ersten taeglichen lauf dazu.
    """
    rows = {}

    def put(day, key, value):
        rows.setdefault(day, {"d": day})[key] = value

    plan = [("gld", lambda: td_series("GLD", days), 8),
            ("spy", lambda: td_series("SPY", days), 8),
            ("btc", lambda: cg_chart("bitcoin", days), 2),
            ("eth", lambda: cg_chart("ethereum", days), 2)]

    for key, fetch, pause in plan:
        try:
            series = fetch()
        except Exception as exc:  # noqa: BLE001
            print("  FEHL %-4s %s" % (key, _hide(str(exc))[:90]))
            continue
        for day, value in series.items():
            put(day, key, value)
        print("  OK   %-4s %d tage, %s bis %s"
              % (key, len(series), min(series), max(series)))
        time.sleep(pause)

    return [rows[day] for day in sorted(rows)]


def run_daily():
    """der taegliche lauf. eine zeile fuer heute."""
    day = today()
    row = {"d": day}

    try:
        for key, symbol in (("gld", "GLD"), ("spy", "SPY")):
            series = td_series(symbol, 5)
            newest = max(series)
            # an wochenenden und feiertagen liefert der etf keinen neuen tag.
            # dann schreiben wir nichts, statt einen alten kurs auf heute zu
            # datieren. die luecke ist die ehrliche antwort.
            if newest == day:
                row[key] = series[newest]
                print("  OK   %-9s %s" % (key, series[newest]))
            else:
                print("  leer %-9s letzter handelstag %s" % (key, newest))
            time.sleep(8)
    except Exception as exc:  # noqa: BLE001
        print("  FEHL aktien/gold %s" % _hide(str(exc))[:90])

    try:
        prices = cg_price(["bitcoin", "ethereum"])
        if prices.get("bitcoin") is not None:
            row["btc"] = round(float(prices["bitcoin"]), 6)
        if prices.get("ethereum") is not None:
            row["eth"] = round(float(prices["ethereum"]), 6)
        print("  OK   krypto    btc %s  eth %s"
              % (row.get("btc"), row.get("eth")))
    except Exception as exc:  # noqa: BLE001
        print("  FEHL krypto %s" % str(exc)[:90])

    time.sleep(2)
    try:
        dom, total = cg_global()
        if dom is not None:
            row["btc_dom"] = dom
        if total is not None:
            row["total_mcap"] = total
        print("  OK   global    dominanz %s prozent  gesamt %s"
              % (row.get("btc_dom"), row.get("total_mcap")))
    except Exception as exc:  # noqa: BLE001
        print("  FEHL global %s" % str(exc)[:90])

    return [row] if len(row) > 1 else []


# ------------------------------------------------------------------ selftest

def run_selftest():
    fails = []

    def check(name, got, want):
        if got != want:
            fails.append("%s\n    ist  %r\n    soll %r" % (name, got, want))

    # merge legt neue tage an und sortiert
    got = merge([{"d": "2026-08-02", "btc": 2}], [{"d": "2026-08-01", "btc": 1}])
    check("merge sortiert", [r["d"] for r in got], ["2026-08-01", "2026-08-02"])

    # merge ergaenzt eine bestehende zeile, statt sie zu ersetzen
    got = merge([{"d": "2026-08-01", "gld": 400.0}],
                [{"d": "2026-08-01", "btc_dom": 57.3}])
    check("merge ergaenzt", got, [{"d": "2026-08-01", "gld": 400.0, "btc_dom": 57.3}])

    # ein zweiter lauf am selben tag ueberschreibt, er dupliziert nicht
    got = merge([{"d": "2026-08-01", "btc": 100.0}],
                [{"d": "2026-08-01", "btc": 101.0}])
    check("merge ist idempotent", got, [{"d": "2026-08-01", "btc": 101.0}])

    # ein fehlender wert loescht keinen vorhandenen
    got = merge([{"d": "2026-08-01", "spy": 776.34}],
                [{"d": "2026-08-01", "spy": None, "btc": 5.0}])
    check("kein wert loescht nichts", got,
          [{"d": "2026-08-01", "spy": 776.34, "btc": 5.0}])

    # die feldreihenfolge steht fest, damit der diff im repo lesbar bleibt
    got = merge([], [{"d": "2026-08-01", "total_mcap": 3, "gld": 1, "btc": 2}])
    check("feldreihenfolge", list(got[0].keys()), ["d", "gld", "btc", "total_mcap"])

    # der schluessel taucht in keiner meldung auf
    global TD_KEY
    alt, TD_KEY = TD_KEY, "GEHEIM123"
    try:
        check("schluessel maskiert", _hide("fehler mit GEHEIM123 im text"),
              "fehler mit *** im text")
    finally:
        TD_KEY = alt

    # ein leerer log faellt nicht um
    check("leerer log", merge([], []), [])

    if fails:
        print("selftest FEHLGESCHLAGEN")
        for f in fails:
            print("  " + f)
        return 1
    print("selftest ok, 7 faelle")
    return 0


def main(argv):
    if "--selftest" in argv:
        return run_selftest()

    modus = "backfill" if "--backfill" in argv else "taeglich"
    print("pulsehawk marktlogger, %s" % modus)
    print("laufzeitpunkt %s utc" % time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
    print("twelvedata schluessel %s\n"
          % ("gesetzt, %d zeichen" % len(TD_KEY) if TD_KEY else "FEHLT"))

    neu = run_backfill() if modus == "backfill" else run_daily()
    if not neu:
        print("\nkeine neuen werte, log bleibt unveraendert")
        return 0

    rows = merge(load_log(), neu)
    save_log(rows)
    voll = [r for r in rows if all(r.get(k) is not None for k in ("gld", "spy", "btc", "eth"))]
    mit_dom = [r for r in rows if r.get("btc_dom") is not None]
    print("\nlog hat jetzt %d tage, %s bis %s" % (len(rows), rows[0]["d"], rows[-1]["d"]))
    print("  davon %d tage mit allen vier kursen" % len(voll))
    print("  davon %d tage mit dominanz, die altcoin-reihe waechst ab hier"
          % len(mit_dom))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
