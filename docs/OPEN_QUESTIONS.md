# Nyitott kérdések

Amit nem tudunk, amit kalibrálni kell, ami elakadt, ami ellentmondásos a
normatív dokumentumok között.

**Állapotjelölés:** `NYITOTT` · `FOLYAMATBAN` · `LEZÁRVA` (a lezárás
indoklásával és dátummal)

---

## A specifikáció által szándékosan nyitva hagyott paraméterek

Ezeket a specifikáció írója **szándékosan nem találta ki**, mert az kitalálás
lenne. Mind a backtesztből kell kijönnie.

### NY-01 — `w`, a piaci zsugorítás súlya · NYITOTT

**A legfontosabb egyetlen paraméter az egész rendszerben.**

- Jelenlegi érték: `0.35` (a `settings.yaml`-ban, **csak indulóérték**)
- Mit kell tenni: a validációs időszakon azt a `w`-t keresni, ami a legjobb
  **CLV**-t hozza (nem a legjobb P&L-t!)
- Hol: `modellek/kalibracio.py::optimalis_w()`
- Mikor: **Fázis 3**
- Megjegyzés: kezdetben inkább alacsonyabb (0,25–0,35), mert a modell fiatal
  és bizonytalan

### NY-02 — `ξ` (xi), a Dixon-Coles időbeli felejtés üteme · NYITOTT

- Jelenlegi érték: `0.0035` (kb. fél év alatt felezi a súlyt)
- **Ligánként külön** kell illeszteni
- Hol: `modellek/futball.py::illeszt()`
- Mikor: Fázis 2

### NY-03 — `ρ` (rho), az alacsony eredmények korrekciója · NYITOTT

- Az eredeti Dixon-Coles tanulmányban ≈ −0,13 angol adatokra
- **Ligánként újra kell illeszteni** — nem feltételezünk semmit
- Hol: `modellek/futball.py::illeszt()`
- Mikor: Fázis 2

### NY-04 — `σ_margó` és `σ_össz` a kosármodellhez · NYITOTT — BLOKKOLÓ

**Ez blokkolja a teljes kosármodellt.** A specifikáció kimondja: "amíg ez
nincs meg, a kosármodell nem ad javaslatot."

- A backteszt tényleges hibáinak szórásából kell becsülni
- **Ligánként külön** (az NBA és az EuroLeague nem ugyanaz)
- Hol: `modellek/kosar.py::sigma_becsles()`; a `kosar_aktiv()` addig `False`
- Mikor: Fázis 7

### NY-05 — A valódi `min_edge` küszöb · NYITOTT

- Jelenlegi: 5 pp délelőtt / 3,5 pp este
- A backteszt mondja meg, mi az a küszöb, ami után a fogadás ténylegesen megéri
- Mikor: Fázis 3

### NY-06 — A `min_odds: 1.30` / `max_odds: 6.00` sáv · NYITOTT

- Jó-e ez a sáv, vagy szűkíteni kell?
- Mikor: Fázis 3

---

## Ellentmondások a normatív dokumentumok között

### NY-07 — A Kelly-példatáblázat felfelé kerekít · LEZÁRVA (2026-09-17)

**A kérdés:** a specifikáció 9. lépésének példatáblázata két helyen eltér a
saját 7. szabályától.

| Eset | A spec példája | A spec 7. szabálya szerint | Eltérés |
| --- | --- | --- | --- |
| odds 3,50, p 0,331 | "800 Ft" | 700 Ft | a spec a kerekített f*=0,064-gyel számolt (a pontos 0,06357) |
| odds 6,00, p 0,197 | "455 → **500 Ft**" | 400 Ft | a spec **felfelé** kerekített |

**A spec 7. pontja szó szerint:** "Kerekítés 100 Ft-ra lefelé."
**A 6. pont indoklása:** "Nem kerekítünk fel, mert az felültetéléshez vezet."

**Döntés:** a **normatív szabály nyer** a példatáblázattal szemben. A kód
mindig lefelé kerekít. A példatáblázat illusztráció, kerekített
köztes értékekkel.

**Rögzítve:** `tests/test_kelly.py::test_spec_pelda_kozepes_szorzo` és
`::test_spec_pelda_magas_szorzo`, docstringben az indoklással.

---

### NY-08 — A gyanús piacok kiszűrése a döntési fából · NYITOTT

**A kérdés:** a `vig.py` most már jelzi, ha egy piac overroundja negatív vagy
szokatlanul magas (lásd [DECISIONS.md](DECISIONS.md) D-008). A **döntési fa
még nem használja fel** ezt a jelzést.

**Amit el kell dönteni:**

