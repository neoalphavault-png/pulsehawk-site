# Reports im PulseHawk Measurement Framework

Je Report liegt hier eine Datei `<slug>.json` mit Kopfdaten. Die Seite baut `scripts/b2b_pages.py`. Vorher prüft der gemeinsame Wächter `scripts/report_waechter.py`. Ist eine Prüfung rot, entsteht keine Seite, der Bau bricht ab und meldet nach #ops-log.

Kein Report geht ohne Prüfung durch Claude in den Merge.

## Woher die Zahlen kommen (Ben, 3.11.2026)
- **Rechnung der messenden Sitzung:** Die Spezifikation v1.0 folgt `scripts/wache/report_v1.py` in kaspa-pulse, Stand main nach #245. Einzige Ausnahme ist M6.
- **Auftrag an die Zcash-Sitzung, bis 8.11.2026:** In report_v1.py müssen die 60 min ganz in den Daten liegen, und die Einheit sind ganze Sekunden.
- **Zweite Rechnung:** `scripts/upgrade_report.py` rechnet dieselben Kennzahlen unter denselben Namen aus der Roh-CSV im PH-Format.

| Datei | Wer baut sie | Wo sie liegt |
|---|---|---|
| Köpfe, Rohdaten der Wache (`wache-log.csv`, `zustand.json`), Kettenkonfiguration | messende Sitzung in kaspa-pulse (`roh_export.py`) | kaspa-pulse, Datenbranch der Kette, für Zcash `messung/zcash-mainnet` |
| Messwert-CSV `report-v1-<kette>-<upgrade>.csv` mit `.sha256` | messende Sitzung, `report_v1.py` | ebenda, Ordner `data/zcash-mainnet/report/` |
| Roh-CSV im PH-Format `reports/<slug>.csv` | eine Sitzung in pulsehawk-site mit `scripts/report_import.py` aus den Dateien oben, nach dem Fenster, für Zcash bis spätestens 9.11.2026 | pulsehawk-site `reports/`, öffentlich unter pulsehawk.io/reports/<slug>.csv |
| `werte` in `data/reports/<slug>.json` | dieselbe Sitzung, `report_import.py` übernimmt Wert und n jeder Kennzahl unverändert als Text aus der Messwert-CSV | pulsehawk-site |

- **Prüfung:** Der Wächter rechnet jede Kennzahl aus der Roh-CSV neu und vergleicht Wert und n exakt als Text mit `werte`.
- **Unabhängigkeit:** Zwei Codebasen rechnen auf denselben Eingängen.
- **Die Probe:** `python3 scripts/upgrade_report_probe.py --wache <kaspa-pulse>/scripts/wache` zeigt das auf Testdaten. Mit `--m6-nachgezogen` rechnet sie M6 schon so, wie es der Auftrag an die Zcash-Sitzung verlangt.

### Format der Roh-CSV
Spalten genau in dieser Reihenfolge: `report_id,method_version,kind,label,height,time_utc,value`

| kind | label | height | time_utc | value |
|---|---|---|---|---|
| block | leer | Höhe | Kopfzeit | Abstand zum Block davor in s, beim ersten Block leer |
| meta | `log` | leer | Kopfzeit des Aktivierungsblocks | 1, das Log der Wache ist da |
| reorg | leer | Höhe aus dem Log | Ankunft bei der Wache | Tiefe in Blöcken |
| split | `alarm` oder `entwarnung` | Höhe aus dem Log | Ankunft bei der Wache | Tiefe aus dem Log |
| peer | `activation`, `plus_6h`, `plus_24h` oder `plus_72h` | leer | Zeit der Probe | 1 unter dem Mindestprotokoll, 0 darüber |

- **Zeiten:** in UTC als `JJJJ-MM-TTThh:mm:ssZ`.
- **Blöcke:**
  - Lückenlos vom Block vor dem Fenster bis zum ersten Block mit Kopfzeit ab 72 h nach dem Aktivierungsblock.
  - Der Wächter schneidet das Fenster daraus über die Höhe, wie `report_v1.py`.
- **Reorg und split:** in der Reihenfolge des Logs.
- **Peer:** je Peer eine Zeile, aus den Versionen der Probe. Die Probe nach 6 h bleibt in den Rohdaten, der Report zeigt sie nicht.
- **Keine Adressen:** Die CSV enthält keine Adressen, Hostnamen oder Peer-Kennungen.

### Kennzahlen, die der Report zeigt
Die Namen sind die der Messwert-CSV (`upgrade_report.kennzahlen()`):
- **M1, je `vor` und `nach`:** `p50`, `p90`, `p99`, jeweils auch mit `_modell`.
- **M2:** `laengste_luecke_*`, `luecken_ueber_5x_ziel_*`.
- **M3:** `reorgs_ab_tiefe_2_*`, `reorgs_tiefe_1_*`, `reorgs_tiefe_2_*`, `reorgs_tiefe_3_plus_*`, `reorg_max_tiefe_*`.
- **M4:** `kettenspaltung_dauer_*`, `kettenspaltung_laengste_*`.
- **M5:** `peers_unter_min_protokoll_aktivierung`, `_aktivierung_plus_24h`, `_aktivierung_plus_72h`.
- **M6:** `zeit_bis_stabil`, in ganzen Sekunden.
- **M7:** `erster_block_kopfzeit`, `kopfzeit_minus_schaetzung`.

## Zahlen nachtragen, Schritte
1. **Dateien holen:** die Dateien der Wache und die Messwert-CSV vom Datenbranch, in einen eigenen leeren Ordner.
2. **Importieren:**

   `python3 scripts/report_import.py --slug <slug> --kette <kette.json> --koepfe <koepfe.csv.gz> --roh <ordner> --metriken <report-v1-...csv> --geaendert JJJJ-MM-TT`

   Das Skript bricht ab, solange `report_v1.py` M6 noch in Minuten schreibt.
3. **Prüfen:** `python3 scripts/report_waechter.py --pruefen <slug>`. Rot heißt: nichts veröffentlichen, Ursache beheben.
4. **Bauen:** `python3 scripts/b2b_pages.py`, danach PR. Kein Report geht ohne Prüfung durch Claude in den Merge.

## Neuer Report-Typ
- **Gemeinsamer Wächter:** Er wird nicht je Typ neu gebaut.
- **Neuer Typ:** bekommt ein eigenes Modul wie `scripts/upgrade_report.py` mit:
  - `QUELLEN_FELDER`, `zeilen`, `rechnen`, `oeffentlich`, `pruefe_plausibel`;
  - `seiten_werte`, `titel`, `seite`, `VERSIONEN`, `spezifikation_html`.
- **Eintrag in `TYPEN`:** in `scripts/report_waechter.py` mit Status `active` und Version.
