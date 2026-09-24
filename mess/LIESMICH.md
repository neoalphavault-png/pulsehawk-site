# mess/ — Messlaeufe, kein Seiteninhalt

## ⚠️ DIESER BRANCH WIRD NIE GEMERGT. DAS IST ABSICHT.

`mess/ma-linien-2026-09-23` sammelt Rechenskripte, mit denen wir vor einer
Entscheidung nachsehen, was in den eigenen Daten steht. Sie bauen nichts,
schreiben nichts und veraendern kein Archiv. Sie rechnen und drucken.

Der Branch existiert, damit die Rechnungen nicht verloren gehen und
jemand sie in einem halben Jahr noch einmal laufen lassen kann. Er ist
kein Vorschlag fuer main.

## ⚠️ DER DIFF GEGEN MAIN IST GROSS, UND DAS IST KEIN VERSEHEN

Am 24.09.2026 wurde `pages/gold-2026-09-24` in diesen Branch gemergt.
Grund: `mess/rueckschlaege.py` braucht
`market_log.reihe_mit_logvorrang()`, und die Funktion liegt dort. Ohne
den Merge haette das Skript die Vorrangregel — Marktlog gewinnt am
rechten Rand — ein drittes Mal kopieren muessen, und genau das sollte
die Funktion ja beenden.

Der Branch traegt deshalb die ganze Seitenarbeit als Unterbau. Das sieht
im Vergleich mit main nach viel aus.

**Nicht "aufraeumen".** Wer den Unterbau herausrebast, nimmt den
Skripten ihre Grundlage. Wenn `pages/gold-2026-09-24` in main ist, loest
sich das von selbst: dann steht die Funktion ohnehin in main, und ein
frischer Messbranch von main aus braucht den Merge nicht mehr.

## Was hier liegt

| Datei | Frage | Stand |
|---|---|---|
| `ma_linien.py` | Gleitende Durchschnitte: SMA50d, SMA200d, SMA200w | 23.09.2026 |
| `gold_in_baermaerkten.py` | Was GLD und SPY in Bitcoins Zyklusfenstern taten | 23.09.2026 |
| `rueckschlaege.py` | Rueckgaenge innerhalb der Bullenmaerkte, ab Schwelle | 24.09.2026 |

Jedes Skript hat `--selftest`. Die Definitionen stehen im Kopf der
jeweiligen Datei, damit spaeter niemand raten muss, was genau gezaehlt
wurde.
