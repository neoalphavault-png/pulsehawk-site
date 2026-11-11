# Frischhaltung Teil 2: Rückfall statt Abbruch, tägliche Prüfung (Auftrag Ben 11.11.2026)

**Kopf Punkt 1:** Code in `4cc1d21` auf `site/frisch-rueckfall`, auf main nach `f15513e`. Selbst-Merge nach der Regel vom 26.10.

**Punkt 2:** Die Workflow-Datei kommt in einem eigenen PR, den Ben merged. Er baut auf diesem auf.

## 1. Rückfall statt Abbruch beim Alter

- **Zeitlose Fassung:** Ist der neueste Report älter als `FRISCH_TAGE` (21), bricht der Bau nicht mehr ab. Die Startseite baut dann die zeitlose Fassung:
  - **"Latest report":** Titel, Kennung und Link ("Read the report with its window, date and raw data"), ohne Kopfzahl.
  - **Messkacheln mit Wert:** Ist ihr Wert älter als die Grenze, entfallen sie. Dafür steht der Link "Earlier measurements, each with its window and the date it was published, are on our reports page". Mit der Zcash-Testnet-Kachel entfällt auch das Testnet-Diagramm.
  - **Kacheln ohne Wert** (Alexandria, Kaspa) und **frische Werte** bleiben stehen.
- **Abbruch mit Exit-Code 1 bleibt für echte Fehler:**
  - Wert ohne label, Fenster oder Datum;
  - sha256 passt nicht zur CSV.
- **Selbsttest** `python3 scripts/datiert.py --selbsttest`, 10 Fälle. Neu sind fünf Altersfälle: am Tag der Veröffentlichung, ein Tag vor Gelb, ab Gelb, genau an der Grenze, einen Tag drüber. Für jeden prüft der Test, dass es keinen Fehler gibt und dass zeitlose Fassung und Stufe stimmen.
- **Probe-Datum:** `PH_HEUTE=JJJJ-MM-TT` setzt das Baudatum für Proben. Im normalen Bau bleibt es leer.

### Beweis zeitlose Fassung

- **Bau:** mit `PH_HEUTE=2026-12-01`, 22 Tage nach PH-UR-2026-001. Exit-Code 0, 0 von 25 Seiten mit Funden.
- **Ergebnis:**
  - Kopfzahl 17.0 s fehlt.
  - Zcash-Testnet-Kachel und Diagramm fehlen, ihr Wert ist vom 18.10.
  - BCH bleibt, sein Wert vom 11.11. ist am 1.12. erst 20 Tage alt.
  - Der Link auf /reports/ steht da, die letzte Zeile lautet "pages built 1 December 2026".
- **Nachweis:**
  - Ausgabe in `beweis-3-zeitlose-fassung.txt`.
  - Bilder `home-390-dark-zeitlos.jpg` und `home-1440-dark-zeitlos.jpg`.
  - Zum Vergleich die normale Fassung `home-390-dark.jpg` und `home-1440-dark.jpg`.
- Danach zurückgesetzt, normaler Bau.

## 2. Prüfmodus für die tägliche Prüfung

- **Aufruf:** `python3 scripts/datiert.py --pruefen [--melden] [--probe] [--heute JJJJ-MM-TT]`. Der Modus liest nur. Er baut nichts und schreibt nichts.
- **Stufen:**

  | Stufe | Alter des neuesten Reports | Meldung nach #ops-log | Exit-Code |
  |---|---|---|---|
  | grün | unter 14 Tage (`GELB_TAGE`) | keine | 0 |
  | gelb | ab 14 Tage | mit den Resttagen | 0 |
  | rot | ab 21 Tage | ja | 1 |
  | rot | bei echten Fehlern | mit der Liste der Fehler | 1 |

