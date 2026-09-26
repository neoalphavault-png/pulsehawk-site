#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dayn_grafik.py, die Tageskarte fuer den DAY-N-Post auf @pulsehawkio.

EINE VORLAGE, TAEGLICH NUR ANDERE ZAHLEN
Innerhalb einer Serie bleibt die Form konstant. Hier ist das kein Zwang,
sondern der Grund, warum dieser Generator so klein sein kann: er tauscht
vier Zahlen und zwei Datumsangaben, sonst nichts.

WAS DRAUFSTEHT
Zwei Bloecke, und jede Zahl traegt ihren Bezugspunkt im SELBEN Block.
Eine Tageszahl ohne ihren Stichtag ist keine Aussage.
  1. Tage seit dem Zyklushoch, mit Datum und Preis des Hochs.
  2. Tage seit dem tiefsten Preis danach, mit Datum und Preis, und dem
     Vorbehalt "if that low holds" - das Tief ist erst im Rueckblick eines.

LOGO OBEN UND UNTEN
Die Karte wird beschnitten weitergeschickt. Wer oben abschneidet, soll
unten noch sehen, woher sie kommt, und umgekehrt. Die Adresse steht in
der Fusszeile.

WOHER DIE ZAHLEN KOMMEN
Aus denselben Funktionen wie die Zyklusseiten, importiert aus
stamp_pages. Das ist Absicht: eine Karte, die dem eigenen Archiv
widerspricht, waere schlimmer als gar keine. Rechter Rand aus dem
Marktlog, Historie aus dem Archiv, wie ueberall.

GERENDERT WIRD MIT CHROMIUM
Pillow ist in der Umgebung nicht da, Chromium schon. Die Karte ist
deshalb HTML und wird als PNG fotografiert, 1080x1350, also 4:5.

    python3 scripts/dayn_grafik.py                 baut graphics/dayn.png
    python3 scripts/dayn_grafik.py --selftest
