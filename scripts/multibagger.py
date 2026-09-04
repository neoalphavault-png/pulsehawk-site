#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
multibagger.py  -  Scanner fuer das Format 365 DAYS LATER (dienstags).

Findet US-Aktien, die sich in einem Jahr vervielfacht haben, GEZAEHLT aus
Tagesschluessen (Twelve Data), und legt den besten, gegengeprueften Kandidaten
in data/multibagger-pick.json - fertig fuer den Short-Generator.

Doktrin:
  - Nur selbst gezaehlte Zahlen. Der Kandidat wird vor der Auswahl aus einer
    zweiten Quelle (Stooq) unabhaengig nachgerechnet. Weicht er >1.5% ab,
    fliegt er raus.
  - Der Unternehmens-Satz kommt aus einer zitierbaren Quelle (Wikipedia-
    Einleitung): WAS die Firma macht, nie WARUM der Kurs lief.
  - Der Massstab steht dabei: wie viele S&P-500-Aktien haben verdoppelt,
    und wie liefen S&P 500 und Gold im selben Jahr (eigenes Archiv).
  - Rotation: ein Ticker kommt fruehestens nach 180 Tagen wieder.

Ablauf pro Lauf (taeglich):
  1. Universum (S&P 500/400/600 + Nasdaq-100 von Wikipedia) hoechstens einmal
     pro Woche neu laden -> data/multibagger-universe.json
  2. Naechste N Ticker (TD_PER_DAY, Standard 700) per Twelve Data abrufen,
     1-Jahres-Vielfaches rechnen -> data/multibagger-scan.json (Cursor in
     data/multibagger-state.json, laeuft rund)
  3. Auswahl + Gegenpruefung + Basisrate -> data/multibagger-pick.json

  python3 scripts/multibagger.py            # normaler lauf
  python3 scripts/multibagger.py --selftest # ohne netz
  python3 scripts/multibagger.py --pick-only
  python3 scripts/multibagger.py --mark-used NVDA   # nach dem bau eintragen
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data")
P_UNIVERSE = os.path.join(DATA, "multibagger-universe.json")
P_SCAN = os.path.join(DATA, "multibagger-scan.json")
P_STATE = os.path.join(DATA, "multibagger-state.json")
P_PICK = os.path.join(DATA, "multibagger-pick.json")
P_LOG = os.path.join(DATA, "multibagger-log.json")
P_HIST = os.path.join(DATA, "history.json")
P_MLOG = os.path.join(DATA, "market-log.json")

TIMEOUT = 25
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")
TD_KEY = os.environ.get("TWELVEDATA_API_KEY", "").strip()
# zweitquellen mit schluessel: werden nicht per ip gesperrt wie stooq/yahoo
# von github-rechnern (beobachtet 04.09.2026: stooq tageslimit, yahoo 429).
TIINGO_KEY = os.environ.get("TIINGO_API_KEY", "").strip()
AV_KEY = os.environ.get("ALPHAVANTAGE_API_KEY", "").strip()
TD = "https://api.twelvedata.com"
TD_PER_MIN = int(os.environ.get("TD_PER_MIN", "8"))     # free plan: 8/min
TD_PER_DAY = int(os.environ.get("TD_PER_DAY", "700"))   # free plan: 800/tag
UNIVERSE_MAX_AGE = 7      # tage
SCAN_FRESH = 6            # tage, aelter gilt nicht mehr als frisch
MIN_MULT = 2.0            # ab verdoppelung ist es ein kandidat
ROTATION_DAYS = 180
VERIFY_TOL = 0.015        # 1.5 prozent abweichung zwischen den quellen
MIN_PRICE_1Y = 1.0        # penny-stocks raus (unter 1 dollar vor einem jahr)

WIKI_LISTS = [
    ("sp500", "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"),
    ("sp400", "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"),
    ("sp600", "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies"),
    ("ndx", "https://en.wikipedia.org/wiki/Nasdaq-100"),
]


def _hide(text):
    return text.replace(TD_KEY, "***") if TD_KEY else text


def today_iso():
    return str(dt.datetime.now(dt.timezone.utc).date())


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def fetch(url, accept="application/json", tries=2, pause=6):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": accept})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            last = exc
            if i + 1 < tries:
                time.sleep(pause * (i + 1))
    raise last


