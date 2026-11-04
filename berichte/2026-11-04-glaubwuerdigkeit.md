# Glaubwürdigkeit PulseHawk (Auftrag Ben, 4.11.2026)

PR #54, Branch `site/glaubwuerdigkeit`. Selbst-Merge nach Bens Regel vom 26.10. (Korrektur 4.11.): keine Workflows, kein deploy, kein c2, kein Secrets-Bezug, Checks grün, keine Konflikte, Textregeln bestanden.
Frist: So 8.11. 18:00.

## Was gemacht wurde

1. **/track-record** wird aus `data/track-record.json` gebaut.
   - Felder: Veröffentlichung (Datum und Link), Netz, Gegenstand, unser Wert, Ergebnis (gezählt, mit Fenster, n und 95-%-Intervall), Abweichung, Methoden-IDs, Status.
   - Es gibt zwei Arten von Einträgen: "Our estimate" und "Against a published value".
   - Der Wächter in `b2b_pages.py` (`pruefe_track_record`) prüft beim Bau:
     - Jeder Eintrag hat einen https-Link und ein ISO-Datum.
     - "in band" und "outside" stehen nur mit gezähltem Ergebnis (Wert, Fenster, n, Intervall) und einer Abweichung.
     - "open" hat kein Ergebnis.
     - Eine Schätzung braucht eine Blockhöhe.
     - Ein Upgrade braucht seine Spec-Nummer im Feld Netz.
     - Methoden-IDs müssen bekannt sein.

   Ist eine Bedingung verletzt, bricht der Bau ab.

   Einträge:
   - **TR-001, Vergleich:** BCH-Tempnet, Median 43 s gegen 41,6 s (60 s × ln 2, CHIP-2025-03). Fenster 15.10. 12:56 bis 21.10. 09:59 UTC, n 7.571, 95-%-Intervall 41 bis 44 s. Der Vergleichswert liegt im Intervall: in band. Quelle ist die Startseite #bch-median, 22.10.
   - **TR-002, Vergleich:** Zcash-NU7-Testnet, Mittel 23,68 s gegen 25 s (ZIP 218). n 49.202, Intervall 23,48 bis 23,88 s: outside. Veröffentlicht am 18.10. auf /zcash-nu7#mean.
   - **TR-003, Schätzung:** Block 3.543.405 am 6.11. um 02:26 UTC, Band 5.11. 23:01 bis 6.11. 05:51 UTC, Stand 28.10., auf /zcash-nu7. Status open.
   - **TR-004, Schätzung:** 6.11. 02:39 UTC, Band 00:28 bis 05:00 UTC, Stand 2.11., auf /reports/zcash-nu7#m7. Status open.
2. **/corrections** wird aus `data/corrections.json` gebaut (Datum, Seite, was falsch war, was jetzt steht, wer es gemeldet hat). Die drei Einträge stammen aus #48, #50 und #52. Die Fußzeile verlinkt die Seite. /independence verweist auf /corrections statt auf das alte Korrekturlog; `data/korrekturen.json` ist gelöscht.
3. **/about**:
   - Inhalt: Vizora Digital UG (haftungsbeschränkt), Düsseldorf, hello@pulsehawk.io. Wer uns bezahlt: Gebühren, keine Tokens, Preis vor der Messung fest und nie vom Ergebnis abhängig, "did not pass" ist ein gültiges Ergebnis. Rolle: "We measure and report, others decide."
   - Links: /method, /track-record, /corrections, github.com/pulsehawk/methods.
   - Schema: Organization und AboutPage. Person kommt erst dazu, wenn `GRUENDER` in `b2b_pages.py` gesetzt ist. Bis dahin fehlt der Gründer-Abschnitt und der Bau warnt.
   - Es gibt keine Aussage zu einer Akkreditierung.
