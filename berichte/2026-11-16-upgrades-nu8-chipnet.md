# Upgrade-Kalender, Stand 16.11.2026: Zcash NU8 als proposed, BCH Chipnet unverändert (Auftrag Ben 16.11.2026)

**Kopf:** Daten, Generator und neu gebaute Seiten auf `daten/upgrades-nu8`, als PR an main. Fertig am 16.11.2026.

## Was gemacht wurde

- **Zcash NU8 neu:** Eintrag `zcash-nu8-mainnet` mit Status proposed. Quelle ist das Zcash-Forum, Thread 59124, ohne Höhe und ohne Datum, wie von dir vorgegeben. Die Seite zeigt „not set“.
  - Der Thread heißt „Vision for January 2027“. Er ist der Vorschlag eines Forumsteilnehmers für eine Liste von Änderungen in NU8, keine Spezifikation.
  - Den Zielmonat aus dem Thread übernehme ich nicht, weil kein Datum in den Kalender soll.
- **BCH Chipnet:** Den Eintrag `bch-2027-chipnet` lasse ich unverändert auf scheduled, weil die offizielle Quelle fehlt (siehe unten).
- **Generator:** Mit der neuen Zeile hätte der Tabellenabschnitt 262 Wörter gehabt, die Textregel erlaubt unter 250. Ich habe zwei Änderungen in `scripts/b2b_pages.py` gemacht.
  - Die Tabelle ist geteilt in „Which upgrades are coming?“ und „Which upgrades have activated?“.
  - Die Seite schreibt „last updated“ statt „checked on“. Ich habe nur die zwei Einträge dieses Auftrags neu geprüft, die übrigen tragen in `data/upgrades.json` weiter ihr Prüfdatum vom 9.11.
- **Prüfungen:** `b2b_check.py` meldet 0 von 25 Seiten mit Funden, der Selbsttest 0 von 26 Fällen falsch. `ph_kalender_post.py` besteht seinen Selbsttest, und es gibt keinen Entwurf, weil in den nächsten 14 Tagen kein Termin ansteht. Der Secret-Scan ist sauber.

## Was beim Chipnet fehlt

Ich finde keine offizielle Bestätigung, dass das Upgrade am 15.11. aktiviert hat.
- **Release:** Bitcoin Cash Node hat nach v29.2.0 vom 1.10. kein Release veröffentlicht.
- **Commits:** Der letzte Commit auf master ist vom 12.11.
- **Quellcode:** In `src/chainparams.cpp` für Chipnet steht weiter „tentative protocol upgrade“ mit der Aktivierungszeit 1794744000. Es gibt keine Aktivierungshöhe und keinen Checkpoint nach dem 15.11. Bei den früheren Upgrades kamen beide später dazu, etwa `upgrade12Height`.
- **Spezifikation:** Die Seite der Upgrade-Spezifikation ist aus dieser Sitzung gesperrt. Das habe ich nicht umgangen.

## PR-Nummern

- dieser PR in pulsehawk-site

## Offene Fragen an Ben

1. Reicht dir für den Chipnet-Status eine BCHN-Quelle mit Aktivierungshöhe, sobald sie erscheint? Oder soll ich den Eintrag schon mit unserer eigenen Zählung als „measured by us“ führen? Die Zählung haben wir, die Quelle verlangt die Regel aber vom Projekt.
2. Die Kalenderregel verlangt eine Quelle vom Projekt selbst, der NU8-Eintrag nennt einen Forumsbeitrag. Soll ich die Quelle auf den ZIP oder die Ankündigung umstellen, sobald es eines davon gibt?

## Was Ben tun muss

- Die zwei Fragen beantworten.
