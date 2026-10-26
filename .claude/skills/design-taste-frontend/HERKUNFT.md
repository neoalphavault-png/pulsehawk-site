# Herkunft

Unveränderte Kopie von `skills/taste-skill/` aus
https://github.com/leonxlnx/taste-skill, Commit
`12af471f627f866411b4bd785b19646d3672784c` ("tasteskill v2.1.5: community
fixes (#172)"), Lizenz MIT (`LICENSE`, aus dem Wurzelverzeichnis des Repos).

Eingebunden am 26.10.2026 auf Bens Auftrag. Kein Update auf einen neueren
Stand ohne neue Prüfung durch Claude (Ben, 26.10.2026).

Für pulsehawk.io gilt: Marke geht vor. Farben, Schriften und der Falke
bleiben. Vom Skill kommen Komposition, Typo-Größen, Abstände, Hierarchie und
Bildwelt, nicht seine Farbrichtungen. Bilder aus `scripts/assets.mjs` nur mit
Lizenz cc0 oder pd, jede Quelle im Bildregister.

Die Arbeitsdateien des Skills landen in `.taste-skill/` im Repo und werden
nicht eingecheckt (`.gitignore`). `.claude/` liefert Jekyll nicht aus
(`_config.yml`).

Geprüft vor dem Einbinden: Die Skripte rufen nur öffentliche Bildarchive ab
(`assets.mjs`: Openverse, Wikimedia Commons, Art Institute of Chicago, Met,
Internet Archive, NASA), ohne Schlüssel. `inspect.mjs` und `scenes.mjs` starten
einen Browser und einen Server nur auf dem eigenen Rechner (Loopback).
`draw.mjs` schreibt einen Verlauf nach `~/.taste-skill/history.json`.
Es gibt keine Installationsschritte und keine Abhängigkeiten.
