# CLAUDE.md — a projekt belépési pontja

**Ha új szálon kezdesz dolgozni ezen a projekten, ezt olvasd el először.**
Utána a [docs/PROGRESS.md](docs/PROGRESS.md) mondja meg, hol tartunk.

---

## A projekt öt mondatban

1. Automatizált sportfogadási tipprendszert építünk a magyar **Tippmix Pro**
   platformra, ami naponta kétszer e-mailben küld konkrét fogadási
   javaslatokat tétösszeggel.
2. A rendszer **nem azt jósolja meg, ki nyer** — minden eseményre kiszámolja a
   saját valószínűség-becslését, összeveti a Tippmix szorzójából számolt fair
   árral, és csak ott javasol fogadást, ahol az eltérés elég nagy és
   megbízható.
3. A futás **12 lépésből** áll, mindig ugyanabban a sorrendben: adatgyűjtés →
   névillesztés → feature-építés → modellek → kalibráció és piaci zsugorítás →
   vig-eltávolítás → döntési fa → tétezés → kombináció → e-mail → naplózás.
4. A siker mércéje a **CLV (closing line value)**, nem a rövid távú nyereség —
   a nyereség szerencse kérdése, a CLV nem.
5. A rendszer **nem garantáltan nyereséges**; ha a backteszt nem mutat pozitív
   CLV-t, az a becsületes válasz, hogy ne éleseddjen.

---

## A két normatív dokumentum

Mindent **ezekből kell levezetni**, nem saját verzióból:

| Fájl | Mit tartalmaz |
| --- | --- |
| `docs/Tippmix tipprendszer — döntési logika specifikáció.md` | **A normatív specifikáció.** A 12 lépés pontos algoritmusa, küszöbökkel és képletekkel. |
| `docs/compass_artifact.md` | Kutatási jelentés: adatforrások, platform-részletek, infrastruktúra, korlátok. |

Ha a kettő ellentmond egymásnak, **a specifikáció nyer**, és az ellentmondást
be kell írni a [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md) fájlba — nem
csendben eldönteni.

---

## Technológiai stack

| Terület | Választás | Miért |
| --- | --- | --- |
| Python | **3.12** | Minden szükséges csomag támogatja; a 3.13 még helyenként törik |
| Csomagkezelő | **uv** | Gyors, lockfile-t ad, az Actionsben is sokkal gyorsabb a pipnél |
| Adattár | **Supabase (Postgres)** | Felhasználói döntés. A backteszt lokális Parquet-cache-t használ a sebességért. |
| Tesztelés | **pytest** | |
| Linter/formatter | **ruff** | Egyben mindkettő, nulla konfiguráció |
| Ütemezés | **GitHub Actions** | A repó publikus → korlátlan perc |
| E-mail | **Gmail SMTP** app-jelszóval | Ingyenes, absztrahált küldő-interfész mögött |
| Modellezés | pandas, numpy, scipy | |
| Adatforrások | soccerdata, understatapi, nba_api, euroleague-api | |
| Scraping | httpx (elsődleges), playwright (tartalék) | |
| Névillesztés | rapidfuzz | |

---

## Könyvtárszerkezet

