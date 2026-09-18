# Döntési napló

Minden technológiai és módszertani döntés: mi volt a kérdés, milyen
lehetőségek voltak, mit választottunk, miért.

**SZABÁLY: régi bejegyzést soha nem írunk át.** Ha később megváltoztatunk egy
döntést, az **új bejegyzésként** kerül a végére, és hivatkozik a felülírt
döntésre. Így a projekt története és a "miért így?" kérdés visszakereshető
marad.

---

## D-001 — Python 3.12 és uv csomagkezelő

**Dátum:** 2026-09-17
**Döntéshozó:** felhasználó (kérdésre válaszolva)

**A kérdés:** melyik Python-verzió és csomagkezelő?

**Opciók:**

| Opció | Előny | Hátrány |
| --- | --- | --- |
| 3.12 + uv | gyors telepítés, lockfile, gyors CI | újabb eszköz, kevesebb példa a neten |
| 3.12 + pip/venv | mindenhol működik, ismerős | lassú, gyengébb reprodukálhatóság |
| 3.11 + uv | maximális csomagkompatibilitás | elavulóban |
| Poetry | érett, elterjedt | lassabb, bonyolultabb konfiguráció |

**Döntés:** Python 3.12 + uv.

**Miért:** a 3.12-t minden szükséges csomag (soccerdata, nba_api, scipy)
támogatja, a 3.13 még helyenként törik. Az uv a GitHub Actionsben lényegesen
gyorsabb a pipnél, és a `uv.lock` reprodukálható környezetet ad — ez fontos,
mert a backteszt eredménye csomagverziótól függhet.

---

## D-002 — Publikus GitHub-repó

**Dátum:** 2026-09-17
**Döntéshozó:** felhasználó

**A kérdés:** publikus vagy privát repó?

**Opciók:**

| Opció | Actions-perc | Kockázat |
| --- | --- | --- |
| Publikus | **korlátlan** | bárki látja a modellt és a naplót; 60 nap után letiltódik az ütemezés |
| Privát | 2000 perc/hó | a napi 3 futás ~450 perc, belefér |

**Döntés:** publikus.

**Következmények, amiket kezelni kell:**

1. **Keepalive kötelező** — a GitHub 60 nap commit-inaktivitás után letiltja
   az ütemezett workflow-kat. Megoldás:
   `.github/workflows/keepalive.yml`, heti üres commit.
2. **A titokkezelés nem opcionális óvatosság.** Egy véletlenül commitolt kulcs
   azonnal kompromittált. Megoldás: `gitleaks` a CI-ben, szigorú `.gitignore`,
   minden titok kizárólag környezeti változóból.
3. A fogadási stratégia és a modell nyilvános lesz. Ez a felhasználó tudatos
   döntése.

---

## D-003 — Csak Supabase, lokális SQLite nélkül

**Dátum:** 2026-09-17
**Döntéshozó:** felhasználó

**A kérdés:** Supabase, lokális SQLite, vagy mindkettő?

**Ez a döntés szembemegy mindkét normatív dokumentummal:**

- A **kutatási jelentés** (7. szakasz) kifejezetten a Supabase ellen érvel:
  "ingyenes tier 2 projekt, 500 MB, de **7 nap inaktivitás után szünetelteti**
  a projektet — kényelmetlen ütemezett jobhoz". Ajánlása: "SQLite a repóban
  kezdetnek, később Turso".
- A **döntési logika specifikáció** 12. lépése explicit SQLite-ot ír:
  `data/tippek.db`.

**Opciók:**

| Opció | Backteszt-sebesség | Éles írás | Komplexitás |
| --- | --- | --- | --- |
| Mindkettő | gyors (lokális) | Supabase | két backend |
| Csak Supabase | lassú (hálózat) | Supabase | egy backend |
| Csak SQLite | gyors | fájl-konfliktus Actionsben | egy backend |

**Döntés:** csak Supabase, a felhasználó választása szerint.

