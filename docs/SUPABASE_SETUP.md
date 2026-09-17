# Supabase beállítása

**Ezt a VS Code-on kívül kell elvégezned**, a Supabase webes felületén. A
lépések sorrendje számít.

Becsült idő: 5 perc.

---

## Amire szükséged lesz

- Egy meglévő Supabase-projekt (te mondtad, hogy már van)
- A [db/migrations/001_init.sql](../db/migrations/001_init.sql) fájl tartalma

---

## 1. lépés — A séma létrehozása

Ez hozza létre a hét táblát, az indexeket, a row level security-t és a három
nézetet.

1. Nyisd meg a [supabase.com](https://supabase.com) oldalt, jelentkezz be
2. Kattints a projektedre
3. A **bal oldali menüben** keresd meg az **SQL Editor** ikont
   (`>_` jel, kb. a menü közepén)
4. Kattints rá, majd a jobb felső sarokban: **+ New query**
5. **Nyisd meg a VS Code-ban** a `db/migrations/001_init.sql` fájlt
6. Jelöld ki a **teljes tartalmát** (Ctrl+A), másold ki (Ctrl+C)
7. Illeszd be a Supabase SQL-szerkesztőjének nagy szövegmezőjébe (Ctrl+V)
8. Kattints a jobb alsó sarokban a zöld **RUN** gombra
   (vagy Ctrl+Enter)

**Amit látnod kell:** alul megjelenik egy zöld sáv: `Success. No rows returned.`

Ez a helyes eredmény — a `CREATE TABLE` parancsok nem adnak vissza sorokat.

### Ha hibát kapsz

| Hibaüzenet | Mit jelent | Mit csinálj |
| --- | --- | --- |
| `relation "futasok" already exists` | már lefuttattad egyszer | Nincs teendő, a séma megvan. A script `if not exists`-t használ, így újrafuttatható. |
| `permission denied` | nem a projekt tulajdonosaként vagy belépve | Ellenőrizd, hogy a saját projektedben vagy-e |
| `syntax error at or near ...` | a másolás közben elveszett egy rész | Másold ki újra a TELJES fájlt |

---

## 2. lépés — Ellenőrzés a felületen

1. Bal oldali menü: **Table Editor** (táblázat ikon, feljebb)
2. A táblák listájában látnod kell mind a hetet:

   - `bankroll_naplo`
   - `futasok`
   - `ismeretlen_csapatok`
   - `kiesesek`
   - `kombinaciok`
   - `modell_illesztesek`
   - `tippek`

3. Mindegyik mellett egy **zöld pajzs ikon** kell legyen, ami azt jelenti:
   a row level security **be van kapcsolva**. Ha sárga figyelmeztetést látsz
   ("RLS disabled"), az baj — akkor az `alter table ... enable row level
   security` sorok nem futottak le.

> **Miért nincs egyetlen policy sem?** Szándékos. RLS bekapcsolva + nulla
> policy = az anon és authenticated kulccsal **semmi nem látható**. Csak a
> service role kulcs fér hozzá, amit kizárólag a pipeline használ. Ez a
> helyes alapállapot egy publikus repóhoz tartozó adatbázisnál.

---

## 3. lépés — A kulcsok kimásolása

Ehhez a [SECRETS.md](SECRETS.md) ad részletes útmutatót. Röviden:

1. Bal oldali menü alja: **Settings** (fogaskerék)
2. **Data API** → másold a **Project URL**-t → `.env` → `SUPABASE_URL=`
3. **API Keys** → a **`service_role`** sor → **Reveal** → másold →
   `.env` → `SUPABASE_SERVICE_ROLE_KEY=`

**Vigyázz:** az `anon` és a `service_role` kulcs egymás alatt van, és
hasonlóan néz ki. A pipeline-nak a **`service_role`** kell.

---

## 4. lépés — Ellenőrzés a VS Code-ból

Vissza a terminálba:

```powershell
uv run tippmix kapcsolat-teszt
```

**Amit látnod kell:**

```json
{
  "kapcsolat": "ok",
  "tablak": {
    "futasok": { "allapot": "ok", "sorok": 0 },
    "tippek": { "allapot": "ok", "sorok": 0 },
    ...
  },
  "hianyzo_tablak": [],
  "sema_kesz": true
}

A séma rendben van. Minden tábla elérhető.
```

Ha `sema_kesz: false`, a hiányzó táblák neve is ott lesz — akkor az 1. lépés
nem futott le teljesen.

---

## Későbbi séma-változások

**A `001_init.sql` fájlt soha nem írjuk át.** Ez szándékos szabály
(lásd [CLAUDE.md](../CLAUDE.md) 2. pont): az eredeti definíció a projekt
története, és a reprodukálhatóság múlik rajta.

Ha új mező vagy tábla kell:

1. Új fájl: `db/migrations/002_valami_leiro_nev.sql`
2. Benne `ALTER TABLE` (nem átírt `CREATE TABLE`)
3. Ugyanígy lefuttatod az SQL Editorban
4. A [docs/DECISIONS.md](DECISIONS.md) fájlba bejegyzés, hogy miért kellett

Amikor ilyen változás jön, **külön szólok**, hogy mit kell a Supabase
felületén lefuttatnod.

---

## Az ingyenes tier korlátai

| Korlát | Érték | Érint minket? |
| --- | --- | --- |
| Projektek száma | 2 | Nem |
| Tárhely | 500 MB | Nem — a napi napló pár száz sor |
| Inaktivitás miatti szüneteltetés | 7 nap | **Nem**, mert naponta 3× futunk |
| Egyidejű kapcsolatok | 60 | Nem |

> A kutatási jelentés a 7 napos szüneteltetés miatt a Supabase ellen érvelt.
> Napi kétszeri futásnál ez a korlát sosem áll be — minden futás
> aktivitásnak számít. Ha valaha hetekre leállítjuk a rendszert, a projekt
> szünetelhet; ilyenkor a Supabase felületén egy kattintással újraindítható,
> adatvesztés nélkül.
