# Zcash NU7 Mainnet, zweite und letzte Woche der CSV (18.11.2026)

Auftrag Ben 23.10.: nach der Aktivierung zwei Wochen lang jede Woche eine CSV. Das ist die zweite und letzte.

## Was gemacht ist

- **Stand und CSV:** `stand-2026-11-18.json` und `.md` und `zcash-mainnet-nu7-intervals-2026-11-18.csv` liegen auf `messung/zcash-mainnet` (Bot-Commit `f37e69b`). Sie kamen aus dem geplanten Lauf 44322519990 von `zcash-mainnet.yml` am 18.11. um 14:16 UTC. Der Lauf war grün, ein Start von Hand war nicht nötig.
- **Abruf:** 14:19 UTC, Spitze 3.586.394, 96.678 Köpfe. Geprüft sind Verkettung, Arbeit gegen nBits und 219 Zebra-Checkpoints.
- **Gegenprobe:** zwei Peers, `/Zakura:1.8.9/` und `/Zebra:7.0.0/`, je 500 von 500 gleich. Ein dritter Versuch brach mit Zeitüberschreitung ab.
- **Adressen:** Im Job-Log stehen keine IPs und keine Hostnamen, das hat ein Subagent über alle 565 Zeilen geprüft. Stand, Markdown und CSV enthalten nur Zahlen.
- **PH-Entwurf:** `ph-entwurf-zcash-mainnet.yml` lief grün (44323181053), der Entwurf ging mit HTTP 200 an Discord. Er vergleicht gegen das benannte Fenster vom 6.11. 02:34 bis 11.11. 12:51 UTC. Die Regel vom 13.11. (#320) greift also.
- **Veröffentlichung:** Die CSV kommt mit diesem PR nach `data/zcash-mainnet/` in pulsehawk-site, Ben merged.
  - sha256 `f18ee47639960f75255bc9b59903760618f961f215a1f43b71fb9c12a8740f86`
  - Die ersten 18.594 Zeilen sind gleich wie in der CSV vom 11.11.

## Abstände gegen 25 s, zwei Wochen

Fenster 6.11. 02:34 bis 18.11. 14:18 UTC, Abstände der Blöcke 3.543.406 bis 3.586.394. Die Werte kommen aus unseren eigenen Köpfen, die berechnete Spalte gilt für exponentielle Abstände mit 25 s.

| | gezählt | berechnet |
|---|---:|---:|
| Abstände | 42.989 | |
| Mittel | 25,10 s | 25 s |
| Median | 17 s | 17,3 s |
| p90 | 58,0 s | 57,6 s |
| p99 | 116,0 s | 115,1 s |
| über 75 s | 4,88 % | 4,98 % |
| über 173 s | 0,098 % | 0,1 % |
| längste Lücke | 4 min 9 s, vor Block 3.543.445 am 6.11. um 03:11:24 UTC | etwa 4 min 41 s |
| negative Abstände | 0 | 0 |

**Nur die zweite Woche**, 11.11. 12:51 bis 18.11. 14:18 UTC, Blöcke 3.561.999 bis 3.586.394, aus der CSV nachgerechnet:
- 24.396 Abstände
- Mittel 25,00 s, Median 17 s, p90 57,0 s, p99 115,0 s
- über 75 s 4,82 %, über 173 s 0,086 %
- Längster Abstand 4 min 4 s, vor Block 3.562.835 am 11.11. um 18:41:48 UTC

## Einpendeln

Gegenüber dem 11.11. hat sich nichts geändert.
- **Eingependelt** ab Block 3.544.439, nach 1.034 Blöcken, etwa 8,4 h nach dem ersten NU7-Block. Regel: Mittel über 100 Blöcke innerhalb von ±20 % von 25 s, gehalten über 1.000 Blöcke.
- **Schwierigkeit relativ zu vor NU7:** 0,794 bei NU7 + 1, 0,504 bei + 100, 0,321 bei + 1.000, 0,326 bei + 5.000. Die Spitze lag bei 0,367. Bei gleicher Hashrate wäre ein Drittel zu erwarten (0,333).

Im Discord-Entwurf steht „settled near 25 s“. Damit ist das Mittel gemeint. Der Median von 17 s passt dazu, denn bei exponentiellen Abständen liegt er bei 25 s mal ln 2.

## Verlauf über alle Stände

| Stand | Spitze | Abstände vor NU7 | Mittel / Median vor | Abstände nach NU7 | Mittel / Median nach | über 75 s nach | Gegenprobe |
|---|---:|---:|---|---:|---|---:|---|
| 23.10. | 3.527.841 | 38.124 | 75,34 / 53 s | | | | 2 × 500/500 |
| 28.10. | 3.533.510 | 43.793 | 75,34 / 53 s | | | | 2 × 500/500 |
| 4.11. | 3.541.609 | 51.892 | 75,35 / 53 s | | | | 1 × 500/500 |
| 6.11. | 3.543.655 | 53.687 | 75,34 / 53 s | 250 | 38,21 / 25 s | 13,2 % | 2 × 500/500 |
| 11.11. | 3.561.998 | 53.687 | 75,34 / 53 s | 18.593 | 25,23 / 17 s | 4,95 % | 1 × 500/500 |
| **18.11.** | **3.586.394** | 53.687 | 75,34 / 53 s | **42.989** | **25,10 / 17 s** | **4,88 %** | 2 × 500/500 |

- **Vor NU7:** Die Zahl bleibt ab dem 6.11. fest, weil das Fenster vor NU7 dann geschlossen ist. Es reicht ab 20.9.2026.
- **Längste Lücke nach NU7:** in allen Ständen ab dem 6.11. dieselbe, 4 min 9 s.

## PR-Nummern

- dieser PR in pulsehawk-site (CSV und Bericht)

## Offene Fragen an Ben

1. **Täglicher Lauf:** Mit dieser CSV ist der Auftrag vom 23.10. erfüllt. Soll der tägliche Lauf von `zcash-mainnet.yml` jetzt abgeschaltet werden? Davon hängt auch der tägliche PH-Entwurf ab, denn er startet nach jedem Lauf. Ob die wöchentliche Auswertung des Zuhörers „dauer“ diese Köpfe braucht, prüfe ich vor einer Abschaltung. Eine Abschaltung wäre eine Workflow-Änderung als PR an dich.

## Was Ben tun muss

- Diesen PR prüfen und mergen.
- Frage 1 beantworten.