```
config/
  settings.yaml          Minden küszöb, súly és limit. A kódban NINCS beégetett szám.
  ligak.yaml             Engedélyezett bajnokságok és piacok.

data/
  team_aliases.csv       Csapatnév-leképezés — VERZIÓZOTT (kézi munka eredménye)
  league_map.csv         Bajnokság-leképezés — VERZIÓZOTT
  raw/ manual/ cache/    gitignore

db/migrations/
  001_init.sql           Az alapséma. KÉSŐBB NEM ÍRJUK ÁT — lásd a 2. elvet.

src/tippmix/
  kozos/        config.py, titkok.py, naplo.py, ido.py, tipusok.py, hibak.py
  gyujtes/      1. lépés — tippmix_scraper.py, tortenelmi.py
  illesztes/    2. lépés — nevillesztes.py
  jellemzok/    3. lépés — epito.py
  modellek/     4-6. lépés — futball.py, kosar.py, kalibracio.py
  dontes/       7-8. lépés — vig.py, dontesi_fa.py, hirveto.py
  tetezes/      9-10. lépés — kelly.py, kombinacio.py
  kimenet/      11. lépés — level_formazo.py, email_kuldo.py
  adattar/      12. lépés — supabase_kliens.py, naplozo.py
  backteszt/    keret.py
  pipeline.py   a 12 lépés vezérlője
  cli.py        parancssori felület

.github/workflows/  delelotti-futas, esti-futas, zaro-odds, ci, keepalive
tests/              pytest
docs/               PROGRESS, DECISIONS, OPEN_QUESTIONS, SECRETS, SUPABASE_SETUP
```

---

## Futtatási parancsok

```powershell
uv sync --extra dev                        # környezet felállítása
uv run tippmix config-ellenorzes           # a YAML-ok validálása
uv run tippmix kapcsolat-teszt             # Supabase-kapcsolat + séma
uv run tippmix futtat --tipus delelott     # délelőtti futás
uv run tippmix futtat --tipus este         # esti futás
uv run tippmix futtat --szarazon --smoke   # smoke: nincs e-mail, nincs DB
uv run tippmix zaro-odds                   # záró szorzók a CLV-hez
uv run pytest                              # teljes tesztkészlet
uv run pytest -m smoke                     # csak smoke-tesztek
uv run ruff check . ; uv run ruff format . # lint + formázás
```

---

## A projekt öt kritikus szabálya

Ezek a specifikációból jönnek, és **megsértésük csendben értéktelen
javaslatokat gyárt** — nem dob hibát, csak rossz eredményt ad.

1. **Nincs beégetett szám a kódban.** Minden küszöb, súly, limit a
   `config/settings.yaml`-ból jön.

2. **Nincs jövőbe látás.** Minden jellemzőt úgy kell számolni, hogy kizárólag
   a meccs kezdése előtti adatokat használja. Ugyanaz a kódfüggvény építi a
   jellemzőket élesben és backtesztben, egyetlen `asof_utc` paraméterrel. Ha
   ezt elrontod, a backteszt csodálatos eredményt ad, élesben meg buksz.

3. **A névillesztés soha nem automatikus.** A fuzzy találat 95%-ban jó, 5%-ban
   csendben rossz csapatot választ. Az 5% hibás párosítás rosszabb, mint az,
   hogy egy meccs kimarad. A javaslat a levélbe megy, a felhasználó írja be a
   CSV-be.

4. **A piaci zsugorítás nem opcionális.** `p_végleges = w × p_kalibrált +
   (1−w) × p_piac_fair`. Az esetek nagy részében a piacnak van igaza, nem
   nekünk. A zsugorítás következménye — sokkal kevesebb tipp — nem hiba, hanem
   a védelem a hamis élek ellen.

5. **Nincs veszteségpótlás.** Ha az előző nap mínusz volt, az a mai tétekre
   semmilyen hatással nincs. Ez a legfontosabb védelem a bankroll ellen.

---

## Minden munkamenet végén kötelező

**Ezek frissítése a feladat része, nem külön kérés.** Ha befejezel egy egységet
és nem frissítetted a `PROGRESS.md`-t, akkor a feladat nincs kész. Ne várd meg,
hogy szóljanak.

| Fájl | Mikor írsz bele |
| --- | --- |
| [docs/PROGRESS.md](docs/PROGRESS.md) | Minden érdemi lépés után és minden munkamenet végén: mit csináltál, miért, mi működik, mi nem, mi a következő. Időrendi, naplószerű. |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Minden technológiai és módszertani döntésnél: mi volt a kérdés, milyen opciók voltak, mit választottunk, miért. **Régi bejegyzést soha nem írunk át** — a változás új bejegyzésként kerül a végére. |
| [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md) | Amit nem tudunk, amit kalibrálni kell, ami elakadt, ami ellentmondásos a dokumentumokban. |

