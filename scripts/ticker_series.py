#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ticker_series.py - der Scanner im Ticker-Modus: Tagesschluesse EINES Titels
seit einem Startdatum, split-bereinigt, fuer die Tagesserie
"POV: stock instead of product" (Domino's 2010, GoPro, GTA ...).

Laeuft als GitHub Action (ticker.yml), weil api.tiingo.com aus dem
Claude-Container gesperrt ist. Ergebnis: data/ticker/<TICKER>.json mit der
ganzen Reihe plus Gegenpruefung aus einer zweiten Quelle (Stooq, volle
Historie ohne Schluessel; faellt sie aus, Yahoo fuer den letzten Schluss).
Doktrin wie multibagger.py: nur selbst gezaehlte Zahlen, und ohne
Gegenpruefung geht die Zahl nicht raus - das Feld "verified" sagt es.

  python3 scripts/ticker_series.py DPZ --start 2010-01-04
  python3 scripts/ticker_series.py --selftest
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import multibagger as mb  # fetch, tiingo_series-Logik, stooq/yahoo

DATA = os.path.join(mb.REPO, "data", "ticker")
TOL = 0.015


def tiingo_full(symbol, start):
    if not mb.TIINGO_KEY:
        raise RuntimeError("kein TIINGO_API_KEY")
    url = ("https://api.tiingo.com/tiingo/daily/%s/prices?startDate=%s&token=%s"
           % (urllib.parse.quote(symbol.replace(".", "-")), start, mb.TIINGO_KEY))
    rows = json.loads(mb.fetch(url))
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("tiingo antwortet ohne reihe fuer %s" % symbol)
    rows.sort(key=lambda r: r.get("date", ""))
    ser, factor = [], 1.0
    for r in reversed(rows):
        c = r.get("close")
        if c is None:
            continue
        ser.append((r["date"][:10], float(c) / factor))
        sf = r.get("splitFactor") or 1.0
        if sf and sf != 1.0:
            factor *= float(sf)
    ser.sort()
    if len(ser) < 20:
        raise RuntimeError("tiingo liefert zu wenig fuer %s (%d)" % (symbol, len(ser)))
    return ser


def on_or_after(ser, iso):
    for d, v in ser:
        if d >= iso:
            return d, v
    return None


def check(ser_a, ser_b, iso):
    a, b = on_or_after(ser_a, iso), on_or_after(ser_b, iso)
    if not a or not b or a[0] != b[0]:
        return None
    return {"date": a[0], "a": a[1], "b": b[1], "diff": abs(a[1] / b[1] - 1.0)}


def summary(ser, start):
    first = on_or_after(ser, start)
    last = ser[-1]
    mult = last[1] / first[1]
    return {
        "start_date": first[0], "start_close": round(first[1], 4),
        "last_date": last[0], "last_close": round(last[1], 4),
        "mult": round(mult, 4), "from_1000": round(1000.0 * mult, 2),
        "high": max(ser, key=lambda x: x[1])[0], "high_close": round(max(v for _, v in ser), 4),
    }


def run(symbol, start):
    symbol = symbol.upper().strip()
    ser = tiingo_full(symbol, start)
    out = {"ticker": symbol, "source": "tiingo (close, split-bereinigt)", "start": start,
           "fetched": mb.today_iso(), "rows": [[d, round(v, 4)] for d, v in ser],
           "summary": summary(ser, start), "checks": [], "verified": False}
    second = None
    for name, fn in (("stooq", mb.stooq_series), ("yahoo", mb.yahoo_series)):
        try:
            second = (name, fn(symbol))
            break
        except Exception as exc:  # noqa: BLE001
            out["checks"].append({"source": name, "error": mb._hide(str(exc))[:120]})
    if second:
        name, ser2 = second
        for iso in (out["summary"]["start_date"], ser[-1][0]):
            c = check(ser, ser2, iso)
            if c:
                c["source"] = name
                out["checks"].append(c)
        diffs = [c["diff"] for c in out["checks"] if "diff" in c]
        # Stooq/Yahoo liefern dividendenbereinigte Reihen erst bei langen Fenstern
        # abweichend; verifiziert heisst: letzter Schluss innerhalb 1,5 %.
        last_ok = [c for c in out["checks"] if c.get("date") == ser[-1][0] and c["diff"] <= TOL]
        out["verified"] = bool(last_ok)
        out["max_diff"] = round(max(diffs), 5) if diffs else None
    os.makedirs(DATA, exist_ok=True)
    path = os.path.join(DATA, "%s.json" % symbol)
    mb.save(path, out)
    s = out["summary"]
    print("%s: %s %.2f -> %s %.2f = %.2fx, $1.000 -> $%s, verified=%s"
          % (symbol, s["start_date"], s["start_close"], s["last_date"], s["last_close"],
             s["mult"], format(s["from_1000"], ","), out["verified"]))
    for c in out["checks"]:
        print("  check:", c)
    return out


def selftest():
    ser = [("2010-01-04", 10.0), ("2010-01-05", 11.0), ("2026-09-09", 50.0)]
    s = summary(ser, "2010-01-01")
    assert s["start_date"] == "2010-01-04" and s["mult"] == 5.0 and s["from_1000"] == 5000.0, s
    c = check(ser, [("2010-01-04", 10.1), ("2026-09-09", 50.2)], "2010-01-03")
    assert c and c["date"] == "2010-01-04" and abs(c["diff"] - 0.0099) < 0.001, c
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker", nargs="?")
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.ticker:
        ap.error("ticker fehlt")
    dt.date.fromisoformat(a.start)
    run(a.ticker, a.start)


if __name__ == "__main__":
    main()
