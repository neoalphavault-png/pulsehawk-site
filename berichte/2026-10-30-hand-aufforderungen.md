# Bericht 30.10.2026, 📤-Aufforderungen für Kalender und Zcash

Auftrag von Ben vom 28.10.2026, Frist Fr 30.10. 18:00 Berlin.

**Ziel:** Ben postet @pulsehawkio von Hand, genau 3 Posts pro Woche. Zu jedem Entwurf in #ph-entwuerfe kommt deshalb eine Aufforderung nach #moderator-only.

Umgesetzt in **#45** (Branch `ph/hand-aufforderungen`). **Der PR ändert Workflows: Claude prüft, Ben merged.**

## Was gemacht wurde
1. **Sende-Hilfe `scripts/ph/ops_melden.py`, Art `hand`**
   - **Vorbild:** `scripts/ops_melden.py` aus kaspa-pulse, hier nur mit der Art `hand`.
   - **Secret:** Der Webhook kommt nur aus `DISCORD_WEBHOOK_OPS` in der Umgebung, im Workflow nur im Schritt, der sendet. Er erscheint in keiner Ausgabe. Eine Webhook-Adresse in einem Text wird vor dem Senden durch `[webhook]` ersetzt.
   - **Fehlt das Secret:** Es geht nichts raus. Im Job-Log steht "kein DISCORD_WEBHOOK_OPS, nichts an #moderator-only gesendet", darunter die Aufforderung. Der Lauf bleibt grün.
   - **Probe-Modus `--probe`:** Er sendet nichts nach #moderator-only. Die Aufforderung steht im Job-Log und in der Zusammenfassung des Laufs.
   - **Niemand wird angepingt** (`allowed_mentions` leer).
2. **`ph-kalender.yml`, montags**
   - **Entwurf:** geht wie bisher nach #ph-entwuerfe.
   - **Aufforderung:** Danach geht eine Aufforderung nach #moderator-only. Ihr Kopf steht unten im Beispiel. Darunter kommen der vollständige Posttext, `antwort.txt` (weitere Tags, oder "antwort.txt ist leer, keine weiteren Tags.") und der Satz "Die Grafik (kalender.png) hängt im #ph-entwuerfe-Post von heute."
   - **Ohne Eintrag in 14 Tagen:** Es gibt keinen Entwurf und keine `post.txt`, also keine Aufforderung. Im Log steht "kein entwurf, keine aufforderung".
   - **Neuer Eingang `probe`** bei workflow_dispatch, Standard aus.
3. **`ph-entwurf-zcash.yml`, nach jeder CSV**
   - **Aufforderung:** Nach jedem gesendeten Entwurf kommt dieselbe Aufforderung mit "nächster Mi oder Do 17:45".
   - **Grafik:** Der Name ist derselbe wie im Entwurfspost, zum Beispiel `pulsehawk-zcash-verteilung.png`.
   - **Keine neue CSV:** keine Aufforderung.
   - **Probe:** Testläufe auf `ph/discord-entwurf` und workflow_dispatch mit `probe` senden nichts nach #moderator-only.
4. **Selbsttest und Textregeln**
   - **Neuer Schritt `selbsttest aufforderung`** in beiden Workflows. Er läuft vor dem Entwurf.
   - **Abbruch:** Bricht ein Selbsttest ab (Kalender, Zcash-Regeln oder Aufforderung) oder scheitert der Entwurf, laufen die Schritte danach nicht. Dann gibt es auch keine Aufforderung.
   - **Zweite Prüfung:** Vor dem Senden wird der Posttext noch einmal mit der Regel des Entwurfs geprüft. Beim Kalender ist das `regel_funde` für Post und Antwort, bei Zcash `regel_pruefen`. Bei einem Verstoß geht keine Aufforderung raus, und der Schritt wird rot.
   - **`ph_entwurf.py` ist nicht geändert.** Die Datei liegt gleich in kaspa-pulse, und die Aufforderung braucht dort nichts.

## Ergebnisse (lokal, ohne Secrets)
- **`ops_melden.py --selbsttest`:** 22 von 22 Fällen richtig. Geprüft sind:
  - der Kopf wortgleich mit dem Auftrag, für beide Uhrzeiten;
  - Posttext, Antwort und Grafik-Hinweis;
  - Abbruch bei Doppelpunkt, Emoji, Großschreibung, Überlänge, "expected" und bei einem Verstoß in der Antwort;
  - kein Webhook im Text, kein Ping;
  - Probe und fehlendes Secret senden nichts.
