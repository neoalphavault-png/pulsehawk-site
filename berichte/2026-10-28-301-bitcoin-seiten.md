# Bericht 28.10.2026, alte Bitcoin-Seiten auf /method

Auftrag von Ben vom 27.10.2026, Frist Mi 28.10. 18:00 Berlin. Ziel: pulsehawk.io steht klar für unabhängige Messung. Die alten Bitcoin- und Marktseiten der früheren DAY-Serie holen Impressionen über fremde Suchen und verwässern das Thema. Umgesetzt in **#43** (Branch `site/301-bitcoin`).

## Die Seiten
Gesucht habe ich im Repo, in Sitemap, Seitenleiste, Archiv, Skripten und Workflows. Gefunden sind 8 Seiten der Serie und die Archivseite, die sie auflistet. Alle 9 leiten jetzt auf /method:

| Alte URL | Inhalt bisher |
|---|---|
| /bitcoin-halving-to-top.html | Bitcoin-Zyklus, Halving bis Hoch |
| /bitcoin-top-to-bottom.html | Bitcoin-Zyklus, Hoch bis Tief (auch Datenquelle des DAY-N-Posts) |
| /bitcoin-drawdown.html | Abstand zum Allzeithoch |
| /bitcoin-bull-run-length.html | Länge der Bullenmärkte |
| /gold-in-bitcoin-bear-markets.html | Gold und S&P 500 in Bitcoin-Bärenmärkten |
| /bitcoin-dominance.html | Bitcoin-Dominanz |
| /markets.html | Gold, Aktien und Bitcoin über sieben Tage |
| /what-if.html | "What if you had bought bitcoin, gold or the S&P 500" |
| /archive | Liste der acht Seiten oben, gebaut vom Generator |

Jede gilt auch ohne `.html` (/bitcoin-drawdown), denn GitHub Pages liefert dieselbe Datei aus.

## Was gemacht wurde
1. **Weiterleitungen**
   - **Muster:** Jede alte Datei ist jetzt eine kleine Weiterleitungsseite nach dem Muster der bestehenden Kurzlinks in kaspa-pulse (`/x`, `/yt` und andere). Sie hat `meta http-equiv="refresh" content="0; url=/method"`, `link rel="canonical"` auf https://pulsehawk.io/method, `robots noindex, follow` und einen sichtbaren Link für alle, die der Weiterleitung nicht folgen. Kein JavaScript.
   - **Gebaut vom Generator:** `scripts/b2b_pages.py` (`WEITERLEITUNGEN`), nicht von Hand.
2. **Sitemap und interne Links**
   - **Sitemap:** Sie enthält nur noch die 10 Messseiten. Die 8 alten URLs und /archive sind raus, die XML-Struktur ist geprüft.
   - **Fußzeile:** Der Link "Archive" ist auf allen Seiten weg, die Archivseite selbst leitet weiter.
   - **llms.txt:** Der Archiv-Eintrag ist raus.
   - **Sicherung im Generator:** Er bricht jetzt ab, sobald eine Seite eine weitergeleitete Adresse verlinkt (mit und ohne `.html`, relativ und absolut).
3. **Bots stillgelegt (Workflow-Änderung, Ben merged)**
   - **`seitenstempel` (`stamp-pages.yml`, täglich 04:17 und 21:40 UTC) entfernt.** Er hat nur diese Seiten beschrieben und hätte die Weiterleitungen täglich angefasst. Sein Selbsttest liest die alten Seiten, er wäre ab jetzt jeden Tag rot gewesen.
   - **`day n` (`dayn.yml`, täglich 07:30 UTC) entfernt.**
     - Der Post ist seit dem 17.10.2026 pausiert (`data/dayn-schalter.json`).
     - Der Lauf stempelte die Seiten aber weiter und las `bitcoin-top-to-bottom.html` als Datenquelle.
     - Ohne die Seite gibt es keinen DAY-N-Post mehr. Wer die Serie je wieder will, braucht eine neue Datenquelle.
   - **Nicht angefasst:**
     - Die Skripte `stamp_pages.py` und `day_n_post.py` liegen noch im Repo, werden aber von keinem Workflow mehr aufgerufen.
     - Alle Daten unter `data/` bleiben.
     - Der Marktlogger (`market-log.yml`) und die übrigen Workflows laufen weiter.
4. **`CLAUDE.md`:** Der Abschnitt "Seiten" sagt jetzt, dass die alten Seiten weiterleiten und Seitenstempel und DAY-N stillgelegt sind.

## Wichtig: kein echter HTTP-301
**pulsehawk.io liegt direkt auf GitHub Pages** (`server: GitHub.com`, kein CDN davor). GitHub Pages kann für einzelne Pfade keinen Statuscode 301 senden. Es gibt dort keine Weiterleitungsregeln, keine `_redirects` und kein `.htaccess`.

- **`curl -I` auf eine alte URL zeigt deshalb nach dem Merge `HTTP/2 200`** mit der Weiterleitungsseite, nicht `301`.
- **Google:** Google behandelt eine sofortige Meta-Refresh-Weiterleitung (Verzögerung 0) wie eine dauerhafte Weiterleitung. Zusammen mit `canonical` auf /method und `noindex` verschwinden die alten Seiten aus dem Index, und ihre Signale gehen auf /method. Das ist das Ziel des Auftrags.
- **Echter 301 per curl:** Dafür muss vor GitHub Pages ein Dienst mit Weiterleitungsregeln stehen, etwa ein CDN mit DNS-Umstellung, oder die Seite muss auf einen anderen Host. Das ist eine Infrastruktur- und DNS-Entscheidung und gehört Ben.

