# Wednesday routine prompt (Ukentlig utkast-gjennomgang)

Paste this into the routine's prompt field in the Routines UI. It replaces the
previous text. The only substantive change is the LEVERANSE block, which makes
the run verify that the draft reached `main` instead of assuming it did.

---

Ukens Artemis Briefing-artikkel. Følg WEEKLY_REVIEW.md i repoet
grandmasterjc/artemis2-config, og les ARTICLE_STYLE.md i sin helhet før du
skriver noe. Den er fasiten for stemme, struktur, språk, kildebruk,
anti-tells, CTA-tekst og lengde.

Hent siste main. Sjekk state/publish_history.txt og drafts/ så du verken
gjentar en fersk vinkel eller lager et duplikat av noe som allerede ligger
der. Finnes det allerede et utkast for denne uken, vurder det i stedet for å
skrive et nytt, og si fra om det.

Research ukens vinkel med websøk. Bruk den redaksjonelle vurderingslista i
WEEKLY_REVIEW.md, særlig punktet om at omstridt slår nyhetsverdig: den best
presterende saken hittil var en faktasjekk av et argument folk allerede
kranglet om i kommentarfelt. Verifiser nøkkelpåstander mot primærkilder.

Skriv drafts/{article_id}/article_draft.md og en hero.jpg etter spec-en og
bilderegelen. Kjør spec-ens §8-sjekkliste mot ditt eget utkast.

LEVERANSE — dette er der rutinen har feilet før, les nøye:

Utkastet SKAL ligge på main. Miljøet ditt er konfigurert med en utdata-gren,
så et vanlig `git push` kan havne der i stedet, uten at noe feiler. Onsdag
2. september 2026 skjedde nettopp det: kjøringen var grønn, artikkelen var
skrevet og god, men den lå på claude/eloquent-hawking-lwld4y i en draft-PR,
og eieren trodde i en uke at ingen artikkel var skrevet.

Push til main, og verifiser etterpå at det faktisk gikk dit:

    git fetch origin main
    git cat-file -e origin/main:drafts/{article_id}/article_draft.md && echo PAA_MAIN

Skriver den ikke PAA_MAIN, er utkastet IKKE levert. Si det rett ut til
eieren, med grennavn og PR-lenke der det faktisk havnet, så han kan hente det
over. Ikke rapporter suksess fordi kommandoene kjørte uten feil. En grønn
kjøring er ikke et levert utkast.

Å pushe et utkast publiserer ingenting.

Rapporter til meg PÅ NORSK: hvilken vinkel du valgte og hvorfor det er ukens
sak, lenke til utkastet på GitHub, resultatet av main-verifiseringen over,
hva du var usikker på, og spørsmål om det kan publiseres. IKKE kjør
publiseringsworkflowen.

Hvis noe feiler underveis MÅ du si fra til meg med en gang og forklare hva
som gikk galt. Ikke avslutt stille.
