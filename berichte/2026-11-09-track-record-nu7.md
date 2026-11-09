# Track Record: alle vier NU7-Prognosen, "forecast" statt "estimate" (9.11.2026)

**Kopf:** Seite, Code und Daten in `a29a000` auf `site/track-record-nu7`, auf main nach `f6edd8e`.

Auftrag von Ben vom 9.11., Frist 10:30 Berlin, vor dem NU7-Post um 11:00. Die NU7-Karte verweist mit "every result at pulsehawk.io/track-record" auf die Seite.

## Was gemacht wurde

1. **Zwei neue Einträge**
   - **Werte:** aus `berichte/2026-11-08-nu7-karte-tabelle.md` (kaspa-pulse). Ich habe sie gegen die Datendateien nachgeprüft: Median, Band und Kopfzeit stimmen.
   - **Kopfzeit von Block 3,543,405:** 6.11.2026, 02:34:02 UTC, counted.

   | Eintrag | Prognose von | Forecast | 90-%-Band (UTC) | Ergebnis | Status |
   |---|---|---|---|---|---|
   | TR-005 | 23.10.2026 | 6.11. 02:21:52 UTC | 5.11. 22:02:16 bis 6.11. 06:40:25 | the block came 12 min 10 s later | in band |
   | TR-006 | 4.11.2026 | 6.11. 02:40:58 UTC | 6.11. 01:14:45 bis 04:07:28 | the block came 6 min 56 s earlier | in band |
2. **Alle vier NU7-Prognosen in gleicher Form**
   - **Sortierung:** nach Prognosedatum: 23.10., 28.10., 2.11., 4.11.
   - **Zeiten:** Prognose und Band jetzt mit Sekunden, auch bei TR-003 und TR-004.
   - **Zeile "Deviation":** immer aus Sicht des Blocks, in min und s: "The block came 12 min 10 s later" (TR-005), "7 min 46 s later" (TR-003), "5 min 50 s earlier" (TR-004), "6 min 56 s earlier" (TR-006).
   - **Bilanz:** 6 Einträge, 5 in band, 1 outside, 0 open.
   - **/zcash-nu7:** Der Abschnitt "How close were our forecasts?" nennt alle vier in derselben Richtung: "block 3,543,405 came 12 min 10 s later than our forecast as of 23 October 2026, …". "All four forecasts lay inside their 90% band."
3. **"forecast" statt "estimate"** im ganzen sichtbaren Text:
   - /track-record: Title, Description, Lead, Überschriften, Zeile "Our forecast";
   - /zcash-nu7;
   - Startseite;
   - /independence, /corrections, /about;
   - /reports/zcash-nu7 und die Spezifikation /standard/upgrade-report/ und v1-0. Dort betrifft das nur das Wort, nicht die Rechenvorschrift; die Version bleibt 1.0.
   - /upgrades: "Around marks an estimated date" heißt jetzt "an approximate date". Das ist dort kein Forecast, sondern ein Datum aus einer angekündigten Höhe.
   - llms.txt.
4. **b2b_check**
   - "estimate" im sichtbaren Text ist jetzt rot.
   - Die Regel für Upgrade-Zeiten verlangt "forecast" statt "estimate".
   - Selbsttest 22 von 22.
5. **Abschnitte:** Jeder Eintrag im Track Record hat jetzt eine eigene Überschrift (h2, im Stil wie bisher). Sonst wäre "Our forecasts" mit vier Einträgen über 250 Wörter gekommen.

## Quellen der neuen Einträge, bitte prüfen

- **TR-006 (4.11.):** verlinkt `github.com/pulsehawk/methods/blob/04f3f6c/upgrade_report/configs/zcash-mainnet-nu7.json`, Commit vom 4.11.2026 14:06 UTC, mit Forecast und Band.
- **TR-005 (23.10.):**
  - **Quelle:** Diese Prognose stand nie auf pulsehawk.io. Öffentlich war sie nur in der Datendatei `stand-2026-10-23.json` im Messrepo (Commit `9b20504`, 23.10.2026 12:55:33 UTC). Das Messrepo darf pulsehawk.io nicht nennen.
  - **Auszug:** Ich habe deshalb einen Auszug als `data/track-record/zcash-nu7-forecast-2026-10-23.json` auf pulsehawk.io gelegt und verlinkt. Er enthält Forecast, Band, Tempo, Methode, Commit, Commit-Zeit und die sha256 der vollständigen Originaldatei (`c5c53cb9…481a`).
  - **Weggelassen:** die Peer-Software-Liste und die Zakura-Schätzung (deine Regel: kein Zakura-Detail auf der Seite).
  - **Warum ein Auszug:** Eine byte-gleiche Kopie wäre besser prüfbar, hätte aber das Zakura-Feld veröffentlicht.

## Prüfungen

- `b2b_pages.py`: 0 von 24 Seiten mit Funden, kein "estimate" mehr sichtbar.
- `b2b_check.py --selbsttest`: 22 von 22.
- `report_waechter.py --selbsttest`: 55 von 55.
- pyflakes und `secret_scan.py --staged` ohne Fund.
- **Lokal bei 390 und 1440 px:** vier Forecast-Einträge in der Reihenfolge TR-005, TR-003, TR-004, TR-006, kein "estimate", kein waagerechtes Scrollen, der Auszug ist abrufbar.

## Offene Fragen an Ben

- Ist der Auszug als Quelle für TR-005 in Ordnung, oder soll die Prognose vom 23.10. anders belegt werden?
- Die Prognose vom 2.11. (TR-004) nutzte 7 Tage, die anderen drei 14 (aus der Rechentabelle). Soll das im Eintrag stehen?

## Was Ben tun muss

Nichts. Die Abnahme auf pulsehawk.io folgt nach dem Merge als Zeile in diesem Bericht.
