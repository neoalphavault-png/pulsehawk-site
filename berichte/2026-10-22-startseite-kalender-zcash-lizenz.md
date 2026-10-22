# Bericht 22.10.2026, Startseite, Kalender-Entwurf, Zcash-Lizenz

Auftrag von Ben vom 22.10.2026, drei PRs. Alle drei sind gemergt.

## Was gemacht wurde

### PR C, #30, Lizenzzeile auf /zcash-nu7 (gemergt)
- Unter dem CSV-Knopf steht: "Data from PulseHawk, licensed CC BY 4.0. Cite as PulseHawk (2026), Zcash NU7 testnet block intervals, cut-off 18 October 2026."
- Die CSV bleibt unverändert unter `data/zcash-nu7/zcash-nu7-testnet-intervals-2026-10-18.csv` (SHA-256 beginnt mit `c1cda3d7`). Unter `reports/` liegt keine zweite CSV.
- Fund dabei: #29 hatte `zcash-nu7.html` von Hand geändert. Ein Neubau mit `scripts/b2b_pages.py` hätte den CSV-Abschnitt und die `distribution` im Dataset gelöscht. Der Abschnitt steht jetzt im Generator.
- Ohne eigenen Auftrag mitgemacht:
  - Der Knopf trägt wieder die Klasse `plausible-event-name=CSV+Download`, die in #29 weggefallen war.
  - Das Dataset im JSON-LD nennt die Lizenz CC BY 4.0.

### PR A, #31, Bitcoin-Cash-Karte auf der Startseite (gemergt)
- Unter "Which networks have we measured?" steht eine dritte Karte "Bitcoin Cash Tempnet". Sie hat keinen Link, weil es noch keine Fallseite gibt. Sobald `cases/bitcoin-cash.html` existiert, setzt der Generator Link und "Read the Bitcoin Cash case" selbst.
- Die Zahlen stimmen mit der eigenen Zählung überein: kaspa-pulse, Branch `messung/bch-tempnet`, `data/bch/tempnet-2026-10-21.json`, Stand `0712804`. Das sind 7,572 Blöcke, Median 43.0 s, erwartet 41.6 s, erster Block am 15.10.2026. Die Startseite baut nicht aus diesen Daten, deshalb steht die Quelle am Generator.
- Ein Satz ist gegenüber der Vorlage umgestellt, auf "Up to 21 October, 7,572 blocks with a median gap of 43 s against 41.6 s expected." Sonst hätte ein Satz mit einer Ziffer begonnen.
- Das Raster hat jetzt 3 Spalten, unter 760 px eine. Geprüft bei 390, 768 und 1280 px, jeweils ohne waagerechtes Scrollen.

### PR B, #33, montags ein X-Entwurf aus dem Kalender (gemergt)
- `data/upgrades.json` hat je Eintrag das Feld `x_handles`. Gefüllt ist es nur, wo ich sicher war (siehe unten).
- `scripts/ph_kalender_post.py` baut aus den Einträgen der nächsten 14 Tage:
  - einen Posttext, höchstens 280 Zeichen nach X-Zählung und höchstens 4 Handles,
  - `antwort.txt` für die übrigen Handles,
  - eine Grafik in 1600x900.
- Ein Verstoß gegen die Textregeln bricht ab, dann geht nichts raus. Der Selbsttest besteht 48 von 48 Fällen.
- `.github/workflows/ph-kalender.yml` läuft montags um 06:00 UTC. Er schickt an Discord über das Secret `DISCORD_WEBHOOK_PH_DRAFTS` und postet nicht auf X. Ohne Termin in den nächsten 14 Tagen kommt nur eine kurze Meldung.
- Lokal gegen einen nachgestellten Webhook getestet. Die Webhook-URL erscheint in keiner Ausgabe.

### Neben #33 gemergt: #32 aus einer anderen Sitzung
`scripts/ph/ph_entwurf.py` und `.github/workflows/ph-entwurf-zcash.yml` überschneiden sich mit keiner Datei aus #30, #31 oder #33. Der Selbsttest von `ph_kalender_post.py` bleibt auf main grün.

## Prüfungen
- `b2b_check`: 0 von 13 Seiten mit Funden
- Seitenstempel-Selbsttest: 282 von 282
- Lighthouse lokal für `/` und `/zcash-nu7`: 100/100/100/100, Handy und Desktop
- Secret-Scan über alle Dateien: ohne Fund

## Offene Fragen an Ben
1. Stimmen die `x_handles` in `data/upgrades.json`? Eingetragen sind `@Zcash` und `@ZcashFoundation` (Zcash), `@ethereum`, `@monero`, `@avax` und `@solana`.
2. Soll es eine Fallseite `cases/bitcoin-cash.html` geben? Dann bekommt die Karte auf der Startseite ihren Link von selbst.

## Was Ben tun muss
1. Einmal von Hand starten: unter Actions "ph kalender entwurf", "Run workflow", Stichtag `2026-10-01`. Erwartet wird im Discord-Kanal ein Entwurf mit Monero und Ethereum, `post.txt` und der Grafik. Das zeigt vor Montag, ob Secret, Kanal und das Rendern auf dem GitHub-Rechner funktionieren. Aus der Claude-Umgebung ließ sich das nicht testen.
2. Die `x_handles` prüfen und ergänzen (Frage 1).
3. Ab Montag, 26.10., um 06:00 UTC kommt der Entwurf jede Woche. Mit dem heutigen Kalender wäre es die Meldung "kein Eintrag", weil alle datierten Einträge in der Vergangenheit liegen. Neue Termine mit Quelle machen ihn voll.
