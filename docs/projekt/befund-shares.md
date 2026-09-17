# Warum wird geteilt, und warum bei uns nicht

Belege fuer den Umbau des DAY-N-Posts (Bauform, Wendung, Sendezeit).
Stand 17.09.2026. Alles hier ist gemessen oder berichtet, nichts geraten.
Wo etwas berichtet und nicht selbst gemessen ist, steht es dabei.

## A) Die Studie

Berger & Milkman, "What Makes Online Content Viral?", Journal of Marketing
Research 2012. Feldstudie ueber rund 7.000 Artikel der New York Times;
gemessen wurde der Sprung auf die Liste "most emailed".

Effekt je eine Standardabweichung mehr des Merkmals:

| Merkmal | Effekt |
| --- | ---: |
| Wut | +34 % |
| Staunen (awe) | +30 % |
| Angst/Unruhe | +21 % |
| Positivitaet | +20 % |
| Interesse | +18 % |
| Ueberraschung | +14 % |
| praktischer Nutzen | +13 % |
| Traurigkeit | **-16 %** |

Kernaussage der Autoren: nicht positiv gegen negativ entscheidet, sondern
AKTIVIERUNG. Wut, Staunen und Unruhe aktivieren, Traurigkeit deaktiviert.

Fuer uns heisst das zweierlei.

1. Praktischer Nutzen ist der schwaechste Hebel der Liste, und er ist unser
   ganzes Geschaeftsmodell. "Hier ist die Zahl" reicht deshalb nicht.
2. Wut ist der staerkste Hebel und uns per Doktrin verboten (kein
   Namensnennen, kein Angriff). Bleiben Staunen und Ueberraschung, und die
   haben wir im Ueberfluss.

Daraus folgt Zeile 3 des Posts, die Wendung: ein Satz, der aus den Daten
kommt, etwas einordnet und trotzdem nichts ueber die Zukunft behauptet.

## B) Die eigene Beobachtung

Auf @gokugalax haben im Fenster 08.-14.09.2026 genau drei Posts einen
Repost bekommen. Alle drei hatten die Wendung in Zeile 1 oder 2 und waren
in EINEM Satz zitierbar.

**10.09.**

> 14.1 billion kas has not moved in a year.
> that is more than half of everything that exists.

Staunen: Groessenordnung plus Massstab.

**09.09.**

> one wallet on the kaspa chain is down about $85 million on paper.
> last week it bought 4.77 million more.

Wendung: Verlust, dann Kehrtwende. Genau so wird aus Traurigkeit (-16 %)
Staunen (+30 %).

**08.09.**

> kaspa halves every single year.
> it just does it in twelve small steps instead of one big one.

Ueberraschung: alle wissen es falsch.

Gegenbeweis, null Reposts, gleiche Woche:

**07.09.**

> this morning we published the one number that would change our read:
> a weekly close above $0.03082.

Eine Ankuendigung. Kein Staunen, keine Wendung, nichts zum Zitieren.

## C) Mechanik von X

Sprout Social, Auswertung des offengelegten Rankings 2026. Als **berichtet**
behandeln, nicht als Naturgesetz.

| Signal | Gewicht |
| --- | --- |
| Repost | rund 20x ein Like |
| Antwort | rund 13,5x |
| Lesezeichen | rund 10x |
| Externer Link im Post | 50-90 % weniger Reichweite |
| Halbwertszeit eines Posts | rund 6 Stunden |
| Premium (bezahlte Verifizierung) | 2-4x Reichweite |

Daraus folgen zwei harte Regeln:

- Kein Link im Hauptpost. Der Link geht als Selbstantwort darunter, als
  eigener Beitrag.
- Bei sechs Stunden Halbwertszeit ist ein Post am spaeten Abend am naechsten
  Morgen tot, und die bezahlte Verifizierung verpufft mit. Der alte Termin in
  dayn.yml war 21:52 UTC, also 23:52 Berlin.

## D) Die Ausgangslage

Vier Messungen in Folge (18.08., 24.08., 07.09., 14.09.) mit null
Lesezeichen und null Shares. Der DAY-N-Post vom 17.09. hatte 3 Aufrufe,
der vom 13.09. fuenf.

## E) Ziel

Bis zur Messung am Montag, 05.10.2026, traegt mindestens ein eigener Post
je Woche >= 3 Reposts ODER >= 3 Lesezeichen.

Wird das verfehlt, liegt es am Thema, nicht an der Verpackung.

## Was daraus im Code steht

| Befund | Umsetzung |
| --- | --- |
| Aktivierung schlaegt Nuetzlichkeit | `WENDUNGEN` in `scripts/day_n_post.py`, Zeile 3 jedes Posts |
| Wendung in Zeile 1 oder 2, in einem Satz zitierbar | vier Bloecke, Zahl nackt zuerst, Wendung als dritter Block |
| Traurigkeit -16 % | Traurigkeitsregel: Verlustwort ohne Wendung bricht den Lauf ab |
| Externer Link kostet 50-90 % | kein Link im Hauptpost, Link als Selbstantwort |
| Halbwertszeit 6 Stunden | Cron 12:30 UTC statt 01:53 UTC |
| Zitierbar bleibt nur, was mitgeschickt wird | Wendung steht auch im Bild |
