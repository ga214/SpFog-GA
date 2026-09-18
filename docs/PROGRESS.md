# Fejlesztési napló

Időrendi, naplószerű. Minden érdemi lépés után és minden munkamenet végén
bejegyzés: mit csináltunk, miért, mi működik, mi nem, mi a következő lépés.

**Legújabb bejegyzés felül.**

---

## 2026-09-18 (3) — Az 1. lépés kész és élesben működik

### Mit csináltunk

**Kiderült, hogy nem kell Playwright.** A felderítés után megírtuk a
[scripts/wamp_proba.py](../scripts/wamp_proba.py) verifikációt: a WAMP-kézfogás
és a lekérdezés sima `websockets`-szel is megy, böngésző nélkül — **sőt, a
munkahelyi gépről is**, mert a vállalati proxy csak a böngészőt szűri, a
WebSocketet nem. Ez gyorsabb és sokkal kevesebb erőforrást igényel.

**Elkészült az 1. lépés:**

- [gyujtes/wamp_kliens.py](../src/tippmix/gyujtes/wamp_kliens.py) — minimális
  WAMP v2 kliens (HELLO/WELCOME/CALL/RESULT/ERROR). Nem húztunk be nehéz WAMP
  könyvtárat: a protokollnak az a szelete, amit használunk, néhány JSON-tömb.
- [gyujtes/tippmix_scraper.py](../src/tippmix/gyujtes/tippmix_scraper.py) — a
  `letolt()` immár valódi: bajnokságok → meccsek → piacok/szorzók, 3×
  újrapróbálkozással, nyers válasz mentésével. A `kezi_tartalek_olvas()` is kész.
- **16 új teszt**, hálózat nélkül, rögzített Tippmix-rekordmintákon.
  Összesen **108 teszt**, mind zöld.

### Két csendes hiba, amit az első éles próba hozott felszínre

Mindkettő pontosan az a fajta, ami **nem dob kivételt, csak rossz adatot ad** —
amitől a CLAUDE.md kritikus szabályai óvnak.

**1. A bajnokság-párosítás részstringgel.** Az első futás eredménye: a
„Bundesliga" beengedte a másod- és harmadosztályt, a „Premier League" egy
indiai és egy ausztrál női ligát — **az angol Premier League viszont kimaradt**,
mert a Tippmix „Premier Liga"-ként írja.

Javítás: új `tippmix_nev` mező a [ligak.yaml](../config/ligak.yaml)-ban, a
Tippmix pontos írásmódjával, és a párosítás **pontos egyezés** az évad
levágása után. Ez a 3. szabály szelleme: inkább maradjon ki egy bajnokság,
mint hogy rosszat engedjünk be. Az inaktív ligáknál (Championship, Eredivisie,
Primeira Liga) a mező szándékosan hiányzik — a felderítéskor nem voltak a
kínálatban, és nem találgatunk.

**2. Az 1X2 kimenetel neve a csapat neve volt.** A `translatedName` a
hazai győzelemre „Bayern München"-t ad, nem „1"-et. Erre a döntési logika nem
építhet. Javítás: a nyelvfüggetlen `headerNameKey` (`home`/`draw`/`away`/
`over`/`under`) képződik a `settings.yaml` `kimenetel_kod` blokkján keresztül a
`ligak.yaml` kimenetel-kódjaira. Ismeretlen kulcs → kihagyás, nem találgatás.

Harmadik, kisebb hiba: a kosárlabda sportazonosítója **8**, nem 2 (a 2 a golf).

### Mi működik

```
uv run pytest                    → 108 passed
uv run tippmix config-ellenorzes → a konfiguráció érvényes
```

Éles próba a Tippmix ellen: **38 esemény, 190 odds-sor**, két bajnokságból
(Premier Liga, Bundesliga 1.), normalizált kimenetelekkel:

```
Premier Liga | Brentford - Chelsea | 1X2 - Rendes játékidő   | 1 | 2.68
Premier Liga | Brentford - Chelsea | 1X2 - Rendes játékidő   | X | 3.95
Premier Liga | Brentford - Chelsea | 1X2 - Rendes játékidő   | 2 | 2.46
Premier Liga | Brentford - Chelsea | Gólszám 2.5 - Rendes j. | Tobb     | 1.48
Premier Liga | Brentford - Chelsea | Gólszám 2.5 - Rendes j. | Kevesebb | 2.64
```

