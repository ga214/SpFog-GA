# Titokkezelés

**Ez a projekt PUBLIKUS GitHub-repóban él.** Egy véletlenül commitolt kulcs
azonnal kompromittált, és nem elég kitörölni — **cserélni kell**, mert a git
history-ban megmarad, és a publikus repókat automata botok másodpercek alatt
átvizsgálják.

---

## Az alapszabályok

1. **Titok soha nem kerül a repóba** — sem kódba, sem YAML-be, sem commit
   üzenetbe, sem példaként.
2. **Lokálisan** a `.env` fájlban él, ami a `.gitignore`-ban van.
3. **GitHub Actionsben** a GitHub Secretsből jön, környezeti változóként.
4. A `.env.example` **csak a neveket** tartalmazza, értéket soha.
5. A kód a titkokat kizárólag a
   [src/tippmix/kozos/titkok.py](../src/tippmix/kozos/titkok.py) modulon
   keresztül olvassa, és soha nem naplózza őket (a `maszkol()` függvény való
   naplózáshoz).
6. A CI-ben `gitleaks` fut minden commiton — ez az utolsó védvonal, nem az
   első.

---

## A négy titok, és honnan szerzed be

### 1. `SUPABASE_URL`

A Supabase projekted API-végpontja. Nem érzékeny önmagában, de együtt jár a
kulccsal.

**Hol találod:**

