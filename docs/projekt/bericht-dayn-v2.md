# DAY-N-Post v2: Bericht vor dem Livegang

Branch `claude/dayn-post-v2`, Stand 17.09.2026.
**Nichts davon ist live.** Nichts ist nach main gemergt. Alle Commits tragen
`[skip ci]`, damit `automerge-claude.yml` gar nicht erst anspringt.
`dayn.yml` merged Ben von Hand.

Belege, auf denen alles steht: `docs/projekt/befund-shares.md`.

---

## 1. Der Posttext fuer heute, Tag 344 (Fall A)

263 von 280 Zeichen. Sperrschluessel `dayn-2026-09-16`.

```
day 344.

the three completed cycles bottomed on day 406, 364 and 378, counted from daily closes, never intraday highs.

the earliest low of the last three cycles came on day 364. that is 20 days from here.

we count this every day. we never predict the next one.
```

Selbstantwort, eigener Beitrag darunter, traegt den Link:

```
the whole count, every cycle on the same day number: pulsehawk.io/bitcoin-top-to-bottom.html
```

Bild: `docs/projekt/vorschau/day-n-tag344.png`

## 2. Trockenlauf Tag 364 (Fall B, die staerkste Fassung)

208 Zeichen.

```
day 364.

the three completed cycles bottomed on day 406, 364 and 378, counted from daily closes, never intraday highs.

we are inside that window now.

we count this every day. we never predict the next one.
```

Bild: `docs/projekt/vorschau/day-n-tag364.png`

## 3. Trockenlauf Tag 420 (Fall C)

257 Zeichen.

```
day 420.

the three completed cycles bottomed on day 406, 364 and 378, counted from daily closes, never intraday highs.

all three previous cycles had already found their low by now. this one has not.

we count this every day. we never predict the next one.
```

Bild: `docs/projekt/vorschau/day-n-tag420.png`

Nachzustellen mit:

    python3 scripts/day_n_post.py --dry-run
    python3 scripts/day_n_post.py --dry-run --tag 364
    python3 scripts/day_n_post.py --dry-run --tag 420

`--tag` gibt es nur fuer den Trockenlauf; mit `--post` bricht es ab.

---

## 4. Drei Entscheidungen, die Ben abnicken oder umstossen sollte

### 4.1 Der Kurs und der Rueckgang stehen nicht mehr im Hauptpost

Die Bauform hat vier Bloecke, und Zeile 2 ist laut Auftrag das Gegenstueck
mit den **Referenzwerten**, also 406, 364 und 378. Damit ist "bitcoin closed
at 76,070" und "39.0 percent below the top" aus dem Post verschwunden. Der
Post traegt jetzt nur noch Tage, keinen Kurs.

Das ist die wortgetreue Umsetzung des Auftrags und passt zum Befund: ein
Verlust allein ist der einzige gemessene negative Faktor (-16 %). Wenn der
Kurs trotzdem wieder hinein soll, ist der Platz dafuer die Selbstantwort,
und dann muss dort die Wendung mitstehen, sonst greift die
Traurigkeitsregel und der Lauf bricht ab. Eine Zeile Aenderung, sag Bescheid.

### 4.2 Die Quellzeile haengt an Zeile 2

"counted from daily closes, never intraday highs" bleibt laut Punkt 6, die
Bauform hat aber nur vier Bloecke. Sie steht deshalb als Nachsatz in Zeile 2,
weil dort die historische Aussage steht, die sie qualifiziert. Im Bild steht
sie zusaetzlich klein unten, wie verlangt. Wer sie lieber als fuenften Block
haette, sagt es; dann hat der Post fuenf Bloecke.

### 4.3 Die Kosten verdreizehnfachen sich

| | vorher | jetzt |
| --- | ---: | ---: |
| Hauptpost, ohne Link | 0,015 $ | 0,015 $ |
| Selbstantwort, mit Link | - | 0,200 $ |
| **am Tag** | **0,015 $** | **0,215 $** |
| **im Monat** | **rund 0,46 $** | **rund 6,45 $** |

Das ist der Preis dafuer, dass der Link dem Hauptpost nicht mehr 50-90 %
Reichweite nimmt. Er steht so im Auftrag und ist so gebaut. Falls das den
Spend Cap zu nah an die Kante bringt: die Selbstantwort nur montags zu
posten kostet rund 1,30 $ im Monat und ist eine Zeile in `dayn.yml`.

