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
  3. der nenner. seit 20.08.2026 laeuft eurusd mit, weil FOLLOW THE MONEY die
     wochenbewegung um den dollar bereinigt. ohne diese spalte ist jede
     prozentzahl in der grafik zur haelfte eine aussage ueber den massstab
     und nicht ueber den wert. den dollarindex selbst gibt es im freien tarif
     nicht, eurusd ist der ehrliche ersatz und wird auch so beschriftet.
  4. die flussfelder. ebenfalls seit 20.08.2026, weil FOLLOW THE MONEY nicht
     fragt, ob eine rendite echt war, sondern wohin geld gerade geht. dafuer
     reichen preise nicht. der gesamtmarkt steigt auch dann, wenn kein
     einziger dollar dazugekommen ist. die umlaufenden stablecoins sind die
     einzige frei erreichbare zahl, die tatsaechlich geld misst, und der
     umsatz sagt, ob eine bewegung getragen war. beides laeuft ab jetzt mit.

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
FX = "https://api.frankfurter.app"  # ezb-referenzkurse, kein schluessel
DL = ["https://api.llama.fi", "https://stablecoins.llama.fi"]  # ohne schluessel

# die vier sprossen der risikoleiter. gold, aktien, bitcoin, altcoins.
# eth steht so lange fuer die oberste sprosse, bis unsere eigene
# dominanzreihe lang genug ist, um daraus den altcoin-anteil zu rechnen.
#
# ab 20.08.2026 kommen die felder fuer FOLLOW THE MONEY dazu. sie stehen
# bewusst hinten, damit die reihenfolge in bestehenden zeilen ruhig bleibt
# und der diff im repo lesbar ist.
#
#   stables   umlaufende stablecoins in dollar. das ist die einzige zahl in
#             dieser liste, die wirklich geld misst und nicht preis. wer
#             usdt praegt, hat vorher dollar hingelegt. steigt die reihe,
#             ist geld in krypto hineingegangen. faellt sie, heraus.
#   spy_vol   umsatz im aktienindex. eine bewegung mit umsatz ist etwas
#             anderes als dieselbe bewegung ohne. kostet keinen zusaetzlichen
#             aufruf, der wert steht in derselben antwort wie der kurs.
#   xlk xly   die zyklische seite, technologie und konsumgueter.
#   xlu xlp   die defensive seite, versorger und grundbedarf.
#             das verhaeltnis der beiden seiten ist der ehrliche ersatz fuer
#             finviz. es sagt, ob innerhalb des aktienmarktes gerade risiko
#             gesucht oder gemieden wird.
#
# nicht gespeichert, weil aus den obigen ausrechenbar und sonst driftend
#   gold gegen aktien   gld geteilt durch spy
#   stablecoin ratio    marktkapital bitcoin geteilt durch stables
FIELDS = ["gld", "spy", "btc", "eth", "btc_dom", "total_mcap", "eurusd",
          "stables", "spy_vol", "xlk", "xly", "xlu", "xlp"]

# die sechs aktienpapiere, die wir bei twelve data abfragen. reihenfolge
# ist die abfragereihenfolge, jeder eintrag kostet einen credit.
TD_SYMBOLE = [("gld", "GLD"), ("spy", "SPY"), ("xlk", "XLK"),
              ("xly", "XLY"), ("xlu", "XLU"), ("xlp", "XLP")]


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

def td_roh(symbol, points):
    """
    tageswerte von twelve data, kurs und umsatz in einem aufruf. ein credit.
    liefert {tag: {"close": zahl, "volume": zahl oder None}}.
    """
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


def td_series(symbol, points):
    """nur die schlusskurse. gleicher aufruf, schmalere antwort."""
    return dict((tag, w["close"]) for tag, w in td_roh(symbol, points).items())


def dl_parse(data):
    """
    macht aus der defillama-antwort {tag: dollar}. eigene funktion, damit
    der selftest sie ohne netz pruefen kann. beide bekannten fassungen der
    summe werden verstanden, zahl und karte.
    """
    out = {}
    for punkt in data or []:
        if not isinstance(punkt, dict):
            continue
        stamp = punkt.get("date")
        wert = punkt.get("totalCirculatingUSD")
        if stamp is None or wert is None:
            continue
        try:
            day = time.strftime("%Y-%m-%d", time.gmtime(float(stamp)))
        except (TypeError, ValueError):
            continue
        try:
            if isinstance(wert, dict):
                summe = sum(float(v) for v in wert.values() if v is not None)
            else:
                summe = float(wert)
        except (TypeError, ValueError):
            continue
        out[day] = round(summe)
    return out


