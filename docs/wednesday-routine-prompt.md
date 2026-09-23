# Wednesday routine prompt (Ukentlig utkast-gjennomgang)

Copy of the prompt stored in the routine. Keep the two in sync. Changed on
2026-09-23: topics now come from FEATURE_IDEAS.md as explanatory features
instead of contested news angles, and the report must always carry the link.

---

Ukens Artemis Briefing-artikkel. Følg WEEKLY_REVIEW.md i repoet
grandmasterjc/artemis2-config, og les ARTICLE_STYLE.md i sin helhet før du
skriver noe. Den er fasiten for stemme, struktur, språk, kildebruk,
anti-tells, CTA-tekst og lengde.

Hent siste main. Sjekk state/publish_history.txt og drafts/ så du verken
gjentar et tema eller lager et duplikat av noe som allerede ligger der.
Finnes det allerede et utkast for denne uken, vurder det i stedet for å
skrive et nytt, og si fra om det.

Artikkelen er en forklarende feature-artikkel, av typen som kunne stått på
trykk i Illustrert Vitenskap: den besvarer et spørsmål mange lesere har, med
konkrete tall og tydelig forklaring av hvordan ting virker. Ta temaet fra
FEATURE_IDEAS.md: øverste idé med status open, etter reglene i den filen.
Ikke tving temaet inn i en kritisk nyhetsvinkling («NASA/SpaceX er
forsinket»). En aktuell hendelse kan brukes som inngang, men er ikke et krav.
Research temaet med websøk og verifiser nøkkelpåstander mot primærkilder.
Merk ideen som used i FEATURE_IDEAS.md i samme commit som utkastet.

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

Rapporter til meg PÅ NORSK: hvilket tema du valgte og hvorfor, lenke til
utkastet på GitHub, resultatet av main-verifiseringen over, hva du var
usikker på, og spørsmål om det kan publiseres. Lenken til artikkelen SKAL stå
både i sluttsvaret og i varselet, hver gang. IKKE kjør
publiseringsworkflowen.

Hvis noe feiler underveis MÅ du si fra til meg med en gang og forklare hva
som gikk galt. Ikke avslutt stille.