## Prüfungen
- **Textregeln:** `b2b_check` 0 von 12 Seiten mit Fund. Die Archivseite zählt nicht mehr dazu.
- **Sitemap:** `sitemap.xml` parst als gültiges XML im Namensraum sitemaps.org. Alle 10 Adressen haben eine Datei.
- **Interne Links:** Kein Link auf eine der 9 alten Adressen in den Seiten, in `llms.txt` oder in der Sitemap. Gesucht habe ich auch in kaspa-pulse, dort gibt es ebenfalls keinen.
- **Im Browser (Chromium, lokal):** Alle 9 alten Adressen und die Form ohne `.html` landen auf /method mit dem Titel "How we measure blockchains | PulseHawk".
- **Secret-Scan:** ohne Fund.
- **Auf dem Betriebspfad nach dem Merge:** `curl -I` für jede alte URL (erwartet `200` mit `meta refresh` auf /method, siehe oben), sitemap.xml live und Stichproben der Fußzeile. Das Ergebnis kommt als Nachtrag.

## Offene Fragen an Ben
1. **Echter 301:** Reicht dir die Meta-Refresh-Weiterleitung, die Google als dauerhaft wertet? Oder soll ein CDN vor GitHub Pages, damit `curl -I` wirklich 301 zeigt? Das braucht eine DNS-Umstellung.
2. **Workflows:** Sollen `seitenstempel` und `day n` wirklich ganz weg (so im PR, aus der Git-Historie wiederherstellbar)? Oder lieber nur ohne Zeitplan stehen bleiben?
3. **Altlasten:** Sollen `stamp_pages.py`, `day_n_post.py` und die nur für sie gebrauchten Dateien in einem späteren Aufräum-PR raus?

## Was Ben tun muss
1. #43 prüfen und mergen. Er enthält Workflow-Löschungen, deshalb merged Ben.
2. Frage 1 entscheiden.
3. Optional: in der Google Search Console für die alten URLs "Prüfen" anstoßen, damit Google die Weiterleitung schneller sieht.

## Nachtrag 28.10.2026, Prüfung auf dem Betriebspfad
Ben hat #43 am 28.10.2026 gegen 08:10 UTC gemergt (Merge-Commit `0cfbbf2`). Der Seitenstempel hatte in der Nacht davor noch einmal in die alten Seiten geschrieben. Das gab Konflikte in den 8 Dateien, die Claude per Rebase auf main gelöst hat. Die Seiten sind danach mit `b2b_pages.py` neu gebaut, nicht von Hand.

Etwa eine Minute nach dem Merge war die Weiterleitung live. Abruf von pulsehawk.io, jede alte URL mit `curl -I` (Statuszeile) und ein Abruf der Seite (Weiterleitung und canonical):

| URL | Status | Weiterleitung | canonical |
|---|---|---|---|
| /bitcoin-halving-to-top.html | HTTP/2 200 | `http-equiv="refresh" content="0; url=/method"` | `rel="canonical" href="https://pulsehawk.io/method"` |
| /bitcoin-top-to-bottom.html | HTTP/2 200 | `http-equiv="refresh" content="0; url=/method"` | `rel="canonical" href="https://pulsehawk.io/method"` |
| /bitcoin-drawdown.html | HTTP/2 200 | `http-equiv="refresh" content="0; url=/method"` | `rel="canonical" href="https://pulsehawk.io/method"` |
| /bitcoin-bull-run-length.html | HTTP/2 200 | `http-equiv="refresh" content="0; url=/method"` | `rel="canonical" href="https://pulsehawk.io/method"` |
| /gold-in-bitcoin-bear-markets.html | HTTP/2 200 | `http-equiv="refresh" content="0; url=/method"` | `rel="canonical" href="https://pulsehawk.io/method"` |
| /bitcoin-dominance.html | HTTP/2 200 | `http-equiv="refresh" content="0; url=/method"` | `rel="canonical" href="https://pulsehawk.io/method"` |
| /markets.html | HTTP/2 200 | `http-equiv="refresh" content="0; url=/method"` | `rel="canonical" href="https://pulsehawk.io/method"` |
| /what-if.html | HTTP/2 200 | `http-equiv="refresh" content="0; url=/method"` | `rel="canonical" href="https://pulsehawk.io/method"` |
| /archive | HTTP/2 200 | `http-equiv="refresh" content="0; url=/method"` | `rel="canonical" href="https://pulsehawk.io/method"` |
| /bitcoin-drawdown | HTTP/2 200 | `http-equiv="refresh" content="0; url=/method"` | `rel="canonical" href="https://pulsehawk.io/method"` |

Ergebnis:
- **Status:** Jede alte URL liefert, wie im Bericht oben angekündigt, `HTTP/2 200` mit sofortiger Weiterleitung auf /method und `canonical` auf /method, auch die Form ohne `.html`. Einen echten `301` kann GitHub Pages nicht senden (siehe oben, Frage 1).
- **Sitemap:** `sitemap.xml` live parst als gültiges XML, enthält 10 Adressen und keine alte URL.
- **Interne Links:** Auf den 10 Messseiten live (/, /method, /zcash-nu7, /upgrades, /independence, /contact, /tps-verification, /launch-measurement, /upgrade-monitoring, /cases/kaspa) gibt es keinen Link mehr auf eine alte URL.
- **Bots:** `seitenstempel` und `day n` sind mit #43 entfernt und laufen nicht mehr.

## Selbst-Merge, nachgetragen
| PR | Merge-Commit | Was live ist | Abnahme auf der echten URL |
|---|---|---|---|
| #41 | `c64d3df` | Glamsterdam auf Hoodi `activated` in /upgrades | Am 27.10.2026, 06:23 UTC geprüft: /upgrades zeigt "26 October 2026 · activated" und "checked on 27 October 2026". |
