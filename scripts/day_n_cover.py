#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""day_n_cover.py, das Pflichtbild zum taeglichen DAY-N-Post.

WARUM ES DAS GIBT
Belege in docs/projekt/befund-shares.md. Zwei Saetze daraus:
Ein Post wird nach Aktivierung geteilt, nicht nach Nuetzlichkeit, und
weitergeschickt wird oft nur das Bild. Also gehoert der zitierbare Satz
(Zeile 3 des Posts, die Wendung) INS Bild und nicht nur daneben.

Format 4:5 (1080 x 1350), das hochkant-Format, das X in der Zeitleiste am
groessten zeigt. Dunkle PulseHawk-Flaeche, dieselben Farben wie die Seite
(:root in bitcoin-top-to-bottom.html).

Inhalt, von oben nach unten:
  1. Wortmarke und Eyebrow
  2. die Zahl aus Zeile 1 des Posts, gross
  3. die drei Referenztage als Marken auf einer Achse, die heutige
     Position markiert, das Fenster zwischen erstem und letztem Tief
     als Band
  4. die Wendung als Satz, klein darunter
  5. Quelle klein: "daily closes, never intraday highs"

KEIN TEXT OHNE BILD, und kein Bild ohne Schrift: findet das Skript keine
TrueType-Schrift, bricht es ab, statt die Bitmap-Notschrift von Pillow zu
nehmen. Ein Bild mit zerbroeselter Zahl ist schlimmer als kein Post.

    python3 scripts/day_n_cover.py --day 344 \
        --wendung "we are inside that window now." --out build/day-n.png
    python3 scripts/day_n_cover.py --selftest
