# Startseite, Frischhaltung und Navigation (Auftrag Ben 11.11.2026, Frist Fr 13.11. 18:00)

**Kopf:** Seiten, Code und Daten in `4b2f63e` auf `site/startseite-frisch`, auf main nach `7841d1a`. Selbst-Merge nach der Regel vom 26.10. (keine Workflows, kein deploy, kein c2, kein Secrets-Bezug).

**Grundlage:** Den Auftrag habe ich direkt umgesetzt. `claude/ph-website-pruefung-2026-11-11.md` liegt weder in pulsehawk-site noch in kaspa-pulse, wahrscheinlich in deinem lokalen Ordner. Ich konnte sie nicht lesen.

**Überschneidung:** Upgrade-Seiten v2 sind seit #79 und #81 gemergt. Dieser Auftrag baut darauf auf.

## Leitregel

**Zeitlos oder automatisch aktuell.** In `index.html` steht keine getippte Zahl mehr. Entfernt habe ich die bisherigen festen Zahlen im Code:
- `zcash_fragment` (23.68 s, 17.0 s, 52 s, 109 s, 451 s);
- `bch_fragment` und `bch_kachel` (43 s, 41.6 s, 7,572);
- `csv_fragment` (49,203 Zeilen).

Die datierte Schicht kommt jetzt ganz aus vier Dateien:

| Datei | Inhalt |
|---|---|
| `data/reports.json` (neu) | Reports, der neueste ist der Aufmacher-Beleg |
| `data/measurements.json` (neu) | Messungen mit Wert, Fenster und Datum |
| `data/track-record.json` | gewertete Prognosen |
| `data/citations.json` | Zitate |

Der Code dafür steht im neuen Modul `scripts/datiert.py`.

## Umsetzung

1. **Zwei Schichten**
   - **Zeitlos oben, ohne alternde Zahl:**
     - H1 und Lead: wer wir sind, eigene Knoten und eigene Header-Clients, nie aus Dashboards Dritter.
     - Abschnitt "What does independent mean?":
       - der Satz "A grant pays for the measurement, never for the result";
       - Methode vor Bezahlung, kein Ergebnis für einen Zahler geändert, jeder Report nennt den Zahler;
       - wie man eine Messung in Auftrag gibt.
   - **Darunter die datierte Schicht**, abgesetzt durch eine Linie:
     - neuester Report;
     - Prognosen;
     - Messungen und das Zcash-Testnet-Diagramm, das bisher im Hero stand;
     - Zitate.
   - **Am Ende wieder zeitlos:** die Leistungsliste und "How do we start?".
2. **Neuester Report automatisch**
   - **`data/reports.json`:** Je Eintrag Kennung, Netz, Titel, Fenster, Veröffentlichung, Methodenversion, Pfad, CSV und deren sha256.
   - **Startseite:** zeigt den Eintrag mit dem jüngsten `published` als "Latest report", mit Titel, Fenster, Datum und Kopfzahl. Die Kopfzahl kommt aus `data/reports/zcash-nu7.json` (`werte`), also aus der Datei, die der Report selbst schreibt.
   - **Übersicht `/reports/` (neu):** aus derselben Datei, dazu die Messungen aus `data/measurements.json`.
   - **"See a sample report":** auf allen Seiten jetzt der neueste Report (/reports/zcash-nu7), nicht mehr die Fallseite. Auf der Startseite heißt der Knopf "See the latest report".
3. **Sichtbares Stand-Datum**
   - **Form:** Jede Zahl der datierten Schicht trägt sichtbar "counted over <Fenster>, published <Datum>". Bei Quellwerten heißt es "source, checked <Datum>, published <Datum>".
   - **b2b_check:** prüft auf `index.html` und `reports/index.html`, dass jede große Zahl (`dwert`) eine solche Zeile hat. Fehlt sie, ist die Seite rot, und der Bau endet mit Exit-Code 1. Selbsttest mit einem Fehlfall.