**Miért nem blokkoló a 7 napos szüneteltetés:** napi kétszeri (a záró-odds
gyűjtéssel háromszori) futásnál a projekt sosem lesz 7 napig inaktív. A
kutatás óvatossága olyan használatra vonatkozik, ahol ritka a hozzáférés.

**A backteszt-sebességet így kezeljük:** a repository-réteg mögé kerül egy
**lokális Parquet-cache** (`data/cache/`, a `.gitignore`-ban). A Supabase
marad az egyetlen igazságforrás; a backteszt egyszer lehúzza az adatot és
onnantól lokálisan olvas. Ez nem második adatbázis, csak gyorsítótár.

**Séma-következmény:** a specifikáció SQLite-táblaleírása Postgresre
fordítva került a `db/migrations/001_init.sql` fájlba (`bigint generated
always as identity`, `timestamptz`, `numeric`, `jsonb`, indexek, RLS).

---

## D-004 — pytest + ruff már most

**Dátum:** 2026-09-17
**Döntéshozó:** felhasználó

**A kérdés:** kell-e tesztelési keretrendszer és linter már a váz-fázisban?

**Döntés:** pytest + ruff igen, mypy nem.

**Miért:**

- A smoke-teszthez pytest amúgy is kell.
- A ruff linter és formatter egyben, nulla konfigurációval, nagyon gyors.
- **Pénzről van szó.** A "nincs jövőbe látás" szabályt (spec 3. lépés) és a
  vig-eltávolítás helyességét (spec 7. lépés) tesztekkel kell védeni — ezek
  megsértése nem dob hibát, csak csendben értéktelen javaslatokat gyárt.
- A mypy kimaradt, mert a pandas/numpy típusannotációk aránytalanul lassítanák
  a fejlesztést ahhoz képest, amit ez a projekt nyerne vele.

---

## D-005 — Gmail SMTP app-jelszóval, absztrahált küldő mögött

**Dátum:** 2026-09-17
**Döntéshozó:** felhasználó

**A kérdés:** hogyan menjen ki a levél?

**Opciók:** Gmail SMTP / Resend / SendGrid.

**Döntés:** Gmail SMTP app-jelszóval, de a küldő egy `Kuldo` Protocol
interfész mögött.

**Miért:** ingyenes, azonnal működik, napi 500 levél limit (nekünk 3 kell).
Az absztrakció miatt a váltás később egy sor (`alapertelmezett_kuldo()`).

**Biztonsági megjegyzés:** az app-jelszó **nem** a Google-fiók jelszava; 2FA
kell hozzá. Ha kikerül, azonnal cserélni kell. A kód soha nem naplózza.

---

## D-006 — Minden UTC-ben, CET csak megjelenítéskor

**Dátum:** 2026-09-17
**Döntéshozó:** felhasználó

**A kérdés:** hogyan kezeljük az időzónát?

**Döntés:** minden időbélyeg UTC-ben tárolódik és UTC-ben utazik a kódban. A
CET/CEST konverzió **kizárólag** a megjelenítésnél történik, a
`kozos/ido.py::megjelenites()` függvényben.

**Miért:** a magyar nyári időszámítás miatt a 09:00 CET télen 08:00 UTC,
nyáron 07:00 UTC. Ha helyi időt tárolnánk, évente kétszer elcsúszna minden —
csendben.

**Következmény a GitHub Actionsre:** a cron csak UTC-t ismer, ezért minden
napi workflow **két cron-bejegyzést** tartalmaz (téli és nyári). A workflow
mindkettőre elindul, de a `--ido-ellenorzes` kapcsoló miatt csak az fut
végig, amelyik a helyes CET-időben van; a másik azonnal kilép (0 exit kód).

---

## D-007 — A ténylegesen implementált modulok kiválasztása

**Dátum:** 2026-09-17
**Döntéshozó:** Claude, a feladat keretein belül

