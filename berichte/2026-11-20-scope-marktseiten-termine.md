# Scope statt Kosten, alte Marktseiten, Kalender in der täglichen Prüfung, TE-Commit (Ben, 20.11.2026)

PR #103, Kopf: `dcbe05f` auf `site/scope-und-termine`. Frist Mi 25.11. 16:00 Berlin.

## 1. „What does it cost?“ wird „How is it scoped?“

- **Geändert:** die Überschrift an der Quelle (`scripts/b2b_pages.py`) auf /tps-verification und /launch-measurement.
- **Absatz darunter, ohne Preis:**
  - /tps-verification: „Scoped per network and window. Ask for a quote. Longer windows or a measured testnet stress test are custom scope, on request.“
  - /launch-measurement: „Scoped per network and window. Ask for a quote.“

**Suche über alle 34 Seiten und llms.txt** nach cost, price, pricing, EUR, USD, $ und €. Durchsucht wurden der sichtbare Text, die Meta-Angaben und das Schema. „cost“, „pricing“, „EUR“, „USD“ und „$“ kommen nirgends mehr vor. Es bleiben diese Treffer:

| Seite | Treffer | Bewertung |
|---|---|---|
| /contact | Budgetspannen „Under 1,000 €“ bis „Over 15,000 €“ im Formular | kein Preis, die Spannen bleiben nach der Entscheidung vom 5.11. |
| /about | „The price is fixed in the offer, before the measurement starts“, Beschreibung „the price fixed before the first block“ | Grundsatz, kein Betrag |
| /independence | „The price never depends on the result“, Beschreibung und Schema „price fixed in advance“ | Grundsatz, kein Betrag |
| /launch-measurement | „Questions about price or market“ (passt nicht zu uns), FAQ „The price stays the same as long as the scope does.“ | kein Betrag; der erste Treffer meint Marktpreise |
| /tps-verification | „Questions about price or market“ | meint Marktpreise |
| /method | „No price statements“, „No price targets“, „We make no statements about prices.“ | meint Marktpreise |
| llms.txt | Beschreibungen von /independence und /about | wie oben |

## 2. Alte Marktseiten

**Liste aller Seiten dieser Art**, also der früheren DAY-Serie mit Bitcoin- und Marktinhalten:

| Seite | in der Sitemap | in der Navigation oder verlinkt | robots | live |
|---|---|---|---|---|
| /bitcoin-top-to-bottom | nein | nein | noindex, follow | Weiterleitung auf /method |
| /bitcoin-halving-to-top | nein | nein | noindex, follow | Weiterleitung auf /method |
| /markets | nein | nein | noindex, follow | Weiterleitung auf /method |
| /bitcoin-drawdown | nein | nein | noindex, follow | Weiterleitung auf /method |
| /bitcoin-bull-run-length | nein | nein | noindex, follow | Weiterleitung auf /method |
| /bitcoin-dominance | nein | nein | noindex, follow | Weiterleitung auf /method |
| /gold-in-bitcoin-bear-markets | nein | nein | noindex, follow | Weiterleitung auf /method |
| /what-if | nein | nein | noindex, follow | Weiterleitung auf /method |
| /archive | nein | nein | noindex, follow | Weiterleitung auf /method |

- Gilt jeweils mit und ohne `.html`.
- **Geprüft:**
  - die Sitemap mit ihren 18 Adressen;
  - die Navigation und der Fuß aller Seiten;
  - jeder Link in allen 34 Seiten und in llms.txt.
- **Ergebnis:** Keine Seite verlinkt eine dieser Adressen.

**Dein Vorschlag ist schon umgesetzt, deshalb gibt es keinen eigenen PR.**
- Seit dem 27.10. haben alle neun Seiten noindex, stehen nicht in der Sitemap und nicht in der Navigation.
- Erreichbar bleiben sie als Weiterleitung auf /method: Meta-Refresh 0 mit canonical auf /method (`WEITERLEITUNGEN` in `b2b_pages.py`, wie in CLAUDE.md festgelegt).
- Dass sie in der Search Console vom 18.11. noch die meisten Impressionen holen, liegt sehr wahrscheinlich am Zeitraum. Der Standardbericht deckt drei Monate ab, also vor allem die Zeit vor dem 27.10. Google nimmt Adressen mit noindex erst nach dem nächsten Abruf aus dem Index.
- Bis zum 16.12. sollte der Anteil deutlich sinken.

**Daten derselben Herkunft, keine Seiten:** Die Bots „marktlog“, „365 days later scan“ und „langzeitarchiv“ schreiben täglich in `data/`.
- Die Dateien sind live abrufbar, zum Beispiel `/data/market-log.json`, `/data/multibagger-scan.json` und `/data/history.json`.
- Sie sind keine HTML-Seiten und stehen in keiner Sitemap. Für die Search Console spielen sie kaum eine Rolle. Siehe Frage 2.

## 3. Abgelaufener scheduled-Termin in der täglichen Prüfung

