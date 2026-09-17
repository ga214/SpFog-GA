# Automatizált sportfogadási tipprendszer Tippmix Pro-ra — kutatási jelentés és architektúra-ajánlás

## TL;DR
- **A legnagyobb technikai kockázat nem a modellezés, hanem az adatbeszerzés:** a tippmixpro.hu egy EveryMatrix OddsMatrix motorra épülő JavaScript SPA, amelynek nyilvános odds-oldalai láthatók bejelentkezés nélkül és részben elérhetők adatközponti IP-ről is, de a fogadás/belépés Magyarországra van geo-korlátozva; a stats.nba.com viszont igazoltan blokkolja az adatközponti (GitHub Actions) IP-ket — ezért **hibrid infrastruktúrát** javaslok (GitHub Actions a legtöbb feladatra + saját windowsos PC/önhosztolt runner a geo-érzékeny scrapeléshez).
- **Ingyenesen bőven van elég adat a backteszthez:** futballra a football-data.co.uk (záró oddsokkal), Understat (xG 2014/15-től), FBref/soccerdata és ClubElo; kosárra az nba_api és euroleague-api; történelmi zárási oddsok kosárra a sportsbookreviewsonline.com Excel-archívumából és Kaggle-ről ingyen. Fizetős, amint Tippmix-specifikus vagy friss élő oddsot akarsz nemzetközi API-ból.
- **Kezdd a legtraktálhatóbb piacokkal:** futballban Over/Under 2.5 gól és 1X2 Dixon–Coles / bivariate Poisson modellel, kosárban totals és spread; kerüld a hosszú kombinációkat (a margó minden lábbal exponenciálisan halmozódik), maximum 2–3 lábas +EV kombinációkat használj, és a tétezésben frakcionált Kelly-t (¼ vagy kevesebb) alkalmazz. A siker mércéje a **CLV (closing line value)**, nem a rövid távú profit.

## Key Findings