4. **Der Bau bricht ab**
   - **Bedingungen:** `scripts/datiert.py` läuft am Anfang jedes Baus. Er bricht mit Exit-Code 1 ab, und es wird keine Seite geschrieben, wenn
     - der neueste Report älter als `FRISCH_TAGE = 21` Tage ist,
     - einem Wert label, Fenster oder Veröffentlichungsdatum fehlt,
     - oder die sha256 eines Reports nicht zu seiner CSV passt.
   - **Schwelle:** steht als einzelner Wert oben in `datiert.py`.
   - **Selbsttest** `python3 scripts/datiert.py --selbsttest`, 8 Fälle:
     - am Tag der Veröffentlichung, an der Grenze, einen Tag drüber;
     - Wert ohne Datum, Wert ohne Fenster;
     - falsche sha256;
     - interval score im und außerhalb des Bands.
5. **Prognosen direkt unter dem neuesten Report**
   - **Block "Forecasts, scored in public":** Wir veröffentlichen Aktivierungszeiten vorab, datiert und mit Band, und werten jede danach öffentlich, Fehlschläge eingeschlossen.
   - **Zahlen, gerechnet aus `data/track-record.json`:** "4 of 4", die Bandstufe (90%) und der mittlere interval score, 5 h 43 min 14 s, computed. Dazu ein Link auf /track-record.
   - **Interval score:** nach Gneiting und Raftery (2007). Er ist die Breite des Bands plus 2/α mal den Abstand, wenn der Block außerhalb landet. Bei 90% ist das 20-mal der Fehlbetrag.
   - **Neue Felder in track-record.json:** `value_utc`, `band_utc` und `band_level` je Prognose, `value_utc` im Ergebnis, `updated` als Stand-Datum der Liste.
   - **/track-record:** zeigt den Score je Prognose und erklärt ihn bei "How is an entry scored?".
6. **Navigation**
   - **Neue Reihenfolge:** Upgrade readiness, Reports, Track record, Calendar, Method, Independence, Contact.
   - **Track record** steht jetzt in der Hauptnavigation, nicht nur in der Fußleiste.
   - **Aus der Leiste genommen:**
     - TPS verification und Launch measurement: Sie stehen jetzt unter Upgrade readiness ("Beyond upgrades we also offer TPS verification and launch measurement") und weiter in der Leistungsliste der Startseite.
     - Zcash NU7: Die Seite steht unter /reports/ und auf der Startseite.
7. **Verwaiste Blöcke**
   - **Wo:** als eigener Baustein auf /upgrade-monitoring, in der Schema-Beschreibung des Dienstes und in der Leistungszeile der Startseite.
   - **Ehrlicher Zusatz:** "A count from one observation point is a lower bound, because a block that never reaches our listener cannot be counted."
8. **Inhalte, nur über die Dateien**
   - **Neuester Report:** Zcash NU7 Mainnet ist als PH-UR-2026-001 eingetragen (veröffentlicht 9.11., Fenster 5.11. 02:34 bis 9.11. 02:33 UTC).
   - **BCH:** jetzt auf dem Stand 11.11.2026 10:00 UTC. Median 41.0 s counted, n 37,764, Fenster 15.10. 12:56 bis 11.11. 09:58 UTC, gegen 41.6 s computed.
     - Quelle: `tempnet-2026-11-11.json` auf dem Messbranch.
     - Der Tempnet-Abschlussbericht ist laut Bericht der BCH-Sitzung bis Fr 13.11. offen. Ändert sich der Endstand, ändert sich nur `data/measurements.json`.
   - **Testnet-Zahlen:** Zcash NU7 Testnet (23.68 s, Fenster 4. bis 18.10., veröffentlicht 18.10.) bleibt datiert auf der Startseite und unter /reports/, die Fallseite /zcash-nu7 bleibt.
   - **TR-001:** Der Eintrag zeigte auf /#bch-median, wo jetzt der neue Stand steht. Er verlinkt deshalb die Startseite vom 22.10. (Commit `24757e3`, mit "43 s against 41.6 s").
9. **"pages built 11 November 2026"** ist die letzte Zeile der Startseite, aus dem Datum des Baus.

## Beweise