### Mi nem működik még

- A `zaro_odds_lekeres()` (CLV-hez) továbbra is `NotImplementedError` — a
  spec szerint ez a Fázis 5 feladata.
- A 2-10. lépés változatlanul váz.
- Az NBA-ra még nem futott éles próba (a szezon most kezdődik, 38 meccs van
  kínálatban) — a kosárpiacok (TOTAL, SPREAD) Tippmix-kódja még nincs
  felderítve, csak a focié.

### A következő lépés

**Fázis 1:** történelmi adatok letöltése (football-data.co.uk + Understat +
ClubElo) és Supabase-be töltése. Ez kell a 4. lépés (modellek) alá.

Mellékfeladat, amikor sorra kerül: a kosárlabda-piacok Tippmix-kódjának
felderítése ugyanazzal a módszerrel, ahogy a fociét csináltuk.

---

## 2026-09-18 (2) — Playwright WS-felderítő szkript; a munkahelyi gép kiesett

### Mit csináltunk

Megírtuk a Fázis 0 felderítő eszközét:
[scripts/ws_felderites.py](../scripts/ws_felderites.py) — Playwright-tal megnyitja a
`sports2.tippmixpro.hu/hu` oldalt, és a `page.on("websocket")` eseménnyel
minden WS-keretet (küldött és kapott egyaránt) JSONL-be ír, plusz egy emberi
olvasásra szánt összefoglalót. Kapcsolók: `--varakozas`, `--fejjel`,
`--csatorna` (rendszer-Chrome / Edge / Playwright saját Chromiumja).

### Mi derült ki — a lokális út zsákutca

A szkript működik, de **a munkahelyi gépen nem tud a célhoz férni**:

| Böngésző | Eredmény |
| --- | --- |
| Chrome (rendszer) | `net::ERR_SSL_VERSION_OR_CIPHER_MISMATCH` |
| Edge (rendszer) | betölt, de a cím: **„A szervezet által letiltott tartalom"** |
| Playwright Chromium | nem telepíthető, a `cdn.playwright.dev` timeoutol |

Ugyanakkor **`curl`-lal ugyanarról a gépről HTTP 200** jön, és a válasz a
valódi oldal (`<title>Sportfogadás</title>`).

**A tanulság:** a tiltás **böngésző-szintű vállalati policy**, nem hálózati
blokk — ezért megy a curl és bukik a böngésző. A Chrome SSL-hibája ugyanennek
a TLS-elfogó proxynak a mellékhatása. Vagyis nem a megközelítés rossz, hanem
a gép alkalmatlan rá.

### A megoldás: GitHub Actions runner

Új workflow: [.github/workflows/ws-felderites.yml](../.github/workflows/ws-felderites.yml) —
kézzel indítható (`workflow_dispatch`), a runneren telepít Chromiumot,
lefuttatja a szkriptet, és a kimenetet artefaktumként tölti fel (14 nap).

Ez **egyszerre két nyitott kérdést zár le**: megadja a WS-protokollt (NY-11)
és eldönti, hogy az Actions IP-jéről elérhető-e a Tippmix (NY-12) — ami a
teljes infrastruktúra-döntés alapja.

### Az eredmény: a Fázis 0 lezárult, a protokoll megvan

A workflow lefutott (run 35329378180, 1m38s, zöld). Az oldal a runneren
**betöltött**, a WS-kapcsolat létrejött, **250 küldött és 250 kapott keret**
rögzítve valódi odds-adattal.

**A protokoll szabványos [WAMP v2](https://wamp-proto.org/)** (`Wampy.js v6.2.2`
kliens) — a korábbi „egyedi, nem szabványos keretezés" feltételezés **téves
volt**. A handshake autentikáció nélküli: a HELLO-ra azonnal WELCOME jön,
CHALLENGE nélkül. Az adat WAMP CALL-lal kérhető, rekordalapú válaszban:

