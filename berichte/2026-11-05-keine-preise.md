# Keine Preise mehr öffentlich (Auftrag Ben, 5.11.2026)

Preise nennen wir nur noch im Angebot nach einem Gespräch.

## Was gemacht wurde

### Seiten

- **Startseite:** In den drei Leistungszeilen (".lp") steht statt des Preises "Scoped per network and window."
  - **Link auf /contact:** Jede Zeile ist selbst ein Link auf ihre Leistungsseite, und ein Link darf nicht in einem anderen Link stehen. Der Link auf /contact steht deshalb einmal direkt unter den drei Zeilen: "Custom scope, on request. Ask for a quote." Vorher stand dort "Prices as of October 2026 …".
- **/tps-verification, /launch-measurement, /upgrade-monitoring:** Der Preiskasten unter "What does it cost?" ist ersetzt durch "Scoped per network and window. Ask for a quote." mit Link auf /contact.
  - **Wegfall:** Damit entfällt auch "Prices as of October 2026, net, plus VAT …". Auf /upgrade-monitoring entfällt der Zusatz "priced like a launch measurement".
  - **Bleibt:** Der Satz zu längeren Fenstern auf /tps-verification und die FAQ-Antwort "The price stays the same as long as the scope does" auf /launch-measurement bleiben, sie nennen keinen Betrag.
- **/contact:** Die Budgetspannen im Formular bleiben.
- **/independence:** Die Regeln bleiben unverändert (bezahlte Messungen gekennzeichnet, Preis nie vom Ergebnis abhängig, im Angebot festgelegt, keine Client-Tokens).
  - **Hinweis:** Einen Satz "in EUR oder USD" gibt es auf /independence nicht. Dort steht nur, dass eine Zahlung im Token des Kunden beim Eingang umgetauscht wird.

### Schema, llms.txt, Sitemap, Generator

- **Schema:** Die drei Service-Einträge haben kein `offers` mehr, also kein Offer, kein price, kein priceCurrency und keine priceSpecification.
- **llms.txt:** "Services and prices …" mit Beträgen ist ersetzt durch "Services, each scoped per network and window. Ask for a quote at https://pulsehawk.io/contact" mit den Leistungen ohne Beträge.
- **Sitemap:** Sie hat keine Texte, nur `lastmod`. Das ist für die vier geänderten Seiten jetzt der 5.11.2026.
- **`scripts/b2b_pages.py`:** `PREISE`, `PREIS_STAND`, `preis_text()` und `preis_block()` sind entfernt. Neu sind `ANGEBOT_SATZ` und `angebot_html()`.
- **Gegenprobe:** Kein erzeugtes HTML, keine llms.txt und keine sitemap.xml enthält noch einen Betrag oder ein Preisfeld im Schema. Die einzige Ausnahme sind die Budget-Optionen auf /contact.
- **OG-Bilder:** Sie zeigen nur die H1 und enthalten keine Preise.

### b2b_check

- **Beträge:** Ein Betrag mit €, EUR, $ oder USD im sichtbaren Text, in Title, Description oder in Name, Description oder Headline des Schemas ist rot. Ausgenommen sind nur die Optionen des Budget-Felds (`select` mit "budget" in name oder id) auf /contact.
- **Schema:** Offer, price, priceCurrency, priceSpecification und minPrice sind dort rot.
- **Selbsttest:** ein neuer Fall mit drei Prüfungen.
  - Betrag auf einer anderen Seite: rot.
  - Betrag auf /contact außerhalb des Budget-Felds: rot.
  - Nur die Budget-Optionen auf /contact: grün.
- **Gegenprobe gegen die alten Seiten auf main:**

  | Seite | Funde |
  |---|---|
  | index.html | 1 |
  | tps-verification.html | 8 |
  | launch-measurement.html | 8 |
  | upgrade-monitoring.html | 8 |
  | contact.html | 0 |

## Prüfungen

- `b2b_pages.py`: 0 von 24 Seiten mit Funden.
- `b2b_check.py --selbsttest`: 0 von 20 Fällen falsch.
- `report_waechter.py --selbsttest`: 0 von 55 Fällen falsch.
- pyflakes und `secret_scan.py --staged` ohne Fund.
- **Lokal im Browser bei 390 und 1440 px:** kein Betrag im Seitentext. Der Satz steht auf der Startseite 3-mal, auf den drei Leistungsseiten je 1-mal, und auf jeder der vier Seiten gibt es einen Link "Ask for a quote" auf /contact. Kein waagerechtes Scrollen.

## PR

#63. Keine Workflows, kein deploy, kein c2, kein Secrets-Bezug, daher Selbst-Merge nach der Regel vom 26.10.

## Offene Fragen an Ben

- Soll die Überschrift "What does it cost?" auf den drei Leistungsseiten bleiben? Die Antwort darunter ist jetzt "Scoped per network and window. Ask for a quote."

## Was Ben tun muss

Nichts. Die Abnahme auf pulsehawk.io bei 390 und 1440 px folgt nach dem Merge als Zeile in diesem Bericht.