# ---------------------------------------------------------------- universum

class _Tables(HTMLParser):
    """zieht alle tabellen als zeilen von zellen (text, erster link) heraus."""

    def __init__(self):
        super().__init__()
        self.tables, self._t, self._row, self._cell = [], None, None, None
        self._href = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self._t = []
        elif tag == "tr" and self._t is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell, self._href = [], None
        elif tag == "a" and self._cell is not None and self._href is None:
            self._href = a.get("href")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append((" ".join("".join(self._cell).split()), self._href))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self._t.append(self._row)
            self._row = None
        elif tag == "table" and self._t is not None:
            self.tables.append(self._t)
            self._t = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def parse_constituents(page_html, index_name):
    """findet die tabelle mit symbol/ticker + firma, liefert zeilen."""
    p = _Tables()
    p.feed(page_html)
    out = []
    for table in p.tables:
        if not table:
            continue
        head = [c[0].lower() for c in table[0]]
        def col(*names):
            for i, h in enumerate(head):
                if any(n in h for n in names):
                    return i
            return None
        c_sym = col("symbol", "ticker")
        c_name = col("security", "company")
        c_sec = col("gics sector", "sector")
        c_sub = col("sub-industry", "gics sub")
        if c_sym is None or c_name is None:
            continue
        for row in table[1:]:
            if len(row) <= max(c_sym, c_name):
                continue
            sym = row[c_sym][0].strip().upper().replace(".", "-")
            if not re.fullmatch(r"[A-Z0-9-]{1,6}", sym):
                continue
            name, href = row[c_name]
            wiki = None
            if href and href.startswith("/wiki/"):
                wiki = urllib.parse.unquote(href[len("/wiki/"):])
            out.append({
                "ticker": sym, "name": name, "wiki": wiki,
                "sector": row[c_sec][0] if c_sec is not None and len(row) > c_sec else None,
                "industry": row[c_sub][0] if c_sub is not None and len(row) > c_sub else None,
                "index": index_name,
            })
        if out:
            break
    return out


def build_universe():
    seen, uni = {}, []
    for idx, url in WIKI_LISTS:
        try:
            rows = parse_constituents(fetch(url, accept="text/html"), idx)
        except Exception as exc:  # noqa: BLE001
            print("universum %s uebersprungen (%s)" % (idx, str(exc)[:80]))
            continue
        print("universum %s: %d titel" % (idx, len(rows)))
        for r in rows:
            if r["ticker"] in seen:
                seen[r["ticker"]]["indices"].append(idx)
                continue
            r["indices"] = [idx]
            r.pop("index", None)
            seen[r["ticker"]] = r
            uni.append(r)
    if len(uni) < 400:
        raise RuntimeError("universum zu klein (%d), wikipedia-parsing pruefen" % len(uni))
    return {"date": today_iso(), "count": len(uni), "rows": uni}


# ---------------------------------------------------------------- kurse

def td_series(symbol, points=280):
    if not TD_KEY:
        raise RuntimeError("kein twelvedata schluessel gesetzt")
    url = ("%s/time_series?symbol=%s&interval=1day&outputsize=%d&apikey=%s"
           % (TD, urllib.parse.quote(symbol), points, TD_KEY))
    data = json.loads(fetch(url))
    if str(data.get("status", "")).lower() == "error":
        raise RuntimeError(_hide(str(data.get("message", ""))[:120]))
    ser = []
    for row in data.get("values") or []:
        day, close = (row.get("datetime") or "")[:10], row.get("close")
        if day and close is not None:
            ser.append((day, float(close)))
    ser.sort()
    if len(ser) < 200:
        raise RuntimeError("zu wenig kurse fuer %s (%d)" % (symbol, len(ser)))
    return ser


def one_year(ser):
    """letzter schluss, schluss am/nach dem tag vor 365 tagen, vielfaches."""
    d_now, c_now = ser[-1]
    target = (dt.date.fromisoformat(d_now) - dt.timedelta(days=365)).isoformat()
    then = next(((d, c) for d, c in ser if d >= target), None)
    if not then or then[1] <= 0:
        raise RuntimeError("kein kurs vor einem jahr")
    span = [c for d, c in ser if d >= then[0]]
    return {
        "d": d_now, "close": round(c_now, 4),
        "d_1y": then[0], "close_1y": round(then[1], 4),
        "mult": round(c_now / then[1], 4),
        "low": round(min(span), 4), "high": round(max(span), 4),
    }


