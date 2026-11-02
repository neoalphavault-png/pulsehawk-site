# Bericht 2.11.2026, PulseHawk Measurement Framework und Upgrade Report v1.0

Auftrag von Ben vom 2.11.2026, mit der Ergänzung "Measurement Framework" vom selben Tag. Frist Do 5.11. 18:00 Berlin. Damit soll Zcash NU7 als erster Report im Format erscheinen; die Aktivierung ist um den 6.11. geschätzt. Umgesetzt in **#52** (Branch `site/upgrade-report-standard`).

- **Workflows:** Keine Workflow-, deploy- oder c2-Datei ist geändert.
- **Wer merged:** Ben, weil der PR öffentliche Regeln festlegt und vier Fragen offen sind (siehe unten). Sagt Ben "go", merge ich selbst.

## Was gemacht wurde

### Seiten
| Adresse | Inhalt | Index |
|---|---|---|
| /standard/ | "PulseHawk Measurement Framework". Die gemeinsamen Regeln, die gemeinsamen Prüfungen, Unabhängigkeit und Korrekturen, die fünf Report-Typen mit Präfix, Version und Status, Versionsregel, Changelog | ja, Sitemap |
| /standard/upgrade-report/ | "PulseHawk Upgrade Report, specification v1.0", M1 bis M7, Rechenregeln, CSV-Format, Changelog | ja, Sitemap |
| /standard/upgrade-report/v1-0 | Version 1.0 als feste Fassung. Sie bleibt unverändert online, wenn es v1.1 gibt | noindex |
| /standard/confirmation-depth/, /network-baseline/, /load-test/, /anchor-verification/ | geplante Typen, je ein Satz, Präfix, Status planned, ohne Termin und ohne Messwerte | noindex |
| /reports/zcash-nu7 | PH-UR-2026-001, Gerüst ohne Zahlen. Er zeigt Kopf, Quellen und M1 bis M7 mit "Not yet counted", die Schätzung bei M7 und "How to cite" | ja, Sitemap |
| /independence | neu, kurz: fünf Regeln, Finanzierung, Korrekturlog (leer), die Liste "Who cites our numbers?" bleibt | ja |

- **Fußzeile:** Auf allen Seiten stehen jetzt "Measurement Framework" und "Independence".
- **Schema:** Article auf allen neuen Seiten, mit Uhrzeit und Zeitzone. Report-Seiten haben zusätzlich ein Dataset mit `identifier`, `version` (Methode), `license` und `variableMeasured`. Sobald die CSV liegt, kommen `temporalCoverage` und `distribution` dazu.
- **Falke:** wie überall. Die Kaspa-Pulse-Marke steht auf den neuen Seiten nicht (siehe Frage 3).

**Warum mit Schrägstrich am Ende:** /standard/ liegt als `standard/index.html` vor. Gäbe es `standard.html` und den Ordner `standard/` nebeneinander, würde GitHub Pages /standard als Ordner behandeln. Der Aufruf von pulsehawk.io/standard leitet auf /standard/ weiter.

### Die Messwerte des Upgrade Report v1.0
- **M1 bis M7:** wie im Auftrag.
- **Fenster:** vom Block auf der Aktivierungshöhe aus gerechnet, 24 h davor bis 72 h danach.
- **Rechenregeln, festgelegt in der Spezifikation:**
  - **Perzentile:** nach dem nächsten Rang, Wert an Stelle ceil(q × n), ohne Interpolation. Das ist ganzzahlig und exakt nachrechenbar.
  - **Ideale Kette:** p50 = T × ln 2, p90 = T × ln 10, p99 = T × ln 100, auf 0.1 s gerundet, als computed.
  - **Zwei Mengen:** Abstände vor und nach der Aktivierung. Der Abstand, der am Aktivierungsblock endet, gehört zu keiner.
  - **M2:** Abstände strikt über 5 × T.
  - **M5:** drei Proben, jeweils höchstens 1 h neben ihrem Zeitpunkt. Nur die Softwareversion zählt, keine Adresse.
  - **M6:** Zur Abweichung von deinem Text siehe Frage 1.
  - **M7:** Zeit des Aktivierungsblocks und Abstand zu unserer Schätzung. Die Schätzung trägt ihr Datum.

### Quellen, je zwei unabhängige (Prüfung d)
Alles am 2.11.2026 im Original gelesen:

| Wert | Protokoll-Konstante | Release |
|---|---|---|
| Aktivierungshöhe 3,543,405 | ZIP 259, ACTIVATION_HEIGHT (NU7) Mainnet 3543405 | Zebra 7.0.0, Changelog "activates at height 3,543,405" |
| Zielabstand vorher 75 s | ZIP 208, PostBlossomPoWTargetSpacing := 75 | Zebra 7.0.0, `POST_BLOSSOM_POW_TARGET_SPACING = 75` |
| Zielabstand nachher 25 s | ZIP 218, PostNU7PoWTargetSpacing := 25 | Zebra 7.0.0, `POST_NU7_POW_TARGET_SPACING = 25` |