"""
import base64
import datetime
import json
import os
import struct
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

# dieselben funktionen, die auch die seiten rechnen. eine karte, die dem
# archiv widerspricht, waere schlimmer als gar keine.
from stamp_pages import (ARCHIV, HOCH_CLOSE, HOCH_WERT, LOG,  # noqa: E402
                         archiv_reihe, dollar, lang, letzter_schluss,
                         mit_rand, tief_nach)

BREITE, HOEHE = 1080, 1350
ZIEL = os.path.join(REPO, "graphics", "dayn.png")
LOGO = os.path.join(REPO, "hawk.png")

# Chromiums --screenshot laesst die unteren rund 88 Pixel des Fensters
# unrastriert. Bei 1080x1350 traf das genau die Fusszeile: das DOM hatte
# Logo und Adresse, das PNG hatte sie nicht. Deshalb wird mit Ueberhang
# gerendert und danach exakt auf 1080x1350 geschnitten. Der Ueberhang ist
# grosszuegig, damit die Zahl 88 nicht zur stillen Annahme wird.
UEBERHANG = 260

# Der GitHub-Laeufer bringt google-chrome mit, diese Umgebung chromium
# unter /opt/pw-browsers. Beides wird gesucht, damit die Karte nicht an
# einem Pfad scheitert.
CHROME_KANDIDATEN = (
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/opt/pw-browsers/chromium-*/chrome-linux/chrome",
    "/opt/pw-browsers/chromium/chrome",
)


def chrome():
    import glob as _glob
    for muster in CHROME_KANDIDATEN:
        for p in sorted(_glob.glob(muster)):
            if os.access(p, os.X_OK):
                return p
    raise RuntimeError("kein chromium und kein chrome gefunden (gesucht: %s), "
                       "ohne renderer keine karte"
                       % ", ".join(CHROME_KANDIDATEN))


def png_lesen(pfad):
    """(breite, hoehe, byte_pro_pixel, zeilen) - entfiltert, echte pixel."""
    b = open(pfad, "rb").read()
    i, idat, w, h, bd, ct = 8, b"", None, None, None, None
    while i + 8 <= len(b):
        n = struct.unpack(">I", b[i:i + 4])[0]
        typ, dat = b[i + 4:i + 8], b[i + 8:i + 8 + n]
        if typ == b"IHDR":
            w, h, bd, ct = struct.unpack(">IIBB", dat[:10])
        elif typ == b"IDAT":
            idat += dat
        i += 12 + n
    if w is None or bd != 8 or ct not in (2, 6):
        raise ValueError("nur 8-bit rgb oder rgba, gelesen: %s" % pfad)
    bpp = 3 if ct == 2 else 4
    roh = zlib.decompress(idat)
    breit, zeilen, vor = w * bpp, [], bytearray(w * bpp)
    for y in range(h):
        f = roh[y * (breit + 1)]
        z = bytearray(roh[y * (breit + 1) + 1:(y + 1) * (breit + 1)])
        for x in range(breit):
            a = z[x - bpp] if x >= bpp else 0
            o = vor[x]
            c = vor[x - bpp] if x >= bpp else 0
            if f == 1:
                z[x] = (z[x] + a) & 255
            elif f == 2:
                z[x] = (z[x] + o) & 255
            elif f == 3:
                z[x] = (z[x] + (a + o) // 2) & 255
            elif f == 4:
                pp = a + o - c
                pa, pb, pc = abs(pp - a), abs(pp - o), abs(pp - c)
                z[x] = (z[x] + (a if pa <= pb and pa <= pc
                                else o if pb <= pc else c)) & 255
        zeilen.append(bytes(z))
        vor = z
    return w, h, bpp, zeilen


def png_schreiben(pfad, bpp, zeilen):
    w = len(zeilen[0]) // bpp
    roh = b"".join(b"\x00" + z for z in zeilen)

    def stueck(typ, dat):
        return (struct.pack(">I", len(dat)) + typ + dat
                + struct.pack(">I", zlib.crc32(typ + dat) & 0xFFFFFFFF))

    with open(pfad, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")
        fh.write(stueck(b"IHDR", struct.pack(">IIBBBBB", w, len(zeilen), 8,
                                             2 if bpp == 3 else 6, 0, 0, 0)))
        fh.write(stueck(b"IDAT", zlib.compress(roh, 9)))
        fh.write(stueck(b"IEND", b""))
    return pfad


def zuschneiden(pfad, breit, hoch):
    """auf genau breit x hoch stutzen, oben links verankert."""
    w, h, bpp, zeilen = png_lesen(pfad)
    if (w, h) == (breit, hoch):
        return pfad
    if w < breit or h < hoch:
        raise ValueError("bild %dx%d ist kleiner als %dx%d" % (w, h, breit, hoch))
    return png_schreiben(pfad, bpp, [z[:breit * bpp] for z in zeilen[:hoch]])


def helle_pixel(zeilen, bpp, von, bis, schwelle=60):
    """pixel ueber der schwelle in einem waagerechten band.
    Der Blindtest fuer 'da wurde nichts gemalt'."""
    n = 0
    for y in range(max(0, von), min(bis, len(zeilen))):
        z = zeilen[y]
        for x in range(0, len(z), bpp):
            if max(z[x:x + 3]) > schwelle:
                n += 1
    return n


def tage(von, bis):
    a = datetime.date(*[int(x) for x in von.split("-")])
    b = datetime.date(*[int(x) for x in bis.split("-")])
    return (b - a).days


def heute():
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


def _preis_zeile(jetzt, herkunft):
    from market_log import messzeit_hhmm
    uhr = messzeit_hhmm(herkunft, jetzt, "btc")
    return ("last price %s, %s utc" % (lang(jetzt["d"]), uhr) if uhr
            else "last price %s" % lang(jetzt["d"]))


def zahlen(archivrows, logrows, bis=None, herkunft=None):
    """die vier zahlen und zwei daten der karte.
    (werte, None) oder (None, grund).

    'bis' ist der Zaehltag, und er wird bewusst uebergeben statt hier
    ermittelt. Die Seiten zaehlen bis heute, der DAY-N-Textpost zaehlt bis
    zum Tag des juengsten Schlusses - am 24.09.2026 also 353 gegen 352.
    Beides ist fuer sich stimmig, aber Karte und Text gehen im selben
    Tweet raus und duerfen sich nicht widersprechen. Deshalb gibt der
    Post seinen Zaehltag hier hinein, statt dass die Karte selbst raet.
    Ohne 'bis' zaehlt die Karte bis heute, also wie die Seiten."""
    reihe = archiv_reihe(archivrows)
    if not reihe:
        return None, "kein btc im archiv"
    preis = dict(reihe)
    if preis.get(HOCH_CLOSE) is None:
        return None, "das zyklushoch fehlt im archiv"
    if abs(preis[HOCH_CLOSE] - HOCH_WERT) > 0.005:
        return None, ("archiv sagt hoch %.2f, die seiten sagen %.2f"
                      % (preis[HOCH_CLOSE], HOCH_WERT))
    tief = tief_nach(mit_rand(reihe, logrows), HOCH_CLOSE)
    if not tief:
        return None, "kein preis nach dem hoch"
    jetzt = letzter_schluss(logrows)
    if not jetzt:
        return None, "kein btc-schluss im log"
    stichtag = bis or heute()
    n_hoch = tage(HOCH_CLOSE, stichtag)
    n_tief = tage(tief[0], stichtag)
    if n_hoch <= 0 or n_tief <= 0:
        return None, "hoch oder tief liegt nicht in der vergangenheit"
    return {
        "tage_hoch": "{:,}".format(n_hoch),
        "hoch_datum": lang(HOCH_CLOSE),
        "hoch_preis": dollar(HOCH_WERT) + " USD",
        "tage_tief": "{:,}".format(n_tief),
        "tief_datum": lang(tief[0]),
        "tief_preis": dollar(tief[1]) + " USD",
        "stichtag": stichtag,
        "preis_datum": lang(jetzt["d"]),
        "preis": dollar(jetzt["btc"]) + " USD",
        "zaehltag": lang(stichtag),
        # letzter kurs mit uhrzeit nur, wenn sie gemessen ist (auftrag b)
        "preis_zeile": _preis_zeile(jetzt, herkunft),
    }, None


def logo_data():
    with open(LOGO, "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()


# Die Schriftgroessen stehen hier als Zahlen, weil grafik_check.py sie
# gegen die Hausnorm aus content-doktrin.md prueft. Wer eine aendert,
# aendert die Pruefung mit. Der Schluessel ist die Rolle in der Norm,
# nicht das Element: NORM in grafik_check.py haelt die Spannen.
SCHRIFT = {"zahl": 220, "label": 58, "bezug": 48, "marke": 80, "fuss": 34}


def html(w, skala=1.0):
    """die karte. skala<1 liefert dieselbe karte kleiner - dieselbe vorlage,
    dasselbe dom, nur herunterskaliert. Die 390px-Vorschau geht durch genau
    diesen Weg, damit sie nicht versehentlich etwas anderes zeigt als das,
    was gepostet wird."""
    L = logo_data()
    return """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  @page { margin:0 }
  * { margin:0; padding:0; box-sizing:border-box; }
  html,body { width:%(VB)dpx; min-height:%(VH)dpx; background:#080B0F;
              overflow:hidden; }
  .karte { width:%(B)dpx; height:%(H)dpx; background:#080B0F;
         transform:scale(%(S).8f); transform-origin:0 0;
         font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; color:#fff;
         background-image:radial-gradient(ellipse 120%% 55%% at 50%% -8%%,
                          rgba(73,234,203,0.13), transparent 60%%);
         display:flex; flex-direction:column; }
  .marke { display:flex; align-items:center; gap:26px; padding:44px 72px 0; }
  .marke img { width:%(MI)dpx; }
  .marke b { font-size:%(FM)dpx; letter-spacing:12px; font-weight:800; }
  .marke b span { color:#49EACB; }
  .mitte { flex:1; display:flex; flex-direction:column; justify-content:center;
           gap:56px; padding:0 72px; }
  .block { border-left:10px solid #D95926; padding:4px 0 4px 34px; }
  .block.t { border-left-color:#49EACB; }
  .label { font-size:%(FL)dpx; letter-spacing:4px; text-transform:uppercase;
           color:#9BA3AB; font-weight:700; }
  /* Hausnorm: die grosse Zahl ist WEISS. Die Bloecke unterscheiden sich
     am Rand, nicht an der Zahl - sonst konkurriert die Marke mit den
     Daten. */
  .zahl { font-size:%(FZ)dpx; line-height:1.0; font-weight:800;
          letter-spacing:-7px; color:#FFFFFF; margin:2px 0 6px; }
  .bezug { font-size:%(FB)dpx; line-height:1.38; color:#9BA3AB; }
  .bezug b { color:#fff; font-weight:600; }
  .fuss { display:flex; align-items:center; justify-content:space-between;
          margin:0 72px; padding:30px 0 40px; border-top:1px solid #2A313A; }
  .fuss .l { display:flex; align-items:center; gap:16px; }
  .fuss img { width:%(FI)dpx; }
  .fuss span { font-size:%(FF)dpx; color:#9BA3AB; letter-spacing:1px; }
  /* zwei zeilen: zaehltag und letzter kurs, jede fuer sich einzeilig */
  .fuss .zeilen span { display:block; line-height:1.25; white-space:nowrap;
                       letter-spacing:0; }
  .fuss .adr { color:#49EACB; font-weight:800; letter-spacing:2px; }
</style></head><body><div class="karte">
  <div class="marke"><img src="%(L)s" alt=""><b>PULSE<span>HAWK</span></b></div>
  <div class="mitte">
    <div class="block">
      <div class="label">days since the top</div>
      <div class="zahl" id="g-tage-hoch">%(tage_hoch)s</div>
      <div class="bezug">top was <b>%(hoch_datum)s</b><br>at <b>%(hoch_preis)s</b></div>
    </div>
    <div class="block t">
      <div class="label">days since the low</div>
      <div class="zahl" id="g-tage-tief">%(tage_tief)s</div>
      <div class="bezug">lowest so far was <b>%(tief_datum)s</b><br>at
        <b>%(tief_preis)s</b>, if that low holds</div>
    </div>
  </div>
  <div class="fuss">
    <div class="l"><img src="%(L)s" alt=""><div class="zeilen"><span class="z1">day count as of %(zaehltag)s</span><span class="z2">%(preis_zeile)s</span></div></div>
    <span class="adr">pulsehawk.io</span>
  </div>
</div></body></html>""" % dict(w, B=BREITE, H=HOEHE, L=L, MI=92, FI=54, S=skala,
                         VB=int(round(BREITE * skala)),
                         VH=int(round(HOEHE * skala)),
                         FZ=SCHRIFT["zahl"], FL=SCHRIFT["label"],
                         FB=SCHRIFT["bezug"], FM=SCHRIFT["marke"],
                         FF=SCHRIFT["fuss"])


# Was die Vorlage ueber sich selbst wissen muss, holt sich der Check aus
# dem echten Layout statt es zu schaetzen. Zeichenbreiten haengen an der
# Schrift, und die Fusszeile ist schon einmal still auf zwei Zeilen
# umgebrochen, weil ich sie ueberschlagen statt gemessen habe.
MESSSKRIPT = """<script>window.addEventListener('load',function(){
 var o={};
 function kasten(s){var e=document.querySelector(s); if(!e) return null;
   var r=e.getBoundingClientRect();
   return {oben:Math.round(r.top), unten:Math.round(r.bottom),
           links:Math.round(r.left), rechts:Math.round(r.right),
           hoch:Math.round(r.height),
           ueber: e.scrollWidth > e.clientWidth + 1};}
 ['.karte','.marke','.mitte','.fuss','.fuss .z1','.fuss .z2','.fuss .adr',
  '#g-tage-hoch','#g-tage-tief'].forEach(function(s){o[s]=kasten(s);});
 o.seite = {hoch: document.body.scrollHeight};
 document.title = JSON.stringify(o);});</script>"""


def geometrie(w):
    """das echte layout, vom browser gemessen. dict oder RuntimeError."""
    quelle = os.path.join(os.path.dirname(ZIEL) or ".", "messung.html")
    os.makedirs(os.path.dirname(quelle), exist_ok=True)
    with open(quelle, "w", encoding="utf-8") as fh:
        fh.write(html(w).replace("</body>", MESSSKRIPT + "</body>"))
    r = subprocess.run([chrome(), "--headless", "--disable-gpu", "--no-sandbox",
                        "--virtual-time-budget=4000",
                        "--window-size=%d,%d" % (BREITE, HOEHE + UEBERHANG),
                        "--dump-dom", "file://" + quelle], capture_output=True)
    os.remove(quelle)
    dom = r.stdout.decode("utf-8", "replace")
    a, b = dom.find("<title>"), dom.find("</title>")
    if a < 0 or b < a:
        raise RuntimeError("die messung kam ohne ergebnis zurueck")
    return json.loads(dom[a + 7:b].replace("&quot;", '"').replace("&amp;", "&"))


def bauen(w, ziel=ZIEL, skala=1.0):
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    quelle = ziel + ".html"
    with open(quelle, "w", encoding="utf-8") as fh:
        fh.write(html(w, skala))
    cmd = [chrome(), "--headless", "--disable-gpu", "--no-sandbox",
           "--hide-scrollbars", "--force-device-scale-factor=1",
           "--virtual-time-budget=4000",
           "--window-size=%d,%d" % (round(BREITE * skala),
                                    round(HOEHE * skala) + UEBERHANG),
           "--screenshot=" + ziel, "file://" + quelle]
    r = subprocess.run(cmd, capture_output=True)
    if not os.path.exists(ziel):
        raise RuntimeError("chromium hat nichts geschrieben: %s"
                           % r.stderr.decode()[-300:])
    os.remove(quelle)
    zuschneiden(ziel, int(round(BREITE * skala)), int(round(HOEHE * skala)))
    return ziel


def selbsttest():
    schlecht = 0
    gezaehlt = 0

    def pruefe(name, ist, soll):
        nonlocal schlecht, gezaehlt
        gezaehlt += 1
        if ist != soll:
            schlecht += 1
            print("  FEHL %s\n    ist  %r\n    soll %r" % (name, ist, soll))
        else:
            print("  ok   %s" % name)

    pruefe("tage zwischen zwei daten", tage("2025-10-06", "2026-09-24"), 353)
    arch = [{"d": HOCH_CLOSE, "btc": HOCH_WERT},
            {"d": "2026-06-30", "btc": 58534.28}]
    log = [{"d": "2026-09-23", "btc": 84424.0}]
    w, grund = zahlen(arch, log, bis="2026-09-24")
    pruefe("kein grund zum abbruch", grund, None)
    pruefe("tage seit dem hoch", w["tage_hoch"], "353")
    pruefe("tage seit dem tief", w["tage_tief"], "86")
    pruefe("hoch mit datum", w["hoch_datum"], "6 October 2025")
    pruefe("hoch mit preis", w["hoch_preis"], "124,777 USD")
    pruefe("tief mit datum und preis",
           (w["tief_datum"], w["tief_preis"]), ("30 June 2026", "58,534 USD"))
    # faellt bitcoin tiefer, zaehlt die karte ab dem neuen tag
    tiefer = arch + [{"d": "2026-08-01", "btc": 40000.0}]
    w2, _ = zahlen(tiefer, log, bis="2026-09-24")
    pruefe("neues tief zieht den zaehler nach",
           (w2["tage_tief"], w2["tief_datum"]), ("54", "1 August 2026"))
    pruefe("fremdes hoch faellt auf",
           zahlen([{"d": HOCH_CLOSE, "btc": 1.0}], log, bis="2026-09-24")[0], None)
    pruefe("log ohne schluss faellt auf",
           zahlen(arch, [{"d": "2026-09-23", "gld": 1.0}], bis="2026-09-24")[0], None)

    seite = html(w)
    pruefe("beide zahlen stehen in der karte",
           ('>353<' in seite, '>86<' in seite), (True, True))
    pruefe("jede zahl mit ihrem bezugspunkt",
           ("6 October 2025" in seite and "124,777 USD" in seite
            and "30 June 2026" in seite and "58,534 USD" in seite), True)
    pruefe("der vorbehalt steht dabei", "if that low holds" in seite, True)
    pruefe("logo oben und unten", seite.count("data:image/png;base64,"), 2)
    pruefe("adresse in der fusszeile", "pulsehawk.io" in seite, True)
    pruefe("der zaehltag steht auf der karte",
           "day count as of 24 September 2026" in seite, True)
    pruefe("der letzte kurs mit seinem tag, ohne herkunft ohne uhrzeit",
           ">last price 23 September 2026<" in seite, True)
    mit_uhr, _ = zahlen(arch, log, bis="2026-09-24",
                        herkunft={"2026-09-23": {"btc": {"art": "momentaufnahme",
                                                         "zeit": "2026-09-23T22:07:41Z",
                                                         "zeit_aus": "quelle"}}})
    pruefe("mit gemessener zeit steht sie dabei",
           mit_uhr["preis_zeile"], "last price 23 September 2026, 22:07 utc")
    # die karte zaehlt, was man ihr sagt. das ist der ganze grund fuer 'bis'.
    frueher, _ = zahlen(arch, log, bis="2026-09-23")
    pruefe("ein anderer zaehltag gibt andere zahlen",
           (frueher["tage_hoch"], frueher["tage_tief"], frueher["zaehltag"]),
           ("352", "85", "23 September 2026"))
    pruefe("format 4:5", (BREITE, HOEHE, round(HOEHE / BREITE, 4)),
           (1080, 1350, 1.25))
    pruefe("ein renderer ist da", os.access(chrome(), os.X_OK), True)
    print("\n%d von %d faellen falsch" % (schlecht, gezaehlt))
    return 1 if schlecht else 0


def main(argv):
    if "--selftest" in argv:
        print("=" * 60)
        print("SELBSTTEST dayn_grafik")
        print("=" * 60)
        return selbsttest()
    with open(ARCHIV, encoding="utf-8") as fh:
        arch = json.load(fh)
    with open(LOG, encoding="utf-8") as fh:
        log = json.load(fh)
    w, grund = zahlen(arch, log)
    if w is None:
        print("keine karte: %s" % grund)
        return 1
    ziel = bauen(w)
    print("karte gebaut: %s" % ziel)
    print("  tag %s seit dem hoch (%s), tag %s seit dem tief (%s)"
          % (w["tage_hoch"], w["hoch_datum"], w["tage_tief"], w["tief_datum"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
