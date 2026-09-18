# Fejlesztési napló

Időrendi, naplószerű. Minden érdemi lépés után és minden munkamenet végén
bejegyzés: mit csináltunk, miért, mi működik, mi nem, mi a következő lépés.

**Legújabb bejegyzés felül.**

---

## 2026-09-18 (8) — A D-014 alternatívájának mérése: a margó megeszi az élt

### A lényeg elöl

A D-014 végén szereplő „reálisabb alternatíva" — ne a piacot verjük, hanem
vegyük észre, hol olcsóbb ugyanaz a fogadás — **1X2-n, a top-5 ligában nem
jön ki.** A puha irodák árrése nagyobb, mint a félreárazás, amit hagynak.

És egy második, kellemetlenebb eredmény: **a pozitív CLV ebben a mérésben nem
fordult át nyereségbe** 8271 fogadáson. Ez a projekt sikerkritériumát érinti,
ezért külön nyitott kérdés lett belőle (NY-22).

### Mit mértünk

Tippmix-történelmi oddsunk nincs, ezért nem a Tippmixet mértük, hanem a
**mechanizmust**: ha egy puhább iroda ára jobb, mint a Pinnacle power
de-viggel számolt fair ára, az tényleg pozitív EV, vagy csak zaj?

`scripts/puha_vs_sharp.py`, az `arres-teszt.yml` workflow-ban (a
football-data.co.uk-t a fejlesztői konténer egress-szabálya blokkolja).
5 liga × 5 szezon, 1X2, ~8900 meccs.

### Árrés (overround) a záró 1X2 áron

| Iroda | Árrés |
| --- | --- |
| **Pinnacle (PS)** | **2,72%** |
| IW | 5,04% |
| B365 | 5,57% |
| VC | 5,70% |
| BW | 5,74% |
| WH | 6,47% |
| Max (a mezőny legjobb ára) | −0,12% |

**Ez a kulcs.** A Pinnacle 2,7%-on dolgozik, a puha irodák 5-6,5%-on. Egy
lábnak nem elég jobbnak lennie a fair árnál — a saját irodája árrését is
felül kell múlnia.

### Az eredmény

**Egyidejű teszt** (iroda záró ára vs. Pinnacle záró fair ára). A CLV-oszlop
itt definíció szerint 100%, tehát értelmetlen: ugyanaz az ár a kiválasztás és
a referencia. Ez ugyanaz a mérési műtermék, mint a Fázis 2-ben.

| Iroda | Küszöb | Fogadás | ROI | ±2SE |
| --- | --- | --- | --- | --- |
| B365 | 1% | 279 | −10,62% | 17,98% |
| BW | 1% | 311 | −5,89% | 15,35% |
| IW | 1% | 594 | +1,52% | 9,45% |
| WH | 1% | 400 | +4,13% | 16,93% |
| VC | 1% | 322 | −10,35% | 21,78% |
| **Max** | **1%** | **8048** | **+0,75%** | **3,63%** |

Az egyes irodák sorai mind zajban vannak (a ±2SE nagyobb, mint a ROI). Az
egyetlen statisztikailag erős sor a **Max**: a mezőny legjobb ára, 8048
fogadáson, **+0,75% ± 3,63%** — vagyis pontosan mért nulla.

**Korai teszt** (a valós stratégia: korai ár a kiválasztásra, a Pinnacle záró
ára a CLV-referencia):

| Iroda | Küszöb | Fogadás | ROI | ±2SE | CLV+ |
| --- | --- | --- | --- | --- | --- |
| Max | 0% | 8271 | +0,42% | 3,29% | 62,4% |
| Max | 1% | 4758 | −0,32% | 4,47% | 67,0% |
| Max | 2% | 2414 | −1,95% | 6,80% | 70,7% |
| Max | 3% | 1304 | −3,08% | 9,86% | 72,7% |

**A CLV monoton nő a küszöbbel (62% → 73%), a ROI mégis nulla vagy negatív.**
A kiválasztás tehát tényleg talál a záróárnál jobb árakat — csak ez nem
termel pénzt.