| Rekord | Amit ad |
| --- | --- |
| `MATCH` | `"Brentford - Chelsea"`, `startTime` (epoch ms), `parentName: "Premier Liga 2026/2027"` |
| `MARKET` | `"Gólszám 2.5 - Rendes játékidő"`, `paramFloat1: 2.5`, `mainLine: true` |
| `OUTCOME` | `typeName: "Draw"`, `translatedName: "Döntetlen"` |
| `BETTING_OFFER` | **`odds: 2.51`** |
| `MARKET_OUTCOME_RELATION` | a `MARKET`-et és az `OUTCOME`-ot köti össze |

Ez tartalmilag **pontosan az a `markets[] → outcomes[]` szerkezet**, amit a
specifikáció igényel — csak normalizált rekordokként, WAMP-on szállítva.
A teljes útvonallista és a mezőszerkezet:
[OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) NY-11 „Megoldás" szakasz.

**Három nyitott kérdés zárult le egyszerre:**

- **NY-11** (odds-végpont) — a protokoll és a mezőszerkezet megvan
- **NY-12** (Actions IP blokkolt-e) — **nem blokkolt**, a scraping maradhat
  GitHub Actionsben; nem kell önhosztolt runner
- **NY-14** (robots.txt) — mindkét hoszt ténylegesen elolvasva: a `sports2`
  semmit nem tilt, a `www` csak számla-/fiókkezelési útvonalakat. A fogadási
  kínálat olvasása egyik szabályt sem sérti.

### A következő lépés

Az 1. lépés megírása
([gyujtes/tippmix_scraper.py](../src/tippmix/gyujtes/tippmix_scraper.py)).
Mivel a handshake autentikáció nélküli és a protokoll szabványos,
**először Python WAMP-klienssel** (`autobahn`) érdemes próbálni, böngésző
nélkül — sokkal gyorsabb és kevesebb erőforrást igényel. Ha a szerver
`Origin`/`User-Agent` ellenőrzés miatt visszautasítja, a Playwright-út a
bizonyítottan működő tartalék.

Ezután **Fázis 1**: történelmi adatok letöltése és Supabase-be töltése.

---

## 2026-09-18 — GitHub repó élesítve, Fázis 0 elindult (odds-végpont felderítés)

### Mit csináltunk

**Infrastruktúra lezárva:**
- Supabase séma sikeresen lefuttatva (a `tippek_egyedi_napi_idx` IMMUTABLE-hibáját
  javítottuk: `idopont_utc::date` → `(idopont_utc AT TIME ZONE 'UTC')::date`)
- GitHub repó létrehozva és felpusholva: **github.com/ga214/SpFog-GA** (publikus)
- GitHub Secrets beállítva (5 db), próba-workflow (esti-futas, szárazon) sikeres
- CI-hiba javítva: a `gitleaks-action` az első push-nál elhasalt (nem talált
  semmit, csak a commit-tartomány számítása tört el `before` SHA hiányában) —
  áttértünk a gitleaks CLI közvetlen hívására, ami mindig a teljes historyt nézi
- `.claude/settings.json` (projekt- és felhasználói szinten) `bypassPermissions`
  módra állítva a CLAUDE.md 1. elve szerint; a VS Code extension felületén
  emellett külön `/config permissionMode=dontAsk` is szükséges volt — a
  settings.json önmagában nem elég ebben a kliensben

**Fázis 0 elindult — Tippmix odds-végpont felderítése:**

A felhasználó munkahelyi gépéről az IT-szabályzat tiltja a tippmixpro.hu
elérését, ezért a felderítést Claude végezte kiszolgáló-oldali HTTP-hívásokkal
(`curl`, `WebFetch`), ismeretlen (feltehetően nem magyar, esetleg adatközponti)
IP-ről.

**Eredmény — részletek: [docs/OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) NY-11, NY-12.**

Röviden:
- A `www.tippmixpro.hu` és a `sports2.tippmixpro.hu` mindkettő **elérhető
  kívülről**, nincs látható geo/bot-blokk a sima oldal-lekérésnél
