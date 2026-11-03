# Reports im PulseHawk Measurement Framework

Je Report liegt hier eine Datei `<slug>.json` mit Kopfdaten. Die Seite baut `scripts/b2b_pages.py`. Vorher prüft der gemeinsame Wächter `scripts/report_waechter.py`. Ist eine Prüfung rot, entsteht keine Seite, der Bau bricht ab und meldet nach #ops-log.

Kein Report geht ohne Prüfung durch Claude in den Merge.

## Zwei CSV-Dateien

| Datei | Wer baut sie | Wo sie liegt | Inhalt |
|---|---|---|---|
| Messwert-CSV | `scripts/wache/report_v1.py` in kaspa-pulse, messende Sitzung | kaspa-pulse, Branch `messung/zcash-mainnet`, Ordner `data/zcash-mainnet/report/`, Name `report-v1-<kette>-<upgrade>.csv`, dazu `.sha256` und `-eingang.json` | eine Zeile je Kennzahl. Spalten `metrik, kennzahl, wert, einheit, art, fenster_von_utc, fenster_bis_utc, n, quelle, anmerkung` |
| Roh-CSV im PH-Format | dieselbe messende Sitzung in kaspa-pulse, aus denselben Eingängen wie `report_v1.py` (Köpfe, Log, Zustand und Ereignisse der Wache), **bis spätestens 9.11.2026** | zuerst kaspa-pulse, Branch `messung/zcash-mainnet`, `data/zcash-mainnet/report/zcash-nu7.csv` mit `.sha256`. Eine Sitzung in pulsehawk-site kopiert sie unverändert nach `reports/zcash-nu7.csv`. Die öffentliche Adresse ist pulsehawk.io/reports/zcash-nu7.csv | eine Zeile je Block, Reorg, Tip und Peer-Probe, Format unten |

- **Prüfung:** Der Wächter rechnet jeden Wert aus der Roh-CSV neu und vergleicht exakt mit den Werten aus der Messwert-CSV, die unter `"werte"` in `<slug>.json` stehen.
- **Unabhängigkeit:** Die Messwert-CSV ist die unabhängige Rechnung der messenden Sitzung. Der Wächter ist die zweite.

### Format der Roh-CSV
Spalten genau in dieser Reihenfolge: `report_id,method_version,kind,label,height,time_utc,value`

| kind | label | height | time_utc | value |
|---|---|---|---|---|
| block | leer | Höhe | Header-Zeit | Abstand zum Block davor in s, beim ersten Block leer |
| reorg | leer | Höhe der Gabelung | gesehen | Tiefe in Blöcken |
| tip | leer | Höhe | zuerst gesehen | Dauer in s, bis einer der Tips aufgegeben ist |
| peer | `activation`, `plus_6h`, `plus_24h` oder `plus_72h` | leer | Zeit der Probe | 1 alte Software, 0 neue |

- **Zeiten:** in UTC als `JJJJ-MM-TTThh:mm:ssZ`.
- **Blockhöhen:** lückenlos, mit dem Block auf der Aktivierungshöhe.
- **Fenster:** Alle Zeilen liegen zwischen 24 h vor und 72 h nach der Header-Zeit dieses Blocks.
- **Peer-Proben:**
  - Jede Probe liegt höchstens 1 h neben ihrem Zeitpunkt.
  - Die Probe nach 6 h bleibt in den Rohdaten, der Report zeigt sie nicht (Ben, 3.11.2026).
- **Keine Adressen:** Die CSV enthält keine Adressen, Hostnamen oder Peer-Kennungen.

### Von der Messwert-CSV zu `"werte"`
| Messwert-CSV (kennzahl) | `werte` in der JSON |
|---|---|
| `p50_vor`, `p90_vor`, `p99_vor` | `M1.vorher.p50`, `p90`, `p99` |
| `p50_nach`, `p90_nach`, `p99_nach` | `M1.nachher.p50`, `p90`, `p99` |
| `*_modell` in M1 | `M1.*.p50_ideal`, `p90_ideal`, `p99_ideal` |
| `laengste_luecke_vor` und `_nach`, `luecken_ueber_5x_ziel_vor` und `_nach` | `M2.vorher` und `M2.nachher`: `laengste_s`, `ueber_5x` |
| `reorgs_*`, `reorg_max_tiefe_*` | `M3.reorgs`, `M3.max_tiefe` |
| `kettenspaltung_*` | `M4` |
| `peers_unter_min_protokoll_aktivierung`, `_plus_24h`, `_plus_72h` | `M5.activation`, `plus_24h`, `plus_72h`, je `n` und `alt` |
| `zeit_bis_stabil_mittel` | `M6.sekunden` (Minuten mal 60) |
| `erster_block_kopfzeit`, `kopfzeit_minus_schaetzung` | `M7.zeit_utc`, `M7.abstand_s` |

**Stand 3.11.2026:** Die Zuordnung steht. Exakt gleich sind die Werte erst, wenn `report_v1.py` und die Spezifikation v1.0 in allen Punkten dieselbe Rechnung machen. Die offenen Unterschiede stehen in `berichte/2026-11-02-upgrade-report-standard.md`. Bis sie geklärt sind, bleibt Prüfung b) rot, und der Report wird nicht gebaut. So ist es gewollt.

## Zahlen nachtragen, Schritte
1. **Roh-CSV:** `reports/<slug>.csv` aus kaspa-pulse übernehmen. Die sha256 muss zu der `.sha256` dort passen.
2. **Kopfdaten:** In `<slug>.json` gehören:
   - `"csv": "reports/<slug>.csv"`;
   - `"werte"` aus der Messwert-CSV, nach der Tabelle oben;
   - `"geaendert"`;
   - falls nötig eine neuere `"schaetzung"` mit Datum und Band.
3. **Prüfen und bauen:**
   - `python3 scripts/report_waechter.py --pruefen <slug>`, danach `python3 scripts/b2b_pages.py`.
   - Rot heißt: nichts veröffentlichen, Ursache beheben.

## Neuer Report-Typ
- **Gemeinsamer Wächter:** Er wird nicht je Typ neu gebaut.
- **Neuer Typ:** bekommt ein eigenes Modul wie `scripts/upgrade_report.py` mit:
  - `QUELLEN_FELDER`, `zeilen`, `rechnen`, `oeffentlich`, `pruefe_plausibel`;
  - `seiten_werte`, `titel`, `seite`, `VERSIONEN`, `spezifikation_html`.
- **Eintrag in `TYPEN`:** in `scripts/report_waechter.py` mit Status `active` und Version.
