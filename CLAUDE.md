# Hinweise für Claude-Sitzungen in pulsehawk-site

## Abschlussbericht (Ben, 22.10.2026, feste Regel)
Am Ende jeder Aufgabe kommt der Abschlussbericht zusätzlich als Datei
`berichte/JJJJ-MM-TT-<thema>.md` in den Branch des PR. Ist der PR schon
gemergt, kommt der Bericht in einen eigenen kleinen Branch mit PR.

Inhalt:
- was gemacht wurde
- PR-Nummern
- offene Fragen an Ben
- was Ben tun muss

Claude liest die Berichte und PRs direkt auf GitHub und prüft sie. Ben
muss nichts kopieren.

Das Repo ist öffentlich. In einem Bericht stehen nie Schlüssel, Tokens,
IPs, Hostnamen, Wallet-Adressen oder Kundendaten. Vor dem Push läuft
`python3 scripts/secret_scan.py --staged`.

## Branches
Pushes auf `claude/**` gehen über `automerge-claude.yml` sofort nach main.
Alles, was Ben vorher prüfen soll, kommt auf einen Branch außerhalb von
`claude/` und bekommt einen PR.

## Selbst mergen (Ben, 26.10.2026, feste Regel)
Claude mergt eigene PRs selbst (Squash and merge, Branch danach löschen),
wenn alle drei Bedingungen erfüllt sind:
1. Keine Datei unter `.github/workflows/`, `deploy/` und keine c2-Datei
   (Timer, `setup.sh`, Taktgeber) geändert.
2. Alle Checks grün und keine Konflikte. Konflikte löst Claude selbst per
   Rebase auf den aktuellen main, nie im Web-Editor.
3. Öffentliche Texte bestehen die Textregel-Prüfung (`scripts/b2b_check.py`).

Sonst gilt weiter: Claude prüft, Ben merged.

Nach jedem Selbst-Merge kommt eine Zeile in den Bericht: PR, Merge-Commit,
was live ist. Bei Seiten gehört die Abnahme auf der echten URL dazu
(pulsehawk.io abrufen und prüfen, was geändert wurde).

## Seiten
Die B2B-Seiten baut `scripts/b2b_pages.py`. Erzeugte HTML-Dateien werden
nicht von Hand geändert: Der nächste Neubau würde die Änderung löschen.
`scripts/b2b_check.py` prüft die Textregeln. Die alten Datenseiten gehören
dem Seitenstempel (`scripts/stamp_pages.py`).
