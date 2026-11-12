# Cloudflare Web Analytics statt Plausible (Auftrag Ben 12.11.2026)

Kopf: `a6b132a` auf `site/cloudflare-analytics`.

## Was gemacht wurde

1. **Beacon an der Quelle.** `scripts/b2b_pages.py` setzt das Cloudflare-Snippet
   (Konstante `CF_BEACON`) genau einmal direkt vor `</body>`. Das gilt für alle
   25 Seiten, die der Generator baut. Die 9 Weiterleitungsseiten der früheren
   DAY-Serie (`WEITERLEITUNGEN`) haben weiter kein Skript, siehe offene Frage 1.
2. **Plausible ist ganz raus.** Entfernt sind das Skript im Kopf, alle Klassen
   `plausible-event-name=...` (Sample-Knöpfe, CSV- und PDF-Links,
   Kontaktformular) und der Aufruf `window.plausible` im Mailto-Skript.
   `report_waechter.py` erlaubt jetzt den Host static.cloudflareinsights.com
   statt plausible.io. In zwei Skill-Dateien unter `.claude/` stand das
   englische Adjektiv „plausible“, dort steht jetzt „believable“.
   `git grep -i plausible -- ':!berichte'` findet nichts mehr, auch in keiner
   HTML-Datei.
3. **Datenschutz, Abschnitt 3** heißt jetzt „Reach measurement with Cloudflare
   Web Analytics, without cookies“. Er nennt den Anbieter, den Zweck
   (Reichweitenmessung), was erhoben wird, die Rechtsgrundlage Art. 6 (1)(f)
   DSGVO und die Übermittlung in die USA. Die Seitenbeschreibung wurde
   angepasst. Jede Aussage stammt aus Cloudflares eigenen Texten, mit Beleg in
   der Tabelle unten. Abschnitt 7 („no cookies“) bleibt richtig.
4. **CSP.** Es gibt keine: kein Meta-Tag `Content-Security-Policy` und keine
   Datei `_headers`. GitHub Pages setzt keine eigenen Header. Es war also
   nichts zu erweitern.
5. **Prüfung im Generator.** `scripts/b2b_check.py` prüft jede gebaute Seite.
   Das Snippet muss genau einmal da sein, mit dem Site-Token, direkt vor
   `</body>`. Fehlt es, steht es doppelt oder an der falschen Stelle, ist die
   Seite rot. Die alte Plausible-Prüfung ist weg.
6. **Secret-Scan.** Der Scan meldete das Site-Token im Beacon an 26 Stellen,
   alle mit demselben Fingerabdruck `d2f612f792d1`. Ben hat festgelegt, dass
   das Token öffentlich und kein Secret ist. Es steht deshalb mit Begründung in
   der neuen Datei `.secret-scan-allow`. Das ist der Ausnahmeweg, den
   `secret_scan.py` selbst vorsieht. Eingetragen ist nur der Fingerabdruck,
   nie der Wert. Danach meldet `secret_scan.py --staged` und
   `--bereich origin/main..HEAD` nichts mehr.

Cloudflare wertet keine UTM-Parameter und keine eigenen Ereignisse aus. Das ist
bekannt und in Ordnung (Ben). Die Ereignis-Klassen sind deshalb ersatzlos
gestrichen.

## Belege für die Datenschutzseite (nur Cloudflares eigene Angaben)

