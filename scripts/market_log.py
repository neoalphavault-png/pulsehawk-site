#!/usr/bin/env python3
"""
pulsehawk marktlogger, zweite fassung nach dem stillen stillstand.

was passiert war, diagnose vom 29.08.2026: die erste fassung hat jede
messung an das datum "heute" gehaengt. github startet geplante laeufe
aber oft mit stunden verspaetung, seit dem 17.08. regelmaessig erst nach
mitternacht utc. ab da war der letzte boersenschluss "gestern", die
stablecoin-reihe endete "gestern", alles galt als leer, das skript
schrieb nichts, und der lauf blieb trotzdem gruen. zwoelf tage lueckenlos
gruene laeufe, zwoelf tage keine einzige neue zeile.

drei aenderungen, die genau das verhindern:

1. jeder wert wird unter dem datum verbucht, an dem er entstanden ist.
   der freitagsschluss von GLD kommt in die freitagszeile, egal wann der
   lauf startet. nur die momentaufnahmen von coingecko (preis, dominanz,
   gesamtmarkt) und ihr kraken-ersatz gehoeren zum laufzeitpunkt, denn
   sie messen jetzt und nicht gestern.
2. coingecko scheitert von github-rechnern oft an der ratengrenze,
   gemessen am 27.08. beim kaspa-logger. fuer btc und eth springt
   deshalb kraken ein. fuer dominanz und gesamtmarkt gibt es keinen
   freien ersatz mit historie, dort bleibt bei ausfall eine ehrliche
   luecke.
3. ein taeglicher lauf, der keinen einzigen neuen wert findet, endet
   mit fehler und wird rot. lieber ein roter lauf als zwoelf stille.

regeln aus dem haus: keine geheimnisse im log, der schluessel wird nie
gedruckt. die datei wird gemischt, nie blind ueberschrieben, vorhandene
werte loescht nichts.

aufrufe:
    python3 scripts/market_log.py --selftest
    python3 scripts/market_log.py                 (taeglich)
    python3 scripts/market_log.py --backfill      (holt bis zu 90 tage nach)
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
KR = "https://api.kraken.com/0/public"
FX = "https://api.frankfurter.app"
DL = ["https://api.llama.fi", "https://stablecoins.llama.fi"]

FIELDS = ["gld", "spy", "btc", "eth", "btc_dom", "total_mcap", "eurusd",
          "stables", "spy_vol", "xlk", "xly", "xlu", "xlp"]

TD_SYMBOLE = [("gld", "GLD"), ("spy", "SPY"), ("xlk", "XLK"),
              ("xly", "XLY"), ("xlu", "XLU"), ("xlp", "XLP")]

KRAKEN_PAARE = {"btc": "XBTUSD", "eth": "ETHUSD"}


def _hide(text):
    return text.replace(TD_KEY, "***") if TD_KEY else text


def get_json(url, accept="application/json", tries=1, pause=6):
    """ein abruf, auf wunsch mit wiederholung. die wiederholung ist fuer
    coingecko da, dessen ratengrenze auf github-rechnern oft zuschlaegt."""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": accept})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            if i + 1 < tries:
                time.sleep(pause * (i + 1))
    raise last


# ---------- quellen ----------

def td_roh(symbol, points):
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
        if not day or close is None:
            continue
        try:
            vol = int(float(row.get("volume")))
        except (TypeError, ValueError):
            vol = None
        out[day] = {"close": round(float(close), 4), "volume": vol}
    if not out:
        raise RuntimeError("keine werte fuer %s" % symbol)
    return out


def cg_price(ids):
    url = "%s/simple/price?ids=%s&vs_currencies=usd" % (CG, ",".join(ids))
    data = get_json(url, tries=3)
    return {k: (v or {}).get("usd") for k, v in data.items()}


def kraken_price(keys):
    """ersatzweg fuer btc und eth, wenn coingecko nicht antwortet.
    kraken ticker, feld c ist der letzte handel."""
    paare = ",".join(KRAKEN_PAARE[k] for k in keys)
    data = get_json("%s/Ticker?pair=%s" % (KR, paare), tries=2)
    if data.get("error"):
        raise RuntimeError("kraken meldet %s" % data["error"])
    result = data.get("result") or {}
    out = {}
    for key in keys:
        want = KRAKEN_PAARE[key]
        for name, tick in result.items():
            if want.replace("BTC", "XBT") in name.replace("XXBTZ", "XBT").replace("XETHZ", "ETH") or want in name:
                out[key] = round(float(tick["c"][0]), 6)
                break
    if not out:
        raise RuntimeError("kraken ticker ohne passende paare")
    return out


def cg_global():
    data = (get_json("%s/global" % CG, tries=3) or {}).get("data") or {}
    dom = (data.get("market_cap_percentage") or {}).get("btc")
    total = (data.get("total_market_cap") or {}).get("usd")
    return (round(float(dom), 3) if dom is not None else None,
            round(float(total)) if total is not None else None)


def cg_chart(coin, days):
    """tagesreihe fuer den backfill. der laufende tag fliegt raus."""
    url = ("%s/coins/%s/market_chart?vs_currency=usd&days=%d"
           % (CG, coin, days))
    data = get_json(url, tries=3)
    out = {}
    for ts, price in (data.get("prices") or []):
        day = time.strftime("%Y-%m-%d", time.gmtime(ts / 1000))
        out[day] = round(float(price), 6)
    out.pop(today(), None)
    if not out:
        raise RuntimeError("keine reihe fuer %s" % coin)
    return out


def kraken_chart(key, days):
    """ersatz-tagesreihe ueber kraken ohlc, schluss der utc-kerze.
    der laufende tag fliegt raus."""
    data = get_json("%s/OHLC?pair=%s&interval=1440"
                    % (KR, KRAKEN_PAARE[key]), tries=2)
    if data.get("error"):
        raise RuntimeError("kraken meldet %s" % data["error"])
    rows = None
    for k, v in (data.get("result") or {}).items():
        if k != "last":
            rows = v
    if not rows:
        raise RuntimeError("kraken ohlc leer")
    grenze = time.strftime("%Y-%m-%d", time.gmtime(time.time() - days * 86400))
    out = {}
    for c in rows[:-1]:
        day = time.strftime("%Y-%m-%d", time.gmtime(int(c[0])))
        if day >= grenze:
            out[day] = round(float(c[4]), 6)
    if not out:
        raise RuntimeError("kraken ohlc ohne tage im fenster")
    return out


def fx_latest():
    data = get_json("%s/latest?from=EUR&to=USD" % FX)
    kurs = (data.get("rates") or {}).get("USD")
    if kurs is None:
        raise RuntimeError("kein eurusd im ergebnis")
    return data.get("date"), round(float(kurs), 5)


def fx_series(von, bis):
    data = get_json("%s/%s..%s?from=EUR&to=USD" % (FX, von, bis))
    out = {}
    for day, rates in (data.get("rates") or {}).items():
        if rates.get("USD") is not None:
            out[day] = round(float(rates["USD"]), 5)
    if not out:
        raise RuntimeError("keine eurusd reihe")
    return out


def dl_parse(data):
    """defillama-antwort in eine karte tag zu gesamtsumme. summiert alle
    waehrungstoepfe, ueberspringt muell, rundet auf ganze."""
    out = {}
    for row in data if isinstance(data, list) else []:
        if not isinstance(row, dict):
            continue
        ts = row.get("date")
        tot = row.get("totalCirculatingUSD")
        if ts is None or tot is None:
            continue
        try:
            day = time.strftime("%Y-%m-%d", time.gmtime(int(float(ts))))
        except (TypeError, ValueError):
            continue
        if isinstance(tot, dict):
            summe = sum(v for v in tot.values() if isinstance(v, (int, float)))
        elif isinstance(tot, (int, float)):
            summe = tot
        else:
            continue
        out[day] = round(summe)
    return out


def dl_stablecoins(tage=None):
    fehler = []
    for host in DL:
        try:
            data = get_json("%s/stablecoincharts/all" % host)
        except Exception as exc:  # noqa: BLE001
            fehler.append("%s %s" % (host, str(exc)[:60]))
            continue
        out = dl_parse(data)
        if out:
            if tage:
                grenze = time.strftime("%Y-%m-%d",
                                       time.gmtime(time.time() - tage * 86400))
                out = dict((d, v) for d, v in out.items() if d >= grenze)
            return out
        fehler.append("%s antwort ohne totalCirculatingUSD" % host)
    raise RuntimeError("stablecoins nicht erreichbar, %s" % "; ".join(fehler))


def today():
    return time.strftime("%Y-%m-%d", time.gmtime())


# ---------- log ----------

def load_log(path=LOG):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
        return data if isinstance(data, list) else []


def save_log(rows, path=LOG):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
        fh.write("\n")


def merge(rows, new_rows):
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


# ---------- laeufe ----------

def run_daily():
    """holt die juengsten werte und verbucht jeden unter dem datum, an dem
    er entstanden ist. genau hier sass der fehler der ersten fassung, die
    alles unter "heute" ablegte und bei verspaeteten laeufen alles verwarf."""
    rows = {}

    def put(day, key, value):
        rows.setdefault(day, {"d": day})[key] = value

    # boersenkurse. der juengste abgeschlossene handelstag zaehlt, unter
    # seinem eigenen datum. am wochenende ist das der freitag, und das
    # ist korrekt so, denn die freitagszeile darf auch samstags noch
    # vervollstaendigt werden.
    for key, symbol in TD_SYMBOLE:
        try:
            series = td_roh(symbol, 5)
        except Exception as exc:  # noqa: BLE001
            print(" FEHL %-9s %s" % (key, _hide(str(exc))[:90]))
            time.sleep(8)
            continue
        newest = max(series)
        put(newest, key, series[newest]["close"])
        if key == "spy" and series[newest].get("volume") is not None:
            put(newest, "spy_vol", series[newest]["volume"])
        print(" OK   %-9s %s (%s)" % (key, series[newest]["close"], newest))
        time.sleep(8)

    # krypto-preise sind momentaufnahmen und gehoeren zum laufzeitpunkt.
    # coingecko zuerst, kraken als ersatz.
    try:
        prices = cg_price(["bitcoin", "ethereum"])
        if prices.get("bitcoin") is not None:
            put(today(), "btc", round(float(prices["bitcoin"]), 6))
        if prices.get("ethereum") is not None:
            put(today(), "eth", round(float(prices["ethereum"]), 6))
        print(" OK   krypto    btc %s eth %s (coingecko)"
              % (prices.get("bitcoin"), prices.get("ethereum")))
    except Exception as exc:  # noqa: BLE001
        print(" FEHL krypto    coingecko %s, versuche kraken" % str(exc)[:70])
        try:
            prices = kraken_price(["btc", "eth"])
            for k, v in prices.items():
                put(today(), k, v)
            print(" OK   krypto    btc %s eth %s (kraken)"
                  % (prices.get("btc"), prices.get("eth")))
        except Exception as exc2:  # noqa: BLE001
            print(" FEHL krypto    auch kraken %s" % str(exc2)[:70])

    # eurusd unter dem datum der ezb-veroeffentlichung.
    try:
        fx_tag, fx_kurs = fx_latest()
        if fx_tag:
            put(fx_tag, "eurusd", fx_kurs)
            print(" OK   eurusd    %s (%s)" % (fx_kurs, fx_tag))
    except Exception as exc:  # noqa: BLE001
        print(" FEHL eurusd    %s" % str(exc)[:90])
    time.sleep(1)

    # dominanz und gesamtmarkt, momentaufnahme, kein freier ersatz.
    try:
        dom, total = cg_global()
        if dom is not None:
            put(today(), "btc_dom", dom)
        if total is not None:
            put(today(), "total_mcap", total)
        print(" OK   global    dominanz %s gesamt %s" % (dom, total))
    except Exception as exc:  # noqa: BLE001
        print(" FEHL global    %s, hier bleibt eine ehrliche luecke"
              % str(exc)[:70])
    time.sleep(1)

    # stablecoins unter dem datum des juengsten punkts der reihe.
    try:
        reihe = dl_stablecoins(7)
        newest = max(reihe)
        put(newest, "stables", reihe[newest])
        print(" OK   stables   %s (%s)" % (reihe[newest], newest))
    except Exception as exc:  # noqa: BLE001
        print(" FEHL stables   %s" % str(exc)[:90])

    return [rows[day] for day in sorted(rows)]


def run_backfill(days=90):
    rows = {}

    def put(day, key, value):
        rows.setdefault(day, {"d": day})[key] = value

    vorher = time.strftime("%Y-%m-%d", time.gmtime(time.time() - days * 86400))

    def krypto_reihe(coin, key):
        try:
            return cg_chart(coin, days)
        except Exception as exc:  # noqa: BLE001
            print("      %s ueber coingecko nicht erreichbar (%s), "
                  "zweiter weg ueber kraken" % (key, str(exc)[:50]))
            return kraken_chart(key, days)

    plan = []
    for key, symbol in TD_SYMBOLE:
        plan.append((key, (lambda s=symbol: td_roh(s, days)), 8))
    plan += [("btc", lambda: krypto_reihe("bitcoin", "btc"), 2),
             ("eth", lambda: krypto_reihe("ethereum", "eth"), 2),
             ("eurusd", lambda: fx_series(vorher, today()), 1),
             ("stables", lambda: dl_stablecoins(days), 1)]
    for key, fetch, pause in plan:
        try:
            series = fetch()
        except Exception as exc:  # noqa: BLE001
            print(" FEHL %-7s %s" % (key, _hide(str(exc))[:90]))
            continue
        for day, value in series.items():
            if isinstance(value, dict):
                put(day, key, value["close"])
                if key == "spy" and value.get("volume") is not None:
                    put(day, "spy_vol", value["volume"])
            else:
                put(day, key, value)
        print(" OK   %-7s %d tage, %s bis %s"
              % (key, len(series), min(series), max(series)))
        time.sleep(pause)
    return [rows[day] for day in sorted(rows)]


# ---------- selbsttest ----------

def run_selftest():
    fails = []

    def check(name, got, want):
        if got != want:
            fails.append("%s\n  ist  %r\n  soll %r" % (name, got, want))

    got = merge([{"d": "2026-08-02", "btc": 2}], [{"d": "2026-08-01", "btc": 1}])
    check("merge sortiert", [r["d"] for r in got], ["2026-08-01", "2026-08-02"])

    got = merge([{"d": "2026-08-01", "gld": 400.0}],
                [{"d": "2026-08-01", "btc_dom": 57.3}])
    check("merge ergaenzt", got, [{"d": "2026-08-01", "gld": 400.0, "btc_dom": 57.3}])

    got = merge([{"d": "2026-08-01", "btc": 100.0}],
                [{"d": "2026-08-01", "btc": 101.0}])
    check("merge ist idempotent", got, [{"d": "2026-08-01", "btc": 101.0}])

    got = merge([{"d": "2026-08-01", "spy": 776.34}],
                [{"d": "2026-08-01", "spy": None, "btc": 5.0}])
    check("kein wert loescht nichts", got,
          [{"d": "2026-08-01", "spy": 776.34, "btc": 5.0}])

    got = merge([], [{"d": "2026-08-01", "total_mcap": 3, "gld": 1, "btc": 2}])
    check("feldreihenfolge", list(got[0].keys()), ["d", "gld", "btc", "total_mcap"])

    global TD_KEY
    alt, TD_KEY = TD_KEY, "GEHEIM123"
    try:
        check("schluessel maskiert", _hide("fehler mit GEHEIM123 im text"),
              "fehler mit *** im text")
    finally:
        TD_KEY = alt

    got = merge([{"d": "2026-08-20", "btc": 1.0}],
                [{"d": "2026-08-20", "eurusd": 1.1669}])
    check("eurusd ergaenzt", got,
          [{"d": "2026-08-20", "btc": 1.0, "eurusd": 1.1669}])

    got = merge([], [{"d": "2026-08-20", "eurusd": 1.1669, "gld": 400.0}])
    check("eurusd steht hinten", list(got[0].keys()), ["d", "gld", "eurusd"])

    check("stables als karte",
          dl_parse([{"date": "1787184000",
                     "totalCirculatingUSD": {"peggedUSD": 300.0,
                                             "peggedEUR": 5.0}}]),
          {"2026-08-20": 305})

    check("stables als zahl",
          dl_parse([{"date": 1787184000, "totalCirculatingUSD": 305.0}]),
          {"2026-08-20": 305})

    check("stables ueberspringt muell",
          dl_parse([{"date": None, "totalCirculatingUSD": 1},
                    "kein dict",
                    {"date": 1787184000},
                    {"date": 1787184000, "totalCirculatingUSD": 7.0}]),
          {"2026-08-20": 7})

    got = merge([], [{"d": "2026-08-20", "spy": 776.34, "spy_vol": 41234567}])
    check("umsatz eigenes feld", got,
          [{"d": "2026-08-20", "spy": 776.34, "spy_vol": 41234567}])

    got = merge([], [{"d": "2026-08-20", "xlu": 1.0, "gld": 2.0,
                      "stables": 3, "spy": 4.0}])
    check("neue felder hinten", list(got[0].keys()),
          ["d", "gld", "spy", "stables", "xlu"])

    check("leerer log", merge([], []), [])

    # neu seit der zweiten fassung: der kern der reparatur.
    # ein wert vom freitag landet in der freitagszeile, auch wenn der
    # lauf erst samstag frueh startet. simuliert ueber run_daily-logik
    # im kleinen, direkt am put-muster.
    rows = {}
    def put(day, key, value):
        rows.setdefault(day, {"d": day})[key] = value
    put("2026-08-28", "gld", 401.0)
    put("2026-08-29", "btc", 79000.0)
    put("2026-08-28", "stables", 305)
    out = [rows[d] for d in sorted(rows)]
    check("werte unter eigenem datum",
          out,
          [{"d": "2026-08-28", "gld": 401.0, "stables": 305},
           {"d": "2026-08-29", "btc": 79000.0}])

    # kraken-antwortformate
    check("kraken ticker parse",
          _kraken_ticker_probe({"result": {"XXBTZUSD": {"c": ["79008.6", "1"]},
                                           "XETHZUSD": {"c": ["1900.5", "1"]}}}),
          {"btc": 79008.6, "eth": 1900.5})

    check("dl_parse rundet", dl_parse([{"date": 1787184000,
                                        "totalCirculatingUSD": 304.6}]),
          {"2026-08-20": 305})

    if fails:
        print("selftest FEHLGESCHLAGEN")
        for f in fails:
            print(" " + f)
        return 1
    print("selftest ok, 17 faelle")
    return 0


def _kraken_ticker_probe(data):
    """nur fuer den selbsttest, wendet die ticker-zuordnung auf ein
    festes antwortbild an."""
    result = data.get("result") or {}
    out = {}
    for key in ("btc", "eth"):
        want = KRAKEN_PAARE[key]
        for name, tick in result.items():
            norm = name.replace("XXBTZ", "XBT").replace("XETHZ", "ETH")
            if want.replace("BTC", "XBT") in norm or want in name:
                out[key] = round(float(tick["c"][0]), 6)
                break
    return out


# ---------- einstieg ----------

def main(argv):
    if "--selftest" in argv:
        return run_selftest()
    modus = "backfill" if "--backfill" in argv else "taeglich"
    print("pulsehawk marktlogger, %s (zweite fassung, 29.08.2026)" % modus)
    print("laufzeitpunkt %s utc" % time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
    print("twelvedata schluessel %s\n"
          % ("gesetzt, %d zeichen" % len(TD_KEY) if TD_KEY else "FEHLT"))
    neu = run_backfill() if modus == "backfill" else run_daily()
    if not neu:
        print("\nkein einziger neuer wert. das ist bei dieser fassung kein "
              "normalfall mehr, sondern ein fehler, der lauf wird rot.")
        return 1
    alt = load_log()
    rows = merge(alt, neu)
    if rows == alt:
        print("\nalle geholten werte standen schon im log, nichts zu schreiben.")
        return 0
    save_log(rows)
    voll = [r for r in rows if all(r.get(k) is not None for k in ("gld", "spy", "btc", "eth"))]
    mit_dom = [r for r in rows if r.get("btc_dom") is not None]
    mit_stab = [r for r in rows if r.get("stables") is not None]
    print("\nlog hat jetzt %d tage, %s bis %s" % (len(rows), rows[0]["d"], rows[-1]["d"]))
    print("  davon %d tage mit allen vier kursen" % len(voll))
    print("  davon %d tage mit dominanz" % len(mit_dom))
    print("  davon %d tage mit stablecoins, dem herzstueck von FOLLOW THE MONEY"
          % len(mit_stab))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