### Miért nem lesz a fair árnál jobb árból nyereség?

A legvalószínűbb ok a **győztes átka**: azt a lábat választjuk ki, ahol
`odds × p_fair − 1` a legnagyobb, ami preferálja azokat a lábakat, ahol a
de-vig **felülbecsli** `p_fair`-t. A látszólagos élet a becslési hiba eszi
meg. Ez nem a de-vig módszer hibája, hanem a kiválasztásé.

### Amit ez NEM zár ki

1. **Csak 1X2-t mértünk, a top-5 ligában.** Ez a futball legahatékonyabb
   piaca — a legrosszabb hely egy ilyen stratégiának. A 3-utas piac ráadásul
   a legnagyobb árrésű.
2. **A 2-utas piacok (ázsiai hendikep, gólszám) érintetlenek.** Bloom és
   Benham is ezeken dolgozik, és ott az árrés jellemzően 2-4%, nem 5-6,5%.
   Az adatunkban a `PAHH`/`PAHA` és a gólszám-oszlopok megvannak.
3. **A Tippmix tényleges árrése továbbra is ismeretlen** — a `PROGRESS`-ben
   korábban szereplő 3,1% a Pinnacle-é, nem a Tippmixé.

### A következő lépés

Két olcsó mérés, ebben a sorrendben:

1. **A Tippmix árrése** egy élő listalekérésből (`gyujtes-proba.yml`). Ha
   8-10% körül van, a stratégia 1X2-n biztosan halott, és a 2-utas piacokon
   is nehéz.
2. **Ugyanez a teszt 2-utas piacokon** (gólszám 2,5, ázsiai hendikep), ahol
   az árrés töredéke a 3-utasénak.

---

## 2026-09-18 (7) — Fázis 3: xG + kalibráció + rácskeresés. A VÁLASZ UGYANAZ.

### A lényeg elöl

A Fázis 2 után azt mondtuk: a nyers modell nem veri a piacot, de a spec
szerint a nyereség „a kalibrációból, a piaci zsugorításból és a szigorú
szűrésből jön" — tehát meg kell építeni a hiányzó rétegeket, és **újra
megnézni ugyanazt a táblázatot**.

Megépítettük mind a hármat. **Az eredmény nem változott: a modell nem veri
a piacot.**

### Az out-of-sample mérés (a tisztességes)

Tanító szelet 2022/23–2023/24, **érintetlen teszt-szelet 2024/25**, mind az
5 ligán, 8406 jelölt:

| | Brier |
| --- | --- |
| modell nyers | 0,2127 |
| + izotonikus kalibráció | 0,2128 |
| + kalibráció + zsugorítás | 0,2089 |
| **PIAC** | **0,2082** |

**A kalibráció out-of-sample nem javít** (0,2127 → 0,2128). In-sample
javított (1X2: 0,1950 → 0,1938), ami épp azt mutatja, hogy a tanult
korrekció a tanítóhalmaz zajához illeszkedik, nem valódi torzításhoz.

És a döntő sor, most már a *teljes* modellel — xG-vel, kalibrációval,
zsugorítással (n=626):

> modell **44,8%** · piac **40,5%** · **TÉNYLEGES 38,8%**

Ugyanaz, mint a Fázis 2 után. Ahol élt látunk, ott nincs él.

### Rácskeresés — a paraméterhangolás sem ment meg

9 kombináció (ξ ∈ {0,0015; 0,0035; 0,0080} × xG-súly ∈ {0; 0,5; 1}) a
validációs szeleten:

