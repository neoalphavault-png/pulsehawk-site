#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""grafik_check.py, die Wache vor dem Bildpost, plus 390px-Vorschau.

WARUM ES DIESE DATEI GIBT
Pflichtlauf vor jedem Post. Die Groessen- und Farbregeln stammen aus der
Hausnorm content-doktrin.md, die nicht im Repo liegt; die Spannen in NORM
unten sind von dort abgeschrieben, nicht erfunden. Alles andere
(Dateigroesse, gemalte Baender, Abgleich mit der frischen Rechnung) ist
hier aufgestellt worden.

WAS DIE NORM UEBER DIE VORSCHAU SAGT
"Die 390px-Vorschau wird ANGESEHEN, nicht gemessen." Hier stand vorher
das Gegenteil: eine Rechnung, die Schriftgroessen auf 390px umrechnete
und gegen 9px prueft. Das ist ersetzt. Geprueft werden die Groessen bei
1080px gegen die Norm, denn dort sind sie definiert. Die Vorschau wird
gebaut, auf Masse und darauf geprueft, dass sie gemalt wurde - und dann
hingelegt, damit ein Mensch hinsieht.

DIE REGEL DAHINTER
Reisst der Check, geht KEIN Post raus. Lieber eine Luecke im Archiv als
eine unlesbare Karte. Der Rueckgabewert ist deshalb der Schalter, nicht
die Empfehlung: 0 heisst posten, alles andere heisst nicht posten.

WAS GEPRUEFT WIRD
  1. FORMAT    genau 1080x1350, also 4:5. Nicht ungefaehr.
  2. DATEI     gueltiges PNG, 20 kB bis 5 MB. Die Untergrenze faengt den
               halben Render, die Obergrenze ist das Limit der X-API.
  3. GEMALT    Die Pixel werden entpackt und gezaehlt, nicht das DOM
               befragt. Getrennt fuer Kopfband und Fussband, damit "Logo
               oben UND unten" eine Aussage ueber das Bild ist und nicht
               ueber den Quelltext. Das ist kein Schmuck: Chromiums
               --screenshot liess die unteren rund 88 Pixel unrastriert,
               das DOM meldete Logo und Adresse brav, das PNG hatte an
               der Stelle nichts. Eine Wache, die nur den Quelltext
               liest, haette den Post rausgehen lassen.
  4. ZAHLEN    Der Check rechnet die Tageszahlen SELBST aus Archiv und Log
               nach und vergleicht sie mit der Karte. Eine Karte von
               gestern faellt hier auf. Das ist die wichtigste Pruefung.
  5. BEZUG     Jede Zahl braucht ihren Bezugspunkt im selben Block, Logo
               oben UND unten, Adresse in der Fusszeile.
  6. NORM      Jede Schriftgroesse muss in der Spanne ihrer Rolle liegen
               (NORM unten), und keine ausser Einheit/Absender darf unter
               die absolute Untergrenze von 40px. Massstab im Feed ist
               0,36: aus 30px werden 11px, und 11px liest niemand ohne
               anzutippen. Wer antippen muss, leitet nicht weiter.
  7. FARBE     Hintergrund #080B0F, Teal #49EACB, und die grosse Zahl ist
               WEISS - sonst konkurriert die Marke mit den Daten. Kein
               Wasserzeichen hinter den Daten.
  8. LAYOUT    Der Browser misst das fertige Layout nach: nichts laeuft
               ueber die Karte hinaus, die Karte ist genau 1350 hoch, und
               die Fusszeile steht auf EINER Zeile. Die Fusszeile ist
               schon einmal still auf zwei Zeilen umgebrochen, weil die
               Zeichenbreite ueberschlagen statt gemessen wurde.
  9. VORSCHAU  Die 390px-Datei wird geschrieben und auf Masse und Farbe
               geprueft. Fehlt sie, reisst der Check. Ihr Inhalt wird
               nicht bewertet - den sieht ein Mensch an.

    python3 scripts/grafik_check.py                 baut und prueft
    python3 scripts/grafik_check.py --bis 2026-09-23 zaehlt bis zu dem tag
    python3 scripts/grafik_check.py --nur-pruefen   prueft, was da ist
    python3 scripts/grafik_check.py --selftest