**A kérdés:** a "még nem írunk modellkódot" utasítás mellett mit érdemes
mégis megírni?

**Döntés:** négy modul teljes implementációt kapott: `dontes/vig.py`,
`tetezes/kelly.py`, `modellek/kalibracio.py` (a zsugorítás része),
`kozos/ido.py`, valamint a `kimenet/level_formazo.py`.

**Miért:** ezek (a) tiszta matematika vagy formázás, külső adat és modell
nélkül, (b) a specifikáció pontos képletet és példát ad rájuk, (c) teszttel
azonnal ellenőrizhetők, és (d) a smoke-teszt csak így tud valódi kimenetet
produkálni. Nem "modellkód" abban az értelemben, hogy nem becsülnek
valószínűséget — a becslést fogadják el bemenetként.

**Ami szándékosan váz maradt:** minden, ami történelmi adatot, illesztést vagy
külső szolgáltatást igényel.

---

## D-008 — Gyanús piac jelzése a vig-eltávolításban

**Dátum:** 2026-09-17
**Döntéshozó:** Claude (a specifikáción túli kiegészítés)

**A kérdés:** mi történjen, ha egy piac overroundja negatív vagy szokatlanul
magas?

**Háttér:** a tesztírás közben derült ki, hogy a `[1.20, 12.00]` szorzópár
**negatív** overroundot ad (−8,3%). Egy valós fogadóiroda soha nem ad ilyet.
Ha ilyet látunk, az vagy **hiányos kimenetel-lista** (a piac egy részét adtuk
át a függvénynek), vagy elrontott scraping.

**Miért veszélyes csendben átengedni:** negatív overroundnál a power-kitevő
1 alá esik, az eredmény matematikailag érvényes, de **hamis élt gyárt** — a
rendszer azt hinné, hogy értéket talált.

**Döntés:** a `VigEredmeny` kapott egy `gyanus` és `gyanu_oka` mezőt.
Figyelmeztetést naplóz, ha az overround a [0, 0.25] sávon kívül esik, vagy ha
a power és az arányos módszer több mint 5 pp-tel eltér.

**Ami még hátravan:** a döntési fának (8. lépés) ezt a jelzést figyelembe kell
vennie — a gyanús piacok jelöltjeit ki kell szűrni. Ezt a Fázis 4-ben kell
megvalósítani, és a `KiesesiOk` enumot ki kell egészíteni. Rögzítve:
[OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) NY-08.

---

## D-009 — Saját minimális WAMP-kliens, nem Playwright és nem `autobahn`

**Dátum:** 2026-09-18
**Döntéshozó:** Claude, a felhasználó jóváhagyásával

**A kérdés:** hogyan beszéljünk a Tippmix WAMP-végpontjával az 1. lépésben?

**A három opció:**

| Opció | Előny | Hátrány |
| --- | --- | --- |
| **Playwright** (böngésző) | bizonyítottan működik; a böngésző kezeli a protokollt | lassú, ~400 MB böngészőmotor, minden futásnál teljes oldalbetöltés; a munkahelyi gépen a vállalati policy blokkolja |
| **`autobahn`** (teljes WAMP-könyvtár) | szabványkövető, karbantartott | nehéz függőség (Twisted/asyncio réteg) olyan protokollszeletért, amiből öt üzenettípust használunk |
| **Saját minimális kliens** | néhány JSON-tömb, nulla új függőség (a `websockets` már tranzitívan bent van) | nekünk kell karbantartani, ha a Tippmix változtat |

**Ami eldöntötte:** a felderítés kimutatta, hogy a kézfogás **autentikáció
nélküli** (HELLO → WELCOME, nincs CHALLENGE), és a lekérdezés egyetlen
CALL/RESULT párral megvan. Ebből a WAMP-ból öt üzenettípus kell:
HELLO, WELCOME, CALL, RESULT, ERROR. Ezt egy ~130 soros modul lefedi.

