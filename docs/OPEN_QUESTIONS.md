# Nyitott kérdések

Amit nem tudunk, amit kalibrálni kell, ami elakadt, ami ellentmondásos a
normatív dokumentumok között.

**Állapotjelölés:** `NYITOTT` · `FOLYAMATBAN` · `LEZÁRVA` (a lezárás
indoklásával és dátummal)

---

## A specifikáció által szándékosan nyitva hagyott paraméterek

Ezeket a specifikáció írója **szándékosan nem találta ki**, mert az kitalálás
lenne. Mind a backtesztből kell kijönnie.

### NY-01 — `w`, a piaci zsugorítás súlya · NYITOTT

**A legfontosabb egyetlen paraméter az egész rendszerben.**

- Jelenlegi érték: `0.35` (a `settings.yaml`-ban, **csak indulóérték**)
- Mit kell tenni: a validációs időszakon azt a `w`-t keresni, ami a legjobb
  **CLV**-t hozza (nem a legjobb P&L-t!)
- Hol: `modellek/kalibracio.py::optimalis_w()`
- Mikor: **Fázis 3**
- Megjegyzés: kezdetben inkább alacsonyabb (0,25–0,35), mert a modell fiatal
  és bizonytalan

### NY-02 — `ξ` (xi), a Dixon-Coles időbeli felejtés üteme · NYITOTT

- Jelenlegi érték: `0.0035` (kb. fél év alatt felezi a súlyt)
- **Ligánként külön** kell illeszteni
- Hol: `modellek/futball.py::illeszt()`
- Mikor: Fázis 2

### NY-03 — `ρ` (rho), az alacsony eredmények korrekciója · NYITOTT

- Az eredeti Dixon-Coles tanulmányban ≈ −0,13 angol adatokra
- **Ligánként újra kell illeszteni** — nem feltételezünk semmit
- Hol: `modellek/futball.py::illeszt()`
- Mikor: Fázis 2

### NY-04 — `σ_margó` és `σ_össz` a kosármodellhez · NYITOTT — BLOKKOLÓ

**Ez blokkolja a teljes kosármodellt.** A specifikáció kimondja: "amíg ez
nincs meg, a kosármodell nem ad javaslatot."

- A backteszt tényleges hibáinak szórásából kell becsülni
- **Ligánként külön** (az NBA és az EuroLeague nem ugyanaz)
- Hol: `modellek/kosar.py::sigma_becsles()`; a `kosar_aktiv()` addig `False`
- Mikor: Fázis 7

### NY-05 — A valódi `min_edge` küszöb · NYITOTT

- Jelenlegi: 5 pp délelőtt / 3,5 pp este
- A backteszt mondja meg, mi az a küszöb, ami után a fogadás ténylegesen megéri
- Mikor: Fázis 3

### NY-06 — A `min_odds: 1.30` / `max_odds: 6.00` sáv · NYITOTT

- Jó-e ez a sáv, vagy szűkíteni kell?
- Mikor: Fázis 3

---

## Ellentmondások a normatív dokumentumok között

### NY-07 — A Kelly-példatáblázat felfelé kerekít · LEZÁRVA (2026-09-17)

**A kérdés:** a specifikáció 9. lépésének példatáblázata két helyen eltér a
saját 7. szabályától.

| Eset | A spec példája | A spec 7. szabálya szerint | Eltérés |
| --- | --- | --- | --- |
| odds 3,50, p 0,331 | "800 Ft" | 700 Ft | a spec a kerekített f*=0,064-gyel számolt (a pontos 0,06357) |
| odds 6,00, p 0,197 | "455 → **500 Ft**" | 400 Ft | a spec **felfelé** kerekített |

**A spec 7. pontja szó szerint:** "Kerekítés 100 Ft-ra lefelé."
**A 6. pont indoklása:** "Nem kerekítünk fel, mert az felültetéléshez vezet."

**Döntés:** a **normatív szabály nyer** a példatáblázattal szemben. A kód
mindig lefelé kerekít. A példatáblázat illusztráció, kerekített
köztes értékekkel.

**Rögzítve:** `tests/test_kelly.py::test_spec_pelda_kozepes_szorzo` és
`::test_spec_pelda_magas_szorzo`, docstringben az indoklással.

