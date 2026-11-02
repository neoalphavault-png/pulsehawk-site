# Bericht 2.11.2026, Schema-Datum mit Uhrzeit und Zeitzone

Nachtrag von Ben zum Fix "as of" vom 2.11.2026, Frist Mi 4.11. 18:00 Berlin. Umgesetzt in **#50** (Branch `site/schema-datum`). Code-Commit `f4300d1`, den Kopf beim Merge nennt der Abschnitt "Selbst-Merge" unten. Keine Workflow-Änderung.

## Was gemacht wurde
- **Anlass:** Googles Rich Results Test meldete für /zcash-nu7 bei `datePublished` und `dateModified` "ungültiger Datum/Uhrzeit-Wert" und "Zeitzone fehlt", nicht kritisch. Im Schema stand nur das Datum, zum Beispiel `2026-10-28`.
- **`scripts/b2b_pages.py`:** Neue Funktion `schema_zeit()`. Sie schreibt `2026-10-28T06:00:00+00:00`, die Uhrzeit wie in deinem Beispiel, fest 06:00 UTC. Das Datum bleibt der Text- oder Datenstand wie bisher.
  - **Article-Schema, alle Seiten mit Article:** /zcash-nu7, /upgrades und /cases/kaspa.
  - **Dataset auf /zcash-nu7:** Es hat dieselben zwei Felder und sieht jetzt genauso aus.
- **`scripts/b2b_check.py`:** Meldet künftig jedes `datePublished` oder `dateModified` im Schema ohne Uhrzeit und Zeitzone.
- **Sitemap:** `lastmod` bleibt ein reines Datum, das ist dort gültig.

| Seite | datePublished | dateModified |
|---|---|---|
| /zcash-nu7, Article | 2026-10-18T06:00:00+00:00 | 2026-10-28T06:00:00+00:00 |
| /zcash-nu7, Dataset | 2026-10-18T06:00:00+00:00 | 2026-10-18T06:00:00+00:00 |
| /upgrades | 2026-10-16T06:00:00+00:00 | 2026-10-27T06:00:00+00:00 |
| /cases/kaspa | 2026-10-16T06:00:00+00:00 | 2026-10-16T06:00:00+00:00 |

Die Fallseite Alexandria (#47) nutzt dieselbe Funktion. Nach dem Merge hier baue ich #47 auf den neuen main, dann hat auch sie Uhrzeit und Zeitzone.

## Prüfungen
- **Regel greift:** Auf der alten /zcash-nu7 meldet `b2b_check` 4 Funde, zum Beispiel "schema dateModified ohne uhrzeit und zeitzone '2026-10-28'". Auf der neuen Seite ist es keiner.
- **Alle Seiten:** 0 von 12 Seiten mit Fund. Das JSON-LD aller Seiten ist gültig.
- **Sichtbarer Text:** unverändert, deshalb keine neuen Screenshots.
- **Secret-Scan:** ohne Fund.

## Offene Fragen an Ben
1. Den Rich Results Test kann ich aus meiner Umgebung nicht aufrufen. Bitte nach dem Merge für https://pulsehawk.io/zcash-nu7 noch einmal laufen lassen.

## Was Ben tun muss
1. Den Rich Results Test wiederholen (Frage 1).

## Selbst-Merge
| PR | Kopf beim Merge | Merge-Commit | Was live ist | Abnahme auf der echten URL |
|---|---|---|---|---|
| #50 | `6ef9f31` | `a73dbd5` | Schema-Datum mit Uhrzeit und Zeitzone auf /zcash-nu7, /upgrades und /cases/kaspa | Am 2.11.2026 um 08:11 UTC geprüft, kurz nach dem Merge |

Abruf auf pulsehawk.io, JSON-LD:
- **/zcash-nu7, Article:** 2026-10-18T06:00:00+00:00 und 2026-10-28T06:00:00+00:00.
- **/zcash-nu7, Dataset:** 2026-10-18T06:00:00+00:00 und 2026-10-18T06:00:00+00:00.
- **/upgrades, Article:** 2026-10-16T06:00:00+00:00 und 2026-10-27T06:00:00+00:00.
- **/cases/kaspa, Article:** 2026-10-16T06:00:00+00:00 und 2026-10-16T06:00:00+00:00.

**#47 (Alexandria)** ist auf den neuen main gesetzt und neu gebaut (Kopf `164e54f`). Dort steht jetzt `2026-11-01T06:00:00+00:00`.