1. Új kiesési ok kell-e (`GYANUS_PIAC`), vagy a meglévő `NINCS_ODDS` alá
   tartozzon?
2. Hol legyen a fában? Logikailag az 1. pont (érvényes szorzó) után, a 2. pont
   (odds-tartomány) előtt.
3. A "szokatlanul magas overround" (>25%) is kiesést okozzon, vagy csak
   figyelmeztetést?

**Mikor:** Fázis 4, a döntési fa implementálásakor.

---

### NY-09 — E-mail időzítés: fix 18:00 vs. kezdés előtt 60-90 perc · NYITOTT

**Az ellentmondás:**

- A **kutatási jelentés** (Fázis 2 ajánlás): "kezdés előtt ~60–90 perccel a
  végleges, felállás-megerősített tippek (a felállások ~1 órával kezdés előtt
  jönnek)"
- A **specifikáció** (Áttekintés): fix 09:00 és 18:00 CET futás, és az esti
  futás "már megerősített felállásokkal" dolgozik

**A probléma:** egy 21:00-kor kezdődő meccs felállása kb. 20:00-kor jelenik
meg. A 18:00-s futás ezt **nem látja**. Így az esti futás a késői meccseknél
ugyanúgy a "nincs felállás" ágra fut, mint a délelőtti — de az alacsonyabb
(3,5 pp) küszöbbel, ami pont fordítva van, mint ahogy a spec indokolja.

**Lehetséges megoldások:**

| Opció | Előny | Hátrány |
| --- | --- | --- |
| Marad a fix 18:00 (spec) | egyszerű, kiszámítható | a késői meccseknél nincs felállás, de alacsony küszöb van |
| Az esti futás küszöbe meccsenként változik aszerint, hogy van-e felállás | pontos | bonyolultabb; a hírvétó `nincs_ellenorzes` ága már most emeli a küszöböt 1,5× |
| Harmadik futás 20:00-kor | követi a kutatást | több Actions-futás, több levél |

**Megjegyzés:** a spec hírvétó-szabálya (`hianyzo_forras_kuszob_szorzo: 1.5`)
részben már kezeli ezt — ha nincs felállás-adat, a küszöb 1,5×-ére nő. A
3,5 pp × 1,5 = 5,25 pp, ami magasabb, mint a délelőtti 5 pp. Tehát a
rendszer **már most helyesen viselkedik**, csak nem nyilvánvaló módon.

**Állapot:** valószínűleg nincs teendő, de a Fázis 5-ben (hírvétó
implementálása) ellenőrizni kell, hogy a küszöbemelés tényleg érvényesül-e.

---

### NY-10 — A kosármodell `liga_átlag` definíciója · NYITOTT

**A kérdés:** a specifikáció 5. lépésének képlete:

```
pont_hazai = (ORtg_hazai + DRtg_vendég - liga_átlag) / 100 × pace + hazai_előny/2
```

A `liga_átlag` pontos definíciója nincs megadva. Lehet:

- a liga átlagos ORtg-je (valószínű, mert az ORtg és DRtg ugyanabban a
  mértékegységben van)
- a liga átlagos ORtg + DRtg összege
- valami más normalizálás

A képlet csak akkor ad értelmes pontszámot, ha a `liga_átlag` az átlagos ORtg
(ami definíció szerint egyenlő az átlagos DRtg-vel). Akkor
`ORtg_hazai + DRtg_vendég - liga_átlag` egy korrigált támadóerő 100
birtoklásra, amit a pace-szel szorozva pontszámot kapunk.

**Mikor:** Fázis 7 elején tisztázni, mielőtt a kosármodell kódja íródik.

---

## Infrastrukturális bizonytalanságok

### NY-11 — A Tippmix odds-végpont pontos útvonala · FOLYAMATBAN — BLOKKOLÓ

**Ez blokkolja az 1. lépést, tehát az egész rendszert.**

**2026-09-18-i felderítés eredménye** (a felhasználó munkahelyi gépéről nem
volt elérhető az oldal — IT-szabályzat tiltja —, ezért a felderítést a
Claude-munkamenet kiszolgáló-oldali `curl`/`WebFetch` hívásai végezték,
tehát ismeretlen, nem magyar, feltehetően adatközponti IP-ről):

- A `tippmixpro.hu` egy Akamai CDN mögötti, szerveroldalon renderelt (SSR)
  React-alkalmazás. A `www.tippmixpro.hu` **200 OK-t adott kívülről is**,
  nincs látható geo-blokk a fő oldalon.
