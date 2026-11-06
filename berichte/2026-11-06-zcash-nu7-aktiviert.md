# Zcash NU7 aktiviert: /zcash-nu7 und Track record nachgezogen (6.11.2026)

Ausgelöst von der geplanten Aufgabe "Zcash NU7 aktiviert: Seite nachziehen" um 06:11 UTC.

## Quelle

- kaspa-pulse, Branch `messung/zcash-mainnet`, Datei `data/zcash-mainnet/stand-2026-11-06.json` (Abruf 05:13:54 UTC), der erste Stand mit `nach_nu7`.
- Übernommen mit `python3 scripts/zcash_stand.py` nach `data/zcash-nu7/mainnet-stand.json`.
- **Gegenprobe:** Ich habe die Zahlen aus der beiliegenden `zcash-mainnet-nu7-intervals-2026-11-06.csv` (Blöcke 3,543,405 bis 3,543,655) nachgerechnet.
  - n 250, Mittel 38.21 s, Median 25.0 s, p90 85.1 s, p99 162.6 s, längste Lücke 249 s. Das stimmt mit dem Stand überein.
  - Jede Kopfzeit minus die vorige ergibt genau `interval_s`.
- **Prüfungen des Kopf-Clients** laut Stand: prev-hash-Kette, Hash unter dem Ziel aus nBits, Zebra-Checkpoints. Gegenprobe mit zwei Peers, je 500 von 500 Hashes gleich.

## Was auf /zcash-nu7 steht (jede Zahl mit Datum und counted/computed)

- **Lead und Description:** NU7 ist aktiviert, Block 3,543,405 (ZIP 259), Kopfzeit 6 November 2026, 02:34 UTC, counted. Die Description hat 155 Zeichen.
- **"In short":** Die Zeile "NU7 activated on mainnet" zeigt counted, Block 3,543,405 am 6.11. um 02:34 UTC. Die Zeile zum Median nach NU7 zeigt 25.0 s, counted über 250 Intervalle bis 6.11. 05:13 UTC, dazu 17.3 s computed für eine ideale 25-s-Kette. Die Prognose-Zeile entfällt.
- **"First counted numbers after activation":**
  - Kopfzeit von Block 3,543,405, counted.
  - 250 Intervalle bis 05:13 UTC, Mittel 38.21 s und Median 25.0 s counted, gegen 17.3 s computed.
  - Noch nicht auf 25 s eingependelt in den ersten 250 Blöcken, counted.
  - Schwierigkeit 100 Blöcke nach der Aktivierung bei 0.504 des alten Niveaus, counted. Für ein 25-s-Ziel bei gleicher Hashrate wären 0.333 nötig, computed. Das erklärt, warum das Mittel noch über 25 s liegt.
  - **Abgleich mit unseren Schätzungen:** Die vom 28.10. war 7 min 46 s zu früh, die vom 2.11. 5 min 50 s zu spät. Beide lagen in ihrem 90-%-Band, mit Link auf den Track record.
  - **Tabelle:** gezählt, 95-%-Intervall und computed bei 25 s.
    - Mittel 33.58 bis 42.84 s
    - Median 22 bis 31 s
    - p90 73 bis 104 s
    - p99 138 bis 249 s

    Gerechnet mit `scripts/unsicherheit.py` aus der CSV, eingetragen als `nach_nu7` in `data/zcash-nu7/mainnet-unsicherheit.json`. Darunter stehen die Unsicherheitszeile und PH-M-001.
  - **Kürzung:** Die Unsicherheitszeile der Mainnet-Tabellen habe ich um ein paar Wörter gekürzt, weil der Abschnitt sonst über 250 Wörter käme.
- **Datum:** lastmod und dateModified von /zcash-nu7 sind der 6.11.2026.

## Track record

- **TR-003** (Schätzung vom 28.10., 02:26:16 UTC, Band 23:01:22 bis 05:51:31 UTC): Ergebnis 02:34:02 UTC counted, Abweichung +7 min 46 s, **in band**.
- **TR-004** (Schätzung vom 2.11., 02:39:52 UTC, Band 00:28:23 bis 05:00:17 UTC): Ergebnis 02:34:02 UTC counted, Abweichung −5 min 50 s, **in band**.
- **Stand:** 4 Einträge, 3 in band, 1 outside, 0 open. lastmod von /track-record ist der 6.11.2026.
- **Darstellung:** Bei einem Einzelwert (n = 1) zeigt der Eintrag jetzt Wert, Fenster und Auflösung statt "95% interval … 1 values".

## Prüfungen

- `b2b_pages.py`: 0 von 24 Seiten mit Funden, auch mit den Regeln für Spec-Nummer, Upgrade-Zeit, Beträge, now und live.
- `b2b_check.py --selbsttest`: 20 von 20.
- `report_waechter.py --selbsttest`: 55 von 55.
- pyflakes und `secret_scan.py --staged` ohne Fund.
- **Screenshots** 390 und 1440 px, lokal (in `berichte/2026-11-06-zcash-nu7-aktiviert/`): "In short", der Abschnitt nach der Aktivierung und die Schätzungen im Track record. Kein waagerechtes Scrollen.

## PR

#66. Keine Workflows, kein deploy, kein c2, kein Secrets-Bezug, daher Selbst-Merge nach der Regel vom 26.10.

## Offene Fragen an Ben

- Die Kurznotiz zählt erst 250 Blöcke, die Schwierigkeit fällt noch. Soll ich /zcash-nu7 mit dem nächsten täglichen Stand (7.11., 05:23 UTC) noch einmal nachziehen, bis das Einpendeln gezählt ist?
- Der Upgrade Report PH-UR-2026-001 (/reports/zcash-nu7) bleibt bis zum 9.11. ein Gerüst. Die Mainnet-Daten kommen von der Sitzung "Zcash NU7 Testnet Messung".

## Was Ben tun muss

Nichts. Die Abnahme auf pulsehawk.io folgt nach dem Merge als Zeile in diesem Bericht.

## Selbst-Merge und Abnahme (6.11.2026)

- **Merge:** PR #66 per Squash, Merge-Commit `3541dd8`, Branch gelöscht.
- **Abnahme auf pulsehawk.io:** /zcash-nu7, /track-record, /llms.txt und /sitemap.xml sind live byte-gleich mit dem Bau aus `3541dd8`.
- **Im Browser bei 390 und 1440 px:** "In short", der Abschnitt nach der Aktivierung und die Schätzungen im Track record sind da, TR-003 und TR-004 jeweils "In band". Kein waagerechtes Scrollen.
- **Screenshots:** sechs Live-Ausschnitte (`*-live.jpg`) in `berichte/2026-11-06-zcash-nu7-aktiviert/`.
