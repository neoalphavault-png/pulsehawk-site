# ph_entwurf.py in min und s, Vergleich mit benanntem Fenster (Ben, 12.11.2026)

Kopf: `0256db1` auf `site/ph-entwurf-min-s`. Frist: vor der zweiten Woche am 18.11.

## Was gemacht wurde

1. **Dauern in h, min und s.**
   - `dauer()` rundet nicht mehr auf Minuten. Die Regel ist dieselbe wie auf der Seite (`datiert.dauer_text`).
   - Die längste Lücke auf Zcash-Mainnet nach NU7 (249 s) heißt jetzt „4 min 9 s“ statt „4 min“.
   - Die längste Lücke im BCH-Tempnet (20,863 s) heißt „5 h 47 min 43 s“.
2. **Vergleich mit benanntem Fenster.** „against … s in our run a week earlier“ ist weg.
   - Der Wertsatz nennt jetzt das Fenster des früheren Laufs und seine Zahl der Abstände, zum Beispiel BCH:
     „we counted a median block interval of 41.0 s over 37,764 intervals, against 40.0 s over 28,051 intervals in our window 15 oct 2026, 12:56 to 4 nov 2026, 09:58 utc.“
   - Bei Zcash-Mainnet kommen die Grenzen des Fensters aus den Kopfzeiten der Höhen im früheren Stand.
   - Der eigene Wert zählt jetzt ebenfalls Abstände („intervals“), nicht Blöcke. So passen beide Zahlen zueinander.
3. **Deutung „vorwoche“.** Auch hier stehen jetzt Fenster und Zahl statt „the seven days before“:
   „in the seven days to … utc the median rose to … s over … intervals, from … s over … intervals in the seven days to … utc.“
4. **Regelprüfung.** `regel_pruefen` lehnt zwei Dinge ab, bevor ein Entwurf entsteht:
   - Minuten ohne Sekunden;
   - Vergleiche wie „a week earlier“, „week before“ oder „last week“.

   Der Selbsttest prüft das mit drei neuen Verstößen, vier `dauer`-Fällen und einem guten Satz mit Fenster.

## Prüfungen

- `ph_entwurf.py --selbsttest`: 17 Verstöße erkannt, das gute Beispiel bleibt sauber, und alle 4 Deutungen bleiben sauber.
- `ops_melden.py --selbsttest`: 0 Fehler. Es nutzt dieselbe Regelprüfung.
- pyflakes ist sauber, der Secret-Scan findet nichts.
- Probeläufe ohne `--senden` mit den echten Daten aus `messung/bch-tempnet` (Stand 11.11.) und `messung/zcash-mainnet` (Stand 11.11.), Deutungen `luecke`, `p90` und `alt_ziel`. Alle Texte bestehen die Regelprüfung.

## Merge

Selbst-Merge nach der Regel vom 26.10. Geändert ist nur `scripts/ph/ph_entwurf.py`, kein Workflow, kein `deploy/`, keine c2-Datei, kein Secrets-Bezug.

## Offene Fragen an Ben

1. Der Zcash-Mainnet-Entwurf vergleicht gerade mit dem Stand vom 6.11. Das waren nur 250 Abstände direkt nach der Aktivierung, Median 25.0 s. Der Satz nennt das jetzt offen, aber der Vergleich trägt wenig. Ab dem Lauf am 18.11. ist der Stand vom 11.11. (18,593 Abstände) der Vergleich. Soll bis dahin lieber gegen die ideale 25-s-Kette verglichen werden?

## Was Ben tun muss

1. **kaspa-pulse nachziehen, vor dem 18.11.:**
   - Die Läufe für BCH (`ph-entwurf-bch.yml`) und Zcash-Mainnet (`ph-entwurf-zcash-mainnet.yml`) laufen in kaspa-pulse, mit deren Kopie von `scripts/ph/ph_entwurf.py`.
   - Bis heute waren beide Dateien gleich. In kaspa-pulse kann ich nicht schreiben.
   - Bitte die Datei aus pulsehawk-site nach dem Merge 1:1 nach kaspa-pulse übernehmen. Prüfsumme: sha256 beginnt mit `3b2638dcd175c294`.
   - Ohne diesen Schritt geht am 18.11. noch „a week earlier“ und „4 min“ raus.
