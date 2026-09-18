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