- **`ph_kalender_post.py --selbsttest`:** 54 von 54. **`ph_entwurf.py --selbsttest`:** ok.
- **Kein Eintrag (Stichtag 2027-06-01):** keine `post.txt`, "kein entwurf, keine aufforderung".
- **Regelverstoß:** Ein Zcash-Text mit "expected" ergibt "post verstoesst gegen die textregeln, keine aufforderung", Rückgabe 1.
- **Secret-Scan:** ohne Fund.

### Probe Kalender, Stichtag Mo 2.11.2026
````
📤 VON HAND Mo 16:30, X @pulsehawkio, https://x.com/compose/post. Erst nach ✅ von Claude im Chat posten

Posttext
```
network upgrades in the next 14 days, from the pulsehawk calendar

zcash nu7 on mainnet, around 6 november 2026

@zcash @zcashfoundation
pulsehawk.io/upgrades
```
antwort.txt ist leer, keine weiteren Tags.
Die Grafik (kalender.png) hängt im #ph-entwuerfe-Post von heute.
````

### Probe Zcash, CSV vom 18.10.2026
````
📤 VON HAND nächster Mi oder Do 17:45, X @pulsehawkio, https://x.com/compose/post. Erst nach ✅ von Claude im Chat posten

Posttext
```
zcash nu7 testnet with 25 s blocks.
we counted a median block interval of 17.0 s over 49,203 blocks, against 17.3 s computed for an ideal 25 s chain.
the 90th percentile of intervals is 52 s, against 58 s computed for an ideal 25 s chain.
window 4 oct 2026, 18:21 to 18 oct 2026, 05:59 utc, blocks 4,465,026 to 4,514,228.
method on pulsehawk.io
```
antwort.txt ist leer, keine weiteren Tags.
Die Grafik (pulsehawk-zcash-verteilung.png) hängt im #ph-entwuerfe-Post von heute.
````

## Offene Fragen an Ben
1. **Zcash-Mainnet und BCH:** Die Entwürfe aus kaspa-pulse (`ph-entwurf-zcash-mainnet.yml` nach jedem Stand, `ph-entwurf-bch.yml` mittwochs) haben noch keine Aufforderung. Ab NU7 kommt der Zcash-Entwurf vermutlich vor allem von dort. Sollen die beiden auch eine bekommen? Das wäre ein eigener PR in kaspa-pulse. Dort gibt es `ops_melden.py` und `DISCORD_WEBHOOK_OPS` schon.
2. **Zeitzone:** "Mo 16:30" und "nächster Mi oder Do 17:45" stehen wortgleich wie im Auftrag, ohne "Berlin". Soll "Berlin" dazu?
3. **Verspätung:** Der Montagslauf ist für 06:00 UTC geplant, kam am 26.10. aber erst um 12:38 UTC. Das ist noch vor 16:30 Berlin, aber knapp. Soll der Zeitplan früher liegen?

## Was Ben tun muss
1. In pulsehawk-site das Secret `DISCORD_WEBHOOK_OPS` anlegen (Webhook von #moderator-only), unter Settings, Secrets and variables, Actions.
2. #45 prüfen und mergen. Er ändert Workflows, deshalb merged Ben.
3. **Probe auf dem Betriebspfad, nach dem Merge:** "ph kalender entwurf" per "Run workflow" mit `heute` 2026-11-02 und `probe` an starten. Das kann auch Claude übernehmen.
   - **Was die Probe tut:** Der Entwurf geht dabei wie immer nach #ph-entwuerfe. Die Aufforderung steht nur im Job-Log.
   - **Danach:** Der erste echte Lauf ist Mo 2.11.
4. Fragen 1 bis 3 beantworten.

## Nachtrag 28.10.2026, nach dem Merge
- **Merge:** Ben hat #45 am 28.10.2026 um 11:03 UTC gemergt (Merge-Commit `b3c5b3a`).
- **Lauf auf main:** Der Merge hat "ph entwurf zcash" einmal auf main gestartet, Lauf Nr. 5.
  - **Selbsttests:** `selbsttest regeln` und der neue Schritt `selbsttest aufforderung` sind grün.
  - **Kein Versand:** Der Merge brachte keine neue CSV, also gab es keinen Entwurf und keine Aufforderung. Nichts ging nach #ph-entwuerfe oder #moderator-only.
- **Probe des Kalenders:** Die Probe mit `heute` 2026-11-02 und `probe` ist noch nicht gelaufen, weil sie einen echten Entwurf nach #ph-entwuerfe schickt. Sie läuft erst auf Bens Ja. Sonst ist der erste echte Lauf am Mo 2.11.