A verifikáció ([scripts/wamp_proba.py](../scripts/wamp_proba.py)) bizonyította,
hogy böngésző nélkül működik — **és a munkahelyi gépről is**, ahol a
Playwright-út a vállalati proxy miatt elbukott.

**Döntés:** saját minimális WAMP-kliens
([gyujtes/wamp_kliens.py](../src/tippmix/gyujtes/wamp_kliens.py)).

**A kockázat és a tartalék:** ha a Tippmix bevezeti a CHALLENGE-et vagy
megváltoztatja a keretezést, a kliens `AdatgyujtesHiba`-t dob (nem csendben
hibázik), és a Playwright-út továbbra is rendelkezésre áll — a felderítő
szkript és a hozzá tartozó workflow bent maradt a repóban pontosan ezért.

---

## D-010 — A bajnokság-párosítás pontos egyezés, nem részstring

**Dátum:** 2026-09-18
**Döntéshozó:** Claude (az első éles próba tanulsága)

**A kérdés:** hogyan párosítsuk a `ligak.yaml` bajnokságait a Tippmix
neveivel, amik évadot is tartalmaznak ("Premier Liga 2026/2027")?

**Az első megoldás — részstring-egyezés — csendben rossz volt.** Az éles
próba eredménye:

- „Bundesliga" beengedte a **Bundesliga 2.-t és 3.-at**
- „Premier League" beengedett egy **indiai** és egy **ausztrál női** ligát
- az **angol Premier League kimaradt**, mert a Tippmix „Premier Liga"-ként írja

Vagyis egyszerre gyártott hamis találatokat és hagyta ki az igazit — kivétel
nélkül, csendben.

**Döntés:** új `tippmix_nev` mező a `ligak.yaml`-ban a Tippmix pontos
írásmódjával, és a párosítás **pontos egyezés** az évad levágása után
(`"\s+\d{4}(/\d{4})?$"`).

**Miért nem fuzzy:** ez ugyanaz az elv, mint a CLAUDE.md 3. szabálya a
csapatnevekre. A fuzzy találat 95%-ban jó, 5%-ban csendben rossz — és egy
rossz bajnokság-párosítás egy egész liga meccseit viszi be tévesen. Inkább
maradjon ki egy bajnokság: az látható hiány, nem néma hiba.

**Következmény:** ahol a `tippmix_nev` hiányzik (Championship, Eredivisie,
Primeira Liga — a felderítéskor nem voltak kínálatban), a liga **nem
gyűjthető**. Ez szándékos: aktiválás előtt ki kell deríteni a pontos nevet.
Ugyanez érvényes a kosárpiacokra, lásd
[OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) NY-19.

---

## D-011 — A Tippmix felé irányuló forgalom kizárólag GitHub Actionsből indul

**Dátum:** 2026-09-18
**Döntéshozó:** a felhasználó kérése

**A kérdés:** futhat-e a Tippmix-lekérdezés a fejlesztő gépéről?

**A háttér:** a fejlesztő munkahelyi gépet és céges hálózatot használ, ahol az
IT-szabályzat tiltja a tippmixpro.hu elérését. A fejlesztés során kiderült,
hogy a **nyers WebSocket-kapcsolat átmegy a céges proxyn** (csak a böngésző
van tartalomszűrve, lásd NY-11) — tehát a lekérdezés technikailag működik
lokálisan.

**Épp ez a veszélyes:** attól, hogy technikailag megy, még szabályszegésnek
minősülhet, és ennek a fejlesztőre nézve **munkajogi következménye** lehet.
Ez nem technikai, hanem személyes kockázat, és fontosabb, mint a fejlesztői
kényelem.

**Döntés:** minden Tippmix felé irányuló hálózati hívás GitHub Actions
runneren fut, fejlesztés és hibakeresés közben is.

- Az éles futások (`delelotti-futas`, `esti-futas`, `zaro-odds`) eleve így
  mentek — ezeken nem kellett változtatni.