### Der Wächter, einmal für alle Typen
- **Gemeinsamer Teil, `scripts/report_waechter.py`:**
  - Kopfdaten, Report-ID, Quellen;
  - Prüfungen a) bis f);
  - "How to cite";
  - Meldung nach #ops-log;
  - Selbsttest g).
- **Typ-Teil, `scripts/upgrade_report.py`:** Er rechnet nur M1 bis M7 und baut den Inhalt. Ein neuer Typ bekommt ein eigenes Modul mit denselben Funktionen, der Wächter bleibt derselbe.
- **Einbindung in den Bau:** `b2b_pages.py` ruft den Wächter für jede Datei unter `data/reports/` auf.
- **Bei Rot:** Der ganze Bau bricht ab, und die Meldung geht über `scripts/ph/ops_melden.py` (neu mit Art `log`, Secret `DISCORD_WEBHOOK_LOG`) nach #ops-log. Ohne Secret steht sie im Job-Log.

| Prüfung | Was sie tut |
|---|---|
| a | Jeder Wert auf der Seite hat `data-k` (counted, source, computed), `data-n` und ein UTC-Fenster. Kennung und n stehen sichtbar neben dem Wert, das Fenster sichtbar im Abschnitt |
| b | Alle Werte werden aus der CSV neu gerechnet. Sie müssen exakt mit den Werten der messenden Sitzung (`werte` in der JSON) übereinstimmen und auch mit jedem Wert auf der fertigen Seite. Ein Gerüst darf keine Messwerte zeigen |
| c | p50 ≤ p90 ≤ p99, keine negativen Zählungen, alte Peers ≤ n. Das Fenster passt zur Aktivierungshöhe, die Blockhöhen sind lückenlos, Block-Abstand und Zeiten stimmen überein. Report-ID im Muster PH-XX-JJJJ-NNN, Präfix passend zum Typ, Methode gleich der aktiven Spezifikation |
| d | Je zwei Quellen mit verschiedener URL, eine Protokoll-Konstante und ein Release, gleiche Werte, mit Prüfdatum |
| e | Keine IPv4 und IPv6, Host:Port oder fremden Hostnamen, keine Schlüssel (Muster aus `secret_scan.py`), in Seite und CSV |
| f | Textregeln aus `b2b_check`, dazu now, live, Preise und "we offer" |
| g | `python3 scripts/report_waechter.py --selbsttest` |

**Ergebnis des Selbsttests g): 42 von 42 Fällen richtig.**
- **Sauber:** Ein sauberer Testdatensatz und das Gerüst gehen durch.
- **Absichtlich falsch:** 27 falsche Varianten lösen ihre Prüfung aus, jede von a) bis f) mindestens einmal. Darunter:
  - ein anderes p90 der Sitzung;
  - ein geänderter Wert auf der Seite;
  - eine Zeile außerhalb des Fensters;
  - ein Release mit anderer Höhe;
  - eine IP;
  - ein Hostname;
  - ein Host:Port in der CSV;
  - ein Token;
  - ein Gedankenstrich, "now", "we offer" und "$".
- **Meldung:** Die rote Meldung nach #ops-log ist getestet.

So sieht ein Report mit Zahlen aus. Das Muster ist aus Testdaten einer erfundenen "Testchain", nur zur Ansicht und nicht auf der Website:

![Muster mit Testdaten](2026-11-02-upgrade-report-standard/muster-testdaten-1440.jpg)

### Was die Sitzung "Zcash NU7 Testnet Messung" liefern muss
`data/reports/README.md` beschreibt es genau:
1. **CSV:** `reports/zcash-nu7.csv`, Spalten `report_id,method_version,kind,label,height,time_utc,value`, Zeilenarten block, reorg, tip und peer.
2. **Kopfdaten:** In `data/reports/zcash-nu7.json` kommen dazu:
   - `csv`;
   - die eigenen Werte unter `werte`;
   - `geaendert`;
   - falls nötig eine neuere `schaetzung` mit Datum.
3. **Bauen:** `python3 scripts/report_waechter.py --pruefen zcash-nu7`, dann `python3 scripts/b2b_pages.py`.

### Weitere Änderungen
- **`scripts/b2b_check.py`:**
  - `pruefe()` nimmt den HTML-Text auch direkt, damit der Wächter vor dem Schreiben prüft.
  - Die Regel gegen "percent" trifft nur noch das ganze Wort. "Percentile" ist ein Fachwort.
