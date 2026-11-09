# Upgrade-Seiten schlank auf Strategie v2 (Auftrag Ben 9.11.2026, Frist Fr 13.11. 18:00)

**Kopf:** Seiten, Code und Daten in `ffeb533` auf `site/upgrade-seiten-v2`, auf main nach `3584439`. Fertig am 9.11.2026. **Ben merged.**

Keine neue Seite. Die Adressen /upgrades und /upgrade-monitoring bleiben.

## 1. data/upgrades.json (Stand 9.11.2026, vorher 27.10.)

### Geprüft am 9.11.2026

- **Zebra (Zcash):** Release Notes 7.0.0-rc.0 und 7.0.0.
- **Ethereum:** EIP-7773 (raw auf GitHub).
- **Monero:** seraphis-migration/monero Releases (Stressnet v3.0 und v3.1) und der Meilenstein fcmp++ hf, ohne Fälligkeitsdatum.
- **Avalanche:** AvalancheGo v1.15.0.
- **BNB Chain:** bsc v1.8.1 und v1.8.2.
- **Bitcoin Cash:** BCHN v29.2.0.
- **Wie geprüft:** Die GitHub-Webseiten sind aus dieser Umgebung gesperrt. Ein Abruf-Agent hat sie gelesen und wörtlich zitiert, den Rest habe ich über raw-Dateien und die GitLab-API selbst geprüft.

Jeder Eintrag hat `checked` 2026-11-09.

### Änderungen

- **zcash-nu7-mainnet:**
  - status activated, Datum 6.11.2026, in der Datumsspalte "02:34:02 UTC by header time, block 3,543,405, counted".
  - measured_by_us true.
  - Verlinkt sind der NU7-Report (/reports/zcash-nu7) und /track-record.
  - Die alte Notiz mit der Zakura-Schätzung ist raus.
- **Bitcoin Cash, May 2027 network upgrade, neu mit zwei Einträgen:**
  - Quelle ist Bitcoin Cash Node v29.2.0 (Release 1.10.2026), `src/chainparams.cpp`.
  - Mainnet: `upgrade2027ActivationTime = 1810382400`, also erster Block mit Median-Zeit ab 15.5.2027 12:00 UTC.
  - Chipnet: `1794744000`, also 15.11.2026 12:00 UTC, "activates 6 months early".
  - BCHN nennt beides "tentative".
- **bnb-jenner-mainnet:** bsc v1.8.2 setzt Jenner auf dem Mainnet für 8.12.2026, 02:30 UTC (1796697000). Status jetzt scheduled, vorher proposed ohne Datum.
- **bnb-jenner-chapel:** Das Datum 29.10.2026, 02:30 UTC ist vorbei, Status jetzt activated. Das gleiche Vorgehen gilt bereits für Avalanche Helicon.
- **solana-alpenglow-mainnet: entfernt.** SIMD-0326 steht am 9.11. nicht mehr im Agave Feature Gate Tracker, weder im Wiki noch in der raw-Fassung. Ohne Projektquelle bleibt der Eintrag nach der Regel draußen.
- **Neues Feld `time_note`:** Uhrzeit und Bezug hinter dem Datum, etwa "12:00 UTC by median time past". Neues Feld `links`: weitere Belege neben `case`.
- **Ergebnis:** 12 Einträge, alle mit Quelle vom Projekt.

## 2. /upgrade-monitoring heißt "Upgrade readiness and network health"

- **Titel und Überschrift:** Title, H1, Description (150 Zeichen), Schema-Service und OG-Bild sind neu. Die Navigation heißt jetzt "Upgrade readiness", ebenso die Leistungszeile auf der Startseite und der Link auf /upgrades.
- **"What do you get?" mit vier Bausteinen:**
  - **Readiness:** Anteil der Peers auf der neuen Version beim Handshake, dazu eine Aktivierungsprognose mit 80-%- und 95-%-Band.
  - **Watch:** von 24 Stunden vor bis 72 Stunden nach der Aktivierung, Alarm an eine benannte Person.
  - **Report after the upgrade:** Upgrade Report nach der veröffentlichten Spezifikation, mit Rohdaten und Befehlen.
  - **Monthly network health.**
- **"What have we shown so far?":**
  - NU7 (ZIP 259) wurde bei Block 3,543,405 am 6.11.2026 um 02:34 UTC aktiviert, counted.
  - "Four of four published forecasts landed inside their 90% band" mit Link auf /track-record. Die Zahl kommt aus dem Track Record, nicht von Hand.
  - Link auf den Upgrade Report PH-UR-2026-001.
- **"How do we stay independent?":** drei Sätze und ein Link auf /independence:
  - "We publish the method before anyone pays."
  - "A result is never changed for the client who paid for it."
  - "Every report names who paid."
- **"How do we start?":** hello@pulsehawk.io mit dem Betreff "scope for <network> upgrade" als mailto-Link mit vorbelegtem Betreff. Kein Formular, keine Preise, kein now oder live.
- **Entfernt:** die alten Abschnitte "What do we compare", "How does ongoing measurement work?", "What does it cost?" und "Is it the right fit?" sowie die Knöpfe "See a sample report" und "Request a measurement", die aufs Formular führen.
- **FAQ:** Die drei Fragen bleiben (Vorlauf, Testnet, Kalender).

## 3. Prüfungen

- **Textregeln:** `b2b_pages.py` 0 von 24 Seiten mit Funden. Das deckt Gedankenstriche, Doppelpunkte, Pfeile, Beträge, now und live, estimate, Spec-Nummer und Abschnittslänge ab.
- **Selbsttests:** `b2b_check.py --selbsttest` 22 von 22, `report_waechter.py --selbsttest` 55 von 55.
- pyflakes und Secret-Scan ohne Fund.
- **Links:** Alle internen Links beider Seiten zeigen auf vorhandene Seiten. Die externen Quellen habe ich am 9.11. geprüft (siehe oben).
- **Datum:** lastmod und Schema von /upgrade-monitoring und /upgrades sind der 9.11.2026.
- **Screenshots** 390 und 1440 px beider Seiten in `berichte/2026-11-13-upgrade-seiten-v2/`, kein waagerechtes Scrollen.

## Offene Fragen an Ben

1. **Lock-in 15.11.2026:** Eine offizielle Quelle für den Begriff "Lock-in" habe ich nicht gefunden. BCHN nennt für den 15.11.2026 nur die Aktivierung auf Chipnet, und so steht es im Kalender. Bitte eine BCHN- oder Spezifikationsquelle schicken, falls "lock-in" sichtbar sein soll. bitcoincashresearch.org ist von hier gesperrt.
2. **Der Report PH-UR-2026-001** zeigt weiter "pending first numbers". Die Seite verlinkt ihn als Beleg. Die Mainnet-Daten liegen in pulsehawk/methods (PR 5). Soll ich den Report vor dem Merge bauen, oder macht das die Zcash-Sitzung?
3. **Bandbreiten:** Die Seite verspricht für Readiness ein 80-%- und ein 95-%-Band, unsere NU7-Prognosen hatten ein 90-%-Band. Der Beleg-Satz sagt deshalb "90% band". Ist das so richtig?
4. **Alpenglow:** Soll der Eintrag zurückkommen, sobald Solana ein Mainnet-Epoch nennt?

## Was Ben tun muss

- PR prüfen und mergen. Danach nehme ich /upgrade-monitoring und /upgrades auf pulsehawk.io ab und trage das hier ein.