---

## 5. Was gebaut wurde

| Datei | was |
| --- | --- |
| `scripts/day_n_post.py` | neu gebaut: vier Bloecke, Wendung aus den Daten, Traurigkeitsregel, Selbstantwort, Bildpflicht |
| `scripts/day_n_cover.py` | neu: das 4:5-Pflichtbild |
| `.github/workflows/dayn.yml` | Sendezeit 12:30 UTC, Pillow, Reparatur 1 und 2 |
| `docs/projekt/befund-shares.md` | die Belege |
| `.gitignore` | `build/` haelt das Laufzeitbild aus dem Repo |

### Die Wendung kommt aus den Daten

`wendung(n)` vergleicht die heutige Zahl mit der Referenzmenge und waehlt
danach die Vorlage. Die Vorlagen stehen als Tabelle in `WENDUNGEN`:

| Fall | Bedingung | Satz |
| --- | --- | --- |
| A | `n < 364` | "the earliest low of the last three cycles came on day 364. that is N days from here." |
| B | `364 <= n <= 406` | "we are inside that window now." |
| C | `n > 406` | "all three previous cycles had already found their low by now. this one has not." |

Trifft keine Bedingung, gibt es keine Wendung, und der Lauf bricht ab mit
"lieber kein post als ein flacher". Erreichbar ist dieser Ausgang ueber eine
leere oder kaputte Referenzmenge; der Selbsttest fuehrt ihn vor.

### Die Referenzmenge ist nachgerechnet, nicht geraten

`ZYKLEN` in `day_n_post.py` traegt Hoch, Tief, Tagesabstand und Schluss im
Tief. Der Selbsttest rechnet alle drei Zeilen bei jedem Lauf neu aus
`data/history.json` nach: tiefster Tagesschluss zwischen zwei Zyklushochs.

| Zyklus | Hoch | Tief | Schluss | Tage |
| --- | --- | --- | ---: | ---: |
| 2013 to 2015 | 2013-12-05 | 2015-01-15 | 172,00 | 406 |
| 2017 to 2018 | 2017-12-17 | 2018-12-16 | 3.231,91 | 364 |
| 2021 to 2022 | 2021-11-09 | 2022-11-22 | 15.759,61 | 378 |

Stimmt eine Zahl nicht mehr, wird der Selbsttest rot und der Lauf postet
nicht. Dieselben drei Zahlen stehen auf `bitcoin-top-to-bottom.html`; auch
das prueft der Selbsttest.

### Die Traurigkeitsregel

`traurigkeitsregel(text, satz)` sucht `below, down, less, fell, lost` auf
Wortgrenzen ("unless" ist kein "less", "downtown" kein "down"). Findet sie
eines und fehlt die Wendung im selben Post, bricht der Lauf ab. Geprueft
werden Hauptpost UND Selbstantwort. Die Selbstantwort traegt keine Wendung
und darf deshalb ueberhaupt kein Verlustwort tragen; das ist Absicht und
der Grund, warum dort kein Kurs steht.

### Das Bild

`scripts/day_n_cover.py`, 1080 x 1350 (4:5), Farben aus `:root` der Seite.
Enthaelt die Zahl gross, die drei Referenztage als Marken auf einer Achse
mit dem Fenster als Band, die heutige Position in Teal, die Wendung als
Satz darunter und die Quelle klein. Die Achse waechst mit: in Fall C wandert
die Marke nach rechts aus dem Band heraus, statt aus dem Bild zu laufen.

Findet das Skript keine TrueType-Schrift, bricht es ab, statt die
Bitmap-Notschrift zu nehmen. Eine zerbroeselte Zahl ist schlimmer als kein
Post. `day_n_post.py` postet nicht, wenn das Bild fehlt.

Einzige Fremdbibliothek im Repo: Pillow, fest auf 12.3.0 angeheftet, nur
fuer das Bild. `dayn.yml` installiert sie.

### Selbsttests

    python3 scripts/day_n_post.py --selftest     # 0 faelle falsch
    python3 scripts/day_n_cover.py --selftest    # 0 von 15 faellen falsch

---

## 6. Die Sendezeit

Alt: `cron: "52 21 * * *"`, also **21:52 UTC = 23:52 Berlin**.
Neu: `cron: "30 12 * * *"`.

    12:30 UTC = 14:30 Berlin (CEST, Sommerzeit) = 08:30 New York (EDT)
    12:30 UTC = 13:30 Berlin (CET, Winterzeit)  = 07:30 New York (EST)