1. **Tippmix Pro platform (EveryMatrix OddsMatrix).** A Tippmix Pro-t 2023. november 2. óta az EveryMatrix OddsMatrix sportsbook-motorja hajtja; a közbeszerzést az EveryMatrix 2023. január 18-án jelentette be, egy 15 hónapos, 25+ ajánlattevős eljárás lezárásaként. A honlap kliensoldali renderelésű SPA; az odds-adatok a `sports2.tippmixpro.hu` hoston keresztül, strukturált JSON-ként, numerikus eventId szerint érhetők el; a statisztikákat a Sportradar szolgáltatja. Létező scraperek (Apify „caleno/tippmixpro-odds-scraper", Spider Cloud) bizonyítják, hogy az odds gépileg kinyerhető, de a pontos nyers végpont-útvonalak nem publikusak.

2. **Maximális nyeremény: 2 000 000 HUF egységnyi fogadásonként** (nem szelvényenként) a Tippmix Pro online terméknél — ezt a hivatalos Részvételi Szabályzat és az élő fogadószelvény-felület is megerősíti. A gyakran emlegetett 400 000 HUF a retail (papír) Tippmix termékre vonatkozik, nem a Pro-ra. Min. tét 100 HUF, max. tét 100 000 HUF egységnyi fogadásonként.

3. **Fogadási típusok.** Egységnyi fogadás: 1–50 esemény. Normál fogadás „kötés nélkül" (1-es kötés) vagy „kötésben" (halmozott, 2–50 esemény, oddsok szorzódnak). Kombinált fogadás: rendszerfogadás (pl. 4/5, Lucky 15). A kombinációban az egységnyi fogadások tétje min. 10 HUF. Az SzZrt. megtilthatja az ugyanahhoz az eseményhez tartozó kimenetelek kötésben történő fogadását (kötéstiltás, vörös felkiáltójel jelzi).

4. **Geo-korlátozás.** A nyilvános odds-oldalak láthatók külföldről is (sikeres fetch-ek, működő felhő-alapú scraperek), de a belépés/fogadás Magyarországra korlátozott (fórumbejegyzések: külföldről „az adott országból tiltott a fogadás"). A testvéroldal tippmix.hu aktívan, IP alapján blokkol — tehát a szelektív adatközponti/VPN IP-blokkolás képessége megvan. Hogy a GitHub Actions runner IP-ket konkrétan blokkolja-e, nem verifikálható publikusan; empirikusan tesztelni kell.

5. **GitHub Actions korlátok.** A GitHub Docs (billing) szerint publikus repóknál a GitHub Actions ingyenes és korlátlan percidőt ad; privát repóknál a **Free csomag 2 000 standard-runner perc/hó + 500 MB tárhely** (Pro/Team 3 000 perc, Enterprise Cloud 50 000 perc). A cron ütemezés csak a default branchen fut, csak UTC-ben, és nagy terhelésnél 15+ percet késhet. Publikus repóknál 60 nap inaktivitás után az ütemezett workflow automatikusan letiltódik (keepalive akcióval megkerülhető). A runnerek US/EU adatközpontokban futnak, földrajzuk nem befolyásolható.

## Details

### 1. Tippmix / Tippmix Pro platform

**Tippmix vs. Tippmix Pro.** A „Tippmix" a retail (lottózói/papír) fogadás; a „Tippmix Pro" a kizárólag online, EveryMatrix OddsMatrix motorra épülő távszerencsejáték-termék. A jogi alap: 1991. évi XXXIV. törvény, 20/2021. (X.29.) SZTFH rendelet, Ptk. Az engedély 2022. október 24. – 2027. október 23. között érvényes.

**Fogadási típusok és tétek (Tippmix Pro, Részvételi Szabályzat 2024-07-23-tól / 2026-06-08-tól):**
- Egységnyi fogadás: min. 1, max. 50 esemény. Akkor nyer, ha minden benne lévő esemény kimenetelét eltalálta.
- Normál fogadás: „kötés nélkül" (1-es kötésszám) vagy „kötésben" (halmozott, 2–50 esemény).
- Kombinált fogadás (rendszerfogadás): adott kombinációtípus (pl. 4/5) által meghatározott számú egységnyi fogadás egyszerre; speciális kombinációk (Lucky 15 stb.).
- Egységnyi fogadás tétje technikailag 1 Ft, de a normál és kombinált fogadás min. tétösszege 100 HUF; kombinációban az egységnyi fogadások tétje min. 10 HUF.
- Max. tét: 100 000 HUF egységnyi fogadásonként.
- **Max. nyeremény: 2 000 000 HUF egységnyi fogadásonként** (pénzügyi kockázatkezelés, csalás/pénzmosás gyanúja, felelős játékszervezés miatt az SzZrt. eseti korlátozást is alkalmazhat).

**Piacok kombinálásának korlátai:** az SzZrt. megtilthatja ugyanahhoz az eseményhez tartozó kimenetelek együttes (kötésben történő) fogadását; a tiltást a felületen jelzik (pl. vörös felkiáltójel). Ez fontos a kombináció-generátornak: a rendszernek tiszteletben kell tartania a kötéstiltást, és nem szabad ugyanabból az eseményből több lábat egy szelvényre tenni (korreláció + platformtiltás).

**Odds-adat láthatósága és API.** A tippmixpro.hu kliensoldali SPA (a HTML shell feloldatlan i18n tokeneket tartalmaz, pl. `global_loginBtnText_hu`, plusz build verzió pl. `1.0.621`). Az odds-feed az OddsMatrix backend; a `sports2.tippmixpro.hu` hoston keresztül érhető el, strukturált JSON-ként, numerikus eventId szerint (pl. `308741329561284608`), `markets[]`→`outcomes[]`→`{name, side, odds}` szerkezettel. A pontos nyers végpontok nem publikusak. Létező eszközök: Apify „caleno/tippmixpro-odds-scraper" (250+ piac), Spider Cloud tippmixpro/tippmix scraper. Az eredmények elsődleges forrása maga az EveryMatrix Software Limited (a Szabályzat szerint).

**ToS / robots.txt.** A Részvételi Szabályzatban **nem található kifejezett tiltás** a scrapelésre, botokra vagy automatizált hozzáférésre; csak általános „nem rendeltetésszerű / visszaélésszerű használat" elleni fenntartás van (fiók-szint). A robots.txt tartalmát nem sikerült verifikálni; az oldalak `meta name="robots" content="index, follow"`-t hordoznak (ez csak meta-robots, nem a robots.txt). **Jogi/ToS kockázat:** a fogadás külföldről tiltott; az odds nyilvános olvasása gépi úton nincs kifejezetten tiltva, de a fiók-visszaélési klauzula elvben alkalmazható lehet. Óvatos, alacsony frekvenciájú lekérést és a robots.txt tényleges ellenőrzését javaslom.

### 2. Ingyenes történelmi adat — FUTBALL

- **football-data.co.uk** — a backteszt gerince. ~22 európai liga (Anglia 5 szint, Skócia, Németország, Olaszország, Spanyolország, Franciaország, Hollandia, Belgium, Portugália, Törökország, Görögország + „extra" fájlokban sok más). CSV formátum, ingyenes. Oszlopok: teljes/félidei eredmény, lövések, kaput eltaláló lövések, szögletek, faultok, sárga/piros lapok, valamint nyitó ÉS zárási oddsok több fogadóirodától (Bet365, Pinnacle, William Hill stb.), 1X2, Over/Under 2.5 és ázsiai hendikep piacokon (a zárási oddsokat „C" jelöli, pl. `B365CH`, `PSCH`; `PAHH`/`PAHA` a Pinnacle ázsiai hendikep). Angol adatok az 1993/94 szezontól; oddsok a 2000-es évek elejétől. Ez az egyetlen forrás, amely eredményt ÉS zárási oddsot egyben, ingyen ad — kulcsfontosságú a CLV-méréshez.
- **Understat** — xG (expected goals) a 2014/15 szezontól, 6 liga (Premier League, La Liga, Bundesliga, Serie A, Ligue 1, RFPL). Az adat JSON-ként a HTML script tagekbe ágyazva, API-kulcs nélkül elérhető. Python: `understatapi` (MIT licenc, pip). Meccs-, csapat-, játékos- és lövésszintű xG. Ingyenes, de nem hivatalos scraping.
- **soccerdata** (Python csomag) — egységes wrapper FBref, Understat, ClubElo, WhoScored, SofaScore, MatchHistory (football-data.co.uk) forrásokhoz. Ez a leghatékonyabb egyablakos megoldás.
- **FBref / StatsBomb** — mély per-meccs és xG-adatok sok ligára, ingyenes olvasásra; a StatsBomb open data (GitHub, ingyenes, nem-kereskedelmi licenc) néhány versenyre részletes eseményadatot ad.
- **ClubElo** — ingyenes Elo-értékelések napi bontásban, CSV API-val, sok európai ligára; kiváló feature-nek.
- **API-Football (api-sports.io)** — ingyenes tier: 100 kérés/nap, 10 kérés/perc, minden végpont és 1200+ liga, de a történelmi szezonok korlátozottak és 100 kérés/nap kevés napi automatizáláshoz. xG-lefedettsége inkonzisztens. Fizetős: Pro 19 USD/hó (7500 kérés/nap).
- **football-data.org** — ingyenes: 12 nagy liga/kupa, 10 kérés/perc, „free forever"; jó fixture-forrás, de statisztikai mélység korlátozott.
- **OpenFootball** — nyílt, közösségi eredmény/menetrend-adat (nincs odds, nincs mély statisztika).

**xG upcoming fixture-ekre ingyen:** Understat közli a soron következő meccsek xG-alapú előrejelzését is; egyébként a legtöbb ingyenes forrás történelmi xG-t ad, előremutatót nem.

**Kelet-európai / alsóbb ligák:** a football-data.co.uk „extra" fájljai (pl. lengyel, orosz, román, dán, svéd stb.) adnak eredményt+oddsot, de sekélyebb statisztikát; xG ezekre jellemzően nem elérhető ingyen. A Tippmix Pro kínálatában szereplő egzotikusabb ligákra az adatlefedettség a fő korlát — itt a modell konfidenciáját csökkenteni kell vagy ki kell hagyni.

### 3. Ingyenes történelmi adat — KOSÁRLABDA

- **nba_api** (swar/nba_api, MIT licenc) — a hivatalos stats.nba.com végpontok Python-wrappere; per-meccs, per-játékos, box score, play-by-play, shot chart. **Kritikus korlát:** a stats.nba.com Akamai bot-védelem és TLS-fingerprinting mögött van, és **csendben eldobja az adatközponti IP-ket (AWS, GCP, Azure — és így valószínűleg a GitHub Actions runnereket is)**. A `cdn.nba.com` live végpontok (scoreboard, boxscore) viszont bárhonnan működnek. Rate limit dokumentálatlan; konzervatív ~600 ms–2 s késleltetés ajánlott a 429 elkerülésére.
- **Basketball-Reference** — tiszta történelmi box-score adat scrapelésre (nincs koordináta), sok szezonra visszamenőleg; jó, stabil alternatíva az nba_api adatközpont-blokk problémájára.
- **euroleague-api** (giasemidis, PyPI) — EuroLeague és EuroCup: meccs-, játékos-, csapat-statisztika, standings, shot data, play-by-play, boxscore. A `live.euroleague.net/api/` végpontokra épül. Kaggle-en frissített CSV-datasetek is elérhetők (babissamothrakis/euroleague-datasets).
- **Történelmi zárási ODDS kosárra (a kritikus nyitott kérdés):**
  - **sportsbookreviewsonline.com** — ingyenes Excel-archívum NBA-ra (nyitó/záró spread, moneyline, totals, félidők), szezononként. (Megjegyzés: az NBA-archívum a jelzés szerint nem frissül tovább, de a történelmi backteszthez elég.)
  - **Kaggle** — pl. „NBA Historical Stats and Betting Data" (ehallmar) dataset match stats + odds.
  - **BigDataBall** — NBA odds/box/play-by-play Excelben, de fizetős (play-by-play 2002-03-tól).
  - EuroLeague-re ingyenes történelmi zárási odds **gyakorlatilag nem elérhető** — ez valós korlát; EuroLeague backteszthez az oddsokat vagy a The Odds API történelmi végpontjából (fizetős), vagy OddsPortal-scrapeléssel (OddsHarvester) kell beszerezni.

### 4. Történelmi oddsok backteszthez (átfogó)

- **football-data.co.uk** — ingyen, záró oddsokkal (lásd fent). Ez a futball-backteszt alapja.
- **OddsPortal + OddsHarvester** (jordantete/OddsHarvester, GitHub) — Playwright-alapú scraper, 11 sportág, 100+ liga, upcoming és historikus oddsok, JSON/CSV kimenet. Ingyenes, de scrapelés (ToS-kockázat, IP-blokk lehetséges). Jó a football-data.co.uk által nem fedett ligákra/kosárra.
- **The Odds API (the-odds-api.com)** — ingyenes tier: 500 kredit/hó; a `/odds` hívás költsége = piacok × régiók kredit, a `/historical` ennek **10-szerese** (`historical_odds_cost = 10 × number_of_markets × number_of_regions`), azaz az 500 ingyenes kredit egyetlen piac/egy régió esetén is csak ~50 történelmi hívásra elég, több piacnál sokkal kevesebbre — **backtesztre alkalmatlan**. Lefedettség: az API „a legtöbb" fogadóirodát fedi, ami a gyakorlatban ~40 mainstream „soft" irodát jelent (Bet365, DraftKings, FanDuel, William Hill), **Pinnacle nélkül**; magyar fogadóirodát nem fed. Fizetős: kb. 20–199 USD/hó között; a Pinnacle és a teljes történelmi archívum a magasabb csomagokban. Nincs magyar (Tippmix) odds.
- Alternatívák (OddsPapi, SportsGameOdds, SharpAPI) — nagyobb ingyenes lefedettséget hirdetnek (350+ iroda, Pinnacle, ingyenes történelmi), de marketing-forrásból; verifikálni kell éles használat előtt.

**Fontos következtetés:** a nemzetközi oddsokat (Pinnacle, Betfair) csak belső sanity-checkként használd (a követelmény szerint), és a CLV-t a Pinnacle záró vonalához mérd, mivel az a legélesebb, legalacsonyabb margójú (1–3%) referencia.

### 5. Modellezési módszertan

**Futball.**
- **Poisson / bivariate Poisson / Dixon–Coles.** Alap: a hazai és vendég gólokat Poisson-eloszlással modellezed csapat-támadó/-védő erősség + hazai pálya előny paraméterekkel. A **Dixon–Coles (1997)** korrekció [Dixon, M.J. & Coles, S.G. (1997), „Modelling Association Football Scores and Inefficiencies in the Football Betting Market", *Journal of the Royal Statistical Society: Series C (Applied Statistics)*, 46(2):265–280, angol ligás és kupaadatok 1992–1995] (a) egy interakciós taggal növeli az alacsony eredmények (0-0, 1-0, 0-1, 1-1) valószínűségét — a ρ ≈ −0,13 az eredeti angol ligás adatokra illesztett érték, amely azóta is standard kiindulás, de ligánként érdemes újrafittelni —, és (b) időbeli súlyozást ad (frissebb meccsek nagyobb súllyal). A Dixon–Coles ma is az egyik vezető baseline, amit ML-lel nem sikerült szignifikánsan megverni.
- **Piacok traktálhatósága / margó.** A legalacsonyabb margó és legjobb likviditás az **1X2, Over/Under 2.5 gól és ázsiai hendikep** piacokon van; ezek a legjobban modellezhetők Poisson-családdal. A BTTS és pontos eredmény nehezebb. A publikált out-of-sample eredmények **vegyesek**: egy 2023–24 Premier League backteszt szerint a Dixon–Coles önmagában **−15,4% ROI**-t ért el (249 fogadás), miközben egy tapasztalt „human quant" +5,1%-ot (39 fogadás) — azaz a nyereség a kalibrációból, value-szűrésből és tétfegyelemből jön, nem pusztán a modellből. Reálisan a nyers modell alulmarad a záró vonallal szemben; az edge a szelektív, +EV fogadásokban van.
- **Elo / ClubElo, bayesi hierarchikus modellek, xG-alapú modellek** kiegészítő feature-ök; az xG jobb előrejelző a nyers góloknál.

**Kosárlabda.**
- Megközelítések: **Elo**, Four Factors (eFG%, TOV%, ORB%, FT rate), possession-alapú offenzív/defenzív rating (pace-adjusted), pihenő/back-to-back hatás, hazai pálya előny (NBA-ben mérsékelt, EuroLeague-ben jellemzően nagyobb). A back-to-back és utazási fáradtság kimutatható, kihasználható jel.
- **Piacok:** a totals és a spread a leginkább modellezhető; a moneyline nehéz favoritoknál (favourite-longshot bias).

**Ismert piaci inefficienciák:** favourite–longshot bias (a longshotokat túlárazzák — a favoritokra fogadás magas találati arány, negatív hozam); túlreagálás a friss eredményekre; a **CLV (closing line value)** a legmegbízhatóbb skill-mérce.

**Kombinációk matematikája.** A bookmaker margója **lábanként exponenciálisan halmozódik**: 5%-os lábankénti margónál egy 2 lábas kombináció ~10%, 4 lábas ~(1,05)⁴−1 ≈ 21,6%, 5 lábas ~27,6%, 10 lábas ~40–60% effektív házelőny. Konkrét szám: 5 lábas, egyenként 5% margós, valódi p⁵ nyerési eséllyel a várható kifizetés ~77 fillér/1 forint (−23%). **+EV kombináció csak akkor lehetséges, ha minden láb önmagában +EV** (a modell valószínűsége meghaladja a margóval korrigált implikált valószínűséget), és a lábak függetlenek (nem korreláltak, nem ugyanabból az eseményből). Ekkor a dupla (2 láb, egyenként ~5% edge) nettó pozitív maradhat, a treble kb. break-even. **Ajánlás: max. 2–3 láb, kizárólag önállóan +EV lábakból** — a 4 lábas felső határt (a felhasználó követelménye) csak kivételesen, erős edge-nél használd.

**Vig eltávolítása.** Decimál odds → implikált valószínűség = 1/odds; az összeg 1 fölé megy (overround). Eltávolítási módszerek: **proportional/multiplicative** (egyszerű, de nem kezeli a favourite-longshot bias-t), **power** (exponenssel, jó általános választás), **Shin** (iteratív, információs aszimmetriát feltételez, akadémiailag a legmegalapozottabb; 2 kimenetelnél az additive-vel ekvivalens). **Ajánlás: a power módszer** a modellezés alapértelmezettje (kezeli a bias-t, valid tartományban marad); a Pinnacle-konszenzus kinyerésére a Shin. A proportional legyen a stabil referencia.

**Tétezés.** Kelly-formula: f\* = (p·o − 1)/(o − 1) = edge/nettó odds. A teljes Kelly rendkívül volatilis (X% eséllyel X%-os drawdown), és modell-bizonytalanságnál túl-tétel. **Ajánlás kis bankrollra (50 000 HUF) és bizonytalan modellnél: ¼ Kelly vagy kevesebb** (a szakma 25–50%-ot használ; kezdőknek/kis bankrollra 20% is indokolt), plusz kemény tételplafon. A követelmény szerinti 200–5000 HUF sáv jól illeszkedik: a ¼-Kelly tét legyen a [200, 5000] HUF-ba vágva. Kombinációra a Kelly-tétet a kombináció eredő edge-ére és eredő oddsára számold, de konzervatívabban (nagyobb bizonytalanság).

**Mintaméret (skill vs. szerencse).** Realisztikus 2–5% ROI mellett a statisztikai szignifikancia eléréséhez **több száz–több ezer fogadás** kell; néhány tucat fogadás (mint a fenti +5,1%-os human quant 39 fogadása) nagy varianciájú, nem bizonyít edge-et. Nagyságrendi tájékozódásként: közel-even oddsnál a fogadásonkénti hozam szórása ~1 egység, így n fogadáson a becsült ROI standard hibája ~1/√n; egy 3%-os valódi edge ~2σ-s (kb. 95%-os) kimutatásához n ≈ (2/0,03)² ≈ 4400 fogadás kell, 5%-os edge-hez ~1600. Ezért a backteszt legyen 2–3 év, több liga, és a value-t a **CLV-vel is validáld**, ne csak a P&L-lel (a CLV sokkal kevesebb mintán ad megbízható jelet).

### 6. Hír- és felállás-adat

- **Futball:** API-Football ad sérülés/felállás-adatot (ingyenes tieren korlátozottan); a megerősített kezdőcsapatok jellemzően a kezdés előtt ~1 órával jelennek meg. FBref/soccerdata és a sajtó (RSS). Ingyenes, automatizálható RSS-forrás a nagy ligákra korlátozott.
- **Kosár:** az **NBA hivatalos Injury Report** (PDF, meccsnap előtti fix időpontokban frissül) az elsődleges forrás; parse-olható. EuroLeague-re a hivatalos oldal + euroleague-api.
- **Override-logika:** a hírréteg vétózhat egy tippet (kulcsjátékos-sérülés, eltiltás, rotáció, motivációhiány). Az e-mail időzítését a felállások megjelenéséhez kell igazítani (lásd lent).

### 7. Infrastruktúra

- **GitHub Actions.** Publikus repo: ingyenes, korlátlan perc. Privát repo: **2 000 standard-runner perc/hó + 500 MB tárhely** a Free csomagban (Pro/Team 3 000 perc, Enterprise Cloud 50 000 perc; a nagyobb runnerek sosem esnek a keretbe). Cron: csak default branch, csak UTC, nagy terhelésnél 15+ perc késés (nem alkalmas percre pontos feladatra). Publikus repóban 60 nap inaktivitás után az ütemezett workflow letiltódik — keepalive akcióval (gautamkrishnar/keepalive-workflow vagy efrecon/gh-action-keepalive) megkerülhető. Runnerek US/EU adatközpontban; földrajz nem befolyásolható → **adatközponti IP**, ami a stats.nba.com és potenciálisan a tippmixpro.hu geo/bot-szűrésébe ütközhet.
- **Geo-probléma megoldásai:** (a) a geo-érzékeny scrapelést (Tippmix Pro odds, esetleg nba_api) futtasd a **saját windowsos PC-den** (magyar residenciális IP) egy önhosztolt GitHub Actions runnerrel vagy ütemezett Task Schedulerrel; (b) a modellezést, e-mailt, nem-geo-érzékeny adatgyűjtést GitHub Actionsön. Ingyenes európai/magyar egress IP-t adó felhő free tier gyakorlatilag nincs megbízhatóan; a saját PC a legbiztosabb magyar IP-forrás.
- **E-mail Pythonból.** Gmail SMTP + **app-jelszó** (a rendes jelszó nem működik 2FA-val), a titkokat **GitHub Secrets**-ben tárold (soha ne a repóban). Alternatíva: dedikált e-mail-küldő (pl. transactional SMTP) — de a Gmail app-jelszó ingyenes és elég.
- **Perzisztens tárolás.** Opciók: (a) **SQLite fájl visszacommitolása a repóba** minden futás végén (egyszerű, verziózott, ingyenes, kis adatnál ideális); (b) **Turso** (libSQL/SQLite-kompatibilis felhő; ingyenes tier: 5 GB tárhely, ~500M sorolvasás/hó, ~10M sorírás/hó, nincs kényszerszünet); (c) **Supabase** (Postgres; ingyenes tier 2 projekt, 500 MB, de **7 nap inaktivitás után szünetelteti** a projektet — kényelmetlen ütemezett jobhoz); (d) GitHub artifacts (átmeneti, 90 nap). **Ajánlás: SQLite a repóban** kezdetnek, később Turso, ha nő az adat.

### 8. Létező open-source projektek

- **jordantete/OddsHarvester** — OddsPortal scraper (Playwright), upcoming+historic oddsok, 11 sport, 100+ liga, JSON/CSV. Hasznos oddsforrás.
- **swar/nba_api** (MIT) — NBA statisztikai wrapper.
- **giasemidis/euroleague_api** — EuroLeague/EuroCup adat.
- **collinb9/understatapi** (MIT) — Understat xG.
- **soccerdata** — egységes futball-adat wrapper (FBref, Understat, ClubElo, MatchHistory).
- **dashee87** blog + kód — Dixon–Coles/Poisson Python-implementáció (tananyagnak kiváló).
- **opisthokonta.net** — Dixon–Coles, Conway–Maxwell–Poisson backtesztek (módszertan).
- **tanamsethi31/footymodel** — Dixon–Coles + lineup-aware, walk-forward backteszt a záró oddsokkal (studyra érdemes, ellenőrizd a licencet).

## Recommendations

**Fázis 0 — verifikáció (első hét).**
1. Teszteld empirikusan egy GitHub Actions runnerről ÉS a saját magyar IP-dről: (a) betölt-e a tippmixpro.hu odds-JSON (`sports2.tippmixpro.hu`), (b) elérhető-e a stats.nba.com. Ez dönti el a végleges infrastruktúrát.
2. Töltsd le a robots.txt-t (`tippmixpro.hu/robots.txt` és `sports2.tippmixpro.hu/robots.txt`) és olvasd el ténylegesen; tartsd magad hozzá.

**Fázis 1 — adat + backteszt (első 1–2 hónap).**
- Futball: football-data.co.uk (eredmény+záró odds) + Understat (xG) + ClubElo, `soccerdata`-val. Kosár: Basketball-Reference / nba_api (box score) + sportsbookreviewsonline.com (záró odds) + euroleague-api.
- Modellek: futballra **Dixon–Coles (idősúlyozott) az O/U 2.5 és 1X2 piacokra**; kosárra **Elo + Four Factors a totals/spread piacokra**. Vig-eltávolítás power módszerrel; value = modell-p > margóval korrigált implikált p.
- Backteszt 2–3 évre, walk-forward; a fő mérce a **CLV a Pinnacle záró vonalához** (football-data.co.uk `PSC*`/`PAHH`), másodlagos a P&L. Csak akkor menj élesbe, ha több száz szimulált fogadáson pozitív CLV-t mutatsz.

**Fázis 2 — élesítés (kis téttel).**
- Kandidátus-lista **kizárólag a Tippmix Pro kínálatából** (odds-scrape); nemzetközi odds csak sanity-check. Value-szűrés → hírréteg-vétó (NBA Injury Report, felállások) → tétezés ¼-Kelly-vel, [200, 5000] HUF-ba vágva.
- Kombináció: **max. 2–3 láb, csak önállóan +EV lábakból, különböző eseményekből**, kötéstiltás tiszteletben tartva; a 2 000 000 HUF/egységnyi fogadás plafon alatt maradva.
- E-mail napi kétszer: reggeli előzetes + **kezdés előtt ~60–90 perccel** a végleges, felállás-megerősített tippek (a felállások ~1 órával kezdés előtt jönnek).

**Küszöbök, amik módosítanák a tervet:**
- Ha a GitHub Actions IP-t blokkolja a Tippmix Pro/NBA → **teljes átállás saját PC-re** (Windows Task Scheduler vagy önhosztolt runner).
- Ha a backteszt CLV nem pozitív → ne menj élesbe; finomítsd a modellt/piacválasztást.
- Ha az élő CLV 100+ fogadáson negatív → állítsd le a valós tétet, vissza a modellhez.

## Caveats
- **Geo-blokk a GitHub Actionsön**: nem verifikált, hogy a Tippmix Pro konkrétan blokkolja-e a runner IP-ket; a stats.nba.com viszont igazoltan blokkolja az adatközponti IP-ket. Empirikus teszt kötelező.
- **ToS-kockázat**: a Részvételi Szabályzat nem tilt kifejezetten scrapelést, de a fogadás külföldről tiltott, és a fiók-visszaélési klauzula elvben alkalmazható; alacsony frekvenciájú, tiszteletteljes lekérést és a robots.txt betartását javaslom. Jogi tanácsot ez nem helyettesít.
- **Az odds-végpontok pontos útvonala nem publikus**; a scraper törékeny lehet (a platform verziózott, változhat).
- **Nyereményesség nem garantált**: a publikált out-of-sample eredmények vegyesek; a nyers Dixon–Coles akár veszteséges is lehet. Az edge a szelektivitásból, kalibrációból és tételfegyelemből jön.
- **EuroLeague történelmi odds** ingyen gyakorlatilag nem elérhető — ez korlátozza a kosaras backtesztet EuroLeague-re.
- **Free tier változékonyság**: a The Odds API és társai kredit-/limitszabályai gyakran változnak; élesítés előtt ellenőrizd.
- **Mintaméret-becslés**: a fenti n ≈ 1600–4400 fogadás becslés közel-even oddsra és egyszerűsítő szórásfeltevésre épül; a tényleges küszöb az oddsstruktúrától függ.
- Néhány marketing-forrás (OddsPapi, SharpAPI stb.) állításait éles használat előtt független teszttel kell igazolni.