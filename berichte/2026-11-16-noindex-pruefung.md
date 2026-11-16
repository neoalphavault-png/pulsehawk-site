# noindex-Prüfung (Ben, 16.11.2026)

Anlass: Die Google Search Console meldet neue Seiten mit „Durch noindex-Tag ausgeschlossen“.

Geprüft wurde main auf Stand `e925455`, dazu jede Seite live auf pulsehawk.io.

## Ergebnis

- **Keine öffentliche Seite trägt noindex.** Startseite, /track-record, /zcash-nu7, /upgrades, /upgrade-monitoring, /reports/ und alle anderen Inhaltsseiten stehen auf `index, follow`, auf main wie live. Ein Korrektur-PR war nicht nötig.
- **Kein Header setzt noindex.** Keine der 34 Seiten liefert live einen `X-Robots-Tag`. Eine Datei `_headers` gibt es nicht, und GitHub Pages setzt keine eigenen Robots-Header.
- `robots.txt` erlaubt alles und nennt die Sitemap.
- Die Sitemap enthält genau die 18 indexierbaren Seiten und keine der 16 noindex-Seiten.

## Die 16 Seiten mit noindex (Meta-Tag `noindex, follow`)

| Seite | Art | Gewollt? |
|---|---|---|
| /archive | Weiterleitung auf /method (frühere DAY-Serie, seit 27.10.) | ja |
| /bitcoin-bull-run-length | Weiterleitung auf /method | ja |
| /bitcoin-dominance | Weiterleitung auf /method | ja |
| /bitcoin-drawdown | Weiterleitung auf /method | ja |
| /bitcoin-halving-to-top | Weiterleitung auf /method | ja |
| /bitcoin-top-to-bottom | Weiterleitung auf /method | ja |
| /gold-in-bitcoin-bear-markets | Weiterleitung auf /method | ja |
| /markets | Weiterleitung auf /method | ja |
| /what-if | Weiterleitung auf /method | ja |
| /standard/anchor-verification/ | Spezifikation „planned“, Entwurf | ja |
| /standard/confirmation-depth/ | Spezifikation „planned“, Entwurf | ja |
| /standard/load-test/ | Spezifikation „planned“, Entwurf | ja |
| /standard/network-baseline/ | Spezifikation „planned“, Entwurf | ja |
| /standard/upgrade-report/v1-0 | Archivfassung v1.0 der Spezifikation, inhaltsgleich mit /standard/upgrade-report/ | ja, sonst doppelter Inhalt |
| /impressum | Rechtliches | siehe Frage 1 |
| /datenschutz | Rechtliches | siehe Frage 1 |

Die neun Weiterleitungen sind keine Inhaltsseiten. Es sind die Weiterleitungsseiten aus `b2b_pages.py` (`WEITERLEITUNGEN`), jeweils mit Meta-Refresh 0 und canonical auf /method. noindex gehört dort zum Aufbau, wie in CLAUDE.md beschrieben.

## Warum Google sie gerade meldet

Ich sehe die Search Console nicht. Wahrscheinlich hat Google Seiten neu gecrawlt, die über Links gefunden werden:
- die vier geplanten Spezifikationen und v1.0, verlinkt von /standard/;
- /impressum und /datenschutz, verlinkt aus dem Fuß jeder Seite, /datenschutz zuletzt am 13.11. geändert;
- die alten DAY-Adressen.

Steht in der Meldung eine Adresse, die oben fehlt, bitte schicken.

## Offene Fragen an Ben

1. **Impressum und Datenschutz** tragen noindex seit Beginn (`legal=True` im Generator). Sie sind öffentlich, aber weder Entwurf noch Fall- oder interne Seite. Ich habe sie nicht geändert.
   - Meine Empfehlung: so lassen. Gesetzlich nötig ist, dass die Seiten erreichbar sind, und das sind sie über den Fuß jeder Seite. In der Suche bringen sie nichts.
   - Willst du sie indexiert haben, ist das eine kleine Änderung im Generator.
2. **Die Archivfassung v1.0** könnte statt noindex auch ein canonical auf /standard/upgrade-report/ tragen. Dann zeigt die Search Console sie unter „Alternative Seite mit kanonischem Tag“ statt unter noindex. Inhaltlich ändert sich nichts. Soll ich das umstellen?

## Was Ben tun muss

Nichts, außer die beiden Fragen zu beantworten. Die gemeldeten Ausschlüsse sind gewollt und schaden der Indexierung der Inhaltsseiten nicht.