- A sportfogadási rész egy **iframe**, ami a `sports2.tippmixpro.hu/hu`
  oldalt tölti be. Ez is **200 OK-t adott kívülről**,
  `Access-Control-Allow-Origin: *` fejléccel (szándékosan nyitott CORS).
- A `sports2.tippmixpro.hu/robots.txt` tartalma: `User-agent: * / Disallow:`
  — **semmilyen bot semmilyen útvonalon nincs tiltva.**
- **A várt egyszerű JSON REST-végpont (amit a kutatási jelentés feltételezett)
  NEM létezik ebben a formában.** Ehelyett:
  - Az oldal konfigurációja: `apiConfig.host = "https://sports-api.everymatrix.com"`,
    `sportsApiConfig.ucsOperatorId = 2901` (a Tippmix Pro operátor-azonosítója
    az EveryMatrix rendszerben), `webApi.realm = "www.tippmixpro.hu"`.
  - A tényleges élő odds-adat **WebSocket-en (`wss://sportsapi.tippmixpro.hu/v2`)
    érkezik**, egy saját, nem szabványos protokollon (`reconnectDetails`,
    `onQuotaLimitHandler`, `onChallengeHandler` mintákkal a kliens kódban) —
    ez NEM sima socket.io vagy egyszerű pub/sub, hanem egyedi keretezés.
  - A kliens JS-ben (`chunk.source~main.js`, 3,8 MB) nem található közvetlen
    REST-URL-minta az odds-listára; a `.get("odds-*")` hívások widget-
    konfigurációt kérnek le (pl. `.get("odds-banner")`), nem eseményadatot.
  - **Nem sikerült publikus dokumentáció vagy kódrészlet nélkül
    rekonstruálni a WS-handshake pontos formátumát** (autentikáció,
    subscribe-üzenet formátuma, az `operatorId`-n és a `realm`-en túl mit
    kell még küldeni).

**Következmény a tervre:** a kutatási jelentés "JSON, numerikus eventId,
markets[]→outcomes[]" feltételezése **valószínűleg elavult vagy pontatlan**
volt — lehet, hogy egy régebbi platformverzióra vonatkozott, vagy a
`Apify caleno/tippmixpro-odds-scraper` más, nem publikus végpontot használ,
amit reverse engineeringgel derített ki (böngésző Network fülén, valódi
felhasználói munkamenetben, ahol a WS-forgalom is látszik JSON-üzenetenként).

**Amit még ki kell deríteni, és HOGYAN:**

1. **A WS-protokoll pontos üzenetformátuma.** Ehhez egy éles böngészőben,
   Network fülön (WS tab) kell figyelni a `wss://sportsapi.tippmixpro.hu/v2`
   forgalmát — ez `curl`-lal vagy szerveroldali fetch-csel nem deríthető ki,
   mert a WS handshake és az azt követő üzenetek bináris/JSON keretezése
   böngészőn kívül nem triviálisan reprodukálható. **Ez a felhasználó
   munkahelyi gépéről nem megy** (IT-tiltás) — otthoni gépről vagy
   telefonról (mobilnetről, ha az oldal ott elérhető) kellene megnézni.
2. **Alternatíva: a Playwright-alapú headless böngésző út.** Mivel a
   `pyproject.toml` már tartalmazza a Playwright-ot tartaléknak, ez lehet
   az elsődleges megoldás, nem a tartalék: egy fejnélküli Chromium
   megnyitja az oldalt, végrehajtja a JS-t, és a WS-üzeneteket a
   `page.on("websocket")` eseménnyel el lehet csípni programozottan —
   így nem kell a protokollt kézzel reverse engineeringelni, a böngésző
   csinálja meg helyettünk, mi csak "hallgatózunk". Ez lassabb és
   erőforrás-igényesebb, mint egy sima HTTP GET, de megbízhatóbb, mint
   egy félig kitalált WS-kliens.
3. **A meglévő Apify-scraper tanulmányozása** (`caleno/tippmixpro-odds-scraper`)
   — ha publikus a forráskódja vagy legalább a dokumentációja, abból
   kiderülhet, hogy REST-et vagy WS-t használ, és ha REST-et, milyen
   végpontot.

**Mikor:** Fázis 0, folytatás — jelenleg itt tartunk.

### NY-12 — Blokkolja-e a Tippmix a GitHub Actions IP-ket? · RÉSZBEN LEZÁRVA (2026-09-18)

- **A fő domain (`www.tippmixpro.hu`) és a `sports2.tippmixpro.hu` NEM
  blokkolt** ismeretlen, feltehetően adatközponti IP-ről sem — mindkettő
  200 OK-t adott egy Claude-munkamenet szerveroldali HTTP-kliensének
  kéréseire, semmilyen Cloudflare/Akamai bot-kihívás vagy geo-tiltás nem
  jelentkezett a sima oldal-lekéréseknél.
