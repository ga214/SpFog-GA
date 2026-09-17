# Tippmix tipprendszer — döntési logika specifikáció

2026-09-17 · @Someone

## Áttekintés: mi történik egy napi futáskor

A program **nem** azt csinálja, hogy megnézi a meccseket és kiválasztja, ki fog nyerni. Azt csinálja, hogy **minden Tippmix Pro-n kínált eseményre kiszámolja a saját valószínűség-becslését, összeveti azzal, amit a Tippmix szorzója sugall, és csak ott javasol fogadást, ahol a kettő között elég nagy és megbízható az eltérés.** Ha nincs ilyen, a levél üres.

A futás 12 lépésből áll, mindig ebben a sorrendben:

| # | Lépés | Bemenet | Kimenet |
| --- | --- | --- | --- |
| 1 | Esemény-begyűjtés | tippmixpro.hu | nyers esemény- és szorzólista |
| 2 | Névillesztés | nyers lista | statisztikai DB-hez kötött események |
| 3 | Feature-építés | történelmi DB | meccsenkénti jellemzővektor |
| 4 | Futballmodell | jellemzők | gólvárakozás, eredménymátrix |
| 5 | Kosármodell | jellemzők | margó- és összpont-eloszlás |
| 6 | Kalibráció, zsugorítás | nyers modell-valószínűség | végleges p\_modell |
| 7 | Vig-eltávolítás, él | Tippmix szorzó + p\_modell | edge, EV |
| 8 | Szűrők és vétók | jelöltek | túlélő tippek |
| 9 | Tétezés | túlélő tippek | konkrét Ft-összegek |
| 10 | Kombináció-építés | egyes tippek | 2-3 lábas szelvények |
| 11 | Napi limitek, e-mail | minden javaslat | elküldött levél |
| 12 | Naplózás | minden javaslat | adatbázis-sor a CLV-hez |

A lépések sorosan futnak, megszakítási pontokkal: ha az 1. lépés nem hoz adatot, nincs futás; ha a 8. lépés mindent kiszűr, a 9-11. lépés nem fut le, hanem „ma nincs tipp" levél megy ki.

**Két napi futás.** A délelőtti (09:00 CET) a kora délutáni kezdésű meccsekre ad javaslatot, a kezdőcsapatok ismerete nélkül, ezért magasabb küszöbbel. Az esti (18:00 CET) a késői meccsekre ad javaslatot, már megerősített felállásokkal, alacsonyabb küszöbbel. Ugyanaz az esemény csak egyszer javasolható: a második futás átugorja, amire már ment javaslat.

## Konfiguráció: minden szám egy helyen

Egyetlen fájl, `config/settings.yaml`. A kódban sehol ne legyen beégetett szám. Az alábbi értékek **kiindulási pontok**, a backteszt fogja őket véglegesíteni.

```yaml
bankroll:
  induló_ft: 50000
  aktuális_ft: 50000          # kézzel frissíted, vagy a napló számolja

tét:
  kelly_hányad: 0.25          # negyed-Kelly
  min_ft: 200
  max_ft: 5000
  max_bankroll_százalék: 0.04 # egy tippre max a bankroll 4%-a
  kerekítés_ft: 100

napi_limit:
  max_tipp_db: 6
  max_kitettség_bankroll_százalék: 0.10
  max_kombináció_db: 2

küszöb:
  min_edge_délelőtt: 0.05     # 5 százalékpont
  min_edge_este: 0.035
  min_ev: 0.03                # 3% várható hozam
  min_odds: 1.30
  max_odds: 6.00
  max_eltérés_referenciától: 0.08

modell:
  zsugorítás_w: 0.35          # mennyit ér a saját modell a piaci árhoz képest
  dixon_coles_xi: 0.0035      # időbeli súlyozás
  min_meccs_csapatonként: 12
  modell_max_kor_nap: 8

kombináció:
  max_láb: 3
  min_láb_edge: 0.05
  tét_szorzó: 0.5             # a kombináció tétje a Kelly-érték fele

futás:
  délelőtt_cet: "09:00"
  este_cet: "18:00"
  min_perc_kezdésig: 45
```

**Miért van két `min_edge`?** Délelőtt nincs meg a kezdőcsapat, tehát nagyobb a bizonytalanság. Ugyanaz az él délelőtt kevesebbet ér, mint este, ezért délelőtt többet kérünk belőle.

**A `max_bankroll_százalék` és a `max_ft` közül mindig a szigorúbb nyer.** 50 000 Ft bankrollnál a 4% = 2000 Ft, tehát kezdetben ez a plafon, nem az 5000 Ft. Az 5000 Ft csak nagyobb bankrollnál válik elérhetővé.

**Biztonsági megjegyzés:** ebben a fájlban soha ne legyen jelszó, API-kulcs vagy e-mail-jelszó. Azok külön fájlba (`.env`, `.gitignore`-ba téve) és GitHub Secretsbe mennek. Erre a kód írásakor külön kitérek.

## 1. lépés — Esemény-begyűjtés a Tippmix Pro-ról