| Aussage auf der Seite | Quelle, wörtlich |
|---|---|
| keine Cookies, kein localStorage | https://www.cloudflare.com/web-analytics/ „Cloudflare Web Analytics does not use any client-side state, such as cookies or localStorage, to collect usage metrics.“ |
| kein Fingerprinting über IP, User Agent oder anderes | ebenda „We also don’t “fingerprint” individuals via their IP address, User Agent string, or any other data for the purpose of displaying analytics.“ |
| keine personenbezogenen Daten | https://developers.cloudflare.com/web-analytics/about/ „Cloudflare Web Analytics does not collect or use your visitors’ personal data.“ |
| keine Verfolgung über Websites hinweg | https://developers.cloudflare.com/web-analytics/data-metrics/data-origin-and-collection/ „Cloudflare does not track individual end users across our customers’ Internet properties.“ |
| Skript von static.cloudflareinsights.com, Messwerte über die Performance API | ebenda (Ladeort des Beacons) und about/ („collects metrics using the Performance API“) |
| Besuche, Seitenaufrufe, Ladezeit, Core Web Vitals | https://developers.cloudflare.com/web-analytics/data-metrics/high-level-metrics/ |
| Seitenadresse, verweisende Seite, Land, Gerätetyp, Browser, Betriebssystem | https://developers.cloudflare.com/web-analytics/data-metrics/dimensions/ (Path, Referer, Country, Device type, Browser, Operating system) |
| Anbieter Cloudflare, Inc., 101 Townsend St, San Francisco, CA 94107, USA | https://www.cloudflare.com/privacypolicy/ (Kontakt, Fassung vom 4.11.2025) |
| USA-Übermittlung über das EU-U.S. Data Privacy Framework | ebenda „When Cloudflare transfers personal data from the EEA, Switzerland, or the United Kingdom (UK) to the United States, we rely on our certifications under the EU-U.S. Data Privacy Framework (EU-U.S. DPF) …“ |

## Prüfungen vor dem Push

- `b2b_pages.py` hat neu gebaut, 0 von 25 Seiten mit Funden.
- `b2b_check.py --selbsttest`: 0 von 26 Fällen falsch.
- `datiert.py --selbsttest`: 0 von 10 Fällen falsch.
- `report_waechter.py --selbsttest`: 0 von 55 Fällen falsch.
- `secret_scan.py --selbsttest`: 0 Fehler.
- pyflakes ist sauber.
- Netzwerkprobe mit Playwright gegen den lokalen Bau auf Port 80, Seiten `/`
  und `/datenschutz.html`. Ergebnis je Seite: `GET 200`
  static.cloudflareinsights.com/beacon.min.js, `POST 204`
  cloudflareinsights.com/cdn-cgi/rum, keine Anfrage an plausible.io.
  Auf Port 8781 scheitert der Sendeaufruf, weil Cloudflare
  `Access-Control-Allow-Origin` nur ohne Port zurückgibt. Für pulsehawk.io
  antwortet Cloudflare mit `https://pulsehawk.io`, dort passt es.

## Merge

Den PR mergt Ben, nicht Claude. Grund: Der PR enthält eine Ausnahme für den
Secret-Scan (`.secret-scan-allow`), und Änderungen mit Bezug zu Secrets sind
nach der Regel vom 26.10. (bestätigt 4.11.) vom Selbst-Merge ausgenommen.
Workflows, `deploy/` und c2-Dateien sind nicht geändert. Nach dem Merge folgt
die Abnahme auf pulsehawk.io in einem eigenen kleinen Bericht-PR.

## Offene Fragen an Ben

1. Die 9 Weiterleitungsseiten (zum Beispiel /archive, /markets, /what-if)
   leiten ohne Verzögerung per Meta-Refresh auf /method weiter. Sie stehen auf
   noindex und hatten nie Plausible. Ich habe sie ohne Beacon gelassen, weil
   der Besuch auf /method ohnehin gezählt wird. Sollen sie trotzdem einen
   Beacon bekommen?
2. Die lokale Probe hat zwei Testbesuche mit dem Host „localhost“ an Cloudflare
   geschickt. Im Dashboard kann deshalb einmalig localhost auftauchen. Das ist
   harmlos und lässt sich per Host-Filter ausblenden.

## Was Ben tun muss

1. Den PR prüfen und mergen, bis So 15.11. 18:00.
2. Nach dem Merge und meiner Abnahme im Cloudflare-Dashboard nachsehen, ob
   Besuche auf pulsehawk.io ankommen.
3. Bei Plausible kann das Konto für pulsehawk.io gekündigt werden. Von der
   Seite geht keine Anfrage mehr dorthin.