- **Ez még NEM bizonyítja, hogy a WS-végpont (`wss://sportsapi.tippmixpro.hu/v2`)**
  is ugyanígy elérhető-e — a WS-handshake más védelmi réteget kaphat, ezt
  külön kell tesztelni, ha kiderül a protokoll formátuma.
- **Ez sem magyar IP-ről történt teszt** — tehát a "fogadás Magyarországra
  korlátozott" kutatási megállapítás (a beléptetés/fogadás szintjén) itt
  nem cáfolható vagy erősíthető meg, csak az, hogy a puszta oldal-lekérés
  nem geo-blokkolt.
- **Tényleges GitHub Actions runner IP-ről még nem volt teszt** — a fenti
  csak azt mutatja, hogy NEM minden külső/adatközponti IP van blokkolva,
  de a GitHub Actions IP-tartományai specifikusan lehetnek feketelistán,
  amit csak egy tényleges Actions-workflow-futással lehet kizárni.
- Ha a WS-út túl bonyolultnak bizonyul, vagy blokkolva lesz Actionsből:
  a scraping a felhasználó windowsos gépére kerül (önhosztolt runner vagy
  Task Scheduler) — ez már a terv része volt.
- Mikor: Fázis 0, folytatás

### NY-13 — A `stats.nba.com` adatközponti IP-blokkja · NYITOTT

- A kutatás szerint **igazoltan blokkolja** az AWS/GCP/Azure IP-ket, tehát
  valószínűleg a GitHub Actions runnereket is
- A `cdn.nba.com` live végpontok viszont bárhonnan működnek
- Tartalék: Basketball-Reference
- Mikor: Fázis 0 (teszt), Fázis 7 (megoldás)

### NY-14 — A robots.txt tényleges tartalma · NYITOTT

- A kutatás **nem tudta verifikálni** a `tippmixpro.hu/robots.txt`-t
- A Részvételi Szabályzat nem tilt kifejezetten scrapelést, de van általános
  "nem rendeltetésszerű használat" klauzula
- Mit kell tenni: letölteni és **ténylegesen elolvasni** mindkét hoston,
  majd tartani magunkat hozzá
- Mikor: **Fázis 0, a végpont-felderítéssel együtt**

### NY-15 — EuroLeague történelmi záró odds · NYITOTT

- Ingyenesen **gyakorlatilag nem elérhető**
- Ez valós korlát: EuroLeague-re nem tudunk becsületes backtesztet csinálni
- Ezért a `config/ligak.yaml`-ban az EuroLeague `aktiv: false`
- Lehetséges megoldás: OddsPortal-scrapelés (OddsHarvester), ToS-kockázattal
- Mikor: Fázis 7, ha egyáltalán

---

## Módszertani kérdések, amikre később kell válasz

### NY-16 — A backteszt újrafittelési gyakorisága · NYITOTT

A specifikáció azt írja: a modellparamétereket "**minden fordulóra** újra kell
illeszteni". Ez a becsületes módszer, de lassú.

**A kérdés:** mennyit veszítünk, ha 7 naponta illesztünk újra? Ezt mérni kell,
nem feltételezni. A `backteszt/keret.py::walk_forward()` `ujrafittelés_naponta`
paramétere ezt paraméterezhetővé teszi.

**Mikor:** Fázis 2

### NY-17 — Bankroll-frissítés automatizálása · NYITOTT

Jelenleg a `bankroll.aktuális_ft` kézi érték a `settings.yaml`-ban. A
specifikáció megengedi, hogy a napló számolja.

**A kérdés:** mikor kapcsoljuk be az automatikus számolást? A spec figyelmeztet:
"amíg kézi, ne frissítsd naponta — heti egyszer elég, különben a tét ugrál."

Ha automatikus lesz, ugyanez a probléma jelentkezik, csak nagyobb
gyakorisággal. Valószínűleg heti átlagolás kell.

**Mikor:** Fázis 5-6

### NY-18 — Kezdeti `kelly_hányad`: 0,25 vagy 0,15? · NYITOTT

A specifikáció 9. lépése: "Kezdetben ez is lehet túl sok; a `kelly_hányad`
0,15-re csökkentése védekezőbb indulás."

A `settings.yaml`-ban jelenleg **0,25** van (a spec konfigurációs szakasza
szerint). Élesítés előtt el kell dönteni, hogy 0,15-tel induljunk-e.

**Mikor:** Fázis 6 (élesítés) előtt
