# Zcash NU7 Mainnet, erste Woche nach der Aktivierung (11.11.2026)

Auftrag Ben 23.10.: nach der Aktivierung zwei Wochen lang jede Woche eine CSV. Das ist die erste Woche.

## Was gemacht ist

- **Stand und CSV:** `stand-2026-11-11.json` und `.md` und `zcash-mainnet-nu7-intervals-2026-11-11.csv` liegen auf `messung/zcash-mainnet` (Bot-Commit `53b2ee0`). Sie kamen aus dem geplanten Lauf 43023636571 von `zcash-mainnet.yml` am 11.11. um 12:49 UTC. Der Lauf war grün, ein Start von Hand war nicht nötig.
- **Abruf:** 12:52 UTC, Spitze 3.561.998, Köpfe geprüft auf Verkettung, Arbeit und Checkpoints.
- **Gegenprobe:**
  - Diesmal nur ein Peer, `/Zebra:7.0.0/` mit 500 von 500 gleich.
  - Ein zweiter Peer fand sich im Zeitbudget nicht.
  - Am Morgen (Lauf 42985902037) waren es zwei Peers mit je 500 von 500.
- **PH-Entwurf:** `ph-entwurf-zcash-mainnet.yml` lief grün (43024328743), der Entwurf ging mit HTTP 200 nach Discord.
- **Adressen:** In Stand, Markdown und CSV stehen keine IPs und keine Hostnamen. Die CSV hat nur Höhe, Zeitstempel und Abstand.
- **Veröffentlichung:** Die CSV kommt mit diesem PR nach `data/zcash-mainnet/` in pulsehawk-site, Ben merged.
- **Nachgerechnet:**
  - Aus der CSV selbst: 18.593 Abstände, Mittel 25,23 s, Median 17 s, p90 58,0 s, p99 116,0 s, längster 249 s. Das stimmt mit dem Stand überein.
  - Die ersten 250 Abstände sind Zeile für Zeile gleich wie in der CSV vom 6.11.

## Abstände gegen 25 s

Fenster: 6.11. 02:34 bis 11.11. 12:51 UTC, Abstände der Blöcke 3.543.406 bis 3.561.998. Werte aus unseren eigenen Köpfen, die berechnete Spalte gilt für exponentielle Abstände mit 25 s.

| | gezählt | berechnet |
|---|---:|---:|
| Abstände | 18.593 | |
| Mittel | 25,23 s | 25 s |
| Median | 17 s | 17,3 s |
| p90 | 58,0 s | 57,6 s |
| p99 | 116,0 s | 115,1 s |
| über 75 s | 4,95 % | 4,98 % |
| über 173 s | 0,108 % | 0,1 % |
| längste Lücke | 4 min 9 s, vor Block 3.543.445 am 6.11. um 03:11:24 UTC | etwa 4 min 20 s |
| negative Abstände | 0 | 0 |

## Einpendeln

- **Eingependelt:** ab Block 3.544.439, nach 1.034 Blöcken, etwa 8,4 Stunden nach dem ersten NU7-Block. Regel: Mittel über 100 Blöcke innerhalb von ±20 % von 25 s, gehalten über 1.000 Blöcke.
- **Schwierigkeit relativ zu vor NU7:**

  | Block | relativ |
  |---|---:|
  | NU7 + 1 | 0,794 |
  | + 10 | 0,767 |
  | + 100 | 0,504 |
  | + 1.000 | 0,321 |
  | + 5.000 | 0,326 |

  Bei gleicher Hashrate wäre ein Drittel zu erwarten (0,333).

## Vergleich zur Kurznotiz vom 6.11.

Die Kurznotiz zählte nur die ersten 250 Abstände nach NU7, also die Einpendelphase.

| | 6.11., 250 Abstände | 11.11., 18.593 Abstände |
|---|---:|---:|
| Mittel | 38,21 s | 25,23 s |
| Median | 25,0 s | 17 s |
| p90 | 85,1 s | 58,0 s |
| p99 | 162,6 s | 116,0 s |
| über 75 s | 13,2 % | 4,95 % |

Die längste Lücke ist in beiden dieselbe, 4 min 9 s vor Block 3.543.445.

## Zuhörer

Endstand aus `berichte/2026-11-10-zuhoerer-endstand.md` in kaspa-pulse, Fenster ab NU7 bis 8.11. 15:30 UTC:
- 52 von 8.609 Kettenblöcken abgehängt, das sind 0,60 %.
- 40 davon mit geholtem Kopf, alle mit Tiefe 1.
- Vor NU7 waren es 0 von 453.

Der Zwischenstand vom 8.11. (49 von 7.047) ist dadurch ersetzt.

## Zwei Punkte zum Discord-Entwurf

1. Er nennt die längste Lücke als „4 min“. Nach deiner Regel vom 8.11. hieße das „4 min 9 s“. Der Entwurf kommt aus dem alten `ph_entwurf.py`, das Minuten noch rundet.
2. Er vergleicht den Median 17,0 s mit „25.0 s in our run a week earlier“. Dieser Lauf war am 6.11., also vor fünf Tagen, und zählte nur 250 Abstände.

Den Entwurf habe ich nicht geändert, gepostet ist nichts.

## PR-Nummern

- dieser PR in pulsehawk-site (CSV und Bericht)

## Offene Fragen an Ben

1. Soll ich `ph_entwurf.py` auf min und s und auf den richtigen Vergleichstext umstellen, bevor am 18.11. die zweite Woche kommt?

## Was Ben tun muss

- Diesen PR prüfen und mergen.
- Den Entwurf in Discord ansehen, die zwei Punkte oben beachten.
