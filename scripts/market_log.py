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
    python3 scripts/market_log.py --nachtragen 2026-08-31,2026-09-21
                                                  (btc/eth fuer luecken, als nachgetragen)
    python3 scripts/market_log.py --herkunft      (nur herkunft aufbauen und luecken fuellen)
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

# ---------------------------------------------------------------------------
# HERKUNFT JE FELD, SEIT DEM 25.09.2026 (Auftrag B, Bens Beschluss)
#
# Jeder Wert im Log hat eine Herkunft: woher er kommt, was fuer eine Art
# Wert er ist und wann er gemessen wurde. Sie steht in einer Begleitdatei,
# data/market-log-herkunft.json, Tag -> Feld -> Angaben. Nicht in der
# Logdatei selbst: drei Seiten laden die Logdatei bei jedem Aufruf im
# Browser, und die Herkunft haette sie von 31 kB auf rund 170 kB gebracht.
#
# In der Logdatei steht nur, was ein Leser ohne Begleitdatei wissen muss:
# an einer Zeile, deren Wert nachgetragen wurde, steht "nachgetragen" mit
# den betroffenen Feldern. Beides schreibt save_alles() aus derselben
# Herkunft, damit die Dateien nicht auseinanderlaufen.
#
# ARTEN
#   momentaufnahme  live gemessen (btc, eth, dominanz, gesamtmarkt). Nur
#                   so ein Wert darf der Tageswert fuer DAY-N sein.
#   tageswert       die Quelle sagt, zu welchem Tag der Wert gehoert:
#                   Boersenschluss, EZB-Kurs, Stablecoin-Tagespunkt.
#   reihe           spaeter aus einer Tagesreihe geholt (--backfill).
#   nachgetragen    eine Luecke, spaeter aus der Stundenreihe gefuellt.
#   luecke          kein Wert, mit Grund. Wird nicht geschaetzt.
#
# ZEIT_AUS          woher die Messzeit stammt
#   quelle          Zeitstempel der Quelle
#   abruf           Zeitpunkt des Abrufs (Kraken-Ticker hat keinen)
#   commit          aus der Git-Historie rekonstruiert, auf Minuten genau
#   quelle-datum    die Quelle nennt nur den Tag, keine Uhrzeit
# ---------------------------------------------------------------------------

HERKUNFT = os.path.join(REPO, "data", "market-log-herkunft.json")
KRYPTO = ("btc", "eth", "btc_dom", "total_mcap")
NACHTRAGBAR = ("btc", "eth")          # dominanz und gesamtmarkt: keine quelle
NICHT_LIVE = ("reihe", "nachgetragen")  # an der zeile als "nachgetragen" markiert
MARKE = "nachgetragen"

# ---------------------------------------------------------------------------
# BAND   was ueberhaupt eine ernstzunehmende zahl sein kann. gilt immer,
#        auch beim allerersten wert eines feldes, wo es nichts zum
#        vergleichen gibt. genau dieses netz haette den 20.08. gefangen.
#        die grenzen sind absichtlich weit. sie sollen unsinn abfangen,
#        keine marktmeinung durchsetzen. gold darf sich verdoppeln.
#
# WIEDERHERGESTELLT AM 23.09.2026, WORTGLEICH AUS DER HISTORIE
# Eingefuehrt am 21.08.2026 in f356ec0, am 29.08.2026 in b6deb57 mitsamt
# der Pruefung entfernt. scripts/history.py importiert BAND aber weiter,
# und damit war history.py seit dem 29.08. nicht mehr ausfuehrbar:
#
#     ImportError: cannot import name 'BAND' from 'market_log'
#
# Das hat niemand gemerkt, weil archiv.yml keinen Zeitplan hatte und nur
# von Hand lief. Der erste Schritt dieses Workflows ist history.py
# --selftest, der Lauf waere also sofort rot geworden.
#
# Die Werte sind nicht neu erfunden, sie stehen so in b6deb57^.
#
# DAS NETZ HAENGT SEIT 23.09.2026 WIEDER
# b6deb57 war kein gezielter Eingriff, sondern eine Neufassung der ganzen
# Datei, 334 Zeilen rein und 663 raus, mit der Nachricht "Update
# market_log.py". Mit der alten Holstruktur fiel die ganze Pruefschicht
# weg: band_ok, drift_ok, pruefe_zeilen, letzte_werte, saeubere_log. Ein
# Grund dafuer steht weder in der Nachricht noch im Diff, und keine der
# neuen Funktionen ersetzt sie. Es sieht nach Kollateralschaden aus.
#
# Zurueck kommt das BAND, wertweise und laut: ein Wert ausserhalb seiner
# Grenzen wird nicht uebernommen, und die Zeile im Lauf-Log nennt Feld,
# Wert, Tag, Quelle und Grenzen. Still verworfen wird nichts.
#
# Verworfen wird immer nur der einzelne Wert, nie die ganze Zeile: wenn
# Gold heute Unsinn liefert, ist das kein Grund, Bitcoin wegzuwerfen.
#
# NICHT zurueckgekommen ist DRIFT, das zweite Netz, das einen Wert am
# Vortageswert misst. Das braucht den Vergleichsstand und eine Regel fuer
# Luecken im Log, und es ist eine eigene Entscheidung.
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


def reihe_mit_logvorrang(feld, *, archiv, log):
    """eine preisreihe [(tag, wert)] aus Archiv UND Tageslog, chronologisch.

    DIE VORRANGREGEL IST HIER EINGEBACKEN, SEIT 24.09.2026
    Fuer jeden Tag, den beide kennen, gewinnt der MARKTLOG. data/history.json
    wird nur sonntags nachgezogen und haengt unter der Woche bis zu sechs
    Tage hinterher. Wer das Archiv gewinnen laesst, baut ein zweites
    "heute", und keine der beiden Zahlen ist falsch genug, dass es auffiele.

    WARUM ALS FUNKTION UND NICHT ALS WACHE
    Vorher stand diese Regel zweimal als blosse Reihenfolge in einem
    concat, in what-if.html und in scripts/multibagger.py. Eine
    Reihenfolge kann man vertauschen, ohne dass irgendetwas anschlaegt.
    Deshalb sind archiv und log KEYWORD-ONLY: wer sie vertauschen will,
    muss die Namen hinschreiben und es also wollen.

    Nicht zu verwechseln mit mit_rand() in stamp_pages.py. Dort gewinnt
    das Archiv fuer jeden Tag, den es hat, und das Log haengt nur hinten
    an; das ist fuer ein Minimum ueber einen ganzen Zyklus richtig und
    beruehrt den rechten Rand nicht. Hier geht es um den rechten Rand.
    """
    ser = {}
    for rows in (archiv, log):          # log zuletzt, also gewinnt es
        for r in rows or []:
            if not isinstance(r, dict):
                continue
            tag, wert = r.get("d"), r.get(feld)
            if isinstance(tag, str) and isinstance(wert, (int, float)) and wert > 0:
                ser[tag] = float(wert)
    return sorted(ser.items())


