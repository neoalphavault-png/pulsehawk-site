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

5. der plausibilitaetswaechter. seit 22.08.2026. am 20.08. hat der logger
   "stables": 51836205127375208 geschrieben, das 168000fache des richtigen
   wertes. das war keine marktbewegung, das war ein kaputter punkt bei der
   quelle. wir koennen die quelle nicht reparieren, wir koennen uns nur
   weigern, den punkt zu uebernehmen. ein logger, der eine luecke laesst,
   ist besser als einer, der unsinn schreibt. eine luecke sieht man, eine
   falsche zahl rechnet man weiter.

Er postet nichts und er druckt den schluessel niemals.

python3 scripts/market_log.py            taeglicher lauf
python3 scripts/market_log.py --backfill einmalig, holt 90 tage historie
python3 scripts/market_log.py --pruefen  nur nachsehen, schreibt nichts
python3 scripts/market_log.py --selftest rechnet ohne netz
"""

import datetime
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
FX = "https://api.frankfurter.app"
DL = ["https://api.llama.fi", "https://stablecoins.llama.fi"]  # ohne schluessel

FIELDS = ["gld", "spy", "btc", "eth", "btc_dom", "total_mcap", "eurusd",
          "stables", "spy_vol", "xlk", "xly", "xlu", "xlp"]

TD_SYMBOLE = [("gld", "GLD"), ("spy", "SPY"), ("xlk", "XLK"),
              ("xly", "XLY"), ("xlu", "XLU"), ("xlp", "XLP")]

# ---------------------------------------------------------------------------
# der plausibilitaetswaechter
#
# zwei netze, unabhaengig voneinander gespannt.
#
# BAND   was ueberhaupt eine ernstzunehmende zahl sein kann. gilt immer,
#        auch beim allerersten wert eines feldes, wo es nichts zum
#        vergleichen gibt. genau dieses netz haette den 20.08. gefangen.
#        die grenzen sind absichtlich weit. sie sollen unsinn abfangen,
#        keine marktmeinung durchsetzen. gold darf sich verdoppeln.
#
# DRIFT  wie weit sich ein feld an einem tag bewegen darf, gemessen am
#        letzten bekannten wert. gilt nur, wenn es einen vorwert gibt, und
#        die spanne waechst mit der zahl der tage dazwischen, damit eine
#        luecke im log nicht jeden folgewert verwirft. ein feld ohne
#        eintrag hier wird nur vom band geprueft. spy_vol steht bewusst
#        nicht drin, umsatz springt an echten tagen wirklich um das
#        vierfache, das ist die aussage und kein fehler.
# ---------------------------------------------------------------------------

BAND = {
    "gld":        (50.0, 2000.0),
    "spy":        (100.0, 5000.0),
    "xlk":        (10.0, 2000.0),
    "xly":        (10.0, 2000.0),
    "xlu":        (10.0, 2000.0),
    "xlp":        (10.0, 2000.0),
    "btc":        (1000.0, 10000000.0),
    "eth":        (10.0, 1000000.0),
    "btc_dom":    (20.0, 95.0),
    "total_mcap": (1e11, 1e15),
    "eurusd":     (0.5, 2.0),
    "stables":    (1e10, 1e13),
    "spy_vol":    (1e6, 1e9),
}

DRIFT = {
    "gld": 0.08,
    "spy": 0.08,
    "xlk": 0.10,
    "xly": 0.10,
    "xlu": 0.08,
    "xlp": 0.08,
    "btc": 0.20,
    "eth": 0.25,
    "btc_dom": 0.05,
    "total_mcap": 0.20,
    "eurusd": 0.04,
    "stables": 0.03,
}

# eine luecke von einem halben jahr darf die spanne nicht ins unendliche
# oeffnen, sonst prueft die drift am ende gar nichts mehr.
DRIFT_MAX_TAGE = 30


def _hide(text):
    """sicherheitsnetz. falls der schluessel je in eine meldung geraet."""
    return text.replace(TD_KEY, "***") if TD_KEY else text


def get_json(url, accept="application/json"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


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


# ---------------------------------------------------------------------------
# pruefung
# ---------------------------------------------------------------------------

def tage_zwischen(a, b):
    """kalendertage zwischen zwei ISO-daten, immer positiv."""
    try:
        da = datetime.date(*[int(x) for x in str(a).split("-")])
        db = datetime.date(*[int(x) for x in str(b).split("-")])
    except (ValueError, TypeError):
        return 1
    return abs((db - da).days)


def band_ok(key, wert):
    """liegt der wert im bereich dessen, was diese groesse sein kann."""
    grenzen = BAND.get(key)
    if grenzen is None or wert is None:
        return True
    try:
        zahl = float(wert)
    except (TypeError, ValueError):
        return False
    return grenzen[0] <= zahl <= grenzen[1]


def drift_ok(key, wert, vorwert, tage):
    """
    hat sich der wert seit dem letzten bekannten stand ploetzlicher
    bewegt, als diese groesse sich bewegen kann. gibt zusaetzlich das
    verhaeltnis zurueck, damit die meldung sagen kann, um welchen faktor.
    """
    d = DRIFT.get(key)
    if d is None or wert is None or not vorwert:
        return True, 1.0
    try:
        q = float(wert) / float(vorwert)
    except (TypeError, ValueError, ZeroDivisionError):
        return True, 1.0
    n = max(1, min(int(tage), DRIFT_MAX_TAGE))
    unten = (1.0 - d) ** n
    oben = (1.0 + d) ** n
    return (unten <= q <= oben), q


def letzte_werte(rows):
    """
    fuer jedes feld der juengste bekannte wert, als (tag, wert).
    der log liegt immer nach tag sortiert vor, save_log sortiert ihn.
    zur sicherheit sortieren wir hier trotzdem, ein einziger falsch
    einsortierter tag wuerde sonst jeden vergleich danach verdrehen.
    """
    out = {}
    for r in sorted(rows, key=lambda x: x.get("d") or ""):
        if not r.get("d"):
            continue
        for key in FIELDS:
            if r.get(key) is not None:
                out[key] = (r["d"], r[key])
    return out


def pruefe_zeilen(neu, rows):
    """
    nimmt die frisch geholten zeilen und gibt sie zurueck, aber ohne die
    werte, die nicht bestehen. verworfen wird immer nur der einzelne wert,
    nie die ganze zeile. wenn gold heute unsinn liefert, ist das kein grund
    bitcoin wegzuwerfen.

    der vergleichsstand waechst waehrend der pruefung mit, damit auch ein
    backfill die tage untereinander vergleicht und nicht nur gegen einen
    leeren log.
    """
    stand = letzte_werte(rows)
    sauber = []
    meldungen = []
    for row in sorted(neu, key=lambda x: x.get("d") or ""):
        tag = row.get("d")
        if not tag:
            continue
        out = {"d": tag}
        for key in FIELDS:
            wert = row.get(key)
            if wert is None:
                continue
            if not band_ok(key, wert):
                lo, hi = BAND[key]
                meldungen.append(
                    "%s %s verworfen. %s liegt ausserhalb von %s bis %s"
                    % (tag, key, wert, _kurz(lo), _kurz(hi)))
                continue
            vor = stand.get(key)
            if vor is not None:
                ok, q = drift_ok(key, wert, vor[1], tage_zwischen(vor[0], tag))
                if not ok:
                    meldungen.append(
                        "%s %s verworfen. %s ist das %sfache von %s am %s"
                        % (tag, key, wert, _faktor(q), vor[1], vor[0]))
                    continue
            out[key] = wert
            stand[key] = (tag, wert)
        if len(out) > 1:
            sauber.append(out)
        else:
            meldungen.append("%s ganze zeile verworfen, kein wert hat bestanden" % tag)
    return sauber, meldungen


def saeubere_log(rows):
    """
    geht den bestehenden log durch und entfernt werte, die nicht einmal im
    band liegen.

    nur das band, niemals die drift. eine zahl, die diese groesse gar nicht
    sein kann, ist ein fehler und darf weg. eine zahl, die nur schnell
    gestiegen ist, kann echt sein, und alte eintraege rueckwirkend nach
    meinung zu loeschen waere genau das, was wir anderen vorwerfen.

    dadurch heilt sich der log beim naechsten lauf von selbst. der kaputte
    20.08. verschwindet, ohne dass jemand eine datei von hand anfasst.
    """
    out = []
    meldungen = []
    for r in rows:
        neu = {}
        for key, wert in r.items():
            if key == "d" or wert is None:
                neu[key] = wert
                continue
            if band_ok(key, wert):
                neu[key] = wert
            else:
                lo, hi = BAND[key]
                meldungen.append(
                    "%s %s entfernt. %s liegt ausserhalb von %s bis %s"
                    % (r.get("d"), key, wert, _kurz(lo), _kurz(hi)))
        out.append(neu)
    return out, meldungen


def pruefe_log(rows):
    """
    nur nachsehen, nichts aendern. meldet band und drift, damit man den
    bestand einmal ansehen kann, ohne dass etwas geschrieben wird.
    """
    meldungen = []
    stand = {}
    for r in sorted(rows, key=lambda x: x.get("d") or ""):
        tag = r.get("d")
        if not tag:
            continue
        for key in FIELDS:
            wert = r.get(key)
            if wert is None:
                continue
            if not band_ok(key, wert):
                lo, hi = BAND[key]
                meldungen.append("%s %s ausserhalb des bandes. %s, erlaubt %s bis %s"
                                 % (tag, key, wert, _kurz(lo), _kurz(hi)))
                continue
            vor = stand.get(key)
            if vor is not None:
                ok, q = drift_ok(key, wert, vor[1], tage_zwischen(vor[0], tag))
                if not ok:
                    meldungen.append("%s %s auffaelliger sprung. %s ist das %sfache "
                                     "von %s am %s"
                                     % (tag, key, wert, _faktor(q), vor[1], vor[0]))
            stand[key] = (tag, wert)
    return meldungen


def _kurz(zahl):
    """grosse grenzen lesbar machen, damit die meldung nicht aus nullen besteht."""
    zahl = float(zahl)
    for teiler, zeichen in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(zahl) >= teiler:
            return "%g%s" % (zahl / teiler, zeichen)
    return "%g" % zahl


def _faktor(q):
    """das verhaeltnis lesbar machen, auch wenn es absurd gross ist."""
    if q >= 1000:
        return "%.0f" % q
    if q >= 10:
        return "%.1f" % q
    return "%.2f" % q


# ---------------------------------------------------------------------------
# quellen
# ---------------------------------------------------------------------------

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
    oben steht.

    am 20.08.2026 hat genau diese quelle einen punkt geliefert, der um das
    168000fache danebenlag. der plausibilitaetswaechter faengt so etwas ab,
    bevor es in den log kommt.
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


def today():
    return time.strftime("%Y-%m-%d", time.gmtime())


# ---------------------------------------------------------------------------
# laeufe
# ---------------------------------------------------------------------------

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
            print("  FEHL  %-7s %s" % (key, _hide(str(exc))[:90]))
            continue
        for day, value in series.items():
            if isinstance(value, dict):
                put(day, key, value["close"])
                if key == "spy" and value.get("volume") is not None:
                    put(day, "spy_vol", value["volume"])
            else:
                put(day, key, value)
        print("  OK    %-7s %d tage, %s bis %s"
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
            print("  FEHL  %-9s %s" % (key, _hide(str(exc))[:90]))
            time.sleep(8)
            continue
        newest = max(series)
        if newest == day:
            row[key] = series[newest]["close"]
            if key == "spy" and series[newest].get("volume") is not None:
                row["spy_vol"] = series[newest]["volume"]
            print("  OK    %-9s %s" % (key, row[key]))
        else:
            print("  leer  %-9s letzter handelstag %s" % (key, newest))
        time.sleep(8)

    try:
        prices = cg_price(["bitcoin", "ethereum"])
        if prices.get("bitcoin") is not None:
            row["btc"] = round(float(prices["bitcoin"]), 6)
        if prices.get("ethereum") is not None:
            row["eth"] = round(float(prices["ethereum"]), 6)
        print("  OK    krypto    btc %s eth %s"
              % (row.get("btc"), row.get("eth")))
    except Exception as exc:  # noqa: BLE001
        print("  FEHL  krypto    %s" % str(exc)[:90])
    time.sleep(2)

    try:
        fx_tag, fx_kurs = fx_latest()
        if fx_tag == day:
            row["eurusd"] = fx_kurs
            print("  OK    eurusd    %s" % fx_kurs)
        else:
            print("  leer  eurusd    letzte veroeffentlichung %s" % fx_tag)
    except Exception as exc:  # noqa: BLE001
        print("  FEHL  eurusd    %s" % str(exc)[:90])
    time.sleep(1)

    try:
        dom, total = cg_global()
        if dom is not None:
            row["btc_dom"] = dom
        if total is not None:
            row["total_mcap"] = total
        print("  OK    global    dominanz %s prozent gesamt %s"
              % (row.get("btc_dom"), row.get("total_mcap")))
    except Exception as exc:  # noqa: BLE001
        print("  FEHL  global    %s" % str(exc)[:90])
    time.sleep(1)

    try:
        reihe = dl_stablecoins(7)
        newest = max(reihe)
        if newest == day:
            row["stables"] = reihe[newest]
            print("  OK    stables   %s" % reihe[newest])
        else:
            print("  leer  stables   letzter punkt %s" % newest)
    except Exception as exc:  # noqa: BLE001
        print("  FEHL  stables   %s" % str(exc)[:90])

    return [row] if len(row) > 1 else []


# ---------------------------------------------------------------------------
# selbsttest
# ---------------------------------------------------------------------------

def run_selftest():
    fails = []
    zaehler = [0]

    def check(name, got, want):
        zaehler[0] += 1
        if got != want:
            fails.append("%s\n     ist  %r\n     soll %r" % (name, got, want))

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

    # ------------------------------------------------------------------
    # plausibilitaetswaechter
    # ------------------------------------------------------------------

    # der fall vom 20.08.2026, wegen dem es diesen waechter gibt
    check("band faengt den 20.08.", band_ok("stables", 51836205127375208), False)
    check("band laesst den echten wert durch", band_ok("stables", 308057841723), True)

    # dominanz ist ein prozentsatz und kann nicht 0 oder 120 sein
    check("dominanz null faellt", band_ok("btc_dom", 0.0), False)
    check("dominanz 120 faellt", band_ok("btc_dom", 120.0), False)
    check("dominanz 58.7 besteht", band_ok("btc_dom", 58.7), True)

    # ein feld ohne band wird nicht geprueft, statt blind verworfen
    check("unbekanntes feld besteht", band_ok("gibtsnicht", 1e30), True)

    # tage zaehlen, in beide richtungen gleich
    check("tage zwischen", tage_zwischen("2026-08-14", "2026-08-21"), 7)
    check("tage zwischen rueckwaerts", tage_zwischen("2026-08-21", "2026-08-14"), 7)

    # der erste wert eines feldes hat nichts zum vergleichen und besteht
    got, meld = pruefe_zeilen([{"d": "2026-08-21", "stables": 308057841723}], [])
    check("erster wert besteht", got,
          [{"d": "2026-08-21", "stables": 308057841723}])
    check("erster wert ohne meldung", meld, [])

    # der kaputte wert kommt gar nicht erst in den log
    got, meld = pruefe_zeilen(
        [{"d": "2026-08-20", "stables": 51836205127375208, "btc": 118000.0}],
        [{"d": "2026-08-19", "stables": 308000000000, "btc": 117000.0}])
    check("kaputter wert wird verworfen", got,
          [{"d": "2026-08-20", "btc": 118000.0}])
    check("und wird gemeldet", len(meld), 1)

    # ein sprung innerhalb des bandes faellt trotzdem durch die drift
    got, _ = pruefe_zeilen(
        [{"d": "2026-08-21", "stables": 600000000000}],
        [{"d": "2026-08-20", "stables": 308000000000}])
    check("drift faengt den sprung", got, [])

    # eine luecke im log verwirft nicht den ersten wert danach
    got, _ = pruefe_zeilen(
        [{"d": "2026-08-21", "btc": 150000.0}],
        [{"d": "2026-08-01", "btc": 100000.0}])
    check("luecke verwirft nicht", got, [{"d": "2026-08-21", "btc": 150000.0}])

    # umsatz darf springen, das ist die aussage und kein fehler
    got, _ = pruefe_zeilen(
        [{"d": "2026-08-21", "spy_vol": 159230406}],
        [{"d": "2026-08-20", "spy_vol": 41234567}])
    check("umsatz darf springen", got, [{"d": "2026-08-21", "spy_vol": 159230406}])

    # ein verworfener wert reisst die uebrigen felder nicht mit
    got, _ = pruefe_zeilen(
        [{"d": "2026-08-21", "gld": 9999999.0, "spy": 640.0}],
        [{"d": "2026-08-20", "gld": 400.0, "spy": 638.0}])
    check("zeile bleibt stehen", got, [{"d": "2026-08-21", "spy": 640.0}])

    # der bestand heilt sich selbst, nur beim band, nie bei der drift
    rows, meld = saeubere_log([
        {"d": "2026-08-19", "stables": 308000000000, "btc": 117000.0},
        {"d": "2026-08-20", "stables": 51836205127375208, "btc": 118000.0}])
    check("heilung entfernt den wert", rows,
          [{"d": "2026-08-19", "stables": 308000000000, "btc": 117000.0},
           {"d": "2026-08-20", "btc": 118000.0}])
    check("heilung meldet einmal", len(meld), 1)

    rows, meld = saeubere_log([
        {"d": "2026-08-19", "btc": 60000.0},
        {"d": "2026-08-20", "btc": 118000.0}])
    check("heilung fasst schnelle bewegung nicht an", len(meld), 0)
    check("heilung laesst die zeilen ganz", rows,
          [{"d": "2026-08-19", "btc": 60000.0},
           {"d": "2026-08-20", "btc": 118000.0}])

    # nachsehen meldet, ohne etwas zu aendern
    meld = pruefe_log([{"d": "2026-08-20", "stables": 51836205127375208}])
    check("nachsehen findet den fehler", len(meld), 1)
    check("sauberer log meldet nichts",
          pruefe_log([{"d": "2026-08-20", "stables": 308000000000}]), [])

    # ein backfill vergleicht die neuen tage auch untereinander
    got, _ = pruefe_zeilen([{"d": "2026-08-19", "stables": 308000000000},
                            {"d": "2026-08-20", "stables": 51836205127375208},
                            {"d": "2026-08-21", "stables": 309000000000}], [])
    check("backfill prueft in sich", [r["d"] for r in got],
          ["2026-08-19", "2026-08-21"])

    if fails:
        print("selftest FEHLGESCHLAGEN")
        for f in fails:
            print("  " + f)
        return 1

    print("selftest ok, %d faelle" % zaehler[0])
    return 0


# ---------------------------------------------------------------------------

def main(argv):
    if "--selftest" in argv:
        return run_selftest()

    if "--pruefen" in argv:
        rows = load_log()
        print("pulsehawk marktlogger, nur nachsehen")
        print("log hat %d tage" % len(rows))
        meldungen = pruefe_log(rows)
        if not meldungen:
            print("\nnichts auffaellig, alle werte im band und ohne sprung")
            return 0
        print("\n%d auffaelligkeiten" % len(meldungen))
        for m in meldungen:
            print("  " + m)
        return 0

    modus = "backfill" if "--backfill" in argv else "taeglich"

    print("pulsehawk marktlogger, %s" % modus)
    print("laufzeitpunkt %s utc" % time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
    print("twelvedata schluessel %s\n"
          % ("gesetzt, %d zeichen" % len(TD_KEY) if TD_KEY else "FEHLT"))

    neu = run_backfill() if modus == "backfill" else run_daily()

    alt = load_log()

    # erst den bestand heilen, damit ein alter kaputter wert nicht als
    # vergleichsmassstab fuer den neuen dient.
    alt, geheilt = saeubere_log(alt)
    if geheilt:
        print("\nbestand geheilt")
        for m in geheilt:
            print("  " + m)

    neu, verworfen = pruefe_zeilen(neu, alt)
    if verworfen:
        print("\nplausibilitaetswaechter")
        for m in verworfen:
            print("  " + m)

    if not neu and not geheilt:
        print("\nkeine neuen werte, log bleibt unveraendert")
        return 0

    rows = merge(alt, neu)
    save_log(rows)

    voll = [r for r in rows if all(r.get(k) is not None
                                   for k in ("gld", "spy", "btc", "eth"))]
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
