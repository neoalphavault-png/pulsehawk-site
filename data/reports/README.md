# Reports im PulseHawk Measurement Framework

Je Report liegt hier eine Datei `<slug>.json` mit Kopfdaten. Die Seite baut `scripts/b2b_pages.py`. Vorher prüft der gemeinsame Wächter `scripts/report_waechter.py`. Ist eine Prüfung rot, entsteht keine Seite, der Bau bricht ab und meldet nach #ops-log.

Kein Report geht ohne Prüfung durch Claude in den Merge.

## Zahlen nachtragen (messende Sitzung)

1. **CSV ablegen:** unter `reports/<slug>.csv`. Spalten genau in dieser Reihenfolge:

   `report_id,method_version,kind,label,height,time_utc,value`

   | kind | label | height | time_utc | value |
   |---|---|---|---|---|
   | block | leer | Höhe | Header-Zeit | Abstand zum Block davor in s, beim ersten Block leer |
   | reorg | leer | Höhe der Gabelung | gesehen | Tiefe in Blöcken |
   | tip | leer | Höhe | zuerst gesehen | Dauer in s, bis einer der Tips aufgegeben ist |
   | peer | `activation`, `plus_24h` oder `plus_72h` | leer | Zeit der Probe | 1 alte Software, 0 neue |

   - **Zeiten:** in UTC als `JJJJ-MM-TTThh:mm:ssZ`.
   - **Blockhöhen:** lückenlos, mit dem Block auf der Aktivierungshöhe.
   - **Fenster:** Alle Zeilen liegen zwischen 24 h vor und 72 h nach der Zeit dieses Blocks.
   - **Peer-Proben:** jeweils höchstens 1 h neben ihrem Zeitpunkt.
   - **Keine Adressen:** Die CSV enthält keine Adressen, Hostnamen oder Peer-Kennungen.

2. **Kopfdaten ergänzen:** in `<slug>.json` `"csv": "reports/<slug>.csv"` eintragen und unter `"werte"` die eigenen, unabhängig gerechneten Werte M1 bis M7. Die Form steht in `scripts/upgrade_report.py`, Funktion `rechnen`.
   - **Exakter Vergleich:** Der Wächter rechnet alles aus der CSV nach und vergleicht exakt.
   - **Regeln:** Perzentile nach dem nächsten Rang, Idealwerte auf 0.1 s, Spezifikation unter /standard/upgrade-report/.
3. **Datum setzen:** `"geaendert"` auf das Datum des Updates.
4. **Prüfen und bauen:**
   - `python3 scripts/report_waechter.py --pruefen <slug>`, danach `python3 scripts/b2b_pages.py`.
   - Rot heißt: nichts veröffentlichen, Ursache beheben.

## Neuer Report-Typ

- **Gemeinsamer Wächter:** Er wird nicht je Typ neu gebaut.
- **Neuer Typ:** bekommt ein eigenes Modul wie `scripts/upgrade_report.py` mit:
  - `QUELLEN_FELDER`, `zeilen`, `rechnen`, `oeffentlich`, `pruefe_plausibel`;
  - `seiten_werte`, `titel`, `seite`, `VERSIONEN`, `spezifikation_html`.
- **Eintrag in `TYPEN`:** in `scripts/report_waechter.py` mit Status `active` und Version.
