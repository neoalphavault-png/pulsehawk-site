# Reproduce-Befehle für /reports/zcash-nu7 freigeschaltet (9.11.2026)

## Was gemacht wurde

- **Anlass:** Die Sitzung "Zcash NU7 Testnet Messung" meldet: Der NU7 Upgrade Report v1 ist in github.com/pulsehawk/methods reproduzierbar, PR 5 ist gemergt (Merge-Commit `0820cde`). Die Daten liegen in `data/zcash-mainnet-nu7/`, gerechnet mit `upgrade_report/report_v1.py` bei `0e5019c`. Die Befehle hat die Sitzung auf einem frischen Clone getestet.
- **Meine Prüfung:**
  - Commit `0820cde` liegt auf main.
  - `data/zcash-mainnet-nu7/` enthält heads.csv.gz, raw/, expected/ und output/.
  - Die Dateien in output/ passen zur erwarteten sha256 in expected/: Report-CSV `0f1e1969…748b8e`, Unsicherheits-CSV `89204aba…eb45cf`.
  - Die Befehle selbst konnte ich hier nicht ausführen, weil die Umgebung fremden Code nicht laufen lässt.
- **`data/reproduce.json`:** Der Eintrag `reports/zcash-nu7` ist jetzt `bestaetigt` true, mit Commit und Herkunft. Der Block "Reproduce this" auf /reports/zcash-nu7 zeigt drei Befehle:
  1. `git clone https://github.com/pulsehawk/methods && cd methods`
  2. `python3 upgrade_report/report_v1.py --config upgrade_report/configs/zcash-mainnet-nu7.json --heads data/zcash-mainnet-nu7/heads.csv.gz --raw data/zcash-mainnet-nu7/raw --out out`
  3. `cd out && sha256sum -c ../data/zcash-mainnet-nu7/expected/report-v1-zcash-mainnet-nu7.sha256`

  Den Selbsttest (`--selftest`) nennt die Seite nicht. Der Block hat drei Befehle nach deinem Auftrag vom 4.11., und der Clone gehört dazu.
- **Datum:** dateModified des Reports ist der 9.11.2026.
- **Hinweis der Sitzung erledigt:** Sie schrieb, im Track Record fehle der 23.10. und die Seite sage noch "estimate". Beides ist seit #75 erledigt.

## Prüfungen

- `b2b_pages.py`: 0 von 24 Seiten mit Funden.
- `report_waechter.py --selbsttest`: 55 von 55.
- `secret_scan.py --staged` ohne Fund.

## Offene Fragen an Ben

- /reports/zcash-nu7 ist weiter das Gerüst mit den Testdaten. Die Sitzung meldet die echten Werte (M1 p50 17.0 s bei n 10,195; M6 13,016 s; M7 "the block came 6 min 56 s earlier than the 4 Nov forecast"). Soll ich den Report mit den Mainnet-Daten aus pulsehawk/methods jetzt bauen, oder macht das die Zcash-Sitzung?
- Für /zcash-nu7 (Testnet-CSV vom 18.10.) gibt es im Repo noch keinen Befehl. Der Block dort zeigt nur den Clone.

## Was Ben tun muss

Nichts. Die Abnahme auf pulsehawk.io folgt nach dem Merge als Zeile in diesem Bericht.

## Selbst-Merge und Abnahme (9.11.2026)

- PR #77 per Squash gemergt, Merge-Commit `0248023`, Branch gelöscht.
- Live auf pulsehawk.io/reports/zcash-nu7 byte-gleich mit dem Bau.
- Der Block "Reproduce this" hat `data-bestaetigt="true"` und zeigt alle drei Befehle, auch die Prüfung gegen `expected/report-v1-zcash-mainnet-nu7.sha256`.