**1. Leitregel**
- **Vorgehen:** Ich habe nur `data/reports.json` geändert, mit dem Testeintrag PH-UR-2026-099 vom 11.11.2026, und dann gebaut.
- **Ergebnis:**
  - Die Startseite zeigt "Latest report, PH-UR-2026-099, TEST entry, not published" mit Fenster und Datum.
  - `git diff -- scripts/` ist leer, `index.html` hat nur der Bau geschrieben.
- **Nachweis:** Ausgabe in `beweis-1-reports-json.txt`, Bild `beweis-1-startseite-testeintrag-1440.jpg`. Danach habe ich zurückgesetzt und neu gebaut.

**2. Abbruch**
- **Fall 1:** `published` des einzigen Reports künstlich auf 2026-10-17 gesetzt.
  - Ausgabe: "neuester report PH-UR-2026-001 ist 25 tage alt (veroeffentlicht 2026-10-17), die grenze ist 21 tage", Exit-Code 1.
  - Die sha256 von `index.html` ist vorher und nachher gleich. Es wurde nichts geschrieben.
- **Fall 2:** einem Wert in `data/measurements.json` das Datum genommen. Ergebnis "messung bch-median ohne veroeffentlichungsdatum", Exit-Code 1.
- Danach zurückgesetzt, Exit-Code 0.
- **Nachweis:** `beweis-2-bau-bricht-ab.txt`.

## Prüfungen

- `b2b_pages.py`: 0 von 25 Seiten mit Funden.
- **Selbsttests:** `b2b_check.py --selbsttest` 26 von 26, `datiert.py --selbsttest` 8 von 8, `report_waechter.py --selbsttest` 55 von 55.
- pyflakes und Secret-Scan ohne Fund.
- **Textregeln:** keine Preise, keine Echtzeitwörter, jede Zahl mit Fenster und label.
- **Screenshots lokal** bei 390 und 1440 px, hell und dunkel, von Startseite, /reports/, /track-record und /upgrade-monitoring (16 Bilder in `berichte/2026-11-11-startseite-frisch/`). Kein waagerechtes Scrollen.
  - **Hinweis zu hell und dunkel:** pulsehawk.io hat nur ein dunkles Design und wertet `prefers-color-scheme` nicht aus. Die Aufnahmen hell und dunkel sind deshalb gleich.

## Offene Fragen an Ben

1. **Abbruch greift nur beim Bauen:** Kein Workflow baut die Seiten. Der Abbruch greift also erst, wenn jemand baut. Ab dem 1.12.2026 bricht jeder Bau ab, wenn bis dahin kein neuer Report eingetragen ist. Soll ein täglicher Workflow `python3 scripts/datiert.py` laufen lassen und bei Rot in #ops-log melden? Das wäre eine Workflow-Änderung, also nur mit deinem Merge.
2. **Helles Design:** Soll pulsehawk.io ein helles Design bekommen, oder bleibt es bei dunkel?
3. **Grundlage:** Bitte `claude/ph-website-pruefung-2026-11-11.md` ins Repo legen oder schicken, falls dort Punkte stehen, die über den Auftrag hinausgehen.

## Was Ben tun muss

Nichts. Die Abnahme auf pulsehawk.io folgt nach dem Merge als Zeile in diesem Bericht.

## Selbst-Merge und Abnahme (11.11.2026)

- **Merge:** PR #83 per Squash, Merge-Commit `72394f0`, Branch gelöscht.
- **Byte-gleich mit dem Bau aus `72394f0` auf pulsehawk.io:**
  - Startseite, /reports/, /track-record, /upgrade-monitoring, /upgrades;
  - /method, /zcash-nu7, /tps-verification;
  - /llms.txt, /sitemap.xml.
- **Weiterleitung:** /reports ohne Schrägstrich leitet mit 301 auf /reports/.
- **Im Browser bei 390 und 1440 px, hell und dunkel:**
  - Startseite in zwei Schichten, "Latest report, PH-UR-2026-001", "4 of 4", Mittel 5 h 43 min 14 s;
  - Messungen mit sichtbarem "counted over …, published …";
  - als letzte Zeile "pages built 11 November 2026";
  - neue Navigation;
  - kein waagerechtes Scrollen.
- **Screenshots:** 16 Live-Aufnahmen (`*-live.jpg`) in `berichte/2026-11-11-startseite-frisch/`.
