# Zcash NU7: Einpendeln gezählt, /zcash-nu7 mit dem Stand vom 7.11. (7.11.2026)

**Kopf:** Seite, Code und Daten in `cf46212` auf `site/zcash-nu7-einpendeln`, auf main nach `7975814`.

Auftrag von Ben vom 7.11.: /zcash-nu7 täglich nachziehen, bis das Einpendeln gezählt ist, spätestens bis zum Report am 9.11. **Kriterium:** Das Mittel über die letzten 250 Blockabstände liegt mit seinem 95-%-Intervall um 25 s.

## Ergebnis

- **Eingependelt, counted:** Die letzten 250 Abstände bis Block 3,548,033 (Kopfzeit 7.11.2026, 11:48:25 UTC) haben ein Mittel von 24.82 s. Das 95-%-Intervall von 21.84 bis 27.80 s enthält 25 s.
- **Erstmals erfüllt:** für die 250 Abstände bis Block 3,543,859 (6.11.2026, 06:46:52 UTC), gut vier Stunden nach dem ersten NU7-Block.
- **Danach:** Von rund 4,130 späteren 250er-Fenstern lagen 97 kurz außerhalb. Das letzte Fenster liegt innerhalb.
- **Keine weiteren Läufe:** Das Kriterium ist erfüllt, deshalb plane ich keine weiteren täglichen Läufe ein.

## Quelle

- **Datei:** kaspa-pulse, Branch `messung/zcash-mainnet`, Lauf "koepfe und stand" vom 7.11.2026, 11:54 UTC.
- **Kein datierter Stand:** Dieser Lauf schreibt nach NU7 keine datierte Datei `stand-2026-11-07.json` mehr, sondern nur `aktuell.json` (Abruf 11:49:56 UTC). Die Uhrzeit 05:23 UTC aus dem Auftrag passt nicht zu den Läufen. Die letzten kamen um 13:24 (5.11.), 05:19 und 13:12 (6.11.) und 11:54 UTC (7.11.).
- **`scripts/zcash_stand.py`:** nimmt jetzt auch `aktuell.json` an. Das Datum ist der Tag des Abrufs, die Quelle nennt Datei und Abrufzeit.
- **Köpfe:** `koepfe.csv.gz` bis Block 3,548,033. Geprüft wurden laut Lauf prev-hash-Kette, Hash unter dem Ziel aus nBits und 89 Zebra-Checkpoints, Gegenprobe 2 × 500 von 500 Hashes.

## Was gemacht wurde

- **Neues Skript `scripts/zcash_einpendeln.py`:** rechnet aus den Köpfen bis zur Höhe des Stands:
  - die 95-%-Intervalle aller Abstände nach NU7;
  - Bens Kriterium für das letzte 250er-Fenster;
  - das erste Fenster, in dem es gilt.

  Es bricht ab, wenn Köpfe fehlen oder n bzw. Mittel nicht zum Stand passen. Das Ergebnis steht in `data/zcash-nu7/mainnet-unsicherheit.json` (`nach_nu7`, `einpendeln_250`).
- **/zcash-nu7:**
  - "In short": Median nach NU7 17.0 s, counted über 4,628 Abstände bis 7.11. 11:48 UTC; 17.3 s computed für die ideale 25-s-Kette.
  - "First counted numbers after activation":
    - Kopfzeit von Block 3,543,405, counted.
    - 4,628 Abstände, Mittel 25.86 s und Median 17.0 s counted, gegen 17.3 s computed.
    - Einpendeln mit Höhe, Datum, Mittel, 95-%-Intervall und dem ersten Treffer, counted.
    - **Tabelle mit 95-%-Intervallen:**

      | Kennzahl | gezählt | 95-%-Intervall | computed bei 25 s |
      |---|---|---|---|
      | Mittel | 25.86 s | 25.10 bis 26.61 s | 25 s |
      | Median | 17.0 s | 16 bis 18 s | 17.3 s |
      | p90 | 60.0 s | 58 bis 63 s | 57.6 s |
      | p99 | 122.7 s | 113 bis 132 s | 115.1 s |
      | längste Lücke | 249 s | Einzelwert | etwa 225 s |

  - **Neuer Abschnitt "How close were our estimates?"** mit PH-M-001 und PH-M-006. Der Abgleich der beiden Schätzungen musste aus dem Abschnitt nach der Aktivierung heraus, sonst wäre der über 250 Wörter gekommen.
  - lastmod und dateModified: 7.11.2026.

## Gegenprobe

- **Kennzahlen:** Mittel, Median, p90, p99, längste Lücke und n aus den Köpfen sind gleich den Werten im Stand (25.86 / 17.0 / 60.0 / 122.7 / 249 / 4,628).
- **Erster Block:** 3,543,405 hat die Kopfzeit 6.11.2026, 02:34:02 UTC.

## Prüfungen

- `b2b_pages.py`: 0 von 24 Seiten mit Funden.
- `b2b_check.py --selbsttest`: 20 von 20.
- pyflakes und `secret_scan.py --staged` ohne Fund.
- **Screenshots** 390 und 1440 px, lokal (`berichte/2026-11-07-zcash-nu7-einpendeln/`): "In short", der Abschnitt nach der Aktivierung und die Schätzungen. Kein waagerechtes Scrollen.

## PR

Siehe die Zeile zum Merge unten. Keine Workflows, kein deploy, kein c2, kein Secrets-Bezug, daher Selbst-Merge nach der Regel vom 26.10.

## Offene Fragen an Ben

- Der Lauf schreibt seit NU7 nur noch `aktuell.json`, keine datierte Stand-Datei mehr. Ist das so gewollt? Für die Nachvollziehbarkeit wäre eine datierte Datei je Tag besser. Das wäre ein Auftrag an die Zcash-Sitzung, nicht an diese.

## Was Ben tun muss

Nichts. Die Abnahme auf pulsehawk.io folgt nach dem Merge als Zeile in diesem Bericht.