- **`_config.yml`:** `data/reports/README.md` geht nicht auf die Website.
- **Neue Datendatei `data/korrekturen.json`:** der Korrekturlog, anfangs leer. Jeder Eintrag hat datum, seite, alt, neu und grund.

## Prüfungen
- **Textregeln:** `b2b_check` 0 von 20 Seiten mit Fund.
- **Wächter:** `report_waechter.py --pruefen` meldet "ok PH-UR-2026-001 zcash-nu7, geruest".
- **Selbsttests:** Wächter 42 von 42, `ops_melden.py` 0 Fehler.
- **Screenshots:** 390 und 1440 px aller neuen Seiten, kein waagerechtes Scrollen. Auf der Report-Seite mit Zahlen brach zuerst die sha256-Zeile bei 390 px aus. Das ist behoben.
- **Code und Daten:**
  - `pyflakes` ohne Fund;
  - Sitemap gültig;
  - JSON-LD gültig, Datum überall mit Uhrzeit und Zeitzone;
  - Secret-Scan ohne Fund.

Screenshots (1440 px, ganze Seite):

![/standard/](2026-11-02-upgrade-report-standard/standard--1440.jpg)

![/standard/upgrade-report/](2026-11-02-upgrade-report-standard/standard-upgrade-report--1440.jpg)

![/reports/zcash-nu7](2026-11-02-upgrade-report-standard/reports-zcash-nu7-1440.jpg)

![/independence](2026-11-02-upgrade-report-standard/independence-1440.jpg)

Die Fassungen für 390 px liegen im selben Ordner.

## Offene Fragen an Ben
1. **M6 Time to stable, wichtig vor dem 6.11.** Dein Text sagt "rolling 1 h p50 within 10 % of target".
   - **Wörtlich erreicht das keine Kette:** Bei zufälligen Blockabständen liegt der p50 einer idealen Kette bei T × ln 2, also 17.3 s bei 25 s. Er liegt nie in der Nähe von 25 s.
   - **Umsetzung:** Ich messe deshalb gegen die idealen 17.3 s. Das steht so in der Spezifikation.
   - **Zweites Problem, die Streuung:** Über eine Stunde sind es nur etwa 144 Abstände. Der p50 schwankt dann um etwa 12 %, selbst bei einer idealen Kette. "Zum ersten Mal innerhalb von 10 %" kann darum ein Zufallstreffer sein.
   - **Vorschlag:** "3 Stunden in Folge innerhalb von 10 %" oder ein Fenster von 6 Stunden.
   - **Zeitpunkt:** Jede Änderung nach dem Merge wäre schon v1.1. Besser entscheiden wir das vorher.
2. **Finanzierung:** Auf /independence steht: "run by Vizora Digital UG, funded by fees for paid measurements and by grants for public measurements". Stimmt das so?
3. **Kaspa Pulse auf /independence:** Die alte Regel "The same team runs Kaspa Pulse" ist raus, wegen "Kaspa-Pulse-Marke nein". Die Fußzeile nennt kaspapulse.com weiter auf allen Seiten. Soll ein neutraler Satz zur Verbindung auf /independence bleiben? Für die Unabhängigkeit wäre das ehrlicher.
4. **M3, M4 und M5 bei Zcash:**
   - **M3 und M4:** Die Zählung in kaspa-pulse läuft über einen Header-Client. Kann er Reorgs und konkurrierende Tips sehen und aufschreiben? Sonst stünde bei M3 und M4 eine 0, die nur "nicht beobachtet" heißt. Dann sollten wir die Sitzung anweisen, das mitzuschreiben.
   - **M5:** Gibt es um +24 h und +72 h eine Peer-Probe?
5. **Schätzung für M7:** Eingetragen ist unsere Schätzung vom Stand 28.10., also 6.11. 02:26 UTC. Du nennst 02:40 UTC. Soll die messende Sitzung vor der Aktivierung den letzten Stand eintragen, mit dessen Datum?
6. **Geplante Typen:** Sind die fünf Sätze so recht, und sollen ihre Unterseiten bis zur Spezifikation `noindex` bleiben?

## Was Ben tun muss
1. In pulsehawk-site das Secret `DISCORD_WEBHOOK_LOG` anlegen (Webhook von #ops-log), unter Settings, Secrets and variables, Actions.
   - **Lokale Läufe:** Läuft der Wächter in einer Claude-Sitzung, steht die Meldung nur im Log.
   - **Workflow:** Soll ein Workflow Reports bauen und melden, wäre das ein eigener PR, den Ben merged.
2. Fragen 1 bis 6 beantworten, vor allem Frage 1 vor dem 6.11.
3. #52 prüfen und mergen, oder "go" sagen, dann merge ich.