---

## Biztonsági elvárások

- **Semmilyen kulcs, jelszó vagy token nem kerülhet a repóba, még példaként
  sem.** A repó publikus.
- A Supabase **service role kulcsa** csak szerveroldalon és GitHub Secretsben
  él. Ha valaha frontend kerül a projektbe, oda **csak anon kulcs** mehet, row
  level security mellett.
- A `.gitignore` tartalmazza a `.env`-et, az adatkönyvtárakat és a lokális
  adatbázisfájlokat.
- Ha bármilyen ponton olyan megoldást javasolsz, aminek biztonsági kockázata
  van, azt **külön mondd el**, ne rejtsd el a kódban.

Részletek: [docs/SECRETS.md](docs/SECRETS.md).

### A Tippmix felé SOHA nem indul forgalom a fejlesztő gépéről

**Ez nem technikai, hanem munkahelyi kockázat, és nincs alóla kivétel.**

A fejlesztő munkahelyi gépet és céges hálózatot használ, ahol az IT-szabályzat
tiltja a tippmixpro.hu elérését. A nyers WebSocket-kapcsolat ugyan átmegy a
céges proxyn (csak a böngésző van szűrve), **de attól még szabályszegésnek
minősülhet** — és ennek a fejlesztőre nézve munkajogi következménye lehet.

Ezért:

- **Minden Tippmix felé irányuló hálózati hívás GitHub Actions runneren fut.**
  Az éles futások (`delelotti-futas`, `esti-futas`, `zaro-odds`) eleve így
  mennek.
- **Fejlesztés és hibakeresés közben is**: ha ki kell próbálni a gyűjtést,
  arra a `gyujtes-proba.yml` workflow való — `gh workflow run
  gyujtes-proba.yml`, majd az eredmény artefaktumként letölthető.
- **Soha ne futtass olyan lokális parancsot, ami a tippmixpro.hu-ra vagy a
  sportsapi.tippmixpro.hu-ra megy** — se `curl`, se Python, se böngésző, se
  „csak egy gyors teszt". Ha úgy érzed, hogy egy hibakereséshez feltétlenül
  kellene, **kérdezz rá a fejlesztőnél**, ne csináld meg magadtól.
- A `scripts/` alatti felderítő szkriptek (`ws_felderites.py`,
  `wamp_proba.py`, `gyujtes_proba.py`) **kizárólag Actionsben futtatandók**,
  akkor is, ha lokálisan technikailag működnének.

Ez a megkötés a Tippmixre vonatkozik. A többi adatforrás (football-data.co.uk,
Understat, ClubElo, NBA) nem szerencsejáték-oldal, azokat nem érinti.

---

## Adatmodell-változások

Ha adatbázis-sémát módosítasz, **mindig jelezd, ha valamit a VS Code-on kívül
kell lefuttatni** (Supabase felületén SQL-t, migrációt, jogosultságot). Legyen
egyértelmű: mit, hol, milyen sorrendben.

---
---

# Együttműködési elvek Claude-dal (AI-asszisztált fejlesztés)

## 1. A legfontosabb elv: NE ÁLLJ MEG ENGEDÉLYT KÉRNI