**Cél:** megkapni azoknak az eseményeknek a listáját, amikre ma egyáltalán fogadhatsz, és hozzájuk a szorzókat. Ez a lista a rendszer *univerzuma* — ami itt nincs benne, arra soha nem kapsz javaslatot.

**Bemenet:** a tippmixpro.hu odds-végpontja (a kutatás szerint `sports2.tippmixpro.hu`, JSON-nal). A pontos útvonalat az első fejlesztési lépésben derítjük ki a böngésző hálózati fülén.

**Amit ki kell nyerni eseményenként:**

| Mező | Példa | Mire kell |
| --- | --- | --- |
| `tippmix_event_id` | 308741329561284608 | azonosítás, duplikátumszűrés |
| `sport` | labdarúgás / kosárlabda | modellválasztás |
| `bajnokság` | Premier League | ligamodell kiválasztása |
| `hazai_nev`, `vendeg_nev` | Arsenal, Chelsea | névillesztés |
| `kezdes_utc` | 2026-09-17T19:00Z | időzítés, szűrés |
| `piac_nev` | Végeredmény / Gólszám 2.5 | piac azonosítása |
| `kimenetel_nev` | Hazai / Több | tipp azonosítása |
| `odds` | 2.15 | él számítása |
| `kotestiltas` | true/false | kombináció-építés |

**Döntések ebben a lépésben:**

