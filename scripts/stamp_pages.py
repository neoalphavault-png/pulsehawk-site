name: seitenstempel

# Schreibt die Tageszaehler taeglich in den Quelltext der Zyklusseiten.
# Der Browser rechnet sie ohnehin, aber Antwortmaschinen lesen oft nur den
# rohen Quelltext und fuehren kein JavaScript aus. Ohne diesen Lauf saehen
# die fuer immer die Zahl vom Tag der Auslieferung.
#
# Laeuft eigenstaendig und fasst den Marktlogger nicht an.
#
# ⚠️ Ab jetzt gilt fuer bitcoin-halving-to-top.html und
# bitcoin-top-to-bottom.html dieselbe Regel wie fuer index.html im Repo
# kaspa-pulse. Niemals eine alte lokale Kopie hochladen, der Bot hat die
# Datei inzwischen veraendert.

on:
  schedule:
    - cron: "17 4 * * *"    # taeglich 04:17 utc, weit weg vom marktlogger
  workflow_dispatch:

permissions:
  contents: write

jobs:
  stempeln:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: selbsttest
        run: python3 scripts/stamp_pages.py --selftest

      - name: stempeln
        run: python3 scripts/stamp_pages.py

      - name: aendern und schieben
        run: |
          if [ -z "$(git status --porcelain)" ]; then
            echo "nichts geaendert, kein commit"
            exit 0
          fi
          git config user.name "pulsehawk bot"
          git config user.email "actions@github.com"
          git add -A
          git commit -m "seitenstempel $(date -u +%Y-%m-%d)"
          git push