- **Melden:** über `scripts/ph/ops_melden.py`, Art "log" (#ops-log, Secret `DISCORD_WEBHOOK_LOG`).
- **Probe** (`beweis-4-pruefmodus.txt`):

  | Datum | Alter | Ergebnis | Exit-Code |
  |---|---|---|---|
  | 22.11. | 13 Tage | grün | 0 |
  | 23.11. | 14 Tage | gelb, noch 7 Tage | 0 |
  | 30.11. | 21 Tage | rot | 1 |
  | 1.12. | 22 Tage | rot | 1 |
  | heute, sha256 kaputt | | rot mit dem Fehler | 1 |

  Mit kaputter sha256 bricht auch der Bau ab, Exit-Code 1.

## Prüfungen

- `b2b_pages.py`: 0 von 25 Seiten mit Funden.
- **Selbsttests:** `datiert.py --selbsttest` 10 von 10, `b2b_check.py --selbsttest` 26 von 26, `report_waechter.py --selbsttest` 55 von 55.
- pyflakes und Secret-Scan ohne Fund.
- Screenshots bei 390 und 1440 px, normale und zeitlose Fassung, kein waagerechtes Scrollen.
- **Design:** Ben hat am 11.11. entschieden, dass es beim dunklen Design bleibt. Die Bilder sind deshalb nur dunkel.

## Offene Fragen an Ben

- Im Rückfall bleibt der Prognose-Block mit "4 of 4" und Score stehen. Er ist eine gewertete Bilanz mit eigenem Stand-Datum und kein Messwert. Soll er im Rückfall ebenfalls entfallen?

## Was Ben tun muss

- Den Workflow-PR für die tägliche Prüfung prüfen und mergen.
- Die Abnahme von Punkt 1 auf pulsehawk.io folgt nach dem Merge als Zeile in diesem Bericht.

## Selbst-Merge und Abnahme Punkt 1 (11.11.2026)

- **Merge:** PR #86 per Squash, Merge-Commit `3797c56`, Branch gelöscht.
- **Abnahme auf pulsehawk.io:** Startseite und /reports/ sind live byte-gleich mit dem Bau aus `3797c56`.
- **Fassung:** Heute ist der neueste Report 2 Tage alt, darum steht die normale Fassung live. Die zeitlose Fassung zeigen die Bilder `*-zeitlos.jpg` oben.
- **Live-Aufnahmen** bei 390 und 1440 px: `home-390-dark-live.jpg` und `home-1440-dark-live.jpg`. Kein waagerechtes Scrollen.

## Punkt 2: Workflow `datiert-pruefung.yml` (eigener PR, Ben merged)

- **Was er tut:**
  - Läuft täglich um 07:17 UTC und auf Knopfdruck (workflow_dispatch).
  - Führt erst `python3 scripts/datiert.py --selbsttest` aus, dann `python3 scripts/datiert.py --pruefen --melden`.
  - Liest nur: kein Bau, kein Commit, kein Push, `permissions: contents: read`.
- **Meldungen nach #ops-log:**
  - gelb ab 14 Tagen mit den Resttagen;
  - rot ab 21 Tagen und bei echten Fehlern, dann endet der Lauf mit Exit-Code 1;
  - grün meldet nichts.
- **Secret:** `DISCORD_WEBHOOK_LOG` steht nur im meldenden Schritt. Fehlt es, steht die Meldung nur im Job-Log.
- **workflow_dispatch:** nimmt `heute` (Datum für eine Probe) und `probe` (nur Job-Log).
- **Lokal geprüft:**
  - Die YAML ist gültig.
  - Die Shell-Zeile des Schritts ergibt heute grün mit Exit-Code 0.
  - Mit `heute=2026-11-25` und `probe` ergibt sie gelb mit 5 Resttagen, ohne zu senden.
- **Erste Gelb-Meldung:** Für PH-UR-2026-001 kommt sie am 23.11., die erste Rot-Meldung am 30.11., falls bis dahin kein neuer Report eingetragen ist.

## Merge Punkt 2 (11.11.2026)

- **Merge:** Ben hat PR #87 am 11.11.2026 um 20:12 UTC gemergt, Merge-Commit `8318fa7`, Branch gelöscht.
- **Workflow:** "datiert pruefung" (`.github/workflows/datiert-pruefung.yml`) ist auf GitHub aktiv. Der erste geplante Lauf ist am 12.11.2026 um 07:17 UTC.
- **Erwartung:** Der Prüfmodus auf main ergibt heute grün (PH-UR-2026-001, 2 Tage alt, noch 19 Tage). Der erste Lauf meldet also nichts nach #ops-log.
- **Vorschlag:** Ein Probelauf von Hand (workflow_dispatch mit `heute=2026-11-25` und `probe`) zeigt die Gelb-Meldung im Job-Log, ohne zu senden. Ich löse ihn nur nach Bens Ja aus.