- `scripts/datiert.py --pruefen` liest jetzt auch `data/upgrades.json`.
- **Was gemeldet wird:** Jeder Eintrag mit Status scheduled und einem Datum vor heute geht als eigene Meldung „kalender GELB“ nach #ops-log.
- **Inhalt der Meldung:**
  - Chain, Netz, Ereignis, ID, Termin und wer bestätigen muss;
  - ob `upgrades.html` die Zeile noch als scheduled führt, dann steht dabei „seiten neu bauen“.
- **Was sich nicht ändert:** Der Exit-Code hängt weiter nur an der Frische, und eine Workflow-Änderung war nicht nötig.
- **Selbsttest:** 15 Fälle, davon 5 neu:
  - Seite alt;
  - Seite neu gebaut;
  - ohne Seite;
  - am Tag selbst;
  - Meldetext.
- **Probe heute ohne Senden:** „pulsehawk.io kalender GELB: 1 termin(e) vorbei ohne bestaetigung … Bitcoin Cash testnet, May 2027 network upgrade (bch-2027-chipnet), termin 15 November 2026 vorbei, BCHN hat nicht bestaetigt. upgrades.html zeigt awaiting confirmation.“
- **Folge:** Ab morgen 07:17 UTC steht diese Meldung täglich in #ops-log, bis der Chipnet-Eintrag bestätigt ist.

## 4. TE_QUELLE und der erste Commit

**Stand vor der Stufe:**
- Der Workflow „track record events“ lief sechsmal grün, zuletzt am 20.11. um 08:41 UTC.
- TE_QUELLE ist gesetzt und lesbar. Das Log meldet „nichts neu“, weil die Quelle bisher nur eine Vorschau und noch keine Prognose enthält.
- Die Quelle ist der Zustand des Prognoselaufs auf dem Datenbranch `messung/kaspa-reward` in kaspa-pulse.

**Wann die Stufe kommt:**
- Der Prognoselauf läuft um 03:41 und 15:41 UTC.
- Er veröffentlicht eine Stufe, sobald ihr Zeitpunkt in den nächsten 12 h liegt.
- Bei einem Median am 5.12. um 00:21 UTC ist die 14-Tage-Stufe um etwa 21.11. 00:21 UTC fällig. Sie kommt also voraussichtlich mit dem Lauf am 20.11. um 15:41 UTC.

**Probe des Commit-Pfads ohne Commit, mit einer Probe-Prognose im Format der Quelle:**
- `te_sync` meldet „neu: prognose 14d“.
- `b2b_pages` baut ohne Funde, `b2b_check track-record.html` ist grün, `secret_scan --baum` findet nichts.
- /track-record zeigt „Forecast 14 days before 5 December 2026, 00:21 UTC, published … with a lead of …, 80% band …, 95% band …“.

**Der Commit auf main wird nachgetragen, sobald der Lauf ihn gemacht hat.**

## Prüfungen

- `b2b_pages.py`: 0 von 25 Seiten mit Funden.
- Selbsttests:
  - `b2b_check` 0 von 32 Fällen falsch;
  - `datiert` 0 von 15;
  - `ops_melden` 0 Fehler;
  - `te_sync` 5 von 5.
- pyflakes ist sauber, der Secret-Scan findet nichts.

## Merge

Selbst-Merge nach der Regel vom 26.10. Geändert sind nur `scripts/b2b_pages.py`, `scripts/datiert.py`, die neu gebauten Seiten und dieser Bericht. Keine Datei unter `.github/workflows/`, kein `deploy/`, kein c2, kein Bezug zu Secrets.

## Offene Fragen an Ben

1. Die Kalendermeldung kommt jeden Tag, solange ein Termin unbestätigt ist. Reicht das, oder soll sie nur am ersten Tag und dann wöchentlich kommen?
2. Sollen die Bot-Daten unter `data/` (market-log, multibagger, history) weiter öffentlich auf pulsehawk.io liegen? Wenn sie nur für interne Läufe gedacht sind, kann `_config.yml` sie ausschließen. Das wäre eine Entscheidung von dir, weil ein Bot sie vielleicht über die Website liest.

## Was Ben tun muss

- Die zwei Fragen beantworten.
- Am 16.12. in der Search Console nachsehen, ob die Impressionen der alten Adressen gesunken sind.

## Selbst-Merge und Abnahme (20.11.2026)

- **Merge:** PR #103 per Squash, Merge-Commit `7114e41`, Branch gelöscht.
- **Live auf pulsehawk.io, byte-gleich mit dem Bau aus `7114e41`:** /tps-verification, /launch-measurement und die Startseite. „What does it cost?“ kommt auf keiner der drei Seiten mehr vor.
- **Abschnitt „How is it scoped?“ bei 390 und 1440 px:**
  - /tps-verification: „Scoped per network and window. Ask for a quote. Longer windows or a measured testnet stress test are custom scope, on request.“
  - /launch-measurement: „Scoped per network and window. Ask for a quote.“
- **Im Browser:** kein waagerechtes Scrollen, keine JS-Fehler.
- **Aufnahmen:** 4 Stück (`*-scope-*-live.png`) in `berichte/2026-11-20-scope-marktseiten-termine/`.
- **Kalendermeldung:** Sie geht ab dem nächsten Lauf der täglichen Prüfung (07:17 UTC) nach #ops-log.
- **TE-Commit:** noch offen, die Zeile folgt.