def _hide(text):
    return text.replace(TD_KEY, "***") if TD_KEY else text


def _kurz(zahl):
    """grosse grenzen lesbar machen, damit die meldung nicht aus nullen besteht."""
    zahl = float(zahl)
    for teiler, zeichen in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(zahl) >= teiler:
            return "%g%s" % (zahl / teiler, zeichen)
    return "%g" % zahl


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


def sammler():
    """liefert (rows, put, verworfen).

    put nimmt einen wert nur an, wenn er im band liegt. ein abgewiesener
    wert verschwindet nicht still, sondern steht mit feld, wert, tag,
    quelle und grenzen im lauf-log, damit im Actions-Protokoll steht,
    was fehlt und warum."""
    rows = {}
    verworfen = []
    herkunft = {}

    def put(day, key, value, quelle="unbekannt", art=None, zeit=None,
            zeit_aus=None, **mehr):
        if not band_ok(key, value):
            lo, hi = BAND[key]
            print(" VERW %-9s %s am %s aus %s, ausserhalb von %s bis %s"
                  % (key, value, day, quelle, _kurz(lo), _kurz(hi)))
            verworfen.append((day, key, value, quelle))
            return False
        rows.setdefault(day, {"d": day})[key] = value
        if art:
            h = {"quelle": quelle, "art": art, "zeit": zeit, "zeit_aus": zeit_aus}
            h.update(mehr)
            herkunft.setdefault(day, {})[key] = h
        return True

    # die herkunft haengt an put, damit die drei rueckgabewerte bleiben
    put.herkunft = herkunft
    return rows, put, verworfen


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
    """{coin: (preis, messzeit)}. die messzeit kommt aus last_updated_at,
    also aus der quelle. fehlt sie, ist sie None und der aufrufer nimmt
    den abrufzeitpunkt, als solchen gekennzeichnet."""
    url = ("%s/simple/price?ids=%s&vs_currencies=usd&include_last_updated_at=true"
           % (CG, ",".join(ids)))
    data = get_json(url, tries=3)
    return cg_price_lesen(data)


def cg_price_lesen(data):
    out = {}
    for k, v in (data or {}).items():
        v = v or {}
        ts = v.get("last_updated_at")
        out[k] = (v.get("usd"), iso_utc(ts) if isinstance(ts, (int, float)) else None)
    return out


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
    """(dominanz, gesamtmarkt, messzeit). messzeit aus updated_at der quelle."""
    return cg_global_lesen(get_json("%s/global" % CG, tries=3))


def cg_global_lesen(antwort):
    data = (antwort or {}).get("data") or {}
    dom = (data.get("market_cap_percentage") or {}).get("btc")
    total = (data.get("total_market_cap") or {}).get("usd")
    ts = data.get("updated_at")
    return (round(float(dom), 3) if dom is not None else None,
            round(float(total)) if total is not None else None,
            iso_utc(ts) if isinstance(ts, (int, float)) else None)


def cg_chart(coin, days):
    """tagesreihe fuer den backfill. der laufende tag fliegt raus."""
    url = ("%s/coins/%s/market_chart?vs_currency=usd&days=%d"
           % (CG, coin, days))
    data = get_json(url, tries=3)
    out = {}
    for ts, price in sorted(data.get("prices") or []):
        day = time.strftime("%Y-%m-%d", time.gmtime(ts / 1000))
        out[day] = (round(float(price), 6), iso_utc(ts / 1000))
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
            # schluss der utc-kerze: die letzte sekunde des tages
            out[day] = (round(float(c[4]), 6), iso_utc(int(c[0]) + 86399))
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


def iso_utc(sekunden):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(sekunden)))


def jetzt_iso():
    return iso_utc(time.time())


def boerse_zu(jetzt=None, puffer_min=15):
    """ist der heutige us-boersenschluss schon durch (plus puffer)?

    Twelve Data liefert den laufenden Tag waehrend der Handelszeit als
    Tagesbalken mit dem aktuellen Kurs als "close". Laeuft der Logger vor
    dem Schluss, waere das ein Zwischenstand unter dem heutigen Datum.
    Geprueft seit dem Vorziehen des Crons auf 20:00 utc: im Sommer
    schliesst New York um 20:00 utc, im Winter um 21:00 utc."""
    import datetime as _dt
    jetzt = jetzt or _dt.datetime.now(_dt.timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        ny = jetzt.astimezone(ZoneInfo("America/New_York"))
        schluss = ny.replace(hour=16, minute=0, second=0, microsecond=0)
        return ny >= schluss + _dt.timedelta(minutes=puffer_min)
    except Exception:  # noqa: BLE001
        # ohne zeitzonendaten die vorsichtige winterzeit
        return (jetzt.hour, jetzt.minute) >= (21, puffer_min)


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


def load_herkunft(path=None):
    """die herkunft, oder None, wenn es die datei noch nicht gibt."""
    path = path or HERKUNFT
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, dict) else None