def dl_stablecoins(tage=None):
    """
    umlaufende stablecoins in dollar, von defillama. kein schluessel.

    das ist die einzige frei erreichbare zahl, die geld misst und nicht
    preis. sie faellt nicht, wenn der markt faellt, sondern nur, wenn
    jemand stablecoins zurueckgibt und dollar mitnimmt.

    zum aufbau der antwort. defillama liefert eine liste von punkten, jeder
    mit einem unix-datum und einer summe. die summe steht je nach fassung
    als zahl oder als karte {peggedUSD: ..., peggedEUR: ...}. wir summieren
    in beiden faellen alles auf, das ist die zahl, die auf der webseite
    oben steht. der sandkasten hat kein netz, diese verzweigung ist deshalb
    absichtlich breit und wird beim ersten echten lauf in der action
    bestaetigt oder korrigiert.
    """
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


def fx_series(von, bis):
    """
    eurusd von der ezb ueber frankfurter. ein bereich, ein aufruf, kein
    schluessel. die ezb veroeffentlicht nur an bankarbeitstagen, an
    wochenenden und feiertagen fehlt der tag einfach. das ist gewollt,
    eine luecke ist ehrlicher als ein alter kurs mit neuem datum.
    """
    url = "%s/%s..%s?from=EUR&to=USD" % (FX, von, bis)
    data = get_json(url)
    out = {}
    for day, paar in (data.get("rates") or {}).items():
        kurs = (paar or {}).get("USD")
        if kurs is not None:
            out[day] = round(float(kurs), 5)
    if not out:
        raise RuntimeError("keine eurusd werte")
    return out


def fx_latest():
    """der zuletzt veroeffentlichte kurs, mit seinem eigenen datum."""
    data = get_json("%s/latest?from=EUR&to=USD" % FX)
    kurs = (data.get("rates") or {}).get("USD")
    if kurs is None:
        raise RuntimeError("kein eurusd im ergebnis")
    return data.get("date"), round(float(kurs), 5)


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

    vorher = time.strftime("%Y-%m-%d", time.gmtime(time.time() - days * 86400))

    # der aktienteil laeuft ueber td_roh, weil der umsatz in derselben
    # antwort steht. ein feld mehr, kein aufruf mehr.
    plan = []
    for key, symbol in TD_SYMBOLE:
        plan.append((key, (lambda s=symbol: td_roh(s, days)), 8))
    plan += [("btc", lambda: cg_chart("bitcoin", days), 2),
             ("eth", lambda: cg_chart("ethereum", days), 2),
             ("eurusd", lambda: fx_series(vorher, today()), 1),
             ("stables", lambda: dl_stablecoins(days), 1)]

    for key, fetch, pause in plan:
        try:
            series = fetch()
        except Exception as exc:  # noqa: BLE001
            print("  FEHL %-7s %s" % (key, _hide(str(exc))[:90]))
            continue
        for day, value in series.items():
            if isinstance(value, dict):
                put(day, key, value["close"])
                if key == "spy" and value.get("volume") is not None:
                    put(day, "spy_vol", value["volume"])
            else:
                put(day, key, value)
        print("  OK   %-7s %d tage, %s bis %s"
              % (key, len(series), min(series), max(series)))
        time.sleep(pause)

    return [rows[day] for day in sorted(rows)]