"""
import argparse
import os
import sys

BREITE, HOEHE = 1080, 1350          # 4:5
RAND = 84

# dieselben Farben wie :root in bitcoin-top-to-bottom.html
BG = (8, 11, 15)
LINE = (26, 29, 33)
TEAL = (73, 234, 203)
BTC = (217, 89, 38)
TXT = (255, 255, 255)
DIM = (155, 163, 171)
DIMMER = (122, 130, 140)

# Liberation Sans ist metrisch wie Arial, die Seite setzt Helvetica/Arial.
# DejaVu und FreeSans sind der Rueckfall; auf ubuntu-latest liegen alle drei.
SCHRIFTEN = {
    "fett": ("LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf", "FreeSansBold.ttf",
             "Helvetica-Bold.ttf", "Arial Bold.ttf"),
    "normal": ("LiberationSans-Regular.ttf", "DejaVuSans.ttf", "FreeSans.ttf",
               "Helvetica.ttf", "Arial.ttf"),
}
ORTE = ("/usr/share/fonts/truetype/liberation",
        "/usr/share/fonts/truetype/liberation2",
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/truetype/freefont",
        "/usr/share/fonts", "/usr/local/share/fonts",
        "/Library/Fonts", "/System/Library/Fonts",
        os.path.expanduser("~/.fonts"))


def schriftdatei(art):
    """Erster Treffer aus SCHRIFTEN[art] im Dateisystem. None, wenn keine da
    ist; der Aufrufer bricht dann ab."""
    for name in SCHRIFTEN[art]:
        for ort in ORTE:
            p = os.path.join(ort, name)
            if os.path.isfile(p):
                return p
        for wurzel in ("/usr/share/fonts", "/usr/local/share/fonts"):
            for dirpath, _, dateien in os.walk(wurzel):
                if name in dateien:
                    return os.path.join(dirpath, name)
    return None


def laden(art, groesse):
    from PIL import ImageFont
    p = schriftdatei(art)
    if not p:
        sys.exit("keine TrueType-Schrift gefunden (%s). Ohne Schrift kein Bild, "
                 "ohne Bild kein Post." % ", ".join(SCHRIFTEN[art]))
    return ImageFont.truetype(p, groesse)


def umbrechen(draw, text, font, breite):
    """Gieriger Zeilenumbruch auf die gemessene Pixelbreite."""
    worte, zeilen, zeile = text.split(), [], ""
    for w in worte:
        versuch = (zeile + " " + w).strip()
        if draw.textlength(versuch, font=font) <= breite or not zeile:
            zeile = versuch
        else:
            zeilen.append(zeile)
            zeile = w
    if zeile:
        zeilen.append(zeile)
    return zeilen


def gesperrt(draw, xy, text, font, fill, sperrung):
    """Text mit Buchstabenabstand, wie .eyebrow und .nav b auf der Seite.
    Gibt die Endbreite zurueck."""
    x, y = xy
    start = x
    for z in text:
        draw.text((x, y), z, font=font, fill=fill)
        x += draw.textlength(z, font=font) + sperrung
    return x - sperrung - start


def achse(draw, y, marken, heute, fonts):
    """Die drei Referenztage als Marken auf einer Achse, das Fenster
    dazwischen als Band, die heutige Position in Teal.

    Die Skala umfasst immer alle Marken UND den heutigen Tag, mit etwas
    Luft an beiden Enden. Steht der heutige Tag weit rechts (Fall C),
    waechst die Skala mit, statt den Punkt aus dem Bild zu schieben."""
    lo_wert = min(list(marken) + [heute])
    hi_wert = max(list(marken) + [heute])
    luft = max(18, int((hi_wert - lo_wert) * 0.16))
    lo_wert, hi_wert = lo_wert - luft, hi_wert + luft
    links, rechts = RAND, BREITE - RAND

    def x(wert):
        return links + (rechts - links) * (wert - lo_wert) / float(hi_wert - lo_wert)

    # Band zwischen erstem und letztem Tief: das "window" aus der Wendung
    draw.rectangle([x(min(marken)), y - 36, x(max(marken)), y + 36],
                   fill=(14, 34, 32))
    draw.line([links, y, rechts, y], fill=LINE, width=3)

    for wert in sorted(marken):
        px = x(wert)
        draw.line([px, y - 28, px, y + 28], fill=DIM, width=3)
        beschriftung(draw, px, y - 48, str(wert), fonts["marke"], DIM, unten=True)

    px = x(heute)
    draw.line([px, y - 58, px, y + 58], fill=TEAL, width=4)
    draw.ellipse([px - 13, y - 13, px + 13, y + 13], fill=TEAL)
    beschriftung(draw, px, y + 66, "day %d" % heute, fonts["heute"], TEAL, unten=False)

    # Die Bildunterschrift steht rechts, damit sie nie unter der Teal-Marke
    # steht; die wandert mit dem Tag ueber die ganze Breite.
    text = "days from top to low, three completed cycles"
    b = draw.textlength(text, font=fonts["zyklus"])
    draw.text((BREITE - RAND - b, y + 128), text, font=fonts["zyklus"], fill=DIMMER)
    return y + 128 + fonts["zyklus"].size


def beschriftung(draw, px, y, text, font, fill, unten):
    """Mittig unter/ueber px, aber nie ueber den Rand hinaus."""
    b = draw.textlength(text, font=font)
    x = min(max(px - b / 2.0, RAND), BREITE - RAND - b)
    hoehe = font.size + 6
    draw.text((x, y - hoehe if unten else y), text, font=font, fill=fill)


def glanz(bild):
    """Der Teal-Schimmer oben, wie background-image auf der Seite
    (radial-gradient ellipse at 50% -10%). Die Maske wird klein gerechnet und
    hochskaliert; das gibt den weichen Verlauf ohne Filterbibliothek. Sie
    faellt an allen Raendern auf null, sonst steht eine sichtbare Kante im
    Bild."""
    from PIL import Image
    kx, ky = 96, 48
    roh = Image.new("L", (kx, ky))
    px = roh.load()
    for y in range(ky):
        for x in range(kx):
            # Ellipse mit Mittelpunkt oben mittig, wie 50% -10% auf der Seite
            dx = (x - (kx - 1) / 2.0) / ((kx - 1) / 2.0)
            dy = (y + ky * 0.10) / float(ky)
            r = (dx * dx + dy * dy) ** 0.5
            px[x, y] = int(max(0.0, 1.0 - r) ** 1.6 * 255 * 0.34)
    maske = roh.resize((BREITE, 560), Image.BICUBIC)
    bild.paste(Image.new("RGB", maske.size, TEAL), (0, 0), maske)
    return bild


def bauen(tag, wendung, marken, quelle="daily closes, never intraday highs"):
    """Das fertige Bild. Erwartet den Tag als Zahl und die Wendung als
    fertigen Satz; beides kommt aus day_n_post.py, damit Bild und Post nie
    auseinanderlaufen."""
    from PIL import Image, ImageDraw
    if not isinstance(tag, int) or tag <= 0:
        sys.exit("tag muss eine positive ganze zahl sein, ist %r" % (tag,))
    if not (wendung or "").strip():
        sys.exit("ohne wendung kein bild: der zitierbare satz ist der grund "
                 "fuer das bild")
    if not marken:
        sys.exit("ohne referenztage kein bild")

    bild = Image.new("RGB", (BREITE, HOEHE), BG)
    glanz(bild)
    d = ImageDraw.Draw(bild)
    fonts = {
        "marke": laden("fett", 30),
        "heute": laden("fett", 34),
        "zyklus": laden("normal", 24),
    }

    # 1. Wortmarke, Eyebrow
    f_marke = laden("fett", 30)
    b = gesperrt(d, (RAND, RAND), "PULSE", f_marke, TXT, 7)
    gesperrt(d, (RAND + b + 7, RAND), "HAWK", f_marke, TEAL, 7)
    gesperrt(d, (RAND, RAND + 58), "BITCOIN CYCLE, DAYS FROM THE TOP",
             laden("normal", 21), DIMMER, 5)

    # 2. die Zahl aus Zeile 1, gross und nackt. Sie schrumpft, wenn sie
    #    sonst ueber den Rand liefe (vierstellig ab Tag 1000).
    d.text((RAND, 228), "day", font=laden("normal", 54), fill=DIM)
    zahl = "{:,}".format(tag)
    groesse = 300
    while groesse > 120:
        f_zahl = laden("fett", groesse)
        if d.textlength(zahl, font=f_zahl) <= BREITE - 2 * RAND:
            break
        groesse -= 10
    d.text((RAND - groesse // 21, 300 - groesse // 5), zahl, font=f_zahl, fill=TXT)

    # 3. die Achse
    unten = achse(d, 700, marken, tag, fonts)

    # 4. die Wendung, der Satz, der mitgeteilt wird, wenn nur das Bild
    #    weitergeht. Mittig im Feld zwischen Achse und Fusslinie, damit ein
    #    Einzeiler (Fall B) kein Loch hinterlaesst.
    f_wendung = laden("fett", 46)
    zeilen = umbrechen(d, wendung, f_wendung, BREITE - 2 * RAND)
    feld_oben, feld_unten = unten + 40, HOEHE - 132 - 30
    y = feld_oben + max(0, (feld_unten - feld_oben - len(zeilen) * 62) // 2)
    for zeile in zeilen:
        d.text((RAND, y), zeile, font=f_wendung, fill=TXT)
        y += 62

    # 5. Quelle, Fusslinie
    d.line([RAND, HOEHE - 132, BREITE - RAND, HOEHE - 132], fill=LINE, width=2)
    f_fuss = laden("normal", 26)
    d.text((RAND, HOEHE - 108), quelle, font=f_fuss, fill=DIMMER)
    b = d.textlength("pulsehawk.io", font=f_fuss)
    d.text((BREITE - RAND - b, HOEHE - 108), "pulsehawk.io", font=f_fuss, fill=DIM)
    return bild


def schreiben(bild, pfad):
    ordner = os.path.dirname(os.path.abspath(pfad))
    if ordner:
        os.makedirs(ordner, exist_ok=True)
    bild.save(pfad, "PNG", optimize=True)
    groesse = os.path.getsize(pfad)
    if groesse > 5 * 1024 * 1024:
        sys.exit("bild ist %d kB gross, X nimmt hoechstens 5 MB" % (groesse // 1024))
    return groesse


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--day", type=int, help="die Tageszahl aus Zeile 1")
    ap.add_argument("--wendung", help="Zeile 3 des Posts, woertlich")
    ap.add_argument("--marken", default="406,364,378",
                    help="die Referenztage, Komma getrennt")
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build", "day-n.png"))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selbsttest()
    if a.day is None or not a.wendung:
        ap.error("--day und --wendung werden gebraucht")
    marken = [int(x) for x in a.marken.split(",") if x.strip()]
    groesse = schreiben(bauen(a.day, a.wendung, marken), a.out)
    print("bild geschrieben: %s, %d kB, %dx%d" % (a.out, groesse // 1024, BREITE, HOEHE))
    return 0


def selbsttest():
    schlecht = 0

    def pruefe(name, ist, soll):
        nonlocal schlecht
        if ist != soll:
            schlecht += 1
            print("  FEHL %s\n    ist  %r\n    soll %r" % (name, ist, soll))
        else:
            print("  ok   %s" % name)

    pruefe("format ist 4:5", round(BREITE / float(HOEHE), 3), 0.8)
    pruefe("schrift fett gefunden", schriftdatei("fett") is not None, True)
    pruefe("schrift normal gefunden", schriftdatei("normal") is not None, True)

    from PIL import Image, ImageDraw
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    f = laden("normal", 40)
    lang = "the earliest low of the last three cycles came on day 364. that is 20 days from here."
    zeilen = umbrechen(d, lang, f, BREITE - 2 * RAND)
    pruefe("langer satz wird umbrochen", len(zeilen) > 1, True)
    pruefe("umbruch verliert kein wort", " ".join(zeilen), lang)
    pruefe("kurzer satz bleibt eine zeile",
           len(umbrechen(d, "we are inside that window now.", f, BREITE - 2 * RAND)), 1)

    # drei Faelle, drei Bilder, jedes muss entstehen und 4:5 sein
    for tag, satz in ((344, "that is 20 days from here."),
                      (364, "we are inside that window now."),
                      (420, "all three previous cycles had already found their low by now.")):
        b = bauen(tag, satz, [406, 364, 378])
        pruefe("bild fuer tag %d hat 4:5" % tag, b.size, (BREITE, HOEHE))
        # nicht nur Hintergrund: es muss Teal im Bild sein (Marke, Achse)
        farben = {f[1] for f in b.getcolors(200000) or []}
        pruefe("tag %d traegt teal" % tag, TEAL in farben, True)

    for kaputt, warum in (((344, "", [406]), "ohne wendung"),
                          ((0, "satz", [406]), "tag null"),
                          ((344, "satz", []), "ohne marken")):
        try:
            bauen(*kaputt)
        except SystemExit:
            pruefe("bricht ab: %s" % warum, True, True)
        else:
            pruefe("bricht ab: %s" % warum, False, True)

    print("%d von 15 faellen falsch" % schlecht)
    return 1 if schlecht else 0


if __name__ == "__main__":
    sys.exit(main())
