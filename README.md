# Tippmix tipprendszer

Automatizált sportfogadási tipprendszer a magyar Tippmix Pro platformra.
A rendszer naponta kétszer saját statisztikai modellel értékeli a Tippmix Pro
kínálatában szereplő futball- és kosárlabda-eseményeket, és e-mailben küld
konkrét fogadási javaslatokat tétösszeggel együtt.

> **A rendszer nem azt csinálja, hogy megjósolja, ki nyer.** Azt csinálja, hogy
> minden eseményre kiszámolja a saját valószínűség-becslését, összeveti azzal,
> amit a Tippmix szorzója sugall, és csak ott javasol fogadást, ahol a kettő
> között elég nagy és megbízható az eltérés. Ha nincs ilyen, a levél üres.

**Jelenlegi állapot:** fejlesztői váz. A pipeline összeáll és végigfut, de a
2-10. lépés (modellek, döntési logika) még nincs implementálva. Nem termel
valódi javaslatot. Lásd [docs/PROGRESS.md](docs/PROGRESS.md).

---

## Indulás nulláról

### Előfeltételek

- **Python 3.12** — nem kell külön telepíteni, az `uv` letölti
- **[uv](https://docs.astral.sh/uv/)** — csomagkezelő
  (`winget install astral-sh.uv` vagy `pip install uv`)
- **Git**
- **Supabase projekt** — ingyenes tier elég

### 1. A függőségek telepítése

```powershell
uv sync --extra dev
```

Ez létrehozza a `.venv` könyvtárat, letölti a Python 3.12-t, ha nincs, és
telepít mindent a `uv.lock` alapján.

### 2. Titkok beállítása

```powershell
Copy-Item .env.example .env
```

Majd töltsd ki a `.env` fájlt. Hogy honnan szerzed be az egyes értékeket,
azt a [docs/SECRETS.md](docs/SECRETS.md) írja le lépésről lépésre.

**A `.env` soha nem kerül a repóba** — a `.gitignore` tiltja. A repó publikus.

### 3. Az adatbázis-séma létrehozása

A `db/migrations/001_init.sql` fájlt le kell futtatni a Supabase felületén.
Pontos lépések: [docs/SUPABASE_SETUP.md](docs/SUPABASE_SETUP.md).

### 4. Ellenőrzés

```powershell
uv run tippmix config-ellenorzes     # a YAML-ok érvényesek-e
uv run tippmix kapcsolat-teszt       # él-e a Supabase-kapcsolat, megvan-e a séma
uv run pytest                        # a teljes tesztkészlet
```

Ha mind a három rendben lefut, a környezet kész.

---

## Parancsok

| Parancs | Mit csinál |
| --- | --- |
| `uv run tippmix futtat --tipus delelott` | Délelőtti futás |
| `uv run tippmix futtat --tipus este` | Esti futás |
| `uv run tippmix futtat --szarazon --smoke` | Smoke-futás: nem küld e-mailt, nem ír DB-be |
| `uv run tippmix zaro-odds` | Záró szorzók begyűjtése a CLV-hez |
| `uv run tippmix kapcsolat-teszt` | Supabase-kapcsolat és séma ellenőrzése |
| `uv run tippmix config-ellenorzes` | A YAML-konfigurációk validálása |
| `uv run pytest` | Teljes tesztkészlet |
| `uv run pytest -m smoke` | Csak a smoke-tesztek |
| `uv run ruff check .` | Linter |
| `uv run ruff format .` | Formázás |

---

## Könyvtárszerkezet

```
config/
  settings.yaml          Minden küszöb, súly és limit. A kódban NINCS beégetett szám.
  ligak.yaml             Engedélyezett bajnokságok és piacok.

data/
  team_aliases.csv       Csapatnév-leképezés (VERZIÓZOTT — kézi munka eredménye)
  league_map.csv         Bajnokság-leképezés (VERZIÓZOTT)
  raw/                   Nyers Tippmix-válaszok (gitignore)
  manual/                Kézi tartalék CSV-k (gitignore)
  cache/                 Parquet-cache a backteszthez (gitignore)

db/migrations/
  001_init.sql           Az alapséma. KÉSŐBB NEM ÍRJUK ÁT — új migráció jön.

src/tippmix/
  kozos/                 Konfiguráció, titkok, naplózás, idő, típusok, hibák
  gyujtes/               1. lépés — Tippmix-scraper, történelmi adatok
  illesztes/             2. lépés — névillesztés
  jellemzok/             3. lépés — feature-építés jövőbe látás nélkül
  modellek/              4-6. lépés — Dixon-Coles, kosármodell, kalibráció, zsugorítás
  dontes/                7-8. lépés — vig-eltávolítás, él, döntési fa, hírvétó
  tetezes/               9-10. lépés — Kelly, kombináció
  kimenet/               11. lépés — levélformázás, e-mail
  adattar/               12. lépés — Supabase, naplózás, CLV
  backteszt/             Walk-forward backteszt-keretrendszer
  pipeline.py            A 12 lépés vezérlője
  cli.py                 Parancssori felület

.github/workflows/       GitHub Actions: délelőtti, esti, záró-odds, CI, keepalive
tests/                   pytest
docs/                    Dokumentáció — lásd alább
```

---

## Dokumentáció

| Fájl | Mit tartalmaz |
| --- | --- |
| [CLAUDE.md](CLAUDE.md) | **Minden új fejlesztői szál ezt olvassa el először.** |
| [docs/PROGRESS.md](docs/PROGRESS.md) | Időrendi napló: mi készült el, mi működik, mi a következő |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Minden technológiai és módszertani döntés, indoklással |
| [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md) | Amit nem tudunk, amit kalibrálni kell, ami elakadt |
| [docs/SECRETS.md](docs/SECRETS.md) | Melyik kulcs hova megy, honnan szerzed be |
| [docs/SUPABASE_SETUP.md](docs/SUPABASE_SETUP.md) | Az adatbázis beállítása lépésről lépésre |
| `docs/compass_artifact.md` | Kutatási jelentés: adatforrások, platform, infrastruktúra |
| `docs/Tippmix tipprendszer — döntési logika specifikáció.md` | **A normatív specifikáció.** Minden ebből vezetendő le. |

---

## A 12 lépés

| # | Lépés | Bemenet | Kimenet | Állapot |
| --- | --- | --- | --- | --- |
| 1 | Esemény-begyűjtés | tippmixpro.hu | nyers esemény- és szorzólista | váz |
| 2 | Névillesztés | nyers lista | statisztikai DB-hez kötött események | váz |
| 3 | Feature-építés | történelmi DB | meccsenkénti jellemzővektor | váz |
| 4 | Futballmodell | jellemzők | gólvárakozás, eredménymátrix | váz |
| 5 | Kosármodell | jellemzők | margó- és összpont-eloszlás | váz |
| 6 | Kalibráció, zsugorítás | nyers modell-valószínűség | végleges p_modell | **zsugorítás kész** |
| 7 | Vig-eltávolítás, él | Tippmix szorzó + p_modell | edge, EV | **kész** |
| 8 | Szűrők és vétók | jelöltek | túlélő tippek | váz |
| 9 | Tétezés | túlélő tippek | konkrét Ft-összegek | **kész** |
| 10 | Kombináció-építés | egyes tippek | 2-3 lábas szelvények | váz |
| 11 | Napi limitek, e-mail | minden javaslat | elküldött levél | **formázás kész** |
| 12 | Naplózás | minden javaslat | adatbázis-sor a CLV-hez | séma kész, író váz |

---

## Fontos tudnivalók

**A siker mércéje a CLV, nem a nyereség.** A nyereség rövid távon szinte
teljesen a szerencsén múlik. Ha 100 fogadáson átlagosan pozitív a CLV, a
rendszer tényleg előbb látja meg az információt, mint a piac. Ha negatív, a
nyerő hetek szerencsések voltak.

**A rendszer nem garantáltan nyereséges.** Egy 2023-24-es Premier League
backtesztben a tiszta Dixon-Coles modell −15,4% ROI-t hozott 249 fogadáson.
A nyereség — ha van — a kalibrációból, a piaci zsugorításból és a szigorú
szűrésből jön, nem a nyers modellből. Lehet, hogy a backteszt után az lesz a
becsületes válasz, hogy ez a rendszer nem termel élt.

**Biztonság.** A repó publikus. Titok soha nem kerülhet bele, még példaként
sem. A Supabase service role kulcs csak szerveroldalon és GitHub Secretsben
él. Részletek: [docs/SECRETS.md](docs/SECRETS.md).

---

## Licenc és felelősség

Magánprojekt, saját használatra. A szerencsejáték kockázattal jár; ez a
rendszer nem pénzügyi tanács, és nem garantál nyereséget.
