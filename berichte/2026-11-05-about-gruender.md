# /about: Gründer mit Porträt (Nachtrag Ben, 5.11.2026)

## Was gemacht wurde

- **Gründer:** `GRUENDER` in `scripts/b2b_pages.py` ist jetzt "Benjamin Alkanli". Damit ist die offene Frage 3 aus `berichte/2026-11-04-glaubwuerdigkeit.md` beantwortet. Der Gründer-Abschnitt auf /about erscheint, und der Bau warnt nicht mehr.
- **Bild `assets/about/founder.jpg`:**
  - quadratisch zugeschnitten, über die volle Bildbreite, oben ab der Bildkante, Kopf und Schultern mittig;
  - 800 × 800 px, JPEG progressiv, 113 KB (Qualität 90);
  - sonst keine Bearbeitung und kein Filter. Das Bild ist schwarzweiß und hatte drei gleiche Farbkanäle, deshalb ist es als Graustufen-JPEG gespeichert: optisch gleich, nur kleiner.
  - Ohne Metadaten. Das Original liegt nicht im Repo.
- **Quelle:** Hier kam das Porträt in 1570 × 2000 px an, nicht in 2023 × 2576. Das Seitenverhältnis ist gleich, für 800 × 800 reicht es.
- **/about:**
  - Das Bild steht neben dem Namen, 200 × 200 px angezeigt. Alt-Text: "Benjamin Alkanli, founder of PulseHawk". Darunter steht "Founder of PulseHawk".
  - Bei 390 px reicht die Breite nicht für Bild und Namen nebeneinander, dort steht der Name unter dem Bild.
  - Die Ecken sind wie bei den Karten der Seite per CSS gerundet (12 px). Die Datei selbst ist unverändert.
- **Schema:** schema.org Person mit `name`, `jobTitle` Founder, `worksFor` PulseHawk und `image` https://pulsehawk.io/assets/about/founder.jpg. AboutPage hat jetzt `mainEntity` die Person.
- **Datum:** lastmod und dateModified von /about sind der 5.11.2026.
- **Text:** Den Satz aus dem Platzhalter ("who runs the measurements and signs the reports") habe ich nicht übernommen, weil er nicht von dir kam. Es steht nur Name und "Founder of PulseHawk".

## Prüfungen

- `b2b_pages.py`: 0 von 24 Seiten mit Funden.
- `secret_scan.py --staged` ohne Fund.
- Screenshots 390 und 1440 px (in `berichte/2026-11-05-about-gruender/`), kein waagerechtes Scrollen.

## PR

#59 (Selbst-Merge nach deiner Regel vom 26.10.: keine Workflows, kein deploy, kein c2, kein Secrets-Bezug).

## Offene Fragen an Ben

- Soll auf /about ein Satz zu deiner Rolle stehen? Wenn ja, bitte den Wortlaut.

## Was Ben tun muss

- Nichts. Die Abnahme auf pulsehawk.io bei 390 und 1440 px folgt nach dem Merge als Zeile in diesem Bericht.

## Selbst-Merge und Abnahme (5.11.2026)

- **Merge:** PR #59 per Squash, Merge-Commit `2887de5`, Branch gelöscht.
- **pulsehawk.io/about:** live byte-gleich mit dem Bau.
- **Bild:** `/assets/about/founder.jpg` liefert 200, image/jpeg, 115.781 Byte, gleich der Datei im Repo.
- **Im Browser bei 390 und 1440 px:** Das Bild lädt mit 800 px Eigenbreite und wird 200 px breit gezeigt. Alt-Text "Benjamin Alkanli, founder of PulseHawk". Kein waagerechtes Scrollen.
- **Screenshots:** `about-live-390.jpg` und `about-live-1440.jpg` in `berichte/2026-11-05-about-gruender/`.
