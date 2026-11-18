# Track Record, Rubrik „scheduled protocol events“ (Auftrag Ben 16.11.2026, Test freigegeben am 13.11.)

**Kopf:** Seite, Daten, Sync-Skript und Sync-Workflow auf `track-record/protocol-events`, als PR an main. **Ben merged**, weil ein Workflow dabei ist. Die Prognosen selbst kommen aus dem PR in kaspa-pulse (Branch `kaspa/reward-prognose`).

## Was gemacht wurde

- **Neue Rubrik** auf /track-record, „Scheduled protocol events“, unter den Upgrade-Prognosen und den Vergleichen. Sie hat eine eigene Zählung, und die Upgrade-Bilanz (6 Einträge, 5 im Band) bleibt unverändert.
- **Daten:** `data/track-record-events.json` mit dem Eintrag TE-001, dem nächsten Kaspa-Reward-Schritt.
  - Auslöser ist der DAA score 610.101.000, der erste DAA score von Reward-Monat 55 nach rusty-kaspa v2.1.0.
  - Der Reward geht von 1,94454365 auf 1,83540480 KAS je Block.
  - Gezählt wird die Kopfzeit des ersten Blocks der ausgewählten Kette mit DAA score mindestens beim Auslöser, vom eigenen Knoten.
- **Prognosen:** 14 Tage, 7 Tage, 2 Tage und 24 Stunden vorher, je mit 80- und 95-%-Band, Wertung im 80-%-Band, im 95-%-Band oder außerhalb. Bis zur ersten Prognose zeigt die Seite „Not published yet“. Die Seite nennt nirgends ein festes Datum.
- **Zeitstempel auf pulsehawk-site:** `scripts/te_sync.py` übernimmt neue Prognosen aus dem öffentlichen Zustand des Prognoselaufs. Eine veröffentlichte Prognose ändert es nie, bei Abweichung bricht es ab. Der Commit der Datendatei ist der Zeitstempel. Die Seite verlinkt die Historie dieser Datei.
- **Workflow `track-record-events.yml`:** stündlich, ohne Secret. Er baut nur, wenn etwas neu ist, und committet nach main. Die Quelle liest er aus der Repo-Variable `TE_QUELLE`, damit das Site-Repo das Messrepo nicht nennt. Ohne Variable tut er nichts.
- **Prüfungen:** `b2b_check.py` meldet 0 von 25 Seiten mit Funden, der Selbsttest 0 von 26 Fällen falsch, `te_sync.py --selbsttest` 5 von 5. Der Secret-Scan ist sauber.
- **Bandhinweis:** Die Seite nennt jetzt 90-%-Bänder (Upgrades) und 80/95-%-Bänder (Ereignisse). Deshalb steht der von der Prüfung verlangte Satz darin: „Our upgrade forecasts above used a 90% band. From the next event on we publish an 80% and a 95% band.“

## PR-Nummern

- dieser PR in pulsehawk-site
- PR in kaspa-pulse, Prognoselauf (`kaspa/reward-prognose`)

## Offene Fragen an Ben

1. Ist die Wertung so recht? Eine Prognose zählt als im 80-%-Band, im 95-%-Band oder außerhalb. Bei den Upgrades hieß es bisher in band oder outside gegen ein 90-%-Band.

## Was Ben tun muss

- Diesen PR und den PR in kaspa-pulse mergen, am besten bis Do 19.11., damit die 14-Tage-Prognose rechtzeitig um den 21.11. kommt.
- Die Repo-Variable `TE_QUELLE` in pulsehawk-site setzen (Settings, Secrets and variables, Actions, Variables). Der Wert ist die Raw-Adresse von `data/kaspa-reward/zustand.json` auf dem Branch `messung/kaspa-reward` in kaspa-pulse. Der volle Wert steht im Bericht in kaspa-pulse.
