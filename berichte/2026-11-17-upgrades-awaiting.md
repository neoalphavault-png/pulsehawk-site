# Upgrade-Kalender: awaiting confirmation, v1.0 mit canonical, NU8-Quelle (Ben, 17.11.2026)

PR #100, Kopf: `6b145cc` auf `site/upgrades-awaiting`.

## Was gemacht wurde

1. **Folgefix #98: Termin vorbei, keine Bestätigung**
   - `scripts/b2b_pages.py` hat die neue Funktion `upgrade_stand()`.
   - Ein Eintrag mit Status scheduled, dessen Datum vor dem Bautag liegt, zeigt im Kalender „awaiting confirmation“. Darunter steht die Notiz „The scheduled time has passed. BCHN has not confirmed the activation yet.“
   - Das Datum bleibt stehen. Am Tag selbst bleibt der Eintrag scheduled, weil die Uhrzeit dann noch aussteht.
   - Als bestätigt gilt ein Upgrade erst, wenn `data/upgrades.json` es mit Quelle auf activated setzt.
   - Den Namen in der Notiz liefert das neue Feld `confirmer` in `data/upgrades.json`. Für `bch-2027-chipnet` steht dort „BCHN“, ohne das Feld steht der Name der Chain.
   - BCH Chipnet zeigt damit 15 November 2026, 12:00 UTC, „awaiting confirmation“ mit Notiz.
2. **Selbsttest und Prüfung**
   - `scripts/b2b_check.py` hat die neue Prüfung `funde_kalender`. Eine Kalenderzeile mit „scheduled“ und vergangenem Datum ist rot. Die alte /upgrades von main hätte sie gemeldet: „kalender scheduled mit vergangenem datum 2026-11-15“.
   - Der Selbsttest hat sechs neue Fälle:
     - Datum vorbei;
     - am Tag selbst;
     - Datum kommt;
     - bestätigt;
     - ohne Datum;
     - eine alte Zeile, die rot werden muss.
3. **Antwort zu #97, v1.0 mit canonical**
   - /standard/upgrade-report/v1-0 trägt statt noindex ein canonical auf /standard/upgrade-report/ und steht wieder auf `index, follow`.
   - Sitemap und llms.txt führen die Seite weiter nicht. Dafür sorgt die neue Funktion `indexiert()`: Eine Seite mit canonical auf eine andere Seite kommt dort nicht hinein.
   - Impressum und Datenschutz behalten noindex.
4. **Antwort zu #98, NU8-Quelle**
   - Es gibt noch keinen ZIP für NU8. In zcash/zips (Stand 16.11.2026) fehlt ein „Deployment of the NU8 Network Upgrade“. Nur der Entwurf ZIP 248 (Extensible Transaction Format) erwähnt NU8, und dort nur hypothetisch.
   - Eine offizielle Ankündigung habe ich nicht gefunden. Die Seiten der Zcash-Organisationen sind aus dieser Sitzung nicht erreichbar, nur das Forum.
   - Der Eintrag bleibt proposed mit der Forumsquelle. Ich stelle ihn um, sobald es einen ZIP oder eine Ankündigung gibt.

## Prüfungen

- `b2b_pages.py` hat neu gebaut, 0 von 25 Seiten mit Funden.
- Selbsttests:
  - `b2b_check` 0 von 32 Fällen falsch;
  - `datiert` 0 von 10;
  - `report_waechter` 0 von 55;
  - `ph_kalender_post` 0 von 56.
- pyflakes ist sauber, der Secret-Scan findet nichts.
- Lokal im Browser bei 390 und 1440 px: Die Chipnet-Zeile zeigt Status und Notiz, kein waagerechtes Scrollen.

## Offene Fragen an Ben

1. Die Seiten werden nur beim Bau neu geschrieben. Läuft ein Termin ab, ohne dass jemand baut, steht scheduled weiter da, bis zum nächsten Bau. Soll die tägliche Prüfung (`datiert.py --pruefen`) einen abgelaufenen scheduled-Termin in #ops-log melden? Das wäre nur Code in `datiert.py`, keine Workflow-Änderung.

## Was Ben tun muss

Nichts außer der Frage oben. Die Abnahme auf pulsehawk.io folgt nach dem Merge in diesem Bericht.