4. **/method** hat feste IDs PH-M-001 bis PH-M-006, jede mit eigenem Anker (#ph-m-001), Beschreibung und Validierung (womit und wann geprüft). Die Quelle ist `VERFAHREN` in `scripts/report_waechter.py`.
5. **Reproduce und Unsicherheit:**
   - /zcash-nu7 hat eine Spalte "95% interval" in der Testnet-Tabelle und der Mainnet-Tabelle vor NU7, dazu Wilson-Intervalle für die Anteile und für 5 von 780 (0,27 bis 1,49 %).
   - Jeder Abschnitt dort hat eine Zeile "Measurement uncertainty" und die Methoden-IDs.
   - /zcash-nu7 und /reports/zcash-nu7 haben den Block "Reproduce this". Die Rechnung steht in `scripts/unsicherheit.py`.
6. **Wächter `b2b_check.py`:**
   - Ein Absatz, der eine Kette oder ein benanntes Upgrade zusammen mit Aktivierung, Upgrade, Hardfork oder Konsensregel nennt, braucht eine Spec-Nummer (ZIP, CHIP, KIP, BIP, EIP, SIMD oder BEP).
   - Eine vorhergesagte Upgrade-Zeit steht nur mit Blockhöhe und "estimate".
   - Mess- und Report-Seiten ohne Methoden-IDs, Unsicherheitszeile oder Reproduce-Block sind rot.
   - `--selbsttest` hat 18 Fälle.
   - Wegen der neuen Regeln geänderte Texte: KIP-14 auf /cases/kaspa, ZIP 259 auf der Startseite, ZIP 218 und ZIP 259 auf /zcash-nu7, ZIP 259 im Report-Lead und bei PH-M-006. Die Prognose auf /zcash-nu7 heißt jetzt "our estimate".
7. **Startseite:** Der Zähler ab 3 bleibt. Dazu kommt ein Satz mit Link auf /track-record.

### Prüfungen

- `b2b_pages.py`: 0 von 23 Seiten mit Funden.
- `b2b_check.py --selbsttest`: 0 von 18 Fällen falsch.
- `report_waechter.py --selbsttest`: 0 von 55 Fällen falsch.
- pyflakes ist sauber, `secret_scan.py --staged` hat nichts gefunden.
- Screenshots in 390 und 1440 px (track-record, corrections, about, method, zcash-nu7, reports/zcash-nu7): kein seitliches Scrollen.
- **M6:** Die Probe gegen kaspa-pulse main zeigt jetzt ohne Schalter 36 von 36 Kennzahlen gleich, der Wächter ist grün. Die M6-Änderung steht in report_v1.py auf main (ganze Sekunden). Der Schalter `--m6-nachgezogen` gibt jetzt nur einen Hinweis aus.

## Offene Fragen an Ben

1. **Nicht geprüfte Einträge:** Zwei Einträge stehen nicht im Track record, weil ich die Quelle nicht selbst prüfen konnte. Die Foren von Bitcoin Cash Research und der Zcash Community sind aus dieser Umgebung nicht erreichbar.
   - **Stale-Rate BCH:** 0,38 % gegen 0,41 % (CHIP, 30.10.). In unseren Daten steht 0,38 % (16 von 4.223), den Vergleichswert 0,41 % finde ich nirgends.
   - **NU7-Schätzung vom 29.10.:** Forum-Beitrag #33.

   Bitte die beiden Permalinks schicken oder die Foren in der Umgebung freigeben. Dann trage ich beide nach.
2. **TR-002, Datum:** Im Auftrag steht 22.10. Die Seite /zcash-nu7 war aber schon am 18.10. mit 23,68 s öffentlich, deshalb steht 18.10. im Eintrag. Passt das?
3. **Gründer:** Wie soll der Name auf /about und im Schema stehen? Bis zur Entscheidung bleibt der Platzhalter `GRUENDER`, und der Abschnitt fehlt.
4. **Methodennamen:**
   - **Unterschiede:** Die IDs stimmen mit METHODS.md in github.com/pulsehawk/methods (main) überein, zwei Namen aber nicht:
     - PH-M-002 heißt dort "Tip switches and chain split", bei uns "Reorg depth from the listener" (deine Liste).
     - PH-M-004 heißt dort "First seen and propagation", bei uns "Propagation from the listener".
   - **Welche Fassung gilt?** Ich gleiche die andere Seite an.
5. **Veröffentlichungsdatum des Reports:** `data/reports/zcash-nu7.json` nennt als Veröffentlichung den 3.11., live ist der Report seit dem Merge von #52 am 4.11. Soll ich das Datum auf den 4.11. setzen?

## Reproduce-Befehle

- **Stand der Befehle:** github.com/pulsehawk/methods hat auf main drei Befehle für das Testnet-Beispiel. Für /reports/zcash-nu7 habe ich die passenden Mainnet-Befehle eingetragen (`data/reproduce.json`). Sie bleiben unbestätigt, bis die Zcash-Sitzung sie für genau diese Seite bestätigt und die Mainnet-Eingaben nach dem Messfenster im Repo liegen.
- **Was die Seite zeigt:** Bis dahin nur den Clone-Befehl und den Satz, wann der Rest kommt.
- **Ungeprüft:** Ich konnte die Befehle hier nicht ausführen, die Umgebung lässt fremden Code nicht laufen. Die Zcash-Sitzung hat auf meine Nachricht noch nicht geantwortet.
- **Testnet-Seite:** Für die Testnet-CSV vom 18.10. auf /zcash-nu7 gibt es im Methods-Repo noch keinen Befehl.

## Was Ben tun muss

- Nichts zum Mergen: #54 merge ich selbst, die Abnahme auf pulsehawk.io folgt als eigene Zeile.
- **#47 nach dem Merge von #54:** Beide PRs ändern die Startseite und /cases/kaspa. #47 rebase ich auf den neuen main, baue neu und prüfe wieder.
- Die offenen Fragen 1 bis 5 beantworten.
- Die Zcash-Sitzung bitten, die Reproduce-Befehle für /reports/zcash-nu7 zu bestätigen. Danach setze ich `bestaetigt` auf true.

## Nach der NU7-Aktivierung (Trigger 6.11.)

- TR-003 und TR-004 bekommen das gezählte Ergebnis (Zeit von Block 3.543.405) und den Status in band oder outside.
- Für den Teil "nach_nu7" in `data/zcash-nu7/mainnet-unsicherheit.json` rechne ich die Intervalle mit `scripts/unsicherheit.py --koepfe`. Bis dahin sagt die Seite, dass sie noch fehlen.

## Selbst-Merge und Abnahme (4.11.2026)

- **Merge:** PR #54 per Squash gemergt, Merge-Commit `f764629`. Der Branch `site/glaubwuerdigkeit` ist gelöscht.
- **Abnahme auf pulsehawk.io um 14:13 UTC:** /track-record, /corrections, /about, /method, /zcash-nu7, /reports/zcash-nu7, /independence, die Startseite und /cases/kaspa sind live byte-gleich mit dem Bau aus `f764629`.
- **Geprüfte Inhalte:**
  - /track-record zeigt 4 Einträge.
  - /method hat 6 Anker PH-M-001 bis PH-M-006.
  - /zcash-nu7 und /reports/zcash-nu7 haben je 7 Methodenzeilen, 7 Zeilen "Measurement uncertainty" und den Block "Reproduce this".
  - Der Link auf /track-record steht auf der Startseite und in der Fußzeile.
  - Die Sitemap führt die drei neuen Seiten.

## Nachtrag 4.11.2026, Antwort der Sitzung "Zcash NU7 Testnet Messung"

- **IDs:** PH-M-001 bis PH-M-006 sind abgestimmt. METHODS.md liegt in pulsehawk/methods auf main (PR #1 dort gemergt).
- **Namen:** Bei PH-M-002 und PH-M-004 weichen die Namen noch ab, siehe offene Frage 4.
- **Reproduce:**
  - Die Mainnet-Befehle für /reports/zcash-nu7 stehen jetzt wörtlich so in `data/reproduce.json`, wie die Sitzung sie genannt hat. Die Prüfsummendatei heißt `report-v1-zcash-mainnet-nu7.sha256`.
  - Die Befehle bleiben als folgend markiert (`bestaetigt` false), bis der Daten-PR mit `data/zcash-mainnet-nu7/` in pulsehawk/methods gemergt ist, ab etwa 9.11.
- **Code auf /method:** Jede ID hat jetzt eine Zeile "Code", die dem Stand im Repo entspricht.
  - PH-M-001 bis PH-M-004: Die Rechnung aus den aufgezeichneten Daten steht in `upgrade_report/report_v1.py`. Kopf-Client und Zuhörer folgen.
  - PH-M-005: folgt.
  - PH-M-006: Die Report-Zeilen stehen in report_v1.py, die Prognose selbst folgt.

  Vorher stand dort pauschal "The code for each ID is in github.com/pulsehawk/methods". Das stimmte nicht, weil die Erzeugung der Eingaben noch nicht im Repo liegt (Bens Frist dafür: 30.11.).
- **Link:** /method verlinkt METHODS.md.
- **M7:** Unser M7 hat keinen Wert "erste Sicht", deshalb bleiben die IDs für M7 bei PH-M-001 und PH-M-006. Die Probe zeigt weiter 36 von 36.