- Új: [gyujtes-proba.yml](../.github/workflows/gyujtes-proba.yml) —
  a gyűjtés kipróbálása runneren, az eredmény artefaktumként letölthető.
  Nem küld e-mailt, nem ír adatbázisba, nem igényel titkot.
- A `scripts/` alatti, Tippmixet hívó szkriptek egy **tényleges
  védőkorlátot** kaptak ([_csak_actionsben.py](../scripts/_csak_actionsben.py)):
  ha nem CI-ben futnak, kilépnek, mielőtt bármit hívnának.

**Miért kód, nem csak komment:** egy figyelmeztető komment nem állít meg egy
jövőbeli munkamenetet, ami „csak gyorsan kipróbálná". A védőkorlát igen. A
`TIPPMIX_ENGEDEM_A_LOKALIS_HIVAST=1` felülbírálás létezik, de kizárólag a
felhasználó kifejezett kérésére használható.

**Hatókör:** ez a megkötés a Tippmixre vonatkozik. A többi adatforrás
(football-data.co.uk, Understat, ClubElo, NBA) nem szerencsejáték-oldal, azokat
nem érinti — a Fázis 1 történelmi adatgyűjtése tehát futhat lokálisan is.

---

## D-012 — A történelmi adat Parquet-ben, nem SQLite-ban

**Dátum:** 2026-09-18
**Döntéshozó:** Claude

**A kérdés:** a specifikáció „Fejlesztési sorrend" táblázata a Fázis 1-re
„Történelmi adatok letöltése, **SQLite-ba** töltése (foci)" ír. Kövessük?

**Miért tértünk el:**

1. **A spec SQLite-ja a Supabase-döntés előtti állapot.** A felhasználó
   később Supabase-t választott igazságforrásnak — a `settings.yaml`
   `adattar.backend: "supabase"`. Egy harmadik tároló (SQLite) beékelése
   csak zavart okozna.
2. **A `settings.yaml` eleve Parquet-cache-t ír elő** a backteszthez
   (`adattar.cache_konyvtar`), épp azért, hogy ne olvassunk százezer sort
   hálózaton keresztül.
3. **A hozzáférési minta oszlopos, nem soros.** A Dixon-Coles illesztés és a
   backteszt a teljes ligatáblát olvassa egyben, nem egyedi sorokat keres —
   erre a Parquet gyorsabb, és a pandas natívan kezeli.

**Döntés:** a letöltött történelmi meccsadat `data/tortenelmi/<liga>.parquet`
fájlokba kerül, gitignore-olva (regenerálható:
`uv run tippmix tortenelmi-letoltes`).

**Mi NEM változik:** a Supabase marad az igazságforrás a *futási*
eredményekre (tippek, CLV, naplózás) — az a 12. lépés. Ez a döntés csak a
modellillesztés bemenetéről szól.

**A spec-eltérés rögzítve**, ahogy a CLAUDE.md előírja: ha a spec és a
gyakorlat eltér, azt le kell írni, nem csendben eldönteni.

---

## D-013 — `setuptools` explicit függőségként a soccerdata miatt

**Dátum:** 2026-09-18
**Döntéshozó:** Claude

**A probléma:** a `soccerdata` **egyetlen almodulja sem importálható** Python
3.12-n:

```
ModuleNotFoundError: No module named 'distutils'
```

**Az ok:** a `soccerdata` behúzza az `undetected-chromedriver`-t, ami a
`distutils`-t importálja. A `distutils` a Python 3.12-ben **megszűnt** (PEP
632). A `soccerdata/__init__.py` mindent behúz, ezért még a `clubelo` vagy a
`match_history` sem érhető el, pedig azoknak semmi közük a böngésző-vezérléshez.

**A mérlegelt opciók:**