- A `sports2.tippmixpro.hu/robots.txt`: `Disallow:` — semmi nincs tiltva
- **A kutatási jelentés által feltételezett egyszerű JSON REST-végpont NEM
  található.** Az odds-adat **WebSocket-en** (`wss://sportsapi.tippmixpro.hu/v2`)
  érkezik, saját (nem socket.io) keretezéssel. Megvan az operátor-azonosító
  (`ucsOperatorId: 2901`) és a realm (`www.tippmixpro.hu`), de a WS-üzenetek
  pontos formátuma nem deríthető ki szerveroldali HTTP-kliensből — ehhez
  éles böngészőben kell figyelni a WS-forgalmat, vagy Playwright-tal
  programozottan elcsípni (`page.on("websocket")`)

### Mi nem működik még

- A WS-protokoll formátuma ismeretlen → **az 1. lépés (esemény-begyűjtés)
  továbbra sem írható meg**
- Nincs teszt arra, hogy a GitHub Actions runner IP-je blokkolva van-e — csak
  azt tudjuk, hogy NEM minden külső IP van blokkolva

### A következő lépés

Két párhuzamos út, bármelyikkel folytatható:

1. **Playwright-tal programozott WS-lehallgatás** — nem kell kézzel
   reverse engineerelni a protokollt, a böngésző motorja csinálja, mi csak
   figyeljük az üzeneteket. Ez lehet, hogy közvetlenül a végleges
   scraper-megoldás lesz, nem csak felderítés.
2. **A felhasználó otthoni gépéről vagy telefonjáról** (nem a tiltott
   munkahelyi hálózatról) böngésző Network fülén WS-forgalom megnézése —
   gyorsabb, ha van rá alkalom, de nem feltétlenül szükséges, ha az 1. út
   működik.

Mivel a Playwright már szerepel a függőségek között, valószínűleg ez az
egyszerűbb és véglegesebb megoldás — a következő menetben ezt érdemes
kipróbálni: egy kis Python-szkript, ami Playwright-tal megnyitja a
`sports2.tippmixpro.hu/hu` oldalt, és kiírja az összes WS-üzenetet fájlba
elemzésre.

---

## 2026-09-17 — Fejlesztői környezet felállítása (Fázis −1)

### Mit csináltunk

A teljes fejlesztői váz összelövése. **Modellkód szándékosan nem készült** —
a cél egy futtatható, dokumentált, üres váz volt, amiben holnap el lehet
kezdeni a tényleges fejlesztést.

**Elkészült:**

- **Könyvtárszerkezet** a 12 lépéshez igazítva, alcsomagonként
  (`gyujtes`, `illesztes`, `jellemzok`, `modellek`, `dontes`, `tetezes`,
  `kimenet`, `adattar`, `backteszt`, `kozos`)
- **Python 3.12 + uv környezet**, `pyproject.toml` + `uv.lock`, minden
  specifikációban említett csomaggal
- **`config/settings.yaml`** — a specifikáció "Konfiguráció" szakasza szó
  szerint, plusz a szövegtörzsből levezetett technikai blokkok (gyűjtés,
  névillesztés, hírvétó, platform-limitek, leállítás, idő, naplózás, adattár,
  e-mail), mindegyik forrásmegjelöléssel
- **`config/ligak.yaml`** — 8 futball-liga (5 aktív), NBA + EuroLeague,
  piacdefiníciók aktív/inaktív kapcsolóval
- **`data/team_aliases.csv`, `data/league_map.csv`** — fejléc + 3-3 példasor
- **Supabase**: kliens-modul, `kapcsolat-teszt` parancs, teljes séma
  (`db/migrations/001_init.sql`): 7 tábla, indexek, RLS minden táblán
  policy nélkül, 3 nézet a CLV-hez és a leállítási feltételekhez
- **Titokkezelés**: `.env.example`, `.gitignore` (az első commit előtt kész),
  `titkok.py` maszkolással, `docs/SECRETS.md`
- **5 GitHub Actions workflow**: délelőtti, esti, záró-odds, CI (lint +
  teszt + gitleaks), keepalive
- **Naplózás**: `structlog` alapú, futás-azonosítóval minden soron, konzol és
  JSON formátumban
- **`README.md`**, **`CLAUDE.md`**, és ez a három dokumentum
- **92 teszt**, mind zöld

### Amit ténylegesen implementáltunk (nem csak váz)