Ha egy feladatot egyszer, egyértelműen kiadok ("csináld meg X-et", "vidd végig Y
pipeline-t"), az AI-nak **a teljes folyamatot végig kell futtatnia megállás és
visszakérdezés nélkül** – beleértve azokat a lépéseket is, amik önmagukban "veszélyesnek"
tűnhetnek (pl. git push élesre, fájlok felülírása, külső API hívás), **ha ezek a feladat
elfogadott, ismert részei**.

**Miért fontos ez ennyire:** a visszakérdezés nem óvatosság, hanem súrlódás – minden
megállás azt jelenti, hogy nekem kell ott ülnöm és jóváhagyni valamit, amit már egyszer
elrendeltem. Ha egy folyamatot egyszer jóváhagytam (akár egy korábbi beszélgetésben), az
a jövőben – **más szálban, más munkamenetben is** – ugyanúgy megállás nélkül fusson le.

**Hogyan kell ezt a gyakorlatban alkalmazni:**
- Ha egy ismétlődő, dokumentált pipeline-ról van szó (letöltés → feldolgozás → build →
  deploy → ellenőrzés), az AI ne kérdezzen rá minden lépés előtt, hanem fusson végig rajta.
- Több cél/URL/feladat egy üzenetben = ugyanez a trigger mindegyikre, egymás után,
  visszakérdezés nélkül.
- **Csak akkor álljon meg, ha VALÓDI akadály merül fel** – azaz olyan technikai vagy
  tartalmi döntési pont, amit nem lehet a korábbi instrukciókból levezetni (pl. a bemenet
  szokatlan formátumú, vagy két ésszerű megoldás közül kellene választani, aminek más-más
  következménye van). Ez nem "engedélykérés", hanem valós útelágazás – ilyenkor helyes
  megállni.
- A gyakorlatban ez azt jelenti, hogy a permission-rendszert (allowlist) is úgy kell
  beállítani, hogy ne akadjon fenn triviális dolgokon: ha egy könyvtárra vagy
  parancsmintára engedélyt adok, azt **a lehető legáltalánosabb szülőkönyvtárra/mintára**
  add meg, ne a jelenleg éppen futó konkrét példányra (pl. ha ma egy adott azonosítóval
  dolgozunk, a jövőben másik azonosítóval is fog – az engedély legyen elég tág ahhoz, hogy
  ne kelljen újra jóváhagyni).
- Compound/láncolt parancsoknál (`cmd1 && cmd2`, `until ... do ... done`) minden
  al-lépést külön is le kell fedni az allowlistben, mert az egyes tagokat külön nézheti a
  jóváhagyás-ellenőrzés.

**Amiben viszont tényleg meg kell állni** (ezek nem kivételek a szabály alól, hanem más
kategória):
- Publikált/éles, korábban jóváhagyott munka újbóli módosítása, felülírása vagy
  visszamenőleges ellenőrzése – lásd 2. pont.
- Olyan akció, ami visszavonhatatlan és harmadik felet érint (pl. email kiküldés külső
  címzettnek) – ilyenkor az AI állítsa össze a kész, futtatható parancsot/tartalmat, de ne
  indítsa el saját döntésből.
- Route-szintű/architekturális kódváltoztatás vagy DNS/domain-szintű beavatkozás, ha ez
  nem volt a feladat explicit része.

## 2. Egyéb gyakorlati elvek

- **DB-séma vagy hasonló, örökölt struktúra evolúciójánál**: az eredeti/alap definíciót ne
  módosítsd utólag – az új igényt a struktúra VÉGÉRE illeszd (pl. `ALTER TABLE`, ne a
  `CREATE TABLE` átírása), hogy a történet és a reprodukálhatóság megmaradjon.
- **Nyelvhasználat**: ha a fejlesztő magyarul ír, válaszolj magyarul – ne válts át angolra.

---

## Amit még tudnod kell a fejlesztőről

- A tervezés, magyarázat és hibakeresés chatben zajlik, a kódot te írod.
- Soha ne találgass. Ha valamit nem tudsz, mondd meg, és kérdezz vissza ahelyett, hogy
  kitalálnál egy megoldást.
- Kódpéldánál mindig add meg a pontos fájlelérési utat.
- Ha valamit a fejlesztőnek kell csinálnia, legyél konkrét: melyik fájl, hova kattintson,
  mit gépeljen be. A szakzsargon nem segít.
- Ha több megoldás létezik, röviden sorold fel a kompromisszumokat, mielőtt ajánlasz.
- Fontos, hogy mindig értse, mi készült el.