| Opció | Értékelés |
| --- | --- |
| Python 3.11-re visszalépni | a CLAUDE.md 3.12-t ír elő; egy tranzitív függőség miatt visszalépni aránytalan |
| `soccerdata` elhagyása, saját CSV-letöltő | a football-data.co.uk CSV-k formátuma szezononként változik; a wrapper épp ezt kezeli |
| `setuptools` felvétele | a `setuptools` shimmeli a `distutils`-t; egysoros javítás |

**Döntés:** `setuptools>=69.0` a `pyproject.toml` függőségei közé, kommenttel
az indoklásról.

**A kockázat:** a `setuptools` egy jövőbeli verziója megszüntetheti a
`distutils`-shimet. Ha ez bekövetkezik, a tünet ugyanez az import-hiba lesz,
és akkor a `soccerdata` elhagyása kerül újra napirendre. Addig ez a
legkisebb beavatkozás.

---

## D-014 — A Fázis 2-3 mérési eredménye: a modell nem veri a piacot

**Dátum:** 2026-09-18
**Döntéshozó:** a mérés (nem vélemény)

**A kérdés:** teljesül-e a specifikáció kilépési feltétele?

> „A 2. és 3. fázis a lényeg. Ha ezeken átjutunk és a backteszt nem mutat
> pozitív CLV-t, akkor a 4-6. fázist nem érdemes megépíteni ebben a formában.
> Jobb ezt a 2. héten megtudni, mint a 8-on."

**A válasz: nem teljesül. A modell nem veri a piacot.**

**A bizonyíték** (out-of-sample, érintetlen 2024/25-ös teszt-szelet, 5 liga,
8406 jelölt):

| | Brier |
| --- | --- |
| modell nyers | 0,2127 |
| + izotonikus kalibráció | 0,2128 |
| + kalibráció + zsugorítás | 0,2089 |
| **PIAC (záró ár, vig-mentes)** | **0,2082** |

A döntő mutató: ahol a teljes modell 3%+ élt lát (n=626), a modell 44,8%-ot
mond, a piac 40,5%-ot, és **ténylegesen 38,8%** következik be. A valóság a
piacnál is rosszabb felénk — vagyis ahol élt látunk, ott szisztematikusan
tévedünk.

**Nem paraméterezési hiba.** A 9-pontos rács (ξ × xG-súly) **mind a 9
pontjában** veszítünk a piaccal szemben, és mind a 9-ben a tényleges
gyakoriság a piac becslése alatt van. A legjobb beállításunk 0,2071, a piac
0,2063.

**Amit kipróbáltunk:** Dixon-Coles idősúlyozott ML-illesztéssel,
τ-korrekció, xG-jellemzők (99%+ lefedettség), izotonikus kalibráció, piaci
zsugorítás, adatelégségességi kapu, szigorú él- és odds-szűrés.

**Amit NEM próbáltunk ki, és emiatt a következtetés korlátozott:**

- ClubElo (a forrás halott, NY-20) — de ez részben ugyanazt méri, mint a
  Dixon-Coles csapaterősség
- sérülés-/felállás-adat (a spec hírvétója, 8. lépés)
- piacok közötti eltérés (Tippmix vs Pinnacle) — lásd alább

**A döntés:** a 4-6. fázist **ebben a formában nem építjük tovább.** A
javaslat a leállás.

**Egy reálisabb alternatíva, ha mégis folytatódik:** a jelenlegi rendszer a
*piac véleményét* akarja megverni saját statisztikai becsléssel — ez a nehéz
út. A könnyebb kérdés: **hol tér el a Tippmix a Pinnacle-től?** Ott nem
nekünk kell okosabbnak lennünk a piacnál, csak észrevenni, hogy ugyanaz a
fogadás az egyik helyen olcsóbb. Ez viszont **más rendszer**, nem ennek a
folytatása: más adatgyűjtés (két platform egyszerre), más döntési logika, és
külön kutatást igényel.

**Amit ez a munka ért:** működő Tippmix-integráció (WAMP), 9110 meccses
történelmi adattár xG-vel, és egy becsületes mérőkeret, ami képes volt
kimondani, hogy valami nem működik. Ez utóbbi a ritkább — a legtöbb
fogadási rendszer pont azért bukik, mert nincs ilyen mérése, vagy mert a
jövőbe látás miatt hamis pozitívat mutat.