def run_daily():
    """der taegliche lauf. eine zeile fuer heute."""
    day = today()
    row = {"d": day}

    for key, symbol in TD_SYMBOLE:
        try:
            series = td_roh(symbol, 5)
        except Exception as exc:  # noqa: BLE001
            print("  FEHL %-9s %s" % (key, _hide(str(exc))[:90]))
            time.sleep(8)
            continue
        newest = max(series)
        # an wochenenden und feiertagen liefert der etf keinen neuen tag.
        # dann schreiben wir nichts, statt einen alten kurs auf heute zu
        # datieren. die luecke ist die ehrliche antwort.
        if newest == day:
            row[key] = series[newest]["close"]
            if key == "spy" and series[newest].get("volume") is not None:
                row["spy_vol"] = series[newest]["volume"]
            print("  OK   %-9s %s" % (key, row[key]))
        else:
            print("  leer %-9s letzter handelstag %s" % (key, newest))
        time.sleep(8)

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
        fx_tag, fx_kurs = fx_latest()
        # dieselbe regel wie bei gold und aktien. nur schreiben, wenn der
        # kurs auch wirklich von heute ist.
        if fx_tag == day:
            row["eurusd"] = fx_kurs
            print("  OK   eurusd    %s" % fx_kurs)
        else:
            print("  leer eurusd    letzte veroeffentlichung %s" % fx_tag)
    except Exception as exc:  # noqa: BLE001
        print("  FEHL eurusd %s" % str(exc)[:90])

    time.sleep(1)
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

    time.sleep(1)
    try:
        reihe = dl_stablecoins(7)
        newest = max(reihe)
        # dieselbe regel wie ueberall. defillama traegt den tag oft erst
        # spaet nach, dann bleibt die spalte heute leer und faellt beim
        # naechsten lauf von selbst nach.
        if newest == day:
            row["stables"] = reihe[newest]
            print("  OK   stables   %s" % reihe[newest])
        else:
            print("  leer stables   letzter punkt %s" % newest)
    except Exception as exc:  # noqa: BLE001
        print("  FEHL stables %s" % str(exc)[:90])

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

    # eurusd wird wie jedes andere feld gefuehrt
    got = merge([{"d": "2026-08-20", "btc": 1.0}],
                [{"d": "2026-08-20", "eurusd": 1.1669}])
    check("eurusd ergaenzt", got,
          [{"d": "2026-08-20", "btc": 1.0, "eurusd": 1.1669}])

    # und steht hinten, damit bestehende zeilen im diff ruhig bleiben
    got = merge([], [{"d": "2026-08-20", "eurusd": 1.1669, "gld": 400.0}])
    check("eurusd steht hinten", list(got[0].keys()), ["d", "gld", "eurusd"])

    # defillama, die karten-fassung. alle pegs zusammen, nicht nur usd
    check("stables als karte",
          dl_parse([{"date": "1787184000",
                     "totalCirculatingUSD": {"peggedUSD": 300.0,
                                             "peggedEUR": 5.0}}]),
          {"2026-08-20": 305})

    # defillama, die zahl-fassung. dieselbe zahl, andere schreibweise
    check("stables als zahl",
          dl_parse([{"date": 1787184000, "totalCirculatingUSD": 305.0}]),
          {"2026-08-20": 305})

    # kaputte punkte werden uebersprungen und reissen den lauf nicht ab
    check("stables ueberspringt muell",
          dl_parse([{"date": None, "totalCirculatingUSD": 1},
                    "kein dict",
                    {"date": 1787184000},
                    {"date": 1787184000, "totalCirculatingUSD": 7.0}]),
          {"2026-08-20": 7})

    # der umsatz landet im eigenen feld und nicht im kurs
    got = merge([], [{"d": "2026-08-20", "spy": 776.34, "spy_vol": 41234567}])
    check("umsatz eigenes feld", got,
          [{"d": "2026-08-20", "spy": 776.34, "spy_vol": 41234567}])

    # die neuen felder stehen hinten, bestehende zeilen bleiben im diff ruhig
    got = merge([], [{"d": "2026-08-20", "xlu": 1.0, "gld": 2.0,
                      "stables": 3, "spy": 4.0}])
    check("neue felder hinten", list(got[0].keys()),
          ["d", "gld", "spy", "stables", "xlu"])

    # ein leerer log faellt nicht um
    check("leerer log", merge([], []), [])

    if fails:
        print("selftest FEHLGESCHLAGEN")
        for f in fails:
            print("  " + f)
        return 1
    print("selftest ok, 14 faelle")
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
    mit_fx = [r for r in rows if r.get("eurusd") is not None]
    print("  davon %d tage mit eurusd, der nenner fuer FOLLOW THE MONEY"
          % len(mit_fx))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