Die Berliner Zeit steht als Kommentar ueber der Cron-Zeile.

**Eine Korrektur zum Auftrag:** dort steht, der Lauf laufe um 01:53. In der
Datei stand 21:52 UTC, und der Post vom 16.09. ist laut
`data/x-post-log.json` um 10:16 UTC rausgegangen, also von Hand oder aus
einer Sitzung, nicht aus dem Zeitplan. Am Befund aendert das nichts, die
Zeit war falsch. Falls es noch eine zweite Ausloesung um 01:53 gibt
(Routine ausserhalb dieses Repos), gehoert die mit abgeschaltet, sonst
postet der Tag zweimal. Die Sperre haelt den zweiten Lauf ab, aber dann zur
falschen Stunde.

Um 12:30 ist der juengste Schluss der von gestern Abend, also einen Tag alt.
Die Frischesperre (`--max-age 3`) greift davon unberuehrt.

---

## 7. Die drei offenen Reparaturen vom 17.09.

**1. Fehlgeschlagener X-Post faerbt den Lauf nicht mehr rot.** Erledigt.
`continue-on-error: true` am Schritt "day n posten". Damit der Fehlschlag
nicht still wird, schreibt ein neuer Schritt "fehlschlag melden" eine
`::warning::` und eine Zeile in die Job-Zusammenfassung.

**2. Das Sperrlog schreibt bei Fehlschlag nicht.** Erledigt.
`day_n_post.py` setzt `posted=true` in `$GITHUB_OUTPUT` genau dann, wenn
nach dem Lauf eine Post-ID unter dem Tagesschluessel im Log steht. Der
Schritt "sperrlog sichern" haengt jetzt an dieser Marke statt an
`always()`. Wichtiger Sonderfall, absichtlich so: geht der Hauptpost raus
und faellt nur die Selbstantwort aus, ist `posted` trotzdem `true` und das
Sperrlog wird committet. Sonst postet der naechste Lauf den Hauptpost ein
zweites Mal.

**3. `dayn.yml` in die 10:40-Pruefung.** NICHT erledigt, und zwar hier nicht
erledigbar. Eine 10:40-Pruefung gibt es in `pulsehawk-site` nicht; die
Zeitplaene in diesem Repo sind 04:17 und 21:40 (Seitenstempel), 21:23
(Marktlog), 05:10 (Scanner) und jetzt 12:30 (day n). Die Pruefung liegt
offenbar in `pulse-studio`, und dieses Repo dieser Sitzung nicht
zugaenglich zu machen war eine Berechtigungsfrage, die ich nicht selbst
entscheiden darf. Zwei Wege: entweder Ben traegt `pulsehawk-site/dayn.yml`
dort in die Liste ein, oder er gibt eine Sitzung fuer `pulse-studio` frei,
dann mache ich es in einem Zug.

---

## 8. Was unveraendert geblieben ist

- Keine Kursprognose, kein Kursziel. Die drei Wendungen behaupten nichts
  ueber die Zukunft; Fall C sagt ausdruecklich nur, was NICHT passiert ist.
- "counted from daily closes, never intraday highs" steht im Post und im Bild.
- Die Seiten-Stempelung ist unangetastet, `stamp_pages.py` und
  `stamp-pages.yml` sind nicht angefasst.
- Keine Datei unter `.github/workflows/` ausser `dayn.yml`.
- Die drei Sperren (Frische, Seite gegen Log, Doppelpost) sind unveraendert;
  dazu gekommen ist die vierte: ohne Wendung und ohne Bild geht nichts raus.

---

## 9. Was Ben jetzt tut

1. Die drei Texte oben lesen und die drei Bilder ansehen.
2. Die drei Entscheidungen aus Abschnitt 4 abnicken oder umstossen.
3. Wenn es passt: `claude/dayn-post-v2` von Hand nach main mergen.
   `automerge-claude.yml` kann das nicht, weil der Branch
   `.github/workflows/` anfasst, und das ist hier die richtige Bremse.
4. Danach einmal `workflow_dispatch` mit `dry_run = true`, um zu sehen,
   dass Pillow und die Selbsttests auf dem Runner durchlaufen, bevor der
   erste Zeitplan um 12:30 UTC greift.
5. Klaeren, ob es die zweite Ausloesung um 01:53 gibt (Abschnitt 6).