---

## D-015 — A D-014 alternatíváját 1X2-n megmértük: a margó megeszi az élt

**Dátum:** 2026-09-18
**Döntéshozó:** a mérés (nem vélemény)

**A kérdés:** a D-014 végén javasolt „reálisabb alternatíva" — ne a piacot
verjük saját becsléssel, hanem vegyük észre, hol olcsóbb ugyanaz a fogadás —
működik-e egyáltalán?

**A mérés.** Tippmix-történelmi oddsunk nincs, ezért nem a Tippmixet mértük,
hanem a mechanizmust: puha irodák ára a Pinnacle power de-viggel számolt fair
ára ellen, 5 liga × 5 szezon 1X2 adatán
(`scripts/puha_vs_sharp.py`, `arres-teszt.yml`).

**A válasz: 1X2-n, a top-5 ligában nem működik.**

Árrés a záró 1X2 áron: Pinnacle **2,72%**, a puha irodák **5,04-6,47%**. Egy
lábnak nem elég jobbnak lennie a fair árnál — a saját irodája árrését is
felül kell múlnia.

Az egyes irodák sorai mind zajban vannak (±2SE > |ROI|). Az egyetlen
statisztikailag erős sor a mezőny legjobb ára (`Max`): 8048 fogadáson
**+0,75% ± 3,63%**, azaz pontosan mért nulla. A korai teszten 8271 fogadáson
**+0,42% ± 3,29%**, és a küszöb emelésével a ROI romlik, nem javul.

**A legvalószínűbb ok a győztes átka:** azt a lábat választjuk ki, ahol
`odds × p_fair − 1` a legnagyobb, ami preferálja azokat a lábakat, ahol a
de-vig felülbecsli `p_fair`-t. A látszólagos élet a becslési hiba eszi meg.
Ez a kiválasztás hibája, nem a de-vig módszeré.

**Amit ez NEM zár ki, és ezért a döntés nem „leállás":**

1. Csak **1X2**-t mértünk — a 3-utas piac a legnagyobb árrésű, a top-5 liga
   pedig a leghatékonyabb. Ez a legrosszabb terep egy ilyen stratégiának.
2. A **2-utas piacok** (ázsiai hendikep, gólszám) érintetlenek. Bloom és
   Benham is ezeken dolgozik, és ott az árrés jellemzően 2-4%. Az adatunkban
   a `PAHH`/`PAHA` és a gólszám-oszlopok megvannak.
3. A **Tippmix tényleges árrése ismeretlen** — egy élő listalekérésből
   megmérhető, és lényegében eldönti a kérdést.

**A döntés:** a következő két mérés, ebben a sorrendben, mielőtt bármit
építenénk: (1) a Tippmix árrése, (2) ugyanez a teszt 2-utas piacokon. Ha az
1. mérés 8-10%-ot ad, a stratégia 1X2-n halott, és a 2-utas piacokon is
nehéz lesz.

**Egy policy-következmény, amit itt rögzítünk:** a **Pinnacle és a Betfair
szerencsejáték-oldal**, tehát a D-011 megkötése (a forgalom kizárólag
Actionsből indulhat) **rájuk is vonatkozik** — a CLAUDE.md mentessége
(„a többi adatforrás nem szerencsejáték-oldal") csak a
football-data.co.uk-ra, az Understatra és az NBA-forrásokra igaz. Ha éles
sharp-referencia kell, tisztább egy adatszolgáltatót használni (nem
fogadóirodát).

**Amit ez a munka ért:** egy 2 perces, megismételhető mérés, ami a
„működhet-e egyáltalán" kérdésre számot ad vélemény helyett — és kizárta a
legdrágább zsákutcát, mielőtt bármit megépítettünk volna hozzá.