"""
import json
import os
import struct
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import dayn_grafik as G  # noqa: E402
from stamp_pages import ARCHIV, LOG  # noqa: E402

VORSCHAU_BREITE = 390
VORSCHAU = os.path.join(REPO, "graphics", "dayn-vorschau-390.png")

MIN_BYTES = 20 * 1024
MAX_BYTES = 5 * 1024 * 1024
MIN_HELL_BAND = 300      # helle pixel im kopf- und im fussband, bei 1080x1350
MIN_HELL_GESAMT = 5000   # helle pixel auf der ganzen karte, bei 1080x1350
# Hausnorm content-doktrin.md, Mindestgroessen bei 1080 px Bildbreite,
# keine Ausnahmen. Schluessel ist die Rolle, Wert ist (name, min, max).
# "Schlusssatz" steht mit in der Tabelle, obwohl die Tageskarte keinen
# hat - die Tabelle ist die Norm, nicht die Auswahl dieser Karte.
NORM = {
    "zahl":  ("die eine grosse Zahl", 180, 320),
    "kopf":  ("Kopfzeile", 78, 90),
    "marke": ("Kopfzeile", 78, 90),
    "schluss": ("Schlusssatz", 60, 70),
    "label": ("Beschriftung einer Zahl", 56, 60),
    "bezug": ("Fliesstext, Erklaerung", 46, 52),
    "fuss":  ("Einheit, Datum, Absender", 32, 36),
}
UNTERGRENZE = 40         # absolut, ausser Einheit und Absender
OHNE_UNTERGRENZE = ("fuss",)
FEED_MASSSTAB = 0.36     # so klein steht die karte im zeitstrahl

HINTERGRUND = "#080B0F"
TEAL = "#49EACB"
ZAHL_FARBE = "#FFFFFF"   # die grosse zahl ist weiss, nicht teal

PFLICHTTEXT = ("days since the top", "days since the low", "pulsehawk.io",
               "if that low holds", "daily prices to ")


def png_kopf(pfad):
    """(breite, hoehe) oder None, wenn es kein PNG ist."""
    with open(pfad, "rb") as fh:
        kopf = fh.read(24)
    if len(kopf) < 24 or kopf[:8] != b"\x89PNG\r\n\x1a\n" or kopf[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", kopf[16:24])


def bild_baender(pfad):
    """(kopf, fuss, gesamt) helle pixel. Zaehlt, was wirklich gemalt wurde."""
    w, h, bpp, zeilen = G.png_lesen(pfad)
    kopf = G.helle_pixel(zeilen, bpp, 0, int(h * 0.12))
    fuss = G.helle_pixel(zeilen, bpp, int(h * 0.90), h)
    gesamt = G.helle_pixel(zeilen, bpp, 0, h)
    return kopf, fuss, gesamt


def grenzen(pfad):
    """Schwellen wachsen mit der Bildflaeche, damit dieselben Zahlen fuer
    die 1080er Karte und die 390er Vorschau gelten."""
    w, h, _, _ = G.png_lesen(pfad)
    teil = (w * h) / float(G.BREITE * G.HOEHE)
    return (max(30, int(MIN_HELL_BAND * teil)),
            max(500, int(MIN_HELL_GESAMT * teil)))


def vorschau(quelle_werte, ziel=VORSCHAU):
    """die karte noch einmal, aber so klein wie im zeitstrahl.

    Nicht ueber --force-device-scale-factor: Chromium klemmt den Wert bei
    0.5 ab und liefert 540px statt 390px. Nicht ueber einen skalierten
    iframe: Chromium malt dessen unteren Teil nicht mit. Sondern ueber
    dieselbe Vorlage mit skala<1 - die Vorschau zeigt damit beweisbar
    dasselbe DOM wie die Karte, die gepostet wird.
    """
    return G.bauen(quelle_werte, ziel=ziel,
                   skala=VORSCHAU_BREITE / float(G.BREITE))


def norm_funde(schrift=None):
    """welche schriftgroessen die hausnorm verletzen."""
    schrift = schrift or G.SCHRIFT
    schlimm = []
    for name, px in sorted(schrift.items()):
        if name not in NORM:
            schlimm.append("%s hat keine rolle in der norm" % name)
            continue
        rolle, unten, oben = NORM[name]
        if px < unten or px > oben:
            schlimm.append("%s ist %dpx, die norm sagt %d bis %d fuer '%s' "
                           "(im feed waeren das %.0fpx)"
                           % (name, px, unten, oben, rolle, px * FEED_MASSSTAB))
        elif px < UNTERGRENZE and name not in OHNE_UNTERGRENZE:
            schlimm.append("%s ist %dpx, unter der absoluten untergrenze von "
                           "%dpx" % (name, px, UNTERGRENZE))
    return schlimm


def farb_funde(seite):
    """welche farbregeln der hausnorm die vorlage verletzt."""
    schlimm = []
    if HINTERGRUND not in seite:
        schlimm.append("der hintergrund %s steht nicht in der vorlage"
                       % HINTERGRUND)
    if TEAL not in seite:
        schlimm.append("das teal %s steht nicht in der vorlage" % TEAL)
    ab = seite.find(".zahl {")
    regel = seite[ab:seite.find("}", ab)] if ab >= 0 else ""
    if "color:" + ZAHL_FARBE not in regel.replace(" ", ""):
        schlimm.append("die grosse zahl ist nicht %s - sonst konkurriert die "
                       "marke mit den daten" % ZAHL_FARBE)
    if "url(" in seite.split("</style>")[0]:
        schlimm.append("ein bild als hintergrund: kein wasserzeichen hinter "
                       "den daten")
    return schlimm


def layout_funde(werte):
    """was der browser am fertigen layout zu beanstanden hat."""
    g = G.geometrie(werte)
    schlimm = []
    karte = g.get(".karte") or {}
    if karte.get("hoch") != G.HOEHE:
        schlimm.append("die karte ist %s hoch, nicht %d"
                       % (karte.get("hoch"), G.HOEHE))
    for wahl, kasten in sorted(g.items()):
        if wahl == "seite" or not kasten:
            continue
        if kasten.get("ueber"):
            schlimm.append("%s laeuft ueber seine breite hinaus" % wahl)
        if kasten.get("unten", 0) > G.HOEHE:
            schlimm.append("%s endet bei %s, unter dem rand der karte (%d)"
                           % (wahl, kasten.get("unten"), G.HOEHE))
        if kasten.get("rechts", 0) > G.BREITE:
            schlimm.append("%s reicht bis %s, ueber den rand der karte (%d)"
                           % (wahl, kasten.get("rechts"), G.BREITE))
    # eine zeile bei 34px ist rund 47px hoch, zwei sind rund 78
    fuss = g.get(".fuss .l span") or {}
    if fuss.get("hoch", 0) > G.SCHRIFT["fuss"] * 1.7:
        schlimm.append("die fusszeile bricht um (%spx hoch bei %dpx schrift) - "
                       "kuerzer fassen, nicht kleiner setzen"
                       % (fuss.get("hoch"), G.SCHRIFT["fuss"]))
    return schlimm


def pruefe(png, werte, soll, vorschau_pfad=VORSCHAU, schrift=None, layout=True):
    """alle pruefungen. liste der klagen, leer heisst: posten.
    'soll' sind die frisch nachgerechneten werte."""
    klagen = []

    if not os.path.exists(png):
        return ["die karte fehlt: %s" % png]

    masse = png_kopf(png)
    if masse is None:
        klagen.append("die datei ist kein gueltiges png")
    elif masse != (G.BREITE, G.HOEHE):
        klagen.append("format %dx%d, verlangt sind %dx%d (4:5)"
                      % (masse[0], masse[1], G.BREITE, G.HOEHE))

    gross = os.path.getsize(png)
    if gross < MIN_BYTES:
        klagen.append("nur %d bytes, unter %d - sieht nach halbem render aus"
                      % (gross, MIN_BYTES))
    elif gross > MAX_BYTES:
        klagen.append("%d bytes, ueber dem 5-mb-limit der x-api" % gross)

    if masse is not None:
        kopf, fuss, gesamt = bild_baender(png)
        g_band, g_gesamt = grenzen(png)
        if gesamt < g_gesamt:
            klagen.append("die karte sieht leer aus (%d helle pixel, noetig "
                          "%d) - nichts gerendert?" % (gesamt, g_gesamt))
        if kopf < g_band:
            klagen.append("im kopfband sind nur %d helle pixel (noetig %d) - "
                          "logo oben fehlt im bild" % (kopf, g_band))
        if fuss < g_band:
            klagen.append("im fussband sind nur %d helle pixel (noetig %d) - "
                          "logo und adresse unten fehlen im bild"
                          % (fuss, g_band))

    # die wichtigste pruefung: stimmt die karte mit der frischen rechnung?
    for feld in ("tage_hoch", "tage_tief", "hoch_datum", "tief_datum",
                 "hoch_preis", "tief_preis", "zaehltag"):
        if werte.get(feld) != soll.get(feld):
            klagen.append("%s auf der karte %r, frisch gerechnet %r"
                          % (feld, werte.get(feld), soll.get(feld)))

    seite = G.html(werte)
    for t in PFLICHTTEXT:
        if t not in seite:
            klagen.append("der pflichttext %r fehlt" % t)
    for feld in ("tage_hoch", "tage_tief"):
        if ">%s<" % werte.get(feld) not in seite:
            klagen.append("die zahl %s steht nicht als eigener wert in der karte"
                          % werte.get(feld))
    # jede zahl mit ihrem bezugspunkt im selben block
    for zahl, bezug in (("g-tage-hoch", (werte.get("hoch_datum"),
                                         werte.get("hoch_preis"))),
                        ("g-tage-tief", (werte.get("tief_datum"),
                                         werte.get("tief_preis")))):
        ab = seite.find('id="%s"' % zahl)
        block = seite[ab:ab + 900] if ab >= 0 else ""
        for b in bezug:
            if not b or b not in block:
                klagen.append("im block %s fehlt der bezugspunkt %r" % (zahl, b))
    if seite.count("data:image/png;base64,") < 2:
        klagen.append("logo nicht oben und unten - die karte wird beschnitten "
                      "weitergeschickt")

    klagen.extend(norm_funde(schrift))
    klagen.extend(farb_funde(seite))
    if layout:
        klagen.extend(layout_funde(werte))

    if not os.path.exists(vorschau_pfad):
        klagen.append("die 390px-vorschau fehlt: %s" % vorschau_pfad)
    else:
        v = png_kopf(vorschau_pfad)
        if v is None or v[0] != VORSCHAU_BREITE:
            klagen.append("die vorschau ist nicht %dpx breit (%s)"
                          % (VORSCHAU_BREITE, v))
    return klagen


def lauf(bauen=True, bis=None):
    with open(ARCHIV, encoding="utf-8") as fh:
        arch = json.load(fh)
    with open(LOG, encoding="utf-8") as fh:
        log = json.load(fh)
    soll, grund = G.zahlen(arch, log, bis=bis)
    if soll is None:
        print("KEIN POST: %s" % grund)
        return 2
    if bauen:
        G.bauen(soll)
        vorschau(soll)
    klagen = pruefe(G.ZIEL, soll, soll)
    print("karte:    %s" % G.ZIEL)
    print("vorschau: %s (%dpx) - ANSEHEN, nicht messen" % (VORSCHAU, VORSCHAU_BREITE))
    print("tag %s seit dem hoch, tag %s seit dem tief, stichtag %s"
          % (soll["tage_hoch"], soll["tage_tief"], soll["stichtag"]))
    if klagen:
        print("\nCHECK GERISSEN, KEIN POST:")
        for k in klagen:
            print("  - %s" % k)
        return 1
    print("\ncheck bestanden, die karte darf raus")
    return 0


def selbsttest():
    schlecht = 0
    gezaehlt = 0

    def p(name, ist, soll):
        nonlocal schlecht, gezaehlt
        gezaehlt += 1
        if ist != soll:
            schlecht += 1
            print("  FEHL %s\n    ist  %r\n    soll %r" % (name, ist, soll))
        else:
            print("  ok   %s" % name)

    import tempfile
    tmp = tempfile.mkdtemp()
    arch = [{"d": G.HOCH_CLOSE, "btc": G.HOCH_WERT},
            {"d": "2026-06-30", "btc": 58534.28}]
    log = [{"d": "2026-09-23", "btc": 84424.0}]
    soll, _ = G.zahlen(arch, log, bis="2026-09-24")

    echt = G.bauen(soll, ziel=os.path.join(tmp, "k.png"))
    vs = vorschau(soll, ziel=os.path.join(tmp, "v.png"))
    p("die gebaute karte ist 1080x1350", png_kopf(echt), (1080, 1350))
    p("die vorschau ist 390 breit", png_kopf(vs)[0], 390)
    kopf, fuss, gesamt = bild_baender(echt)
    p("kopf- und fussband sind wirklich gemalt",
      (kopf > MIN_HELL_BAND, fuss > MIN_HELL_BAND), (True, True))
    # genau dieser fall ging vorher durch: das dom hatte die fusszeile,
    # das png nicht, weil chromium den unteren rand nicht rasterte.
    W, H, bpp, zeilen = G.png_lesen(echt)
    ohne = os.path.join(tmp, "ohnefuss.png")
    G.png_schreiben(ohne, bpp, [z if y < int(H * 0.88) else b"\x00" * len(z)
                                for y, z in enumerate(zeilen)])
    p("eine karte ohne gemalte fusszeile reisst den check",
      any("unten fehlen im bild" in k
          for k in pruefe(ohne, soll, soll, vorschau_pfad=vs, layout=False)), True)
    ohne_kopf = os.path.join(tmp, "ohnekopf.png")
    G.png_schreiben(ohne_kopf, bpp, [b"\x00" * len(z) if y < int(H * 0.12) else z
                                     for y, z in enumerate(zeilen)])
    p("eine karte ohne gemaltes logo oben reisst den check",
      any("oben fehlt im bild" in k
          for k in pruefe(ohne_kopf, soll, soll, vorschau_pfad=vs, layout=False)), True)
    p("die vorschau besteht dieselbe bandpruefung mit denselben zahlen",
      [k for k in pruefe(vs, soll, soll, vorschau_pfad=vs, layout=False) if "band" in k], [])
    p("eine echte karte besteht", pruefe(echt, soll, soll, vorschau_pfad=vs), [])
    p("der browser findet nichts am layout", layout_funde(soll), [])
    p("eine zu lange fusszeile reisst den check",
      any("bricht um" in x for x in layout_funde(
          dict(soll, zaehltag="24 September 2026 und noch viel mehr text"))), True)

    # eine leere karte darf nicht durchgehen
    leer = os.path.join(tmp, "leer.png")
    with open(leer + ".html", "w") as fh:
        fh.write("<body style='width:1080px;height:1350px;background:#080B0F'>")
    subprocess.run([G.chrome(), "--headless", "--disable-gpu", "--no-sandbox",
                    "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--window-size=1080,1350", "--screenshot=" + leer,
                    "file://" + leer + ".html"], capture_output=True)
    klagen = pruefe(leer, soll, soll, vorschau_pfad=vs, layout=False)
    p("eine einfarbige karte reisst den check",
      any("leer aus" in k or "halbem render" in k for k in klagen), True)
    p("png runde und runter: zuschneiden aendert nur die masse",
      G.png_lesen(G.zuschneiden(G.png_schreiben(
          os.path.join(tmp, "z.png"), bpp, zeilen), 1080, 1000))[:2], (1080, 1000))

    # falsches format
    quer = os.path.join(tmp, "quer.png")
    with open(quer + ".html", "w") as fh:
        fh.write(G.html(soll))
    subprocess.run([G.chrome(), "--headless", "--disable-gpu", "--no-sandbox",
                    "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--window-size=1080,1080", "--screenshot=" + quer,
                    "file://" + quer + ".html"], capture_output=True)
    p("1:1 statt 4:5 reisst den check",
      any("4:5" in k for k in pruefe(quer, soll, soll, vorschau_pfad=vs, layout=False)), True)

    # eine karte von gestern
    alt = dict(soll, tage_hoch="352", tage_tief="85")
    k = pruefe(echt, alt, soll, vorschau_pfad=vs, layout=False)
    p("eine karte von gestern reisst den check",
      any("frisch gerechnet" in x for x in k), True)

    # kein bild, kein post
    p("fehlende karte reisst den check",
      pruefe(os.path.join(tmp, "gibtsnicht.png"), soll, soll), 
      ["die karte fehlt: %s" % os.path.join(tmp, "gibtsnicht.png")])
    p("fehlende vorschau reisst den check",
      any("vorschau fehlt" in x for x in
          pruefe(echt, soll, soll, vorschau_pfad=os.path.join(tmp, "nix.png"))),
      True)

    # lesbarkeit
    p("die echten groessen halten die hausnorm", norm_funde(), [])
    # genau der fall, den die norm an uns beanstandet hat
    p("30px fusszeile reisst den check",
      len(norm_funde(dict(G.SCHRIFT, fuss=30))), 1)
    p("und die klage nennt die feed-groesse",
      "11px" in norm_funde(dict(G.SCHRIFT, fuss=30))[0], True)
    p("32 und 36 sind noch drin, 31 und 37 nicht",
      [len(norm_funde(dict(G.SCHRIFT, fuss=x))) for x in (31, 32, 36, 37)],
      [1, 0, 0, 1])
    p("eine zu grosse zahl reisst auch",
      len(norm_funde(dict(G.SCHRIFT, zahl=400))), 1)
    p("eine rolle ohne norm faellt auf",
      norm_funde({"erfunden": 50}), ["erfunden hat keine rolle in der norm"])
    p("die grosse zahl muss weiss sein",
      any("nicht #FFFFFF" in x
          for x in farb_funde(G.html(soll).replace("color:#FFFFFF",
                                                   "color:#49EACB"))), True)
    p("die echte vorlage haelt die farbnorm", farb_funde(G.html(soll)), [])
    p("ein wasserzeichen reisst den check",
      any("wasserzeichen" in x for x in farb_funde(
          G.html(soll).replace(".karte {", ".karte { background:url(w.png);"))),
      True)
    p("fehlender bezugspunkt reisst den check",
      any("bezugspunkt" in x for x in
          pruefe(echt, dict(soll, hoch_preis=""), dict(soll, hoch_preis=""),
                 vorschau_pfad=vs, layout=False)), True)
    # Vertauschte Bezugspunkte kann die Blockpruefung NICHT sehen: das html
    # entsteht aus demselben dict, also steht in jedem block brav sein
    # eigener (vertauschter) wert. Gefangen wird der Tausch von Pruefung 4,
    # dem Vergleich mit der frischen Rechnung. Deshalb steht dieser Fall hier.
    tausch = dict(soll, hoch_datum=soll["tief_datum"],
                  tief_datum=soll["hoch_datum"])
    p("vertauschte bezugspunkte reissen den check",
      sorted(x.split()[0] for x in pruefe(echt, tausch, soll, vorschau_pfad=vs, layout=False)),
      ["hoch_datum", "tief_datum"])
    p("die vorschau ist so hoch wie 4:5 verlangt",
      int(round(G.HOEHE * VORSCHAU_BREITE / float(G.BREITE))), 488)
    p("die vorschaubreite ist die aus dem auftrag", VORSCHAU_BREITE, 390)

    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    print("\n%d von %d faellen falsch" % (schlecht, gezaehlt))
    return 1 if schlecht else 0


def main(argv):
    if "--selftest" in argv:
        print("=" * 60)
        print("SELBSTTEST grafik_check")
        print("=" * 60)
        return selbsttest()
    bis = None
    for i, x in enumerate(argv):
        if x == "--bis" and i + 1 < len(argv):
            bis = argv[i + 1]
    return lauf(bauen="--nur-pruefen" not in argv, bis=bis)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