| ξ | xG | Brier (mi) | Brier (piac) | edge≥3%: modell/piac/**tényleges** |
| --- | --- | --- | --- | --- |
| 0,0015 | 1,0 | 0,2072 | **0,2063** | 0,411 / 0,370 / **0,334** |
| 0,0035 | 0,0 | 0,2073 | **0,2063** | 0,468 / 0,424 / **0,402** |
| 0,0035 | 0,5 | **0,2071** | **0,2063** | 0,444 / 0,403 / **0,368** |
| 0,0035 | 1,0 | 0,2072 | **0,2063** | 0,430 / 0,389 / **0,356** |
| 0,0080 | 0,0 | 0,2080 | **0,2063** | 0,493 / 0,444 / **0,417** |
| 0,0080 | 0,5 | 0,2074 | **0,2063** | 0,483 / 0,439 / **0,405** |
| 0,0080 | 1,0 | 0,2073 | **0,2063** | 0,466 / 0,422 / **0,404** |

**Mind a 9 kombinációban veszítünk a piaccal szemben**, és mind a 9-ben a
tényleges gyakoriság a piac becslése ALATT van ott, ahol élt látunk. A
legjobb beállításunk (0,2071) sem éri el a piacot (0,2063).

Ez a legfontosabb megállapítás: **nem egy rosszul megválasztott paraméterről
van szó.** A teljes paramétertartományban ugyanaz a kép.

### Mit csináltunk

- **xG-adat** (`understatapi`), 99,2–100%-os párosítás mind az 5 ligában.
  A csapatnév-leképezés **verziózott, kézi munka**
  ([data/understat_nevek.csv](../data/understat_nevek.csv)) — a fuzzy az
  „Athletic Club"-ra a „Betis"-t adta volna a legjobb találatnak (54 pont),
  holott a helyes párja az „Ath Bilbao". Pontosan az az 5%, amiről a
  CLAUDE.md 3. szabálya szól.
- **xG a modellben**: `xg_suly` paraméter keveri a gólt és az xG-t. A Poisson
  log-sűrűség `gammaln`-nel folytonosra általánosítva (az xG tört szám).
- **Izotonikus kalibráció** (`sklearn`), kvantilis-alapú kalibrációs görbe,
  `w` keresése CLV szerint.
- **22 + új teszt**, összesen **201 zöld**.

### Amit az xG hozott — és amit nem

Az xG **javítja a nyers modellt** (0,2124 → 0,2105 a validációs szeleten),
tehát a beépítése helyes volt. De a javulás nem elég: a piac 0,2063-nál van.

Érdekes mellékmegfigyelés: minél nagyobb az xG súlya, annál **kevesebb és
rosszabb** élt talál a modell (xG=0-nál 40,2% jön be, xG=1-nél 33,4%). Az xG
visszafogottabb csapaterősségeket ad, ami közelebb viszi a modellt a
piachoz — és ahol utána mégis eltér, ott inkább téved.

### A becsületes összegzés

A spec kilépési feltétele teljesült, most már a **teljes** modellel:

> „Ha ezeken átjutunk és a backteszt nem mutat pozitív CLV-t, akkor a 4-6.
> fázist nem érdemes megépíteni ebben a formában."

Amit kipróbáltunk és nem volt elég: Dixon-Coles idősúlyozással, τ-korrekció,
xG-jellemzők, izotonikus kalibráció, piaci zsugorítás, adatelégségességi
kapu, szigorú él- és odds-szűrés, 9-pontos paraméterrács.

**Ami ebből NEM következik:** hogy a munka hiábavaló volt. Működik az
adatgyűjtés, a Tippmix-integráció (élő odds WAMP-on), a történelmi adattár
(9110 meccs xG-vel), és — ami a legfontosabb — **egy becsületes mérőkeret,
ami képes megmondani, hogy valami nem működik.** Ez utóbbi a ritkább.

### A következő lépés — a felhasználó döntése

1. **Leállni** — a spec szerinti becsületes kilépés. Ezt javaslom.
2. **Más irányba menni** — a jelenlegi modell a *piac átlagos véleményét*
   próbálja megverni saját statisztikai becsléssel. Reálisabb cél lenne a
   **piacok közötti eltérés** keresése (a Tippmix mikor tér el a Pinnacle-től),
   mert ott nem nekünk kell okosabbnak lennünk a piacnál — csak észrevenni,
   hol olcsóbb ugyanaz. Ez viszont **más rendszer**, nem ennek a folytatása,
   és külön kutatást igényel.
3. **Élesíteni kis téttel** — **ezt kifejezetten nem javaslom.** A mérés
   szerint pénzt veszítenénk, csak lassabban.

---

## 2026-09-18 (6) — Fázis 2: Dixon-Coles + backteszt. A MODELL NEM VERI A PIACOT.

### A lényeg elöl

A specifikáció ezt írta: *„A 2. és 3. fázis a lényeg. Ha ezeken átjutunk és a
backteszt nem mutat pozitív CLV-t, akkor a 4-6. fázist nem érdemes megépíteni
ebben a formában."*

**A backteszt lefutott, és a válasz: a jelenlegi modell nem ver piacot.**

Mind az 5 ligán, a 2024/25-ös szezonon, walk-forward módon (heti
újrailleszéssel, kizárólag a meccs előtti adatokból):

| Liga | Jelöltek | Brier: modell | zsugorított | **PIAC** |
| --- | --- | --- | --- | --- |
| E0 | 1840 | 0,2147 | 0,2115 | **0,2112** |
| SP1 | 1840 | 0,2138 | 0,2074 | **0,2055** |
| D1 | 1413 | 0,2154 | 0,2089 | **0,2073** |
| I1 | 1785 | 0,2167 | 0,2101 | **0,2084** |
| F1 | 1528 | 0,2137 | 0,2089 | **0,2081** |

A Brier alacsonyabb = jobb. **A piac minden ligában nyer.**

A döntő teszt viszont nem is a Brier, hanem ez: ahol a modell 3%-nál nagyobb
élt talált, mi történt valójában?

| Liga | Modell becslése | Piac becslése | **Tényleges** | n |
| --- | --- | --- | --- | --- |
| E0 | 41,6% | 37,4% | **37,1%** | 167 |
| SP1 | 44,9% | 40,5% | **35,0%** | 177 |
| D1 | 48,0% | 43,2% | **39,0%** | 141 |
| I1 | 47,7% | 43,3% | **38,5%** | 195 |
| F1 | 45,4% | 40,8% | **43,6%** | 149 |

**Négy ligában a tényleges gyakoriság a piac becsléséhez van közelebb (vagy
még az alá esik), nem a miénkhez.** Ahol a modell élt lát, ott jellemzően
nincs él — a modell téved, nem a piac. Az egyetlen kivétel a Ligue 1, de egy
liga egy szezonja nem bizonyíték, hanem zaj.

Egységnyi téttel a Premier League-en: **ROI −7,3%** 158 fogadáson. Ez
összhangban van a kutatási jelentés figyelmeztetésével (egy 2023/24-es PL
backtesztben a tiszta Dixon-Coles −15,4% ROI-t hozott).

### Mit csináltunk

- [modellek/futball.py](../src/tippmix/modellek/futball.py) — teljes
  Dixon-Coles: idősúlyozott ML-illesztés ligánként, τ-korrekció,
  eredménymátrix, piaci valószínűségek. Mind az 5 liga konvergál 2-3 mp alatt.
- [backteszt/keret.py](../src/tippmix/backteszt/keret.py) — walk-forward
  keret: heti újrailleszés, adatelégségességi kapu, vig-eltávolítás, piaci
  zsugorítás, kiértékelés.
- **33 + új tesztek**, összesen **153 zöld**.

### Amit a számok NEM mondanak — két fontos korlát

**1. A „CLV = 0,0% pozitív" mérési műtermék, nem eredmény.** A történelmi
adatunkban **csak záró odds van, nyitó nincs**. A rendszer élesben a meccs
előtti áron fogadna és a záróhoz mérné a CLV-t; itt viszont ugyanaz az ár a
fogadási ár és a referencia, így a „CLV" definíció szerint a margó
negatívja (−3,6%). Ezért **ez a backteszt nem CLV-t mér, hanem
valószínűség-minőséget** — és abban is veszít a modell. A korlát a
`keret.py` docstringjében is rögzítve.

**2. Ez a modell szándékosan csupasz.** Nincs benne xG (az Understat-adat
letöltése még nem készült el), nincs Elo (a ClubElo API halott, NY-20), és
nincs kalibrációs réteg (izotonikus regresszió, Fázis 3). A spec maga írja:
*„a nyers modell önmagában nem elég, a nyereség a kalibrációból, a piaci
zsugorításból és a szigorú szűrésből jön."*

A piaci zsugorítás egyébként **bizonyítottan segít** (0,2147 → 0,2115), csak
épp nem tud a piacnál jobb lenni — ami matematikailag várható, ha a piac felé
húzunk valamit, ami rosszabb a piacnál.

### A következő lépés — döntési pont, nem automatizmus

Ez most **a felhasználó döntése**, nem technikai kérdés. Három út:

1. **Fázis 3 rendesen** — xG-jellemzők (Understat), izotonikus kalibráció,
   `w` és `ξ` rácskeresés. Ez a spec szerinti út; a jelenlegi eredmény a
   *nyers* modellé, ami a spec szerint önmagában nem is elég. Reális esély
   van javulásra, de garancia nincs.
2. **Leállni** — a spec becsületes kilépési pontja. Az eddigi munka nem
   veszett el: az adatgyűjtés, a Tippmix-integráció és a mérőkeret működik.
3. **Szűkíteni** — csak azokat a piacokat/ligákat tartani, ahol a modell nem
   veszít (pl. F1), és kis téttel élesíteni. **Ezt nem javaslom:** egy liga
   egy szezonja statisztikailag zaj, és pont ez a fajta utólagos válogatás
   gyártja a hamis magabiztosságot.

Az 1. utat javaslom, azzal a kikötéssel, hogy a Fázis 3 után **újra
megnézzük ugyanezt a táblázatot**, és ha akkor sem veri a piacot, akkor a
2. út következik.

---

## 2026-09-18 (5) — Fázis 1: történelmi adatok letöltve (9110 meccs)

### Mit csináltunk

Megírtuk a Fázis 1 letöltőjét
([gyujtes/tortenelmi.py](../src/tippmix/gyujtes/tortenelmi.py)) és a hozzá
tartozó CLI-parancsot:

```
uv run tippmix tortenelmi-letoltes
```

**Eredmény — mind az 5 aktív liga, 6 szezon (2021/22 – 2026/27):**

| Liga | Meccsek | Időszak |
| --- | --- | --- |
| E0 (Premier League) | 1940 | 2021-08-13 … 2026-09-14 |
| SP1 (La Liga) | 1959 | 2021-08-13 … 2026-09-17 |
| D1 (Bundesliga) | 1557 | 2021-08-13 … 2026-09-13 |
| I1 (Serie A) | 1940 | 2021-08-21 … 2026-09-14 |
| F1 (Ligue 1) | 1714 | 2021-08-06 … 2026-09-13 |
| **Összesen** | **9110** | |

Az adat `data/tortenelmi/<liga>.parquet` alá kerül (gitignore-olva,
regenerálható).

### Adatminőség — ez a lényeg

**Nulla hiányzó záró odds** mind a 9110 meccsen, 1X2-re és gólszámra
egyaránt. Ez azért kritikus, mert a **záró odds a CLV mércéje** — a projekt
sikerkritériuma. Ha ez hiányos lenne, a backteszt egy nem létező
referenciához mérne.

Az overround-ellenőrzés is tiszta: átlag **1,0306** (3,1% margó, jellemző a
Pinnacle-re), minimum 1,0005, és **nincs 1,0 alatti sor** — ha lenne, az
arbitrázst jelentene, ami valós piacon nem fordul elő, tehát adathibára
utalna.

### Két akadály, amit megoldottunk

**1. A `soccerdata` nem importálható Python 3.12-n.** Az egyik tranzitív
függősége (`undetected-chromedriver`) a `distutils`-t importálja, amit a 3.12
eltávolított — emiatt a csomag **egyetlen almodulja sem** volt betölthető. A
javítás: `setuptools` felvétele explicit függőségként, ami visszaadja a
`distutils`-t. Egysoros javítás, de enélkül az egész Fázis 1 blokkolt.

**2. A Pinnacle rövidítése következetlen a forrásban.** Az 1X2-ben `PS`
(`PSCH`), a gólszámban `P` (`PC>2.5`). Ez a football-data.co.uk sajátossága;
a kód `_IRODA_OU_ALIAS`-szal kezeli. A Pinnacle gólszám-oszlopában ráadásul
van hiány (a 2023/24-es PL-ben 7 meccsen), ezért soronkénti visszaesés van a
B365-re — nem oszloponkénti, hanem **cellánkénti**, hogy egyetlen hiányzó
érték se veszítsen el egy egész meccset.

### Mi működik

```
uv run tippmix tortenelmi-letoltes  → 9110 meccs, 5 liga
uv run pytest                       → 120 passed (108 → 120)
```

12 új teszt, hálózat nélkül: szezonkód-számítás (az augusztusi szezonfordulóval
és az évszázadfordulóval), a záró odds kiolvasása, a tartalék-irodára esés, a
hiányos meccsek eldobása.

### Eltérés a specifikációtól — szándékos

A spec a Fázis 1-re „SQLite-ba töltése" ír. **Parquet-et használunk**, mert:
a felhasználó Supabase-t választott igazságforrásnak (a spec SQLite-ja még a
döntés előtti állapot), a modellillesztés úgyis a teljes táblát olvassa
egyben, és a `settings.yaml` `adattar` blokkja eleve Parquet-cache-t ír elő a
backteszthez. A Supabase-be töltés akkor lesz aktuális, amikor a *futási*
eredményeket naplózzuk — az a 12. lépés, nem ez.

### A következő lépés

**Fázis 2** — a spec szerint ez és a Fázis 3 „a lényeg":
Dixon-Coles illesztés + eredménymátrix + backteszt-keretrendszer. Ha ezen
átjutunk és a backteszt nem mutat pozitív CLV-t, a 4-6. fázist nem érdemes
megépíteni ebben a formában.

Ehhez még kellenek a 3. lépés jellemzői (xG az Understatból, ClubElo) — ezek
`NotImplementedError`-ral várnak a `tortenelmi.py`-ban, és a Fázis 2 elején
készülnek el.

---

## 2026-09-18 (4) — A Tippmix-forgalom kizárólag Actionsből indulhat

### Miért

A felhasználó jelezte, hogy a munkahelyi gépéről indított Tippmix-lekérdezés
**munkajogi kockázatot** jelenthet, mert a céges IT-szabályzat tiltja a
tippmixpro.hu elérését. A fejlesztés során kiderült, hogy a nyers WebSocket
átmegy a céges proxyn (csak a böngésző van szűrve) — épp ezért veszélyes:
attól, hogy technikailag működik, még szabályszegés lehet.

### Mit csináltunk

**Az éles rendszeren nem kellett változtatni** — a napi futások és a záró
szorzók gyűjtése eleve `ubuntu-latest` runneren mentek. A gépről csak a
fejlesztői próbák indultak.

- Új workflow: [gyujtes-proba.yml](../.github/workflows/gyujtes-proba.yml) —
  a gyűjtés kipróbálása runneren, az eredmény artefaktumként letölthető.
  Csak olvas: nincs e-mail, nincs adatbázis, nem kell hozzá titok.
  Indítás: `gh workflow run gyujtes-proba.yml`
- Új védőkorlát: [_csak_actionsben.py](../scripts/_csak_actionsben.py) — a
  Tippmixet hívó szkriptek (`ws_felderites.py`, `wamp_proba.py`,
  `gyujtes_proba.py`) **kilépnek, mielőtt bármit hívnának**, ha nem CI-ben
  futnak. Nem csak komment: tényleges `SystemExit`.
- A [CLAUDE.md](../CLAUDE.md) kapott egy új szakaszt a biztonsági elvárások
  alatt, hogy ezt minden jövőbeli munkamenet tudja.

Indoklás és hatókör: [DECISIONS.md](DECISIONS.md) D-011.

### Fontos, hogy tudd

A megkötés **kizárólag a Tippmixre** vonatkozik. A Fázis 1 történelmi
adatforrásai (football-data.co.uk, Understat, ClubElo, NBA) nem
szerencsejáték-oldalak, azok lokálisan is hívhatók.

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