---

### NY-08 — A gyanús piacok kiszűrése a döntési fából · NYITOTT

**A kérdés:** a `vig.py` most már jelzi, ha egy piac overroundja negatív vagy
szokatlanul magas (lásd [DECISIONS.md](DECISIONS.md) D-008). A **döntési fa
még nem használja fel** ezt a jelzést.

**Amit el kell dönteni:**

1. Új kiesési ok kell-e (`GYANUS_PIAC`), vagy a meglévő `NINCS_ODDS` alá
   tartozzon?
2. Hol legyen a fában? Logikailag az 1. pont (érvényes szorzó) után, a 2. pont
   (odds-tartomány) előtt.
3. A "szokatlanul magas overround" (>25%) is kiesést okozzon, vagy csak
   figyelmeztetést?

**Mikor:** Fázis 4, a döntési fa implementálásakor.

---

### NY-09 — E-mail időzítés: fix 18:00 vs. kezdés előtt 60-90 perc · NYITOTT

**Az ellentmondás:**

- A **kutatási jelentés** (Fázis 2 ajánlás): "kezdés előtt ~60–90 perccel a
  végleges, felállás-megerősített tippek (a felállások ~1 órával kezdés előtt
  jönnek)"
- A **specifikáció** (Áttekintés): fix 09:00 és 18:00 CET futás, és az esti
  futás "már megerősített felállásokkal" dolgozik

**A probléma:** egy 21:00-kor kezdődő meccs felállása kb. 20:00-kor jelenik
meg. A 18:00-s futás ezt **nem látja**. Így az esti futás a késői meccseknél
ugyanúgy a "nincs felállás" ágra fut, mint a délelőtti — de az alacsonyabb
(3,5 pp) küszöbbel, ami pont fordítva van, mint ahogy a spec indokolja.

**Lehetséges megoldások:**

| Opció | Előny | Hátrány |
| --- | --- | --- |
| Marad a fix 18:00 (spec) | egyszerű, kiszámítható | a késői meccseknél nincs felállás, de alacsony küszöb van |
| Az esti futás küszöbe meccsenként változik aszerint, hogy van-e felállás | pontos | bonyolultabb; a hírvétó `nincs_ellenorzes` ága már most emeli a küszöböt 1,5× |
| Harmadik futás 20:00-kor | követi a kutatást | több Actions-futás, több levél |

**Megjegyzés:** a spec hírvétó-szabálya (`hianyzo_forras_kuszob_szorzo: 1.5`)
részben már kezeli ezt — ha nincs felállás-adat, a küszöb 1,5×-ére nő. A
3,5 pp × 1,5 = 5,25 pp, ami magasabb, mint a délelőtti 5 pp. Tehát a
rendszer **már most helyesen viselkedik**, csak nem nyilvánvaló módon.

**Állapot:** valószínűleg nincs teendő, de a Fázis 5-ben (hírvétó
implementálása) ellenőrizni kell, hogy a küszöbemelés tényleg érvényesül-e.

---

### NY-10 — A kosármodell `liga_átlag` definíciója · NYITOTT

**A kérdés:** a specifikáció 5. lépésének képlete:

```
pont_hazai = (ORtg_hazai + DRtg_vendég - liga_átlag) / 100 × pace + hazai_előny/2
```

A `liga_átlag` pontos definíciója nincs megadva. Lehet:

- a liga átlagos ORtg-je (valószínű, mert az ORtg és DRtg ugyanabban a
  mértékegységben van)
- a liga átlagos ORtg + DRtg összege
- valami más normalizálás

A képlet csak akkor ad értelmes pontszámot, ha a `liga_átlag` az átlagos ORtg
(ami definíció szerint egyenlő az átlagos DRtg-vel). Akkor
`ORtg_hazai + DRtg_vendég - liga_átlag` egy korrigált támadóerő 100
birtoklásra, amit a pace-szel szorozva pontszámot kapunk.

**Mikor:** Fázis 7 elején tisztázni, mielőtt a kosármodell kódja íródik.

---

## Infrastrukturális bizonytalanságok

### NY-11 — A Tippmix odds-végpont pontos útvonala · NYITOTT — BLOKKOLÓ