Négy modult megírtunk, mert tiszta matematika, külső adat nélkül tesztelhető,
és a specifikáció pontos képletet ad rájuk:

| Modul | Mit csinál | Tesztek |
| --- | --- | --- |
| `dontes/vig.py` | Vig-eltávolítás power és arányos módszerrel, él, EV | 16 |
| `tetezes/kelly.py` | Kelly-tétezés, plafonok, napi limit arányos csökkentése | 16 |
| `modellek/kalibracio.py` | Piaci zsugorítás, Brier-pontszám | 11 |
| `kozos/ido.py` | UTC/CET konverzió, DST-kezelés | 16 |
| `kimenet/level_formazo.py` | A levél összeállítása a spec formátumában | (smoke) |

A többi modul **szignatúrában kész, törzsben `NotImplementedError`**, a
docstringben a specifikáció vonatkozó szabályaival.

### Mi működik

```
uv run pytest                      → 92 passed
uv run ruff check .                → All checks passed
uv run tippmix config-ellenorzes   → a konfiguráció érvényes
uv run tippmix futtat --tipus este --szarazon --smoke
                                   → mind a 12 lépésen végigmegy, levél összeáll
```

A smoke-futás bizonyítja, hogy a modulok összeállnak: minden import
feloldható, a konfiguráció betölthető, a pipeline nem esik szét, és a levél
értelmes szöveget ad.

### Mi nem működik még

- **A 2-10. lépés nincs implementálva.** A pipeline `--smoke` nélkül
  `NotImplementedError`-t dob az 1. lépésnél.
- **A Supabase-kapcsolat nincs élesben tesztelve** — a séma megírva, de a
  `001_init.sql` még nem futott le a Supabase felületén (ez felhasználói
  lépés, lásd `docs/SUPABASE_SETUP.md`).
- **A GitHub-repó nincs létrehozva** — a lokális git init megtörtént, a
  felpushelás a felhasználó feladata.
- **A `sports2.tippmixpro.hu` végpont pontos útvonala ismeretlen** — ez a
  Fázis 0 első feladata.

### Amit menet közben találtunk

Három ellentmondást találtunk a két normatív dokumentum között, és két hibát a
specifikáció példáiban. Mind rögzítve az
[OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) fájlban (NY-01…NY-08). A legfontosabb:

- a kutatási jelentés a **Supabase ellen érvel** (7 napos szüneteltetés), a
  felhasználó mégis Supabase-t választott — napi futásnál a korlát nem áll be
- a specifikáció **Kelly-példatáblázata** helyenként felfelé kerekít, holott a
  saját 7. szabálya lefelé kerekítést ír elő; a normatív szabály nyert

### A következő lépés

**Fázis 0 — empirikus verifikáció (a spec szerint 1 nap):**

1. Böngésző hálózati fülén kideríteni a `sports2.tippmixpro.hu` odds-végpont
   pontos útvonalát és válaszformátumát
2. Letölteni és **ténylegesen elolvasni** a `tippmixpro.hu/robots.txt` és
   `sports2.tippmixpro.hu/robots.txt` fájlokat
3. Tesztelni, hogy a végpont elérhető-e (a) a magyar IP-ről, (b) GitHub
   Actions runnerről
4. Ugyanez a `stats.nba.com`-ra (a kutatás szerint blokkolja az adatközponti
   IP-ket)

**Ez a teszt dönti el a végleges infrastruktúrát.** Ha az Actions runner
blokkolt, a geo-érzékeny scraping a felhasználó windowsos gépére kerül
(önhosztolt runner vagy Task Scheduler).

Ezután **Fázis 1**: történelmi adatok letöltése (football-data.co.uk +
Understat + ClubElo), Supabase-be töltése.

### Felhasználói teendők a következő menet előtt

1. `db/migrations/001_init.sql` lefuttatása a Supabase SQL Editorában
   → [SUPABASE_SETUP.md](SUPABASE_SETUP.md)
2. `.env` kitöltése → [SECRETS.md](SECRETS.md)
3. GitHub-repó létrehozása és felpushelás (a parancsok a záró összefoglalóban)
4. GitHub Secrets felvétele → [SECRETS.md](SECRETS.md)