def stooq_series(symbol):
    """zweite quelle fuer die gegenpruefung, csv ohne schluessel."""
    url = "https://stooq.com/q/d/l/?s=%s.us&i=d" % urllib.parse.quote(symbol.lower())
    txt = fetch(url, accept="text/csv")
    ser = []
    for line in txt.splitlines()[1:]:
        parts = line.split(",")
        if len(parts) >= 5 and parts[0][:4].isdigit():
            try:
                ser.append((parts[0][:10], float(parts[4])))
            except ValueError:
                pass
    ser.sort()
    if len(ser) < 200:
        raise RuntimeError("stooq liefert zu wenig fuer %s" % symbol)
    return ser


def yahoo_series(symbol):
    """dritte quelle, json ohne schluessel. tagesschluesse der letzten zwei jahre.
    gebaut am 04.09.2026, nachdem stooq von github-rechnern nur noch die
    tageslimit-seite lieferte und damit jeder kandidat unpruefbar blieb."""
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/%s"
           "?range=2y&interval=1d&events=none" % urllib.parse.quote(symbol.replace(".", "-")))
    js = json.loads(fetch(url, tries=3, pause=8))
    try:
        res = js["chart"]["result"][0]
        ts = res["timestamp"]
        cl = res["indicators"]["quote"][0]["close"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("yahoo liefert nichts fuer %s" % symbol)
    ser = []
    for t, c in zip(ts, cl):
        if c is None:
            continue
        d = dt.datetime.utcfromtimestamp(t).date().isoformat()
        ser.append((d, float(c)))
    ser.sort()
    if len(ser) < 200:
        raise RuntimeError("yahoo liefert zu wenig fuer %s" % symbol)
    return ser


def tiingo_series(symbol):
    """tiingo, kostenloser schluessel (50 symbole/stunde). close nur um splits
    bereinigt, damit es mit twelve data vergleichbar bleibt (adjClose dort
    enthaelt auch dividenden)."""
    if not TIINGO_KEY:
        raise RuntimeError("kein TIINGO_API_KEY")
    start = (dt.date.today() - dt.timedelta(days=760)).isoformat()
    url = ("https://api.tiingo.com/tiingo/daily/%s/prices?startDate=%s&token=%s"
           % (urllib.parse.quote(symbol.replace(".", "-")), start, TIINGO_KEY))
    rows = json.loads(fetch(url))
    if not isinstance(rows, list):
        raise RuntimeError("tiingo antwortet ohne reihe fuer %s" % symbol)
    rows.sort(key=lambda r: r.get("date", ""))
    # splits rueckwaerts aufmultiplizieren: kurs vor einem split durch faktor teilen
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
    if len(ser) < 200:
        raise RuntimeError("tiingo liefert zu wenig fuer %s" % symbol)
    return ser


def alphavantage_series(symbol):
    """alpha vantage, kostenloser schluessel (25 abrufe/tag, reicht fuer die
    hoechstens fuenf gegenpruefungen). rohe schluesse, nicht split-bereinigt:
    ein split im jahr laesst den kandidaten dann durchfallen, nicht durchrutschen."""
    if not AV_KEY:
        raise RuntimeError("kein ALPHAVANTAGE_API_KEY")
    url = ("https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=%s"
           "&outputsize=full&apikey=%s" % (urllib.parse.quote(symbol.replace(".", "-")), AV_KEY))
    js = json.loads(fetch(url))
    ts = js.get("Time Series (Daily)")
    if not ts:
        raise RuntimeError("alpha vantage: %s" % str(js.get("Note") or js.get("Information") or js)[:50])
    ser = sorted((d, float(v["4. close"])) for d, v in ts.items())
    if len(ser) < 200:
        raise RuntimeError("alpha vantage liefert zu wenig fuer %s" % symbol)
    return ser


# reihenfolge: schluessel-quellen zuerst (zuverlaessig), die freien danach,
# alpha vantage wegen des tagesbudgets zuletzt. fehlt der schluessel, wird die
# quelle uebersprungen.
SOURCES = (("tiingo", tiingo_series), ("stooq", stooq_series),
           ("yahoo", yahoo_series), ("alphavantage", alphavantage_series))


def wiki_sentence(title):
    """erste aussage der wikipedia-einleitung: was die firma ist/macht."""
    if not title:
        return None
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/%s" % urllib.parse.quote(title)
    try:
        d = json.loads(fetch(url))
    except Exception:  # noqa: BLE001
        return None
    ext = html.unescape(d.get("extract") or "").strip()
    if not ext:
        return None
    m = re.match(r"(.+?[a-z\)][.!?])(\s|$)", ext)
    return (m.group(1) if m else ext)[:260]


# ---------------------------------------------------------------- scan

def run_scan(universe, scan, state, budget):
    rows = universe["rows"]
    n = len(rows)
    cur = int(state.get("cursor", 0)) % max(n, 1)
    done, errs = 0, 0
    pause = 60.0 / max(TD_PER_MIN, 1) + 0.3
    t0 = time.time()
    while done < budget and done + errs < n:
        r = rows[cur]
        cur = (cur + 1) % n
        try:
            ser = td_series(r["ticker"])
            rec = one_year(ser)
            rec["scanned"] = today_iso()
            scan[r["ticker"]] = rec
            done += 1
        except Exception as exc:  # noqa: BLE001
            errs += 1
            scan.setdefault(r["ticker"], {})["error"] = _hide(str(exc))[:80]
            scan[r["ticker"]]["scanned"] = today_iso()
        time.sleep(pause)
    state["cursor"] = cur
    state["last_run"] = today_iso()
    print("scan: %d titel gerechnet, %d fehler, cursor %d/%d, %.0fs"
          % (done, errs, cur, n, time.time() - t0))
    return done


# ---------------------------------------------------------------- auswahl

def benchmarks():
    """s&p 500 und gold ueber ein jahr, aus dem eigenen archiv + log."""
    hist = load(P_HIST, [])
    mlog = load(P_MLOG, [])
    if isinstance(mlog, dict):
        mlog = mlog.get("rows", [])
    out = {}
    for field, label in (("spy", "s&p 500"), ("gld", "gold")):
        ser = {}
        for src in (hist, mlog):
            for row in src or []:
                v = row.get(field) if isinstance(row, dict) else None
                if v not in (None, "") and row.get("d"):
                    ser[row["d"]] = float(v)
        if len(ser) < 250:
            continue
        s = sorted(ser.items())
        rec = one_year(s)
        out[label] = {"pct": round((rec["mult"] - 1) * 100, 1), "d": rec["d"], "d_1y": rec["d_1y"]}
    return out


def fresh(rec, today):
    if not rec or "mult" not in rec or "scanned" not in rec:
        return False
    age = (dt.date.fromisoformat(today) - dt.date.fromisoformat(rec["scanned"])).days
    return age <= SCAN_FRESH


def recently_used(log, ticker, today):
    for e in log:
        if e.get("ticker") == ticker:
            age = (dt.date.fromisoformat(today) - dt.date.fromisoformat(e["date"])).days
            if age < ROTATION_DAYS:
                return True
    return False


def verify(ticker, rec):
    """unabhaengig nachrechnen. die erste erreichbare zweitquelle entscheidet,
    beide muessen dasselbe vielfache sehen. gibt (ok, alt, diff, quelle)."""
    errors, best = [], None
    for name, fn in SOURCES:
        try:
            ser = fn(ticker)
            alt = one_year(ser)
        except Exception as exc:  # noqa: BLE001
            errors.append("%s: %s" % (name, str(exc)[:40]))
            continue
        diff = abs(alt["mult"] / rec["mult"] - 1.0)
        if diff <= VERIFY_TOL:
            return True, alt, diff, name
        # weicht ab (z. b. split nicht bereinigt): naechste quelle fragen
        if best is None or diff < best[1]:
            best = (alt, diff, name)
    if best is None:
        raise RuntimeError("; ".join(errors))
    return False, best[0], best[1], best[2]


def make_pick(universe, scan, log, today, do_verify=True):
    byt = {r["ticker"]: r for r in universe["rows"]}
    cands = []
    for t, rec in scan.items():
        if not fresh(rec, today) or rec.get("close_1y", 0) < MIN_PRICE_1Y:
            continue
        if rec["mult"] >= MIN_MULT and not recently_used(log, t, today):
            cands.append((rec["mult"], t))
    cands.sort(reverse=True)
    # basisrate: s&p-500-mitglieder mit frischem scan
    sp = [scan[r["ticker"]] for r in universe["rows"]
          if "sp500" in r.get("indices", []) and fresh(scan.get(r["ticker"]), today)]
    base = {
        "sp500_scanned": len(sp),
        "sp500_doubled": sum(1 for x in sp if x["mult"] >= 2.0),
        "sp500_tripled": sum(1 for x in sp if x["mult"] >= 3.0),
    }
    pick = None
    tried = []
    for mult, t in cands[:5]:
        rec = scan[t]
        ok, alt, diff, src = (True, None, 0.0, None)
        if do_verify:
            if tried:
                time.sleep(3)
            try:
                ok, alt, diff, src = verify(t, rec)
            except Exception as exc:  # noqa: BLE001
                ok, alt, diff = False, None, None
                tried.append({"ticker": t, "reason": "gegenpruefung nicht moeglich: %s" % str(exc)[:120]})
                continue
        if not ok:
            tried.append({"ticker": t, "reason": "quellen weichen ab (%.2f%%)" % ((diff or 0) * 100)})
            continue
        meta = byt.get(t, {})
        pick = {
            "ticker": t, "name": meta.get("name"), "sector": meta.get("sector"),
            "industry": meta.get("industry"), "indices": meta.get("indices"),
            "mult": rec["mult"], "pct": round((rec["mult"] - 1) * 100, 1),
            "from_1000": round(1000 * rec["mult"]),
            "d": rec["d"], "close": rec["close"], "d_1y": rec["d_1y"], "close_1y": rec["close_1y"],
            "low": rec["low"], "high": rec["high"],
            "drawdown_pct": round((rec["low"] / rec["close_1y"] - 1) * 100, 1),
            "verified": {"source": src, "mult": alt["mult"] if alt else None,
                         "diff_pct": round((diff or 0) * 100, 2)} if do_verify else None,
            "company_sentence": wiki_sentence(meta.get("wiki")) if do_verify else None,
            "wiki": meta.get("wiki"),
        }
        break
    return {
        "date": today, "pick": pick, "base_rate": base,
        "benchmarks": benchmarks(), "candidates_total": len(cands),
        "top10": [{"ticker": t, "mult": m} for m, t in cands[:10]],
        "rejected": tried,
        "source": "daily closes twelve data, counted by us; cross-checked against a second source",
    }


def print_pick(p):
    b, br = p["base_rate"], p["benchmarks"]
    print("\n365 DAYS LATER, stand %s, %d kandidaten >= %.0fx" % (p["date"], p["candidates_total"], MIN_MULT))
    if p["pick"]:
        k = p["pick"]
        print("  >>> %s (%s) %.2fx  $1,000 -> $%s  %s -> %s   %s/%s"
              % (k["ticker"], k["name"], k["mult"], format(k["from_1000"], ","), k["d_1y"], k["d"],
                 k.get("sector"), k.get("industry")))
        if k.get("verified"):
            print("      gegengeprueft: %s %.2fx (abw. %.2f%%)" % (k["verified"]["source"], k["verified"]["mult"] or 0, k["verified"]["diff_pct"]))
        if k.get("company_sentence"):
            print("      " + k["company_sentence"])
    else:
        print("  kein gegengeprüfter kandidat")
    print("  basisrate s&p 500: %d von %d verdoppelt, %d verdreifacht"
          % (b["sp500_doubled"], b["sp500_scanned"], b["sp500_tripled"]))
    for k, v in br.items():
        print("  benchmark %s: %+.1f%%" % (k, v["pct"]))
    for r in p["rejected"]:
        print("  verworfen %s: %s" % (r["ticker"], r["reason"]))


# ---------------------------------------------------------------- selbsttest

SAMPLE_HTML = """<table id="constituents"><tr><th>Symbol</th><th>Security</th>
<th>GICS Sector</th><th>GICS Sub-Industry</th></tr>
<tr><td><a href="/wiki/Apple_Inc.">AAPL</a></td><td><a href="/wiki/Apple_Inc.">Apple Inc.</a></td>
<td>Information Technology</td><td>Technology Hardware</td></tr>
<tr><td>BRK.B</td><td><a href="/wiki/Berkshire_Hathaway">Berkshire Hathaway</a></td>
<td>Financials</td><td>Multi-Sector Holdings</td></tr></table>"""


def selftest():
    rows = parse_constituents(SAMPLE_HTML, "sp500")
    assert [r["ticker"] for r in rows] == ["AAPL", "BRK-B"], rows
    assert rows[0]["wiki"] == "Apple_Inc." and rows[1]["sector"] == "Financials"
    # 1-jahres-rechnung: 400 tage, kurs von 10 auf 35
    base = dt.date(2025, 1, 1)
    ser = [((base + dt.timedelta(days=i)).isoformat(), 10 + 25 * i / 399) for i in range(400)]
    rec = one_year(ser)
    exp_day = (base + dt.timedelta(days=399 - 365)).isoformat()
    exp_mult = 35.0 / (10 + 25 * 34 / 399)
    assert rec["d_1y"] == exp_day and abs(rec["mult"] - exp_mult) < 1e-3, rec
    # auswahl ohne netz: rotation + basisrate
    uni = {"rows": [{"ticker": "AAA", "name": "A", "indices": ["sp500"]},
                    {"ticker": "BBB", "name": "B", "indices": ["sp500"]},
                    {"ticker": "CCC", "name": "C", "indices": ["sp400"]}]}
    t = "2026-09-04"
    scan = {"AAA": {"mult": 3.5, "close_1y": 10, "close": 35, "d": t, "d_1y": "2025-09-04", "low": 9, "high": 36, "scanned": t},
            "BBB": {"mult": 2.1, "close_1y": 10, "close": 21, "d": t, "d_1y": "2025-09-04", "low": 8, "high": 22, "scanned": t},
            "CCC": {"mult": 1.2, "close_1y": 10, "close": 12, "d": t, "d_1y": "2025-09-04", "low": 9, "high": 13, "scanned": t}}
    p = make_pick(uni, scan, [{"ticker": "AAA", "date": "2026-08-01"}], t, do_verify=False)
    assert p["pick"]["ticker"] == "BBB", p          # AAA in rotation gesperrt
    assert p["base_rate"]["sp500_doubled"] == 2 and p["base_rate"]["sp500_tripled"] == 1
    assert p["pick"]["from_1000"] == 2100
    print("selbsttest ok")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--pick-only", action="store_true", help="keine kurse holen, nur auswaehlen")
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--budget", type=int, default=TD_PER_DAY)
    ap.add_argument("--mark-used", default=None, help="ticker nach dem bau in die rotation eintragen")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return 0
    today = today_iso()
    log = load(P_LOG, [])
    if a.mark_used:
        log.append({"date": today, "ticker": a.mark_used.upper()})
        save(P_LOG, log)
        print("eingetragen: %s" % a.mark_used.upper())
        return 0
    print("twelvedata schluessel %s" % ("gesetzt" if TD_KEY else "FEHLT"))
    uni = load(P_UNIVERSE, None)
    age = None
    if uni:
        age = (dt.date.fromisoformat(today) - dt.date.fromisoformat(uni["date"])).days
    if not uni or age > UNIVERSE_MAX_AGE:
        try:
            uni = build_universe()
            save(P_UNIVERSE, uni)
        except Exception as exc:  # noqa: BLE001
            if not uni:
                raise
            print("universum nicht erneuert (%s), altes bleibt" % str(exc)[:80])
    print("universum: %d titel (stand %s)" % (uni["count"], uni["date"]))
    scan = load(P_SCAN, {})
    state = load(P_STATE, {})
    if not a.pick_only:
        run_scan(uni, scan, state, a.budget)
        save(P_SCAN, scan)
        save(P_STATE, state)
    pick = make_pick(uni, scan, log, today, do_verify=not a.no_verify)
    save(P_PICK, pick)
    print_pick(pick)
    return 0


if __name__ == "__main__":
    sys.exit(main())