1. Ha a lekérés hibát dob vagy üres → **3 újrapróbálkozás** 30 mp szünettel. Ha mind elbukik: nincs futás, hibalevél megy ki („nem sikerült az adatlekérés"), a program kilép. Nem találgat, nem használ tegnapi szorzót.
2. Csak azokat az eseményeket tartjuk meg, amelyek kezdése **legalább 45 perccel** a futás után van (`min_perc_kezdésig`). Ami hamarabb kezdődik, arra nem érnél oda fogadni.
3. Csak a konfigban felsorolt sportok és bajnokságok maradnak. Kezdetben: a `config/ligak.yaml`-ban engedélyezett futball-ligák és az NBA/EuroLeague.
4. Csak a támogatott piactípusok maradnak (lásd a 4. és 5. lépést). A többi (szögletszám, lapok, játékospiacok) most eldobásra kerül.
5. A nyers válasz **elmentésre kerül** `data/raw/tippmix_YYYYMMDD_HHMM.json` néven. Ez kell a későbbi hibakereséshez és ahhoz, hogy visszamenőleg ellenőrizni tudd, mit láttunk akkor.

**Kézi tartalék.** Ha a scraping nem megy (IP-blokk, oldalváltozás), a program tud olvasni egy `data/manual/tippmix_YYYYMMDD.csv` fájlt, amibe te másolod be a szorzókat. Ugyanaz az oszlopszerkezet, mint fent. A program automatikusan ezt használja, ha a scraping elbukott, de a kézi fájl mai dátummal létezik.

## 2. lépés — Névillesztés

**Ez a lépés a rendszer leggyakoribb hibaforrása, ezért részletesen leírom.**

A probléma: a Tippmix azt írja, hogy „Manchester Utd", a football-data.co.uk azt, hogy „Man United", az Understat azt, hogy „Manchester United". A program nem tudja magától, hogy ez ugyanaz. Ha rosszul köti össze, rossz csapat statisztikájából számol, és a javaslat értéktelen — **ráadásul észrevétlenül**, mert semmi nem fog hibát dobni.

**A megoldás: kézi leképezési tábla, automatikus javaslattal.**

1. A program minden Tippmix-névre megnézi a `data/team_aliases.csv` fájlt, ami így néz ki:

```
tippmix_nev,sport,kanonikus_id,forras_nevek
Manchester Utd,foci,ENG_MANUTD,"Man United|Manchester United"
Los Angeles Lakers,kosar,NBA_LAL,"LAL|Lakers"
```

2. Ha a név **szerepel** a táblában → kész, megvan a kapcsolat.
3. Ha **nem szerepel** → a program fuzzy kereséssel (`rapidfuzz`, normalizált név: ékezetek le, „FC"/„SK"/„United" szóváltozatok kezelése) javaslatot tesz, de **nem használja fel automatikusan**. Az esemény kimarad a mai futásból, és a levél végén egy „Ismeretlen csapatok" szakasz felsorolja őket a javasolt párosítással. Te egy sorral kiegészíted a CSV-t, és másnaptól működik.

**Miért nem automatikus?** Mert a fuzzy találat 95%-ban jó, 5%-ban viszont csendben rossz csapatot választ (pl. „Manchester City" ↔ „Manchester Utd" hasonlósága magas). Az 5% hibás párosítás rosszabb, mint az, hogy egy meccs kimarad.

**Bajnokság-illesztés.** Ugyanez a `data/league_map.csv`-vel a bajnokságokra, mert a modell ligánként külön van fittelve, és a football-data.co.uk ligakódjaihoz (E0, D1, SP1 stb.) kell kötni.

**Kimenet:** minden Tippmix-esemény kap egy `kanonikus_meccs_id`-t, vagy kiesik `NEVILLESZTES_HIANY` okkal. Az esés okát a program naplózza.

## 3. lépés — Feature-építés jövőbe látás nélkül

**Az alapszabály:** minden jellemzőt úgy kell kiszámolni, hogy **kizárólag a meccs kezdése előtti adatokat** használja. Ez élesben triviálisan teljesül, de a backtesztben nagyon könnyű elrontani, és ha elrontod, a backteszt csodálatos eredményt ad, élesben meg buksz. Ezért ugyanaz a kódfüggvény építi a jellemzőket élesben és backtesztben, egyetlen `asof_datum` paraméterrel.

**Konkrét tiltások:**

- Nem használható a végső tabellaállás, csak az `asof_datum`-ig felhalmozott.
- Nem használható a szezon egészére számolt csapaterősség, csak a gördülő ablak.
- A modell paramétereit (Dixon-Coles illesztés) a backtesztben minden fordulóra **újra kell illeszteni** az addigi adatokból. Ez lassabb, de ez az egyetlen becsületes módszer.

**Futball-jellemzők meccsenként:**

| Jellemző | Ablak | Megjegyzés |
| --- | --- | --- |
| lőtt/kapott gól hazai pályán | utolsó 3 szezon, idősúlyozva | a Dixon-Coles illesztés bemenete |
| lőtt/kapott gól idegenben | ugyanaz |  |
| xG for / xG against | utolsó 10 meccs | ahol elérhető (Understat) |
| ClubElo érték | az `asof_datum`-ra |  |
| pihenőnapok száma | előző meccs óta | fáradtság |
| liga átlagos gólszáma | aktuális szezon eddigi része | normalizálás |

**Kosárlabda-jellemzők:**

| Jellemző | Ablak | Megjegyzés |
| --- | --- | --- |
| offenzív/defenzív rating | utolsó 20 meccs, súlyozva | 100 birtoklásra vetítve |
| pace (birtoklás/meccs) | utolsó 20 meccs | az összpont-becsléshez |
| Elo | folyamatosan frissítve |  |
| back-to-back jelző | volt-e meccs tegnap |  |
| utazás | hazai/idegen, időzóna-váltás |  |
| pihenőnapok |  |  |

**Adatelégségességi kapu.** Ha bármelyik csapatnak kevesebb mint `min_meccs_csapatonként` (12) meccse van az adott szezonban vagy a gördülő ablakban, az esemény **kiesik** `KEVES_ADAT` okkal. Szezonelején ezért hetekig kevés tipp lesz — ez helyes viselkedés, nem hiba.

## 4. lépés — Futballmodell

**Az alapgondolat.** Feltesszük, hogy egy meccsen a hazai csapat gólszáma és a vendég gólszáma két (majdnem) független Poisson-eloszlású szám. Minden csapatnak van egy támadóereje és egy védőereje, és van egy általános hazaipálya-előny. Ebből kijön két szám: `λ_hazai` (a hazai csapat várható góljainak száma) és `λ_vendég`.

```
log(λ_hazai) = támadás[hazai] + védelem[vendég] + hazai_előny
log(λ_vendég) = támadás[vendég] + védelem[hazai]
```

A `támadás` és `védelem` paramétereket ligánként illesztjük a történelmi meccsekre, **idősúlyozva**: egy tavalyi meccs kevesebbet számít, mint a múlt hetiek. A súly `exp(-ξ · napok_száma)`, ahol `ξ = 0.0035` (ez kb. fél év alatt felezi a súlyt). A `ξ` végleges értékét a backteszt adja.

**Dixon-Coles korrekció.** A tiszta Poisson alulbecsli a nagyon alacsony eredményeket (0-0, 1-0, 0-1, 1-1), mert a valóságban a csapatok viselkedése összefügg. A korrekció ezt a négy cellát megszorozza egy `τ(x, y, λ_h, λ_v, ρ)` tényezővel. A `ρ` az eredeti tanulmányban kb. −0,13 volt angol adatokra; nálunk **ligánként újrailleszti** a program.

**Eredménymátrix.** Az `λ`-kból felépítünk egy 11×11-es táblázatot: `P(hazai i gólt lő ÉS vendég j gólt lő)` minden `i, j = 0..10` párra, alkalmazva a Dixon-Coles korrekciót, majd a mátrixot 1-re normalizáljuk.

**Innen minden piac egyszerű összeadás:**

| Piac | Számítás a mátrixból |
| --- | --- |
| Hazai győzelem (1) | cellák összege, ahol i > j |
| Döntetlen (X) | cellák összege, ahol i = j |
| Vendég győzelem (2) | cellák összege, ahol i < j |
| Gólszám 2.5 felett | cellák összege, ahol i + j >= 3 |
| Gólszám 2.5 alatt | cellák összege, ahol i + j <= 2 |
| Mindkét csapat szerez gólt | cellák összege, ahol i >= 1 és j >= 1 |
| Ázsiai hendikep -1 | a megfelelő cellák, half-win/push kezeléssel |

**Első verzióban engedélyezett piacok:** `1X2`, `Gólszám 2.5 felett/alatt`. Ezek a legalacsonyabb margójú, legjobban modellezhető piacok. A BTTS-t és a hendikepet a második körben kapcsoljuk be, amikor a backteszt már mutat valamit.

**Kiesési okok ebben a lépésben:** `ILLESZTES_SIKERTELEN` (a liga modellje nem konvergált), `MODELL_ELAVULT` (a mentett illesztés régebbi, mint `modell_max_kor_nap`).

## 5. lépés — Kosármodell

Kosárban a Poisson nem működik (túl sok pont), helyette **két normális eloszlást** becslünk: a pontkülönbségét és az összpontszámét.

**A becslés menete:**

1. Mindkét csapatra van egy offenzív rating (`ORtg` = szerzett pont 100 birtoklásra) és egy defenzív rating (`DRtg` = kapott pont 100 birtoklásra), a liga átlagához viszonyítva, az utolsó 20 meccsből súlyozva.
2. Becsült birtoklásszám: `pace = (pace_hazai + pace_vendég) / 2`, liga-átlaghoz igazítva.
3. Becsült pontszámok:

```
pont_hazai = (ORtg_hazai + DRtg_vendég - liga_átlag) / 100 × pace + hazai_előny/2
pont_vendég = (ORtg_vendég + DRtg_hazai - liga_átlag) / 100 × pace - hazai_előny/2
```

4. Korrekciók: back-to-back (a fáradt csapat becsült pontja csökken), hosszú utazás, kiesett kulcsjátékos (a hírrétegből, lásd 8. lépés).
5. `várható_margó = pont_hazai - pont_vendég`, `várható_összpont = pont_hazai + pont_vendég`.

**Innen a piaci valószínűségek:**

```
P(hazai fedi a -X hendikepet) = 1 - Φ((X - várható_margó) / σ_margó)
P(összpont > T)               = 1 - Φ((T - várható_összpont) / σ_össz)
P(hazai nyer)                  = 1 - Φ((0 - várható_margó) / σ_margó)
```

ahol `Φ` a standard normális eloszlásfüggvény.

**A két szórásparaméter kritikus, és nem találom ki fejből.** A `σ_margó` és `σ_össz` értékét a backtesztből, a modell hibáinak tényleges szórásából kell megbecsülni, ligánként külön (az NBA és az EuroLeague nem ugyanaz). Amíg ez nincs meg, a kosármodell nem ad javaslatot. Ezt a fejlesztés első fázisában kell elvégezni.

**Első verzióban engedélyezett piacok:** `Összpont felett/alatt`, `Hendikep`. A moneyline nagy favoritoknál kerülendő (a `max_odds`/`min_odds` szűrő úgyis kivágja).

**Hazai pálya előnye.** Az NBA-ben és az EuroLeague-ben más a mértéke; mindkettőt a saját adatából illesztjük, nem feltételezünk semmit.

## 6. lépés — Kalibráció és piaci zsugorítás

Ez a két művelet a rendszer legfontosabb része, és pont ez hiányzik a legtöbb amatőr fogadási modellből.

### Kalibráció

A modell nyers kimenete lehet szisztematikusan torz: pl. amikor 70%-ot mond, a valóságban csak 64%-ban jön be. Ezt méri és javítja a kalibráció.

- **Módszer:** izotonikus regresszió (vagy Platt-skálázás), a backteszt validációs szeletén illesztve, piactípusonként külön.
- **Bemenet:** a modell által adott `p_nyers` és a tényleges kimenetel (0/1) több ezer múltbeli meccsről.
- **Kimenet:** egy leképezés, ami `p_nyers`-ből `p_kalibrált`-at csinál.
- **Ellenőrzés:** kalibrációs görbe és Brier-pontszám. Ha a görbe nem közelíti az átlót, a modell nem használható élesben.

### Piaci zsugorítás

**Ez a legfontosabb pont az egész dokumentumban.** A fogadóiroda ára rengeteg információt tartalmaz, amit a mi modellünk nem lát: sérüléshírek, fogadói pénzáramlás, taktikai hírek. Az esetek nagy részében **a piacnak van igaza, nem nekünk**. Ha a modellünket önmagában használjuk, rendszeresen olyan helyekre fogadunk, ahol nem tévedés van, hanem a modell hiánya.

Ezért a végleges valószínűség a modell és a piac keveréke:

```
p_végleges = w × p_kalibrált + (1 - w) × p_piac_fair
```

ahol `p_piac_fair` a Tippmix szorzójából vig nélkül számolt valószínűség (7. lépés), `w` pedig a modellbe vetett bizalom.

| `w` értéke | Jelentés |
| --- | --- |
| 0 | teljesen a piacot követjük, sosem lesz tipp |
| 0.35 | kiindulási érték: a modell a piactól való eltérés harmadát viszi át |
| 1 | csak a modell számít, a piacot figyelmen kívül hagyjuk |

**A `w`-t nem én találom ki, a backteszt adja meg:** azt az értéket keressük, ami a validációs időszakon a legjobb CLV-t hozza. A 0.35 csak indulóérték. Kezdetben inkább alacsonyabb (0.25–0.35), mert a modell fiatal és bizonytalan.

**A zsugorítás következménye, amit el kell fogadnod:** sokkal kevesebb tipp lesz, mint amennyit egy zsugorítás nélküli rendszer adna. Ez nem hiba, hanem ez a védelem a hamis élek ellen.

## 7. lépés — Vig eltávolítás és az él kiszámítása

**A vig (árrés) az, amit az iroda beépít a szorzóba.** Egy 1X2 piacon a három szorzó reciprokainak összege nem 1, hanem pl. 1,06. Ez a 6% az iroda haszna. Ha ezt nem vesszük ki, minden élünk hamis lesz — 6%-kal jobbnak fogjuk hinni magunkat, mint amilyenek vagyunk.

**A számítás:**

1. Nyers implikált valószínűség minden kimenetelre: `q_i = 1 / odds_i`
2. Az összegük: `S = Σ q_i` (ez > 1)
3. Vig eltávolítása **power módszerrel**: keressük azt a `k` kitevőt, amire `Σ (q_i)^k = 1`. Ezt egyszerű numerikus kereséssel (bisection) megoldjuk. A fair valószínűség: `p_fair_i = (q_i)^k`

**Miért power és nem egyszerű osztás?** Az egyszerű arányos osztás (`q_i / S`) minden kimenetelből ugyanannyi százalékot vesz ki. A valóságban az irodák a kis esélyű kimenetelekre tesznek arányosan nagyobb árrést (favourite-longshot bias). A power módszer ezt figyelembe veszi. Az arányos változatot **referenciaként** végig számoljuk, és ha a kettő nagyon eltér, az figyelmeztető jel.

**Az él és a várható hozam:**

```
edge = p_végleges - p_fair          (százalékpontban)
EV   = p_végleges × odds - 1        (arányos hozam)
```

Példa: a Tippmix 2,20-at ad, ebből `p_fair = 0,435`. A modellünk zsugorítás után 0,48-at mond.

- `edge = 0,48 − 0,435 = 0,045` (4,5 százalékpont)
- `EV = 0,48 × 2,20 − 1 = 0,056` (5,6% várható hozam)

**Referencia-ellenőrzés.** Ha rendelkezésre áll nemzetközi szorzó ugyanarra az eseményre (belső kontrollként, nem fogadási célra), kiszámoljuk annak a fair valószínűségét is. Ha a mi `p_végleges`-ünk **több mint `max_eltérés_referenciától` (8 százalékpont)** eltér a nemzetközi konszenzustól, az azt jelenti, hogy a modellünk valamit nem tud, amit a piac tud. Ilyenkor a tipp **kiesik** `REFERENCIA_ELTERES` okkal. Ez a védőháló a sérülés- és hírhiányból fakadó vak élek ellen.

Ha nincs referencia-adat, a tipp mehet tovább, de a levélben jelezzük, hogy nem volt ellenőrzés.

## 8. lépés — Döntési fa: mi lesz tippből javaslat

Minden jelölt (egy esemény + egy piac + egy kimenetel) végigmegy ezen a soron. **Az első bukott feltételnél kiesik**, és a kiesés okát a program naplózza. Csak a végigment jelöltekből lesz javaslat.

```
JELÖLT: esemény × piac × kimenetel
 │
 1. Van érvényes szorzó?                    nem → NINCS_ODDS
 2. min_odds <= odds <= max_odds?           nem → ODDS_TARTOMANY
 3. Kezdésig >= 45 perc?                    nem → KESO
 4. Névillesztés megvan?                    nem → NEVILLESZTES_HIANY
 5. Elég adat mindkét csapatra (>= 12)?     nem → KEVES_ADAT
 6. A ligamodell friss (<= 8 nap)?          nem → MODELL_ELAVULT
 7. A piac támogatott ehhez a sporthoz?     nem → NEM_TAMOGATOTT_PIAC
 │
 8. edge >= min_edge (napszak szerint)?     nem → KIS_EL
 9. EV >= min_ev?                           nem → KIS_EV
10. Eltérés a referenciától < 8 pp?         nem → REFERENCIA_ELTERES
 │
11. HÍRVÉTÓ: van kizáró hír?                igen → HIRVETO
12. Ment már ma javaslat erre az eseményre? igen → DUPLIKATUM
 │
 → TÚLÉLT: megy a 9. lépésbe (tétezés)
```

### A hírvétó (11. pont) részletesen

A hírréteg **soha nem hoz létre tippet, csak megöl**. Ez szándékos: a hírek számszerűsítése megbízhatatlan, de arra jó, hogy egy nyilvánvalóan elavult modellbecslést leállítson.

| Sport | Vétófeltétel | Forrás |
| --- | --- | --- |
| Kosár | kulcsjátékos `OUT` vagy `DOUBTFUL` a hivatalos NBA Injury Reportban | NBA injury report |
| Kosár | a csapat top-2 percátlagú játékosa hiányzik | ugyanaz |
| Foci | megerősített kezdő tizenegyben hiányzik a 2 legtöbbet játszó mezőnyjátékos vagy a kezdő kapus | felállás-forrás |
| Foci | a felállás még nem elérhető ÉS a délelőtti futásban vagyunk | ekkor `min_edge_délelőtt` a magasabb küszöb, nem vétó |
| Mindkettő | a meccs státusza nem `scheduled` (halasztva, törölve) | Tippmix + statisztikai forrás |

**Fontos korlát:** a „kulcsjátékos" definíciója az elmúlt N meccs játékperceiből származik, nem szubjektív megítélésből. Ha a hírforrás nem elérhető, a program **nem** vétóz vakon — ehelyett a napszaki küszöböt emeli meg 1,5-szeresére, és a levélben jelzi, hogy nem volt hírellenőrzés.

### Amit a fa szándékosan nem tartalmaz

- **Nincs „biztos tipp" kategória.** Nincs olyan feltétel, ami valamit felülírna és átengedne a szűrőkön.
- **Nincs sorozat-alapú logika** („a csapat 5 meccse veretlen, tehát…"). Ez a modell dolga, nem külön szabályé.
- **Nincs veszteségpótlás.** Ha az előző nap mínusz volt, az a mai tétekre semmilyen hatással nincs. Ez a legfontosabb védelem a bankroll ellen.

## 9. lépés — Tétezés

A kérdésed erre az volt, hogy „nem fix tét, mert egy 1,4-es eseményre többet teszek, mint egy 10-esre". Pontosan ezt csinálja a Kelly-formula, méghozzá matematikailag megalapozottan.

**Az alapképlet:**

```
f* = (p × odds - 1) / (odds - 1)
```

ahol `f*` a bankroll azon hányada, amit optimálisan meg kellene tenni, `p` a `p_végleges`.

**Példa ugyanarra az 5%-os élre, két különböző szorzónál:**

| Szorzó | p\_végleges | f\* | negyed-Kelly | tét 50 000 Ft-ból |
| --- | --- | --- | --- | --- |
| 1,40 | 0,764 | 0,174 | 0,0435 | 2 175 → **2 000 Ft** (a 4% plafon vág) |
| 3,50 | 0,331 | 0,064 | 0,0160 | 800 Ft |
| 6,00 | 0,197 | 0,036 | 0,0091 | 455 → **500 Ft** |

Látható: ugyanaz az él alacsony szorzónál nagyobb tétet indokol. Ez pont az, amit kértél.

**A teljes tétszámítás lépései:**

1. `f* = (p_végleges × odds − 1) / (odds − 1)`
2. Ha `f* <= 0` → nincs tipp (ide nem juthatunk el, mert a 8. lépés kiszűrte)
3. `f_használt = f* × kelly_hányad` (0,25)
4. `tét = f_használt × bankroll_aktuális`
5. Levágás felülről: `tét = min(tét, max_ft, max_bankroll_százalék × bankroll)`
6. Levágás alulról: ha `tét < min_ft` (200 Ft) → a tipp **kiesik** `TUL_KIS_TET` okkal. Nem kerekítünk fel, mert az felülteteléshez vezet.
7. Kerekítés 100 Ft-ra lefelé.

**Miért negyed-Kelly és nem teljes?** A teljes Kelly akkor optimális, ha a `p` becslésed *pontos*. A miénk nem az — becslés, hibával. Ha a valós `p` alacsonyabb, mint hitted, a teljes Kelly gyorsan tönkretesz. A negyed-Kelly a várható növekedés kb. 75%-át hozza a volatilitás negyedéért. Kezdetben ez is lehet túl sok; a `kelly_hányad` 0,15-re csökkentése védekezőbb indulás.

**Bankroll-frissítés.** A program a `bankroll_aktuális` értéket a konfigból veszi. Te frissíted, vagy ha később bekapcsoljuk a naplót, az számolja. Amíg kézi, ne frissítsd naponta — heti egyszer elég, különben a tét ugrál.

## 10. lépés — Kombináció-építés

**A szabály egy mondatban:** kombináció csak olyan lábakból épülhet, amelyek **külön-külön is átmentek a 8. lépés teljes döntési fáján**. A kombináció nem eszköz a szorzó feltornázására.

**Az építés menete:**

1. Vedd a túlélt egyes tippeket.
2. Szűrd tovább: csak az `edge >= min_láb_edge` (5 pp) feletti lábak jöhetnek szóba. Ez szigorúbb, mint az egyesnél elvárt.
3. Zárd ki azokat, amelyek ugyanahhoz az eseményhez tartoznak (korreláció + a Tippmix kötéstiltása).
4. Lehetőleg különböző bajnokságból legyenek (közvetett korreláció: ugyanaz az időjárás, ugyanaz a játékvezetői stílus).
5. Generáld az összes 2-es és 3-as kombinációt, számold ki mindegyikre:

```
kombi_odds = Π odds_i
kombi_p    = Π p_végleges_i
kombi_EV   = kombi_p × kombi_odds - 1
```

6. Tartsd meg azokat, ahol `kombi_EV >= min_ev` (3%).
7. Rendezd `kombi_EV` szerint, vedd a legjobb `max_kombináció_db` (2) darabot.
8. Tét: a kombinációra számolt Kelly-érték **fele** (`tét_szorzó: 0.5`), mert a lábak közti rejtett korreláció és a halmozott modellhiba miatt a valós bizonytalanság nagyobb, mint amit a szorzás sugall.
9. Ellenőrizd: `tét × kombi_odds <= 2 000 000 Ft` (a Tippmix Pro nyereményplafonja). Kis téteknél ez sosem fog fogni, de a kód tartalmazza.

**Amit tudnod kell a matekról.** Írtad korábban, hogy tíz darab 1,05-ös eseményt összefűznél. Konkrétan: ha mindegyik láb valódi nyerési esélye 95% és a szorzó 1,05, akkor a valódi fair szorzó 1/0,95 = 1,0526 lenne — vagyis lábanként kb. 0,5% árrést fizetsz. Tíz lábon ez összeszorzódik: a tényleges kifizetés a valódi értéknek kb. 95%-a, tehát **5% biztos veszteség**, miközben a szelvény csak 0,95¹⁰ ≈ 60%-ban jön be egyáltalán. Ezért van a `max_láb: 3`, és ezért csak +EV lábakból.

**Mikor van értelme mégis a kombinációnak?** Ha minden láb önmagában +5% EV-t hoz, akkor egy 2-es kombináció elméleti EV-je 1,05 × 1,05 − 1 = **10,25%** — vagyis a pozitív él is halmozódik. Ez az egyetlen eset, amikor a kombináció jobb az egyesnél. A feltétel viszont szigorú, és ritkán teljesül.

## 11. lépés — Napi limitek és a levél

**Limitek alkalmazása, ebben a sorrendben:**

1. Rendezd az összes javaslatot (egyesek + kombinációk) `EV` szerint csökkenően.
2. Vedd felülről a legjobb `max_tipp_db` (6) darabot.
3. Összegezd a tétjeiket. Ha az összeg > `max_kitettség` (a bankroll 10%-a = 5 000 Ft), akkor **arányosan csökkentsd az összes tétet**, amíg belefér. Ha valamelyik így 200 Ft alá esik, azt hagyd ki, és számold újra.
4. Ami marad, az megy a levélbe.

### A levél tartalma

Az a cél, hogy **kinyisd, és pontosan tudd, mit kell beütnöd a Tippmix Pro-ba**, gondolkodás nélkül.

```
Tárgy: Tippmix javaslatok — 2026-09-17 este — 3 tipp, 3 400 Ft

=== EGYES FOGADÁSOK ===

1) Arsenal - Chelsea  (Premier League, 21:00)
   Piac:     Gólszám 2.5 — Több
   Szorzó:   1.85
   TÉT:      1 500 Ft
   Lehetséges nyeremény: 2 775 Ft

   Modell: 59.2%  |  Piac (vig nélkül): 52.1%  |  Él: +7.1 pp  |  EV: +9.5%
   Indok: mindkét csapat magas xG-t termel (2.1 / 1.7),
          az utolsó 6 egymás elleni meccsből 5-ben volt 3+ gól.
   Ellenőrzés: referencia-piac 53.4% (eltérés 5.8 pp — rendben)
   Felállás: megerősítve, nincs kulcshiányzó

=== KOMBINÁCIÓ ===

K1) 2 lábas kötés — együttes szorzó: 3.42
    TÉT: 400 Ft   |   Lehetséges nyeremény: 1 368 Ft
    a) Arsenal - Chelsea .......... Gólszám 2.5 Több ...... 1.85
    b) Lakers - Celtics ........... Összpont 224.5 Alatt .. 1.85
    Együttes modell-valószínűség: 33.1%  |  EV: +13.2%

=== ÖSSZESÍTŐ ===
Mai összes tét: 3 400 Ft (a bankroll 6.8%-a)
Maximális nyeremény, ha minden bejön: 7 100 Ft

=== NEM JAVASOLT, DE MEGVIZSGÁLVA ===
38 esemény, 112 piac. Kiesési okok:
  KIS_EL: 71 | KEVES_ADAT: 18 | REFERENCIA_ELTERES: 12
  HIRVETO: 6 | ODDS_TARTOMANY: 4 | NEVILLESZTES_HIANY: 1

=== FIGYELEM ===
Ismeretlen csapatnév: "Nott'm Forest" — javasolt: ENG_NOTTFOREST
Add hozzá a data/team_aliases.csv fájlhoz.
```

**Miért van benne a „nem javasolt" rész?** Mert így látod, hogy a rendszer dolgozott, csak nem talált semmit — nem pedig elromlott. Egy üres levél magyarázat nélkül nyugtalanító; egy üres levél azzal, hogy „112 piacot néztem meg, 71-nél túl kicsi volt az él", informatív.

## 12. lépés — Naplózás, CLV és leállítási feltételek

Írtad, hogy a naplót egyelőre te vezeted. A **gépi naplózás viszont akkor is kell**, mert enélkül a rendszer nem tud tanulni és nem tudod megmondani, működik-e. Két külön dologról van szó: a te fogadási naplód (mit tettél meg valójában) és a program saját naplója (mit javasolt és mi lett belőle).

**A program naplója** — SQLite tábla, `data/tippek.db`, minden javaslatról egy sor:

```
futas_id, idopont, tippmix_event_id, sport, bajnoksag,
hazai, vendeg, kezdes, piac, kimenetel,
odds_javaslatkor, p_modell_nyers, p_kalibralt, p_vegleges, p_fair,
edge, ev, javasolt_tet, futas_tipusa (delelott/este),
referencia_odds, hirveto_allapot,
zaro_odds, eredmeny, nyeremeny, clv
```

**A záró szorzó (`zaro_odds`) begyűjtése.** Külön napi futás, kezdés előtt kb. 5 perccel újra lekéri a Tippmix szorzóját minden javasolt tippre, és beírja a sorba. Ebből jön a CLV:

```
CLV = (odds_javaslatkor / zaro_odds) - 1
```

**Miért ez a legfontosabb szám?** Mert a nyereség rövid távon szinte teljesen a szerencsén múlik, a CLV viszont nem. Ha 100 fogadáson átlagosan pozitív a CLV-d, akkor a rendszered *tényleg* előbb látja meg az információt, mint a piac — ez hosszú távon pénz. Ha a CLV negatív, akkor a nyerő heteid szerencsések voltak, és előbb-utóbb visszaadod. A CLV-hez **jóval kevesebb minta kell**, mint a nyereség kimutatásához: pár száz fogadáson már értelmezhető jelet ad, míg a 3%-os ROI statisztikai igazolásához nagyságrendileg több ezer fogadás kellene.

**Automatikus leállítási feltételek.** A program magától leáll (nem küld több javaslatot, csak riasztást), ha:

| Feltétel | Küszöb | Miért |
| --- | --- | --- |
| Bankroll-esés | a csúcshoz képest −30% | valami elromlott |
| Átlagos CLV | 50+ tipp után negatív | nincs valódi él |
| Kalibrációs hiba | Brier-pontszám romlik két hétig | a modell elavult |
| Adathiány | 3 egymást követő sikertelen futás | scraping elromlott |

**Ezek nem javaslatok, hanem beépített kapcsolók.** A lényeg, hogy ne a te hangulatod döntsön a leállásról, hanem előre lefektetett szám.

## Fejlesztési sorrend és a nyitott számok

### A sorrend, amiben Claude Code-ban haladnunk kell

| Fázis | Mit építünk | Mikor kész |
| --- | --- | --- |
| 0 | Scraping-teszt: megy-e a tippmixpro.hu GitHub Actionsről és a gépedről | 1 nap |
| 1 | Történelmi adatok letöltése, SQLite-ba töltése (foci) | 2-3 nap |
| 2 | Dixon-Coles illesztés + eredménymátrix + backteszt-keretrendszer | 1 hét |
| 3 | Kalibráció, `w` és a küszöbök meghatározása backtesztből | 3-4 nap |
| 4 | Tippmix-scraper, névillesztés, él-számítás | 3-4 nap |
| 5 | Tétezés, kombináció, e-mail, naplózás | 2-3 nap |
| 6 | Élesítés kis téttel, csak fociban | — |
| 7 | Kosármodell hozzáadása ugyanezzel a sorrenddel | +1 hét |

**A 2. és 3. fázis a lényeg.** Ha ezeken átjutunk és a backteszt nem mutat pozitív CLV-t, akkor a 4-6. fázist nem érdemes megépíteni ebben a formában. Jobb ezt a 2. héten megtudni, mint a 8-on.

### Amit nem tudok, és a backtesztből kell kijönnie

Ezeket szándékosan nem találtam ki. Ha most számot mondanék rájuk, az kitalálás lenne:

- `w` (a piaci zsugorítás súlya) — a legfontosabb egyetlen paraméter
- `ξ` (a Dixon-Coles időbeli felejtés üteme) ligánként
- `ρ` (az alacsony eredmények korrekciója) ligánként
- `σ_margó` és `σ_össz` a kosármodellhez, ligánként
- a valódi `min_edge` küszöb, ami után a fogadás megéri
- hogy a `min_odds: 1.30` és `max_odds: 6.00` sáv jó-e, vagy szűkíteni kell

### Amit nem fogok tudni megígérni

A kutatás egyik konkrét adata: egy 2023-24-es Premier League backtesztben a tiszta Dixon-Coles modell **−15,4% ROI**-t hozott 249 fogadáson. Ez nem azt jelenti, hogy a módszer rossz — azt jelenti, hogy **a nyers modell önmagában nem elég**, a nyereség a kalibrációból, a piaci zsugorításból és a szigorú szűrésből jön. Pontosan ezért van a 6., a 7. és a 8. lépés ebben a dokumentumban.

Lehet, hogy a backteszt után az lesz a becsületes válasz, hogy ez a rendszer nem termel élt. Ezt akkor meg fogom mondani.