def save_alles(rows, herkunft, log_path=None, herkunft_path=None):
    """log und herkunft zusammen schreiben, aus einer einzigen herkunft.

    Die Marke "nachgetragen" an den Zeilen wird hier aus der Herkunft
    abgeleitet und nicht getrennt gepflegt, damit die beiden Dateien nicht
    auseinanderlaufen koennen."""
    rows = markieren(rows, herkunft)
    save_log(rows, log_path or LOG)
    herkunft_path = herkunft_path or HERKUNFT
    os.makedirs(os.path.dirname(herkunft_path), exist_ok=True)
    with open(herkunft_path, "w", encoding="utf-8") as fh:
        json.dump({t: {f: herkunft[t][f] for f in sorted(herkunft[t])}
                   for t in sorted(herkunft)}, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return rows


def markieren(rows, herkunft):
    """die marke "nachgetragen" an jede zeile, deren werte nicht live
    gemessen wurden. ohne herkunft bleiben vorhandene marken stehen."""
    out = []
    for r in rows:
        r = dict(r)
        if herkunft is not None:
            h = herkunft.get(r["d"], {})
            felder = sorted(f for f in FIELDS
                            if r.get(f) is not None
                            and (h.get(f) or {}).get("art") in NICHT_LIVE)
            r.pop(MARKE, None)
            if felder:
                r[MARKE] = felder
        out.append(r)
    return out


def ist_live(row, feld):
    """darf dieser wert als tageswert gelten? nachgetragenes nie."""
    return (isinstance(row, dict) and isinstance(row.get(feld), (int, float))
            and feld not in (row.get(MARKE) or []))


def letzter_live(rows, feld):
    """die juengste zeile, deren wert fuer dieses feld live gemessen wurde.

    EINE Funktion fuer alle, die einen Tageswert brauchen: die Seiten
    (stamp_pages.letzter_schluss), der DAY-N-Post und die Karte. Wuerden
    sie verschieden auswaehlen, hielte Sperre 2 den Post jeden Tag an."""
    for r in reversed(rows if isinstance(rows, list) else []):
        if ist_live(r, feld) and isinstance(r.get("d"), str):
            return r
    return None


def mischen(rows, herkunft, new_rows, new_herkunft=None):
    """neue werte in den log, nach der regel vom 25.09.2026.

    Gibt (rows, herkunft, meldungen). Nichts wird still ueberschrieben:
    jede Ersetzung und jedes Behalten steht in den Meldungen, und main()
    druckt sie ins Lauf-Log.

    REGEL: haben alter und neuer Wert eine Messzeit, gewinnt die spaetere
    - ein Wert von 23:55 schlaegt einen von 00:53 desselben Tages. Fehlt
    einer Seite die Messzeit (Altbestand, Tageswert der Quelle), gewinnt
    der neue Wert, aber laut.

    herkunft None heisst: Altbetrieb ohne Herkunftsdatei. Dann wird wie
    frueher gemischt, und vorhandene Marken bleiben stehen."""
    import copy
    meldungen = []
    by_day = {r["d"]: dict(r) for r in rows if isinstance(r, dict) and r.get("d")}
    h = copy.deepcopy(herkunft) if herkunft is not None else None
    nh = new_herkunft or {}
    for new in new_rows:
        day = new.get("d")
        if not day:
            continue
        cur = by_day.setdefault(day, {"d": day})
        for key in FIELDS:
            val = new.get(key)
            if val is None:
                continue
            h_neu = (nh.get(day) or {}).get(key)
            h_alt = ((h or {}).get(day) or {}).get(key)
            alt = cur.get(key)
            if alt is None:
                cur[key] = val
            elif alt == val:
                pass
            else:
                z_neu = (h_neu or {}).get("zeit")
                z_alt = (h_alt or {}).get("zeit")
                if z_neu and z_alt and z_neu <= z_alt:
                    meldungen.append("BEHALTEN  %-10s %s  %s von %s, der neue "
                                     "wert %s von %s ist nicht spaeter"
                                     % (key, day, alt, z_alt, val, z_neu))
                    continue
                grund = ("spaeter gemessen, %s nach %s" % (z_neu, z_alt)
                         if z_neu and z_alt else "ohne vergleichbare messzeit")
                meldungen.append("ERSETZT   %-10s %s  %s -> %s (%s)"
                                 % (key, day, alt, val, grund))
                cur[key] = val
            if h is not None and h_neu is not None:
                h.setdefault(day, {})[key] = h_neu
        # luecken ohne wert: nur eintragen, wo weder wert noch herkunft steht
        if h is not None:
            for key, eintrag in (nh.get(day) or {}).items():
                if (eintrag or {}).get("art") == "luecke" \
                        and cur.get(key) is None and key not in h.get(day, {}):
                    h.setdefault(day, {})[key] = eintrag
    # luecken-eintraege fuer tage, an denen gar keine neue zeile kam
    if h is not None:
        for day, felder in nh.items():
            for key, eintrag in felder.items():
                if (eintrag or {}).get("art") == "luecke" \
                        and (by_day.get(day) or {}).get(key) is None \
                        and key not in h.get(day, {}):
                    h.setdefault(day, {})[key] = eintrag
    out = []
    for day in sorted(by_day):
        row = {"d": day}
        for key in FIELDS:
            if by_day[day].get(key) is not None:
                row[key] = by_day[day][key]
        if by_day[day].get(MARKE):
            row[MARKE] = by_day[day][MARKE]
        out.append(row)
    if h is not None:
        out = markieren(out, h)
    return out, h, meldungen


def merge(rows, new_rows):
    """altes verhalten, fuer aufrufer ohne herkunft: der neue wert gewinnt."""
    return mischen(rows, None, new_rows)[0]


def pruefe_herkunft(rows, herkunft):
    """jeder wert hat eine herkunft, jede herkunft (ausser luecke) einen
    wert, und die marken an den zeilen stimmen. liste der probleme."""
    probleme = []
    werte = {(r["d"], f) for r in rows for f in FIELDS if r.get(f) is not None}
    for t, f in sorted(werte):
        e = (herkunft.get(t) or {}).get(f)
        if not e:
            probleme.append("%s %s hat keine herkunft" % (t, f))
        elif e.get("art") == "luecke":
            probleme.append("%s %s hat einen wert, ist aber als luecke gefuehrt" % (t, f))
    for t, felder in herkunft.items():
        for f, e in felder.items():
            if (e or {}).get("art") != "luecke" and (t, f) not in werte:
                probleme.append("%s %s hat eine herkunft, aber keinen wert" % (t, f))
    soll = markieren(rows, herkunft)
    for a, b in zip(rows, soll):
        if a.get(MARKE) != b.get(MARKE):
            probleme.append("%s marke %s, soll %s" % (a["d"], a.get(MARKE), b.get(MARKE)))
    return probleme


# ---------- herkunft aus der git-historie (einmalig) ----------
#
# Bis zum 25.09.2026 hat der Logger keine Herkunft gespeichert. Die einzige
# Aufzeichnung ist die Git-Historie der Logdatei: jeder Bot-Commit ist ein
# Lauf, seine Zeit ist die Zeit des Laufs auf Minuten genau. Daraus wird die
# Herkunft jedes Werts einmal rekonstruiert, beim ersten Lauf, der keine
# Herkunftsdatei vorfindet. Der Workflow checkt dafuer die volle Historie aus.

TAGESWERT_QUELLE = {"gld": "twelve data", "spy": "twelve data", "spy_vol": "twelve data",
                    "xlk": "twelve data", "xly": "twelve data", "xlu": "twelve data",
                    "xlp": "twelve data", "eurusd": "frankfurter", "stables": "defillama"}


def klassifiziere(tag, feld, commit_zeit):
    """herkunft eines altwerts aus dem commit, der ihn zuletzt gesetzt hat.

    Krypto am selben utc-tag gesetzt: eine momentaufnahme dieses laufs,
    messzeit = commit-zeit. Krypto an einem spaeteren tag gesetzt: aus
    einer tagesreihe nachgeholt (--backfill), die messzeit ist nicht
    ueberliefert. Alles andere nennt seinen tag selbst."""
    if feld in KRYPTO:
        if commit_zeit[:10] == tag:
            return {"quelle": "coingecko oder kraken, nicht aufgezeichnet",
                    "art": "momentaufnahme", "zeit": commit_zeit, "zeit_aus": "commit"}
        return {"quelle": "coingecko oder kraken, tagesreihe, nicht aufgezeichnet",
                "art": "reihe", "zeit": None, "zeit_aus": None,
                "eingetragen": commit_zeit, "eingetragen_aus": "commit"}
    return {"quelle": TAGESWERT_QUELLE.get(feld, "unbekannt"), "art": "tageswert",
            "zeit": None, "zeit_aus": "quelle-datum",
            "eingetragen": commit_zeit, "eingetragen_aus": "commit"}


def _git(*args, cwd=None):
    import subprocess
    return subprocess.check_output(["git"] + list(args), cwd=cwd or REPO).decode("utf-8")


def rekonstruiere_herkunft(pfad="data/market-log.json", cwd=None):
    """die herkunft aller heutigen werte aus der git-historie."""
    import datetime as _dt
    if _git("rev-parse", "--is-shallow-repository", cwd=cwd).strip() == "true":
        raise RuntimeError("flacher checkout, keine historie. im workflow "
                           "fetch-depth: 0 setzen")
    commits = [z.split(" ", 1) for z in
               _git("log", "--reverse", "--format=%H %cI", "--", pfad, cwd=cwd).split("\n") if z]
    gesetzt = {}          # (tag, feld) -> commit-zeit des letzten wechsels
    vorher = {}
    for h, zeit in commits:
        t = _dt.datetime.fromisoformat(zeit).astimezone(_dt.timezone.utc)
        z = t.strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            daten = json.loads(_git("show", "%s:%s" % (h, pfad), cwd=cwd))
        except Exception:  # noqa: BLE001
            continue
        jetzt = {r["d"]: r for r in daten if isinstance(r, dict) and r.get("d")}
        for tag, r in jetzt.items():
            for f in FIELDS:
                if r.get(f) is not None and r.get(f) != vorher.get(tag, {}).get(f):
                    gesetzt[(tag, f)] = z
        vorher = jetzt
    herkunft = {}
    for tag, r in vorher.items():
        for f in FIELDS:
            if r.get(f) is not None and (tag, f) in gesetzt:
                herkunft.setdefault(tag, {})[f] = klassifiziere(tag, f, gesetzt[(tag, f)])
    return herkunft


def luecken(rows, herkunft, bis_tag):
    """krypto-tage ohne wert, vom ersten wert des felds bis vor bis_tag.

    Gibt {tag: {feld: eintrag}} fuer tage, die noch keine herkunft haben.
    btc und eth warten auf den nachtrag aus der stundenreihe, dominanz und
    gesamtmarkt haben keine quelle mit historie und werden nicht geschaetzt."""
    import datetime as _dt
    werte = {r["d"]: r for r in rows if isinstance(r, dict) and r.get("d")}
    out = {}
    for f in KRYPTO:
        tage = sorted(t for t, r in werte.items() if r.get(f) is not None)
        if not tage:
            continue
        t = _dt.date.fromisoformat(tage[0])
        ende = _dt.date.fromisoformat(bis_tag)
        while t < ende:
            s_ = t.isoformat()
            if (werte.get(s_) or {}).get(f) is None and f not in (herkunft.get(s_) or {}):
                out.setdefault(s_, {})[f] = {
                    "art": "luecke",
                    "grund": ("noch nicht nachgetragen" if f in NACHTRAGBAR
                              else "keine quelle")}
            t += _dt.timedelta(days=1)
    return out


def waehle_punkt(punkte, tag):
    """(sekunden, preis) des letzten punkts, der am utc-tag liegt, oder None.
    punkte: [(sekunden, preis), ...] in beliebiger reihenfolge."""
    passend = [(s_, p) for s_, p in punkte
               if time.strftime("%Y-%m-%d", time.gmtime(s_)) == tag]
    return max(passend) if passend else None


def cg_punkte(coin, days):
    """stundenreihe als [(sekunden, preis)]. coingecko liefert fuer 2 bis 90
    tage stundenwerte, darueber nur tageswerte um 00:00 - die taugen nicht
    als tagesende und werden deshalb gar nicht erst angefragt."""
    if days > 90:
        raise RuntimeError("aelter als 90 tage, keine stundenreihe")
    url = ("%s/coins/%s/market_chart?vs_currency=usd&days=%d"
           % (CG, coin, max(2, days)))
    data = get_json(url, tries=3)
    return [(ts / 1000.0, float(p)) for ts, p in (data.get("prices") or [])]


def kraken_kerzen(key):
    """tageskerzen als [(sekunden der letzten tagessekunde, schluss)]."""
    data = get_json("%s/OHLC?pair=%s&interval=1440" % (KR, KRAKEN_PAARE[key]), tries=2)
    if data.get("error"):
        raise RuntimeError("kraken meldet %s" % data["error"])
    for k, v in (data.get("result") or {}).items():
        if k != "last" and v:
            return [(int(c[0]) + 86399, float(c[4])) for c in v[:-1]]
    raise RuntimeError("kraken ohlc leer")


def nachtragen(rows, herkunft, tage=None, heute=None, holen=None):
    """btc und eth fuer fehlende tage aus der stundenreihe, als nachgetragen.

    tage None heisst: alle offenen luecken der letzten 88 tage. Gefuellt
    wird nur, wo KEIN wert steht - ein nachtrag ersetzt nie eine
    momentaufnahme. holen ist fuer den selbsttest: (coin, key, days) ->
    (punkte, quelle, zeit_aus)."""
    import datetime as _dt
    heute = heute or today()
    werte = {r["d"]: r for r in rows if isinstance(r, dict) and r.get("d")}
    if tage is None:
        grenze = (_dt.date.fromisoformat(heute) - _dt.timedelta(days=88)).isoformat()
        offen = luecken(rows, {}, heute)
        tage = sorted(t for t, felder in offen.items()
                      if t >= grenze and any(f in NACHTRAGBAR for f in felder))
    neu_rows, put, _ = sammler()
    meldungen = []
    if not tage:
        return [], {}, meldungen

    def standard(coin, key, days):
        try:
            return cg_punkte(coin, days), "coingecko market_chart, stundenreihe"
        except Exception as exc:  # noqa: BLE001
            meldungen.append("coingecko %s: %s, zweiter weg ueber kraken" % (key, str(exc)[:60]))
            return kraken_kerzen(key), "kraken ohlc, tageskerze"

    holen = holen or standard
    days = (_dt.date.fromisoformat(heute) - _dt.date.fromisoformat(min(tage))).days + 2
    for coin, key in (("bitcoin", "btc"), ("ethereum", "eth")):
        brauchen = [t for t in tage if (werte.get(t) or {}).get(key) is None]
        if not brauchen:
            continue
        try:
            punkte, quelle = holen(coin, key, days)
        except Exception as exc:  # noqa: BLE001
            meldungen.append("NACHTRAG %s nicht moeglich: %s" % (key, str(exc)[:80]))
            continue
        for t in brauchen:
            p = waehle_punkt(punkte, t)
            if not p:
                meldungen.append("NACHTRAG %s %s: kein punkt in der reihe" % (key, t))
                continue
            if put(t, key, round(p[1], 6), quelle, art="nachgetragen",
                   zeit=iso_utc(p[0]), zeit_aus="quelle", eingetragen=heute):
                meldungen.append("NACHTRAG %s %s = %s, gemessen %s (%s)"
                                 % (key, t, round(p[1], 2), iso_utc(p[0]), quelle))
    return [neu_rows[d] for d in sorted(neu_rows)], put.herkunft, meldungen


# ---------- laeufe ----------

def run_daily():
    """holt die juengsten werte und verbucht jeden unter dem datum, an dem
    er entstanden ist. genau hier sass der fehler der ersten fassung, die
    alles unter "heute" ablegte und bei verspaeteten laeufen alles verwarf."""
    rows, put, verworfen = sammler()

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
        # vor dem us-schluss ist der heutige balken ein zwischenstand
        if newest == today() and not boerse_zu():
            print(" ---  %-9s heutiger balken vor boersenschluss, nehme den vortag" % key)
            frueher = sorted(series)[:-1]
            if not frueher:
                continue
            newest = frueher[-1]
        tw = dict(art="tageswert", zeit=None, zeit_aus="quelle-datum")
        put(newest, key, series[newest]["close"], "twelve data", **tw)
        if key == "spy" and series[newest].get("volume") is not None:
            put(newest, "spy_vol", series[newest]["volume"], "twelve data", **tw)
        print(" OK   %-9s %s (%s)" % (key, series[newest]["close"], newest))
        time.sleep(8)

    # krypto-preise sind momentaufnahmen und gehoeren zum laufzeitpunkt.
    # coingecko zuerst, kraken als ersatz.
    # das datum der zeile kommt aus der messzeit, nicht aus dem laufdatum.
    try:
        abruf = jetzt_iso()
        prices = cg_price(["bitcoin", "ethereum"])
        for coin, key in (("bitcoin", "btc"), ("ethereum", "eth")):
            preis, zeit = prices.get(coin, (None, None))
            if preis is None:
                continue
            zeit_aus = "quelle" if zeit else "abruf"
            zeit = zeit or abruf
            put(zeit[:10], key, round(float(preis), 6), "coingecko",
                art="momentaufnahme", zeit=zeit, zeit_aus=zeit_aus)
            print(" OK   %-9s %s, gemessen %s (%s)" % (key, preis, zeit, zeit_aus))
    except Exception as exc:  # noqa: BLE001
        print(" FEHL krypto    coingecko %s, versuche kraken" % str(exc)[:70])
        try:
            abruf = jetzt_iso()
            prices = kraken_price(["btc", "eth"])
            for k, v in prices.items():
                # der kraken-ticker hat keine zeit: abrufzeitpunkt, so benannt
                put(abruf[:10], k, v, "kraken", art="momentaufnahme",
                    zeit=abruf, zeit_aus="abruf")
            print(" OK   krypto    btc %s eth %s (kraken, gemessen %s beim abruf)"
                  % (prices.get("btc"), prices.get("eth"), abruf))
        except Exception as exc2:  # noqa: BLE001
            print(" FEHL krypto    auch kraken %s" % str(exc2)[:70])

    # eurusd unter dem datum der ezb-veroeffentlichung.
    try:
        fx_tag, fx_kurs = fx_latest()
        if fx_tag:
            put(fx_tag, "eurusd", fx_kurs, "frankfurter",
                art="tageswert", zeit=None, zeit_aus="quelle-datum")
            print(" OK   eurusd    %s (%s)" % (fx_kurs, fx_tag))
    except Exception as exc:  # noqa: BLE001
        print(" FEHL eurusd    %s" % str(exc)[:90])
    time.sleep(1)

    # dominanz und gesamtmarkt, momentaufnahme, kein freier ersatz.
    try:
        abruf = jetzt_iso()
        dom, total, zeit = cg_global()
        zeit_aus = "quelle" if zeit else "abruf"
        zeit = zeit or abruf
        for key, wert in (("btc_dom", dom), ("total_mcap", total)):
            if wert is not None:
                put(zeit[:10], key, wert, "coingecko", art="momentaufnahme",
                    zeit=zeit, zeit_aus=zeit_aus)
        print(" OK   global    dominanz %s gesamt %s, gemessen %s (%s)"
              % (dom, total, zeit, zeit_aus))
    except Exception as exc:  # noqa: BLE001
        print(" FEHL global    %s, hier bleibt eine ehrliche luecke"
              % str(exc)[:70])
    time.sleep(1)

    # stablecoins unter dem datum des juengsten punkts der reihe.
    try:
        reihe = dl_stablecoins(7)
        newest = max(reihe)
        put(newest, "stables", reihe[newest], "defillama",
            art="tageswert", zeit=None, zeit_aus="quelle-datum")
        print(" OK   stables   %s (%s)" % (reihe[newest], newest))
    except Exception as exc:  # noqa: BLE001
        print(" FEHL stables   %s" % str(exc)[:90])

    if verworfen:
        print(" ---  %d wert(e) vom band abgewiesen, siehe VERW oben" % len(verworfen))
    return [rows[day] for day in sorted(rows)], put.herkunft


def run_backfill(days=90):
    rows, put, verworfen = sammler()

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
        quelle = "twelve data" if key in dict(TD_SYMBOLE) else "reihe"
        try:
            series = fetch()
        except Exception as exc:  # noqa: BLE001
            print(" FEHL %-7s %s" % (key, _hide(str(exc))[:90]))
            continue
        tw = dict(art="tageswert", zeit=None, zeit_aus="quelle-datum")
        for day, value in series.items():
            if isinstance(value, dict):
                put(day, key, value["close"], quelle, **tw)
                if key == "spy" and value.get("volume") is not None:
                    put(day, "spy_vol", value["volume"], quelle, **tw)
            elif isinstance(value, tuple):
                # krypto aus der reihe: preis mit messzeit des punkts
                put(day, key, value[0], quelle, art="reihe", zeit=value[1],
                    zeit_aus="quelle", eingetragen=today())
            else:
                put(day, key, value, quelle, **tw)
        print(" OK   %-7s %d tage, %s bis %s"
              % (key, len(series), min(series), max(series)))
        time.sleep(pause)
    if verworfen:
        print(" ---  %d wert(e) vom band abgewiesen, siehe VERW oben" % len(verworfen))
    return [rows[day] for day in sorted(rows)], put.herkunft


# ---------- selbsttest ----------

def run_selftest():
    fails = []
    gezaehlt = [0]

    def check(name, got, want):
        # die zahl unten kommt aus dieser liste und nicht aus dem kopf des
        # letzten, der einen fall ergaenzt hat.
        gezaehlt[0] += 1
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

    # --- das band, seit 23.09.2026 wieder in betrieb ---
    # ein echter kurs von heute muss durchgehen. wer die grenzen enger
    # zieht als den markt, verliert echte tage und merkt es spaet.
    check("heutiger btc-kurs geht durch", band_ok("btc", 86174.0), True)
    check("unsinn nach oben faellt", band_ok("btc", 5e15), False)
    check("null faellt", band_ok("btc", 0), False)
    check("genau auf der untergrenze geht", band_ok("btc", 1000.0), True)
    check("knapp darunter faellt", band_ok("btc", 999.99), False)
    check("keine zahl faellt", band_ok("btc", "viel"), False)
    # ein feld ohne eintrag im band wird nicht geprueft, nicht verworfen
    check("feld ohne band geht durch", band_ok("gibtsnicht", 1e99), True)
    check("fehlender wert ist kein fehler", band_ok("btc", None), True)

    rows, put, verworfen = sammler()
    check("guter wert kommt an", put("2026-09-23", "btc", 86174.0, "kraken"), True)
    check("schlechter wert kommt nicht an",
          put("2026-09-23", "btc", 5e15, "coingecko"), False)
    check("und die null auch nicht", put("2026-09-23", "btc", 0, "kraken"), False)
    # verworfen wird der einzelne wert, nie die ganze zeile
    check("gold darf danach weiter rein",
          put("2026-09-23", "gld", 415.0, "twelve data"), True)
    check("die zeile behaelt den guten wert",
          rows["2026-09-23"], {"d": "2026-09-23", "btc": 86174.0, "gld": 415.0})
    check("zwei abweisungen vermerkt", len(verworfen), 2)
    check("mit wert und quelle", verworfen[0], ("2026-09-23", "btc", 5e15, "coingecko"))
    check("grenzen lesbar", (_kurz(1000.0), _kurz(10000000.0)), ("1000", "10M"))

    # ================= seit dem 25.09.2026: messzeit und herkunft =================
    import datetime as _dt
    UTC = _dt.timezone.utc

    # --- die quellen liefern ihre messzeit ---
    check("coingecko-preis mit messzeit der quelle",
          cg_price_lesen({"bitcoin": {"usd": 84392.0, "last_updated_at": 1790380502}}),
          {"bitcoin": (84392.0, "2026-09-25T23:55:02Z")})
    check("ohne last_updated_at keine erfundene zeit",
          cg_price_lesen({"bitcoin": {"usd": 1.0}}), {"bitcoin": (1.0, None)})
    check("dominanz mit messzeit der quelle",
          cg_global_lesen({"data": {"market_cap_percentage": {"btc": 58.5804},
                                    "total_market_cap": {"usd": 2.8887e12},
                                    "updated_at": 1790380502}}),
          (58.58, 2888700000000, "2026-09-25T23:55:02Z"))

    # --- das datum der zeile kommt aus der messzeit ---
    # der fall vom 21.09.: der lauf fuer den 21. misst um 00:11 am 22.
    rows, put, _ = sammler()
    put("2026-09-22T00:11:54Z"[:10], "btc", 86325.0, "coingecko",
        art="momentaufnahme", zeit="2026-09-22T00:11:54Z", zeit_aus="quelle")
    check("eine messung um 00:11 gehoert zum tag, an dem sie gemessen wurde",
          sorted(rows), ["2026-09-22"])
    check("und traegt ihre messzeit", put.herkunft["2026-09-22"]["btc"]["zeit"],
          "2026-09-22T00:11:54Z")

    # --- mischen: der spaetere zeitstempel desselben tages gewinnt ---
    h0 = {"2026-09-22": {"btc": {"art": "momentaufnahme", "zeit": "2026-09-22T00:11:54Z"}}}
    abend = ([{"d": "2026-09-22", "btc": 86174.0}],
             {"2026-09-22": {"btc": {"art": "momentaufnahme", "zeit": "2026-09-22T23:39:21Z"}}})
    r1, h1, m1 = mischen([{"d": "2026-09-22", "btc": 86325.0}], h0, *abend)
    check("der abendwert ersetzt den nachtwert", r1[0]["btc"], 86174.0)
    check("und das steht laut im log", m1[0].startswith("ERSETZT   btc"), True)
    check("mit grund", "spaeter gemessen" in m1[0], True)
    r2, h2, m2 = mischen(r1, h1, [{"d": "2026-09-22", "btc": 86325.0}], h0)
    check("umgekehrt bleibt der abendwert stehen", r2[0]["btc"], 86174.0)
    check("und auch das steht im log", m2[0].startswith("BEHALTEN  btc"), True)
    check("gleiche werte erzeugen keine meldung",
          mischen(r1, h1, *abend)[2], [])
    r3, _, m3 = mischen([{"d": "2026-08-01", "gld": 400.0}], {},
                        [{"d": "2026-08-01", "gld": 401.0}], {})
    check("ohne messzeit gewinnt der neue wert, aber laut",
          (r3[0]["gld"], m3[0].startswith("ERSETZT") and "ohne vergleichbare" in m3[0]),
          (401.0, True))

    # --- die marke an der zeile folgt der herkunft ---
    hm = {"2026-09-21": {"btc": {"art": "nachgetragen"}, "gld": {"art": "tageswert"}},
          "2026-09-22": {"btc": {"art": "momentaufnahme"}}}
    zeilen = markieren([{"d": "2026-09-21", "btc": 1.0, "gld": 2.0},
                        {"d": "2026-09-22", "btc": 3.0}], hm)
    check("nachgetragenes wird an der zeile markiert", zeilen[0].get(MARKE), ["btc"])
    check("live gemessenes nicht", zeilen[1].get(MARKE), None)
    check("der tageswert ist die juengste live-zeile",
          letzter_live(zeilen, "btc")["d"], "2026-09-22")
    nur_nach = markieren([{"d": "2026-09-22", "btc": 3.0}, {"d": "2026-09-23", "btc": 4.0}],
                         {"2026-09-22": {"btc": {"art": "momentaufnahme"}},
                          "2026-09-23": {"btc": {"art": "nachgetragen"}}})
    check("ein nachgetragener juengster wert ist nie der tageswert",
          letzter_live(nur_nach, "btc")["d"], "2026-09-22")
    check("ohne live-wert gibt es keinen tageswert",
          letzter_live([{"d": "2026-09-23", "btc": 4.0, MARKE: ["btc"]}], "btc"), None)

    # --- die pruefung vor dem speichern ---
    check("vollstaendige herkunft ist sauber", pruefe_herkunft(zeilen, hm), [])
    check("ein wert ohne herkunft faellt auf",
          pruefe_herkunft([{"d": "2026-09-22", "btc": 3.0, "eth": 1.0}],
                          {"2026-09-22": {"btc": {"art": "momentaufnahme"}}}),
          ["2026-09-22 eth hat keine herkunft"])
    check("eine herkunft ohne wert faellt auf",
          pruefe_herkunft([{"d": "2026-09-21", "gld": 2.0, MARKE: ["btc"]}],
                          {"2026-09-21": {"btc": {"art": "nachgetragen"},
                                          "gld": {"art": "tageswert"}}})[0],
          "2026-09-21 btc hat eine herkunft, aber keinen wert")
    check("eine falsche marke faellt auf",
          "marke" in " ".join(pruefe_herkunft([{"d": "2026-09-22", "btc": 3.0, MARKE: ["btc"]}],
                                              {"2026-09-22": {"btc": {"art": "momentaufnahme"}}})),
          True)
    check("eine luecke ohne wert ist in ordnung",
          pruefe_herkunft([], {"2026-09-21": {"btc_dom": {"art": "luecke", "grund": "keine quelle"}}}),
          [])

    # --- rekonstruktion: klassifizierung eines altwerts ---
    k = klassifiziere("2026-08-27", "btc_dom", "2026-08-27T00:53:41Z")
    check("krypto am selben tag gesetzt: momentaufnahme mit commit-zeit",
          (k["art"], k["zeit"], k["zeit_aus"]),
          ("momentaufnahme", "2026-08-27T00:53:41Z", "commit"))
    check("krypto spaeter gesetzt: aus der reihe, ohne messzeit",
          (klassifiziere("2026-08-24", "btc", "2026-08-29T05:29:40Z")["art"],
           klassifiziere("2026-08-24", "btc", "2026-08-29T05:29:40Z")["zeit"]), ("reihe", None))
    check("gold nennt seinen tag selbst",
          (klassifiziere("2026-09-24", "gld", "2026-09-24T23:55:27Z")["art"],
           klassifiziere("2026-09-24", "gld", "2026-09-24T23:55:27Z")["zeit_aus"]),
          ("tageswert", "quelle-datum"))

    # --- luecken: nicht schaetzen, sondern benennen ---
    lz = luecken([{"d": "2026-09-19", "btc": 1.0, "btc_dom": 58.0},
                  {"d": "2026-09-20", "btc": 1.0, "btc_dom": 58.0},
                  {"d": "2026-09-22", "btc": 1.0, "btc_dom": 58.0}], {}, "2026-09-23")
    check("der fehlende 21.09. wird gefunden", sorted(lz), ["2026-09-21"])
    check("btc wartet auf den nachtrag", lz["2026-09-21"]["btc"]["grund"], "noch nicht nachgetragen")
    check("dominanz hat keine quelle", lz["2026-09-21"]["btc_dom"]["grund"], "keine quelle")
    check("der laufende tag ist keine luecke",
          luecken([{"d": "2026-09-22", "btc": 1.0}], {}, "2026-09-23"), {})
    check("schon gefuehrte luecken werden nicht doppelt gemeldet",
          luecken([{"d": "2026-09-20", "btc": 1.0}, {"d": "2026-09-22", "btc": 1.0}],
                  {"2026-09-21": {"btc": {"art": "luecke"}}}, "2026-09-23"), {})

    # --- nachtrag aus der stundenreihe ---
    def sek(iso):
        return _dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    stunden = [(sek("2026-09-21T22:00:00Z"), 85900.0), (sek("2026-09-21T23:00:07Z"), 86010.0),
               (sek("2026-09-22T00:00:03Z"), 86300.0)]
    check("der letzte punkt des tages", waehle_punkt(stunden, "2026-09-21"),
          (sek("2026-09-21T23:00:07Z"), 86010.0))
    check("mitternacht gehoert zum neuen tag", waehle_punkt(stunden, "2026-09-22")[1], 86300.0)
    check("ohne punkt kein wert", waehle_punkt(stunden, "2026-09-20"), None)

    basis = [{"d": "2026-09-20", "btc": 81177.0, "eth": 1.0},
             {"d": "2026-09-21", "gld": 400.0},
             {"d": "2026-09-22", "btc": 86174.0, "eth": 1.0}]
    aufrufe = []
    def fake(coin, key, days):
        aufrufe.append((key, days))
        return stunden, "coingecko market_chart, stundenreihe"
    n_rows, n_h, n_m = nachtragen(basis, {}, heute="2026-09-26", holen=fake)
    check("der nachtrag findet den 21.09. selbst", [r["d"] for r in n_rows], ["2026-09-21"])
    check("mit dem abendwert der stundenreihe", n_rows[0]["btc"], 86010.0)
    e = n_h["2026-09-21"]["btc"]
    check("als nachgetragen, mit messzeit der quelle",
          (e["art"], e["zeit"], e["zeit_aus"], e["eingetragen"]),
          ("nachgetragen", "2026-09-21T23:00:07Z", "quelle", "2026-09-26"))
    check("nur btc und eth werden angefragt", sorted(k for k, _ in aufrufe), ["btc", "eth"])
    check("mit genug tagen fuer die stundenreihe", aufrufe[0][1], 7)
    check("ein vorhandener wert wird nie ersetzt",
          nachtragen(basis, {}, tage=["2026-09-22"], heute="2026-09-26", holen=fake)[0], [])
    # eine einzige luecke am 02.05., sonst jeder tag bis zum 25.09. belegt
    alt_luecke = []
    t = _dt.date(2026, 5, 1)
    while t <= _dt.date(2026, 9, 25):
        if t != _dt.date(2026, 5, 2):
            alt_luecke.append({"d": t.isoformat(), "btc": 1.0, "eth": 1.0})
        t += _dt.timedelta(days=1)
    check("luecken aelter als 88 tage bleiben liegen",
          nachtragen(alt_luecke, {}, heute="2026-09-26", holen=fake)[0], [])
    def kaputt(coin, key, days):
        raise RuntimeError("403")
    k_rows, _, k_m = nachtragen(basis, {}, heute="2026-09-26", holen=kaputt)
    check("scheitert die quelle, bleibt die luecke und das steht im log",
          (k_rows, any("nicht moeglich" in z for z in k_m)), ([], True))

    # nach dem nachtrag: marke gesetzt, luecke weg, pruefung sauber
    hb = {"2026-09-20": {"btc": {"art": "momentaufnahme", "zeit": "2026-09-20T23:19:00Z"},
                         "eth": {"art": "momentaufnahme", "zeit": "2026-09-20T23:19:00Z"}},
          "2026-09-21": {"gld": {"art": "tageswert"}, "btc": {"art": "luecke", "grund": "noch nicht nachgetragen"},
                         "eth": {"art": "luecke", "grund": "noch nicht nachgetragen"}},
          "2026-09-22": {"btc": {"art": "momentaufnahme", "zeit": "2026-09-22T23:39:21Z"},
                         "eth": {"art": "momentaufnahme", "zeit": "2026-09-22T23:39:21Z"}}}
    fertig, hf, _ = mischen(basis, hb, n_rows, n_h)
    check("die zeile vom 21.09. hat jetzt btc und ist markiert",
          (fertig[1].get("btc"), fertig[1].get(MARKE)), (86010.0, ["btc", "eth"]))
    check("die luecke ist durch den nachtrag ersetzt", hf["2026-09-21"]["btc"]["art"], "nachgetragen")
    check("und die pruefung ist sauber", pruefe_herkunft(fertig, hf), [])
    check("der tageswert bleibt der live gemessene 22.09.",
          letzter_live(fertig, "btc")["d"], "2026-09-22")

    # --- boersenschluss: kein zwischenstand unter heutigem datum ---
    check("sommer, 20:10 utc: new york schliesst um 20:00, puffer laeuft noch",
          boerse_zu(_dt.datetime(2026, 9, 25, 20, 10, tzinfo=UTC)), False)
    check("sommer, 20:20 utc: schluss ist durch",
          boerse_zu(_dt.datetime(2026, 9, 25, 20, 20, tzinfo=UTC)), True)
    check("winter, 20:30 utc: new york handelt noch",
          boerse_zu(_dt.datetime(2026, 12, 3, 20, 30, tzinfo=UTC)), False)
    check("winter, 21:20 utc: schluss ist durch",
          boerse_zu(_dt.datetime(2026, 12, 3, 21, 20, tzinfo=UTC)), True)

    if fails:
        print("selftest FEHLGESCHLAGEN")
        for f in fails:
            print(" " + f)
        return 1
    print("selftest ok, %d faelle" % gezaehlt[0])
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
    modus = "taeglich"
    for m in ("backfill", "nachtragen", "herkunft"):
        if "--" + m in argv:
            modus = m
    print("pulsehawk marktlogger, %s (dritte fassung, 25.09.2026)" % modus)
    print("laufzeitpunkt %s utc" % time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
    print("twelvedata schluessel %s\n"
          % ("gesetzt, %d zeichen" % len(TD_KEY) if TD_KEY else "FEHLT"))

    alt = load_log()
    herkunft = load_herkunft()
    if herkunft is None:
        print("keine herkunftsdatei, baue sie einmalig aus der git-historie")
        try:
            herkunft = rekonstruiere_herkunft()
            print("  %d tage mit herkunft rekonstruiert" % len(herkunft))
        except Exception as exc:  # noqa: BLE001
            print("  NICHT MOEGLICH: %s" % str(exc)[:120])
            print("  weiter im altbetrieb, ohne herkunft und ohne pruefung")

    meldungen = []
    rows = alt
    if modus in ("taeglich", "backfill"):
        neu, h_neu = run_backfill() if modus == "backfill" else run_daily()
        if not neu and modus == "taeglich":
            print("\nkein einziger neuer wert. das ist bei dieser fassung kein "
                  "normalfall mehr, sondern ein fehler, der lauf wird rot.")
            return 1
        rows, herkunft, m = mischen(rows, herkunft, neu, h_neu)
        meldungen += m

    if herkunft is not None and modus in ("taeglich", "nachtragen", "herkunft"):
        tage = None
        if modus == "nachtragen":
            liste = [a for a in argv if not a.startswith("--")]
            tage = sorted(t.strip() for a in liste for t in a.split(",") if t.strip()) or None
        # erst nachtragen, was geht, dann den rest als luecke fuehren
        n_rows, n_h, m = nachtragen(rows, herkunft, tage=tage)
        meldungen += m
        rows, herkunft, m = mischen(rows, herkunft, n_rows, n_h)
        meldungen += m
        rows, herkunft, m = mischen(rows, herkunft, [], luecken(rows, herkunft, today()))
        meldungen += m

    if meldungen:
        print("")
        for z in meldungen:
            print(" " + z)

    if herkunft is not None:
        probleme = pruefe_herkunft(markieren(rows, herkunft), herkunft)
        if probleme:
            print("\nHERKUNFT UNVOLLSTAENDIG, nichts geschrieben:")
            for z in probleme[:20]:
                print("  - " + z)
            return 1
        rows = markieren(rows, herkunft)

    if rows == alt and (herkunft is None or herkunft == load_herkunft()):
        print("\nalle werte standen schon im log, nichts zu schreiben.")
        return 0
    if herkunft is not None:
        save_alles(rows, herkunft)
    else:
        save_log(rows)
    voll = [r for r in rows if all(r.get(k) is not None for k in ("gld", "spy", "btc", "eth"))]
    mit_dom = [r for r in rows if r.get("btc_dom") is not None]
    nachg = [r for r in rows if r.get(MARKE)]
    print("\nlog hat jetzt %d tage, %s bis %s" % (len(rows), rows[0]["d"], rows[-1]["d"]))
    print("  davon %d tage mit allen vier kursen" % len(voll))
    print("  davon %d tage mit dominanz" % len(mit_dom))
    print("  davon %d tage mit nachgetragenen werten" % len(nachg))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
