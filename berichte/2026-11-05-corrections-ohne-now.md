# Folge-PR zu #54: Textregel ohne Echtzeitwörter (Ben, 5.11.2026)

## Was gemacht wurde

- **`scripts/b2b_pages.py`:**
  - Auf /corrections heißt das Feld "What stands now" jetzt "Corrected to".
  - Auf /independence steht "the corrected text and who reported it" statt "what stands now and who reported it".
  - **Description von /corrections:** "what stands now and who reported it" ist ebenso ersetzt. Die Description wäre damit 158 Zeichen lang, über der Grenze von 155. Deshalb fehlt jetzt das Wort "published": "Every correction to a PulseHawk page, dated. What was wrong, the corrected text and who reported it. Found an error? Write to us and we add it here." (148 Zeichen). Diese Description steht auch in llms.txt.
  - **Datum:** lastmod und dateModified von /corrections und /independence sind der 5.11.2026 (`KORR_STAND`).
- **Neu gebaut:** corrections.html, independence.html, llms.txt und sitemap.xml.
- **`data/corrections.json`:** Der Schlüssel `now` bleibt, wie du gesagt hast.
- **`scripts/b2b_check.py`:**
  - "now" steht jetzt in der Liste der Echtzeitwörter. "live" stand schon darin.
  - Beide sind im sichtbaren Text als ganzes Wort rot, Wortteile wie "known" oder "delivered" nicht.
  - Der Selbsttest hat einen Fall mehr, der beide Wörter und beide Wortteile enthält.

## Prüfungen

- `b2b_pages.py`: 0 von 24 Seiten mit Funden. Keine andere Seite enthielt "now" oder "live".
- `b2b_check.py --selbsttest`: 0 von 19 Fällen falsch.
- `report_waechter.py --selbsttest`: 0 von 55 Fällen falsch.
- pyflakes und `secret_scan.py --staged` ohne Fund.

## PR

#61. Keine Workflows, kein deploy, kein c2, kein Secrets-Bezug, daher Selbst-Merge nach der Regel vom 26.10.

## Offene Fragen an Ben

Keine neuen. Die offenen Fragen 1, 2 und 4 bis 6 aus `berichte/2026-11-04-glaubwuerdigkeit.md` bleiben offen.

## Was Ben tun muss

Nichts. Die Abnahme auf pulsehawk.io folgt nach dem Merge als Zeile in diesem Bericht.