**Ez blokkolja az 1. lépést, tehát az egész rendszert.**

- A kutatás szerint `sports2.tippmixpro.hu`, JSON-nal, numerikus eventId
  szerint, `markets[]` → `outcomes[]` → `{name, side, odds}` szerkezettel
- **A pontos nyers végpontok nem publikusak**
- Mit kell tenni: böngésző hálózati fülén kideríteni
- Mikor: **Fázis 0, az első feladat**

### NY-12 — Blokkolja-e a Tippmix a GitHub Actions IP-ket? · NYITOTT

- A nyilvános odds-oldalak külföldről is láthatók (a kutatás szerint)
- De a testvéroldal `tippmix.hu` **aktívan blokkol IP alapján**
- **Nem verifikálható publikusan** — empirikusan tesztelni kell
- Ha blokkolt: a scraping a felhasználó windowsos gépére kerül (önhosztolt
  runner vagy Task Scheduler)
- Mikor: Fázis 0

### NY-13 — A `stats.nba.com` adatközponti IP-blokkja · NYITOTT

- A kutatás szerint **igazoltan blokkolja** az AWS/GCP/Azure IP-ket, tehát
  valószínűleg a GitHub Actions runnereket is
- A `cdn.nba.com` live végpontok viszont bárhonnan működnek
- Tartalék: Basketball-Reference
- Mikor: Fázis 0 (teszt), Fázis 7 (megoldás)

### NY-14 — A robots.txt tényleges tartalma · NYITOTT

- A kutatás **nem tudta verifikálni** a `tippmixpro.hu/robots.txt`-t
- A Részvételi Szabályzat nem tilt kifejezetten scrapelést, de van általános
  "nem rendeltetésszerű használat" klauzula
- Mit kell tenni: letölteni és **ténylegesen elolvasni** mindkét hoston,
  majd tartani magunkat hozzá
- Mikor: **Fázis 0, a végpont-felderítéssel együtt**

### NY-15 — EuroLeague történelmi záró odds · NYITOTT

- Ingyenesen **gyakorlatilag nem elérhető**
- Ez valós korlát: EuroLeague-re nem tudunk becsületes backtesztet csinálni
- Ezért a `config/ligak.yaml`-ban az EuroLeague `aktiv: false`
- Lehetséges megoldás: OddsPortal-scrapelés (OddsHarvester), ToS-kockázattal
- Mikor: Fázis 7, ha egyáltalán

---

## Módszertani kérdések, amikre később kell válasz

### NY-16 — A backteszt újrafittelési gyakorisága · NYITOTT

A specifikáció azt írja: a modellparamétereket "**minden fordulóra** újra kell
illeszteni". Ez a becsületes módszer, de lassú.

**A kérdés:** mennyit veszítünk, ha 7 naponta illesztünk újra? Ezt mérni kell,
nem feltételezni. A `backteszt/keret.py::walk_forward()` `ujrafittelés_naponta`
paramétere ezt paraméterezhetővé teszi.

**Mikor:** Fázis 2

### NY-17 — Bankroll-frissítés automatizálása · NYITOTT

Jelenleg a `bankroll.aktuális_ft` kézi érték a `settings.yaml`-ban. A
specifikáció megengedi, hogy a napló számolja.

**A kérdés:** mikor kapcsoljuk be az automatikus számolást? A spec figyelmeztet:
"amíg kézi, ne frissítsd naponta — heti egyszer elég, különben a tét ugrál."

Ha automatikus lesz, ugyanez a probléma jelentkezik, csak nagyobb
gyakorisággal. Valószínűleg heti átlagolás kell.

**Mikor:** Fázis 5-6

### NY-18 — Kezdeti `kelly_hányad`: 0,25 vagy 0,15? · NYITOTT

A specifikáció 9. lépése: "Kezdetben ez is lehet túl sok; a `kelly_hányad`
0,15-re csökkentése védekezőbb indulás."

A `settings.yaml`-ban jelenleg **0,25** van (a spec konfigurációs szakasza
szerint). Élesítés előtt el kell dönteni, hogy 0,15-tel induljunk-e.

**Mikor:** Fázis 6 (élesítés) előtt