1. Menj a [supabase.com](https://supabase.com) oldalra, jelentkezz be
2. Kattints a projektedre
3. Bal oldali menü alján: **Settings** (fogaskerék)
4. **Data API** menüpont
5. A **Project URL** mező — ilyesmi: `https://abcdefghijkl.supabase.co`
6. Másold ki, és illeszd be a `.env` fájl `SUPABASE_URL=` sora után

### 2. `SUPABASE_SERVICE_ROLE_KEY`

**A legérzékenyebb titok a projektben.**

Ez a kulcs **megkerüli a row level security-t** — aki megszerzi, a teljes
adatbázisodhoz hozzáfér, olvasni és írni is. Ezért:

- csak szerveroldalon (ebben a pipeline-ban) és GitHub Secretsben élhet
- **frontendbe soha nem kerülhet** — ha valaha weboldalt csinálunk a
  projekthez, oda kizárólag az **anon** kulcs mehet, RLS-policy-kkal
- ha valaha kiszivárog, azonnal cseréld (Supabase → Settings → API keys →
  a kulcs melletti menü → Rotate)

**Hol találod:**

1. Supabase Dashboard → a projekted
2. **Settings** → **API Keys**
3. Keresd a **`service_role`** feliratú sort (NEM az `anon`-t!)
4. Kattints a **Reveal** gombra
5. Másold ki — hosszú, `eyJ...`-vel kezdődő szöveg
6. `.env` → `SUPABASE_SERVICE_ROLE_KEY=`

### 3. `EMAIL_FELHASZNALO`

A Gmail-címed, amiről a levelek mennek. Pl. `valaki@gmail.com`.

### 4. `EMAIL_APP_JELSZO`

**Ez NEM a Google-fiókod jelszava.** A Google 2022 óta nem engedi, hogy
programok a rendes jelszóval lépjenek be. Helyette külön "app-jelszót" kell
generálni.

**Előfeltétel:** a Google-fiókodon **be kell kapcsolni a kétlépcsős
azonosítást** (2FA), különben az app-jelszó menüpont meg sem jelenik.

**Lépésről lépésre:**

1. Ha még nincs 2FA:
   - [myaccount.google.com/security](https://myaccount.google.com/security)
   - **Kétlépcsős azonosítás** → **Bekapcsolás**
   - Kövesd a lépéseket (telefonszám vagy authenticator app)

2. App-jelszó generálása:
   - Menj a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
     oldalra
   - Az **Alkalmazás neve** mezőbe írd be: `Tippmix tipprendszer`
   - Kattints a **Létrehozás** gombra
   - Megjelenik egy **16 karakteres** jelszó, négyes csoportokban
     (pl. `abcd efgh ijkl mnop`)

3. **Szóközök nélkül** másold be a `.env` fájlba:
   ```
   EMAIL_APP_JELSZO=abcdefghijklmnop
   ```

4. A Google nem mutatja meg újra — ha elveszted, generálj újat.

### 5. `EMAIL_CIMZETT`

Ide megy a javaslatokat tartalmazó levél. Lehet ugyanaz, mint a feladó.

---

## GitHub Secrets — mit kell felvenni

A GitHub Actions workflow-k ezeket a titkokat várják. **Mind a négy
kötelező**, különben a futás elhasal.

### Hova kell beírni

1. Menj a GitHub-repód oldalára
2. Felül: **Settings** fül (a repó Settingse, nem a fiókodé!)
3. Bal oldali menü: **Secrets and variables** → **Actions**
4. Zöld gomb: **New repository secret**
5. Minden titokhoz egyszer:
   - **Name**: pontosan az alábbi táblázat szerinti név (nagybetűs, alávonás)
   - **Secret**: az érték, ugyanaz, ami a `.env`-ben van
   - **Add secret**

### A felveendő secretek

| Név | Érték | Honnan |
| --- | --- | --- |
| `SUPABASE_URL` | `https://xxxxx.supabase.co` | Supabase → Settings → Data API |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJ...` (hosszú) | Supabase → Settings → API Keys → service_role → Reveal |
| `EMAIL_FELHASZNALO` | `valaki@gmail.com` | a saját Gmail-címed |
| `EMAIL_APP_JELSZO` | 16 karakter, szóköz nélkül | myaccount.google.com/apppasswords |
| `EMAIL_CIMZETT` | `valaki@gmail.com` | ahova a levél megy |

> **Megjegyzés:** a `GITHUB_TOKEN` secretet **nem** kell felvenned — azt a
> GitHub automatikusan biztosítja minden workflow-futáshoz.

### Ellenőrzés

Miután felvetted mind az ötöt, indíts egy próbafutást:

1. A repóban: **Actions** fül
2. Bal oldalt: **Esti futás**
3. Jobb oldalt: **Run workflow** gomb
4. A **Szárazon futtatás** kapcsolót állítsd **true**-ra (így nem küld
   e-mailt és nem ír adatbázisba)
5. **Run workflow**

Ha zöld pipát kapsz, a titkok a helyükön vannak.

---

## Mi történik, ha mégis kikerül egy kulcs

**Ne próbáld meg a git history-ból kitörölni és elfelejteni.** A publikus
repókat botok figyelik; egy service role kulcs perceken belül kihasználható.

1. **Azonnal cseréld a kulcsot:**
   - Supabase: Settings → API Keys → a kulcs melletti `...` → **Rotate**
   - Gmail app-jelszó: myaccount.google.com/apppasswords → a régi
     **törlése**, majd új generálása
2. Frissítsd a `.env`-et és a GitHub Secretset az új értékkel
3. Csak ezután foglalkozz a history tisztításával (ha egyáltalán érdemes)

---

## Ami NEM titok

Ezek nyugodtan a repóban lehetnek:

- a `config/settings.yaml` összes küszöbe, súlya, limitje
- a `config/ligak.yaml` teljes tartalma
- a `data/team_aliases.csv` és `data/league_map.csv`
- a `db/migrations/*.sql` séma
- a bankroll összege (nem érzékeny, és a modell működéséhez tartozik)

Ami **nem** kerülhet be, még akkor sem, ha nem "kulcs":

- a `data/raw/` nyers Tippmix-válaszai (méret + ToS-kockázat)
- a `data/manual/` kézi fájljai (személyes fogadási adat lehet benne)
- bármilyen naplófájl (`logs/`), mert tartalmazhat részleteket
