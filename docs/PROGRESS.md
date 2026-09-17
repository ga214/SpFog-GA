# Fejlesztési napló

Időrendi, naplószerű. Minden érdemi lépés után és minden munkamenet végén
bejegyzés: mit csináltunk, miért, mi működik, mi nem, mi a következő lépés.

**Legújabb bejegyzés felül.**

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
