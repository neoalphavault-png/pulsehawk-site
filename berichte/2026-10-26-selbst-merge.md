# Bericht 26.10.2026, Regel "Selbst mergen"

Ben hat am 26.10.2026 eine neue feste Regel aufgestellt: Claude mergt eigene PRs selbst, wenn drei Bedingungen erfüllt sind. Sonst merged Ben.

## Was gemacht wurde
- **`CLAUDE.md`:** Die Regel steht jetzt unter "Selbst mergen", damit jede künftige Sitzung sie liest. Darin stehen die drei Bedingungen, Squash and merge, das Löschen des Branches und Konflikte nur per Rebase. Dazu kommt nach jedem Selbst-Merge eine Zeile im Bericht.
- **Erster Selbst-Merge, #39:** Der PR enthält nur einen Bericht. Er ändert keine Datei unter `.github/workflows/`, `deploy/` und keine c2-Datei. Beide Checks waren grün, es gab keinen Konflikt, und kein öffentlicher Text ist betroffen.

## Selbst-Merges
| PR | Merge-Commit | Was live ist | Abnahme auf der echten URL |
|---|---|---|---|
| #39 | `60d4841` | Nachtrag im Bericht 2026-10-26-kalender-daten (Ergebnis des Laufs) | Die Website ändert sich nicht. `pulsehawk.io/berichte/2026-10-26-kalender-daten.html` liefert 404, wie es soll. |

## Abnahme der Merges von Ben am 26.10. auf der echten URL
Am 26.10.2026 gegen 17:10 UTC per Abruf von pulsehawk.io geprüft.
- **#38, Startseite:** Die H1 "Blockchains, measured under load", die Pulslinie (`class="puls"`) und der Anker `#bch-median` sind live.
- **#37, Kalender:** `/upgrades` zeigt "around 6 November 2026, block 3,543,405".
- **Nicht öffentlich:** `/berichte/…`, `/CLAUDE.html` und `/.claude/skills/…/SKILL.md` liefern 404.

## Offene Fragen an Ben
Keine neuen.

## Was Ben tun muss
Nichts. Diesen PR merge ich nach der Regel selbst.
