-- =============================================================================
-- 001_init.sql — Tippmix tipprendszer alapséma
--
-- Futtatás: Supabase Dashboard → SQL Editor → New query → beilleszt → Run
-- Lásd: docs/SUPABASE_SETUP.md
--
-- FONTOS SZABÁLY (CLAUDE.md, 2. pont): ezt a fájlt később NEM írjuk át.
-- Minden későbbi séma-változás ÚJ migrációs fájlba megy (002_*.sql,
-- 003_*.sql), ALTER TABLE formában, hogy a történet és a
-- reprodukálhatóság megmaradjon.
--
-- BIZTONSÁG: minden táblán be van kapcsolva a row level security, és NINCS
-- policy. Ez azt jelenti: az anon és authenticated kulcs semmit nem lát,
-- csak a service role kulcs fér hozzá (az megkerüli az RLS-t). A repó
-- publikus, ezért ez nem opcionális.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- futasok — minden pipeline-futás egy sora
--
-- Ez az audit-nyom: mikor futott, milyen típusban, mit talált, hibázott-e.
-- A leállítási feltételek (spec 12. lépés) ezt olvassák:
-- "3 egymást követő sikertelen futás" → scraping elromlott.
-- -----------------------------------------------------------------------------
create table if not exists public.futasok (
    futas_id                text        primary key,
    idopont_utc             timestamptz not null default now(),
    futas_tipusa            text        not null
        check (futas_tipusa in ('delelott', 'este', 'zaro_odds', 'teszt')),
    allapot                 text        not null
        check (allapot in ('sikeres', 'sikertelen', 'nincs_tipp')),
    megvizsgalt_esemeny_db  integer     not null default 0,
    megvizsgalt_piac_db     integer     not null default 0,
    javaslat_db             integer     not null default 0,
    kombinacio_db           integer     not null default 0,
    osszes_tet_ft           integer     not null default 0,
    bankroll_ft             integer,
    hibauzenet              text,
    futasido_mp             numeric(10, 2),
    verzio                  text
);

comment on table public.futasok is
    'Minden pipeline-futás egy sora. A leállítási feltételek ezt olvassák.';

create index if not exists futasok_idopont_idx
    on public.futasok (idopont_utc desc);
create index if not exists futasok_tipus_allapot_idx
    on public.futasok (futas_tipusa, allapot, idopont_utc desc);


-- -----------------------------------------------------------------------------
-- tippek — a program naplója (spec 12. lépés)
--
-- Minden JAVASLATRÓL egy sor. A mezőlista szó szerint a specifikáció 12.
-- lépéséből származik, kiegészítve a technikai kulcsokkal.
--
-- A `zaro_odds`, `eredmeny`, `nyeremeny`, `clv` mezők a javaslat
-- pillanatában üresek — a záró-szorzó gyűjtő futás és az eredményfrissítés
-- tölti fel őket később.
-- -----------------------------------------------------------------------------
create table if not exists public.tippek (
    id                      bigint      generated always as identity primary key,

    -- azonosítás
    futas_id                text        not null references public.futasok (futas_id),
    idopont_utc             timestamptz not null default now(),
    tippmix_event_id        text        not null,

    -- esemény
    sport                   text        not null check (sport in ('foci', 'kosar')),
    bajnoksag               text        not null,
    liga_kod                text,
    hazai                   text        not null,
    vendeg                  text        not null,
    kezdes_utc              timestamptz not null,

    -- piac
    piac                    text        not null,
    kimenetel               text        not null,
    vonal                   numeric(6, 2),

    -- valószínűségek (spec 4-7. lépés)
    odds_javaslatkor        numeric(8, 3) not null check (odds_javaslatkor > 1),
    p_modell_nyers          numeric(7, 6) check (p_modell_nyers between 0 and 1),
    p_kalibralt             numeric(7, 6) check (p_kalibralt between 0 and 1),
    p_vegleges              numeric(7, 6) not null check (p_vegleges between 0 and 1),
    p_fair                  numeric(7, 6) not null check (p_fair between 0 and 1),

    -- él és tét (spec 7. és 9. lépés)
    edge                    numeric(7, 6) not null,
    ev                      numeric(8, 6) not null,
    javasolt_tet            integer     not null check (javasolt_tet >= 0),
    kelly_nyers             numeric(8, 6),
    futas_tipusa            text        not null check (futas_tipusa in ('delelott', 'este')),

    -- ellenőrzések (spec 7. és 8. lépés)
    referencia_odds         numeric(8, 3),
    referencia_p_fair       numeric(7, 6),
    hirveto_allapot         text        not null default 'nincs_ellenorzes'
        check (hirveto_allapot in ('tiszta', 'veto', 'nincs_ellenorzes')),

    -- kombináció (spec 10. lépés): ha ez a tipp egy kombináció lába
    kombinacio_id           bigint,

    -- utólag töltött mezők (záró-szorzó futás + eredményfrissítés)
    zaro_odds               numeric(8, 3),
    zaro_odds_idopont_utc   timestamptz,
    eredmeny                text        check (eredmeny in ('nyert', 'vesztett', 'push', 'torolve')),
    nyeremeny               integer,
    clv                     numeric(8, 6),

    indoklas                text
);

comment on table public.tippek is
    'A program naplója: minden javaslatról egy sor. CLV = odds_javaslatkor / zaro_odds - 1.';
comment on column public.tippek.clv is
    'Closing line value. A legfontosabb szám: a nyereség rövid távon szerencse, a CLV nem.';
comment on column public.tippek.p_vegleges is
    'A piaci zsugorítás után: w * p_kalibralt + (1-w) * p_fair. Spec 6. lépés.';

create index if not exists tippek_futas_idx
    on public.tippek (futas_id);
create index if not exists tippek_kezdes_idx
    on public.tippek (kezdes_utc);
create index if not exists tippek_event_idx
    on public.tippek (tippmix_event_id);
create index if not exists tippek_eredmeny_idx
    on public.tippek (eredmeny) where eredmeny is null;
create index if not exists tippek_clv_idx
    on public.tippek (idopont_utc desc) where clv is not null;

-- Duplikátumszűrés (spec döntési fa 12. pont): ugyanarra az eseményre és
-- piacra ugyanazon a napon csak egyszer mehet javaslat.
--
-- MEGJEGYZÉS: sima "idopont_utc::date" nem indexelhető, mert a cast a
-- munkamenet időzónájától függ, a Postgres ezért nem tekinti IMMUTABLE-nek
-- (hiba: "functions in index expression must be marked IMMUTABLE").
-- Az "AT TIME ZONE 'UTC'" fix zónára rögzíti a kifejezést, ami már
-- IMMUTABLE — ez helyes is, mert a projekt szabálya szerint minden
-- időbélyeg UTC-ben tárolódik (lásd kozos/ido.py).
create unique index if not exists tippek_egyedi_napi_idx
    on public.tippek (
        tippmix_event_id, piac, kimenetel,
        ((idopont_utc at time zone 'UTC')::date)
    );


-- -----------------------------------------------------------------------------
-- kombinaciok — a 2-3 lábas szelvények (spec 10. lépés)
-- -----------------------------------------------------------------------------
create table if not exists public.kombinaciok (
    id                      bigint      generated always as identity primary key,
    futas_id                text        not null references public.futasok (futas_id),
    idopont_utc             timestamptz not null default now(),
    lab_db                  smallint    not null check (lab_db between 2 and 3),
    kombi_odds              numeric(10, 3) not null,
    kombi_p                 numeric(7, 6) not null,
    kombi_ev                numeric(8, 6) not null,
    tet_ft                  integer     not null,
    lehetseges_nyeremeny_ft integer     not null,
    eredmeny                text        check (eredmeny in ('nyert', 'vesztett', 'push', 'torolve')),
    nyeremeny               integer
);

comment on table public.kombinaciok is
    'Kombinációk. Minden láb önmagában is átment a döntési fán.';

create index if not exists kombinaciok_futas_idx
    on public.kombinaciok (futas_id);


-- -----------------------------------------------------------------------------
-- kiesesek — mi miért nem lett javaslat (spec 8. lépés döntési fa)
--
-- Ebből épül az e-mail "NEM JAVASOLT, DE MEGVIZSGÁLVA" szakasza, és ez
-- mutatja meg utólag, hogy a rendszer dolgozott-e vagy elromlott.
-- Összesítve tároljuk okonként, nem jelöltenként — különben napi több száz
-- sor keletkezne érdemi információ nélkül.
-- -----------------------------------------------------------------------------
create table if not exists public.kiesesek (
    id                      bigint      generated always as identity primary key,
    futas_id                text        not null references public.futasok (futas_id),
    ok                      text        not null,
    darab                   integer     not null check (darab > 0),
    pelda_esemeny           text
);

create index if not exists kiesesek_futas_idx
    on public.kiesesek (futas_id);


-- -----------------------------------------------------------------------------
-- ismeretlen_csapatok — a névillesztés hiányai (spec 2. lépés)
--
-- A fuzzy javaslat ide kerül, NEM kerül automatikus felhasználásra.
-- A `feldolgozva` mezőt te állítod true-ra, miután beírtad a
-- data/team_aliases.csv fájlba.
-- -----------------------------------------------------------------------------
create table if not exists public.ismeretlen_csapatok (
    id                      bigint      generated always as identity primary key,
    elso_eszlelés_utc       timestamptz not null default now(),
    utolso_eszlelés_utc     timestamptz not null default now(),
    tippmix_nev             text        not null,
    sport                   text        not null check (sport in ('foci', 'kosar')),
    javasolt_kanonikus_id   text,
    fuzzy_pontszam          smallint,
    eszlelés_db             integer     not null default 1,
    feldolgozva             boolean     not null default false,
    unique (tippmix_nev, sport)
);

comment on table public.ismeretlen_csapatok is
    'Fuzzy javaslatok kézi jóváhagyásra. A program soha nem használja fel őket automatikusan.';


-- -----------------------------------------------------------------------------
-- bankroll_naplo — a bankroll alakulása
--
-- A leállítási feltétel ("bankroll-esés a csúcshoz képest -30%") ezt olvassa.
-- -----------------------------------------------------------------------------
create table if not exists public.bankroll_naplo (
    id                      bigint      generated always as identity primary key,
    idopont_utc             timestamptz not null default now(),
    bankroll_ft             integer     not null,
    valtozas_ft             integer,
    ok                      text,
    csucs_ft                integer
);

create index if not exists bankroll_idopont_idx
    on public.bankroll_naplo (idopont_utc desc);


-- -----------------------------------------------------------------------------
-- modell_illesztesek — mikor és milyen paraméterekkel illesztettünk
--
-- A döntési fa 6. pontja (MODELL_ELAVULT) ezt olvassa: a ligamodell
-- frissebb-e mint modell_max_kor_nap.
-- -----------------------------------------------------------------------------
create table if not exists public.modell_illesztesek (
    id                      bigint      generated always as identity primary key,
    illesztes_idopont_utc   timestamptz not null default now(),
    sport                   text        not null check (sport in ('foci', 'kosar')),
    liga_kod                text        not null,
    modell_tipus            text        not null,
    parameterek             jsonb       not null,
    tanito_meccs_db         integer,
    konvergalt              boolean     not null default true,
    log_likelihood          numeric(14, 4),
    ervenyes_ig_utc         timestamptz
);

create index if not exists modell_liga_idx
    on public.modell_illesztesek (sport, liga_kod, illesztes_idopont_utc desc);


-- =============================================================================
-- ROW LEVEL SECURITY
--
-- Bekapcsoljuk minden táblán, és NEM adunk hozzá policy-t. Következmény:
-- az anon és authenticated kulccsal SEMMI nem látható. Csak a service role
-- kulcs fér hozzá, amit kizárólag a szerveroldali pipeline használ,
-- GitHub Secretsből.
--
-- Ha valaha frontend kerül a projektbe, oda csak az ANON kulcs mehet, és
-- akkor ide kell írni explicit SELECT policy-kat — de csak arra, amit
-- publikussá akarsz tenni.
-- =============================================================================

alter table public.futasok             enable row level security;
alter table public.tippek              enable row level security;
alter table public.kombinaciok         enable row level security;
alter table public.kiesesek            enable row level security;
alter table public.ismeretlen_csapatok enable row level security;
alter table public.bankroll_naplo      enable row level security;
alter table public.modell_illesztesek  enable row level security;


-- =============================================================================
-- NÉZETEK — kényelmes lekérdezések a CLV-hez és a leállítási feltételekhez
-- =============================================================================

-- A CLV alakulása: a legfontosabb szám a rendszer működésének megítéléséhez.
create or replace view public.v_clv_osszesites as
select
    count(*)                                      as tipp_db,
    round(avg(clv)::numeric, 5)                   as atlag_clv,
    round(stddev_samp(clv)::numeric, 5)           as clv_szoras,
    count(*) filter (where clv > 0)               as pozitiv_clv_db,
    round(
        (count(*) filter (where clv > 0))::numeric
        / nullif(count(*), 0), 4
    )                                             as pozitiv_clv_arany
from public.tippek
where clv is not null;

comment on view public.v_clv_osszesites is
    'Ha 50+ tipp után az atlag_clv negatív, a leállítási feltétel teljesül.';

-- Eredmények és hozam
create or replace view public.v_eredmeny_osszesites as
select
    count(*)                                              as elszamolt_tipp_db,
    sum(javasolt_tet)                                     as osszes_tet_ft,
    sum(coalesce(nyeremeny, 0))                           as osszes_nyeremeny_ft,
    sum(coalesce(nyeremeny, 0)) - sum(javasolt_tet)       as nyereseg_ft,
    round(
        (sum(coalesce(nyeremeny, 0)) - sum(javasolt_tet))::numeric
        / nullif(sum(javasolt_tet), 0), 4
    )                                                     as roi,
    count(*) filter (where eredmeny = 'nyert')            as nyert_db
from public.tippek
where eredmeny is not null;

-- Az utolsó futások állapota (leállítási feltétel: 3 egymást követő sikertelen)
create or replace view public.v_utolso_futasok as
select futas_id, idopont_utc, futas_tipusa, allapot, javaslat_db, hibauzenet
from public.futasok
where futas_tipusa in ('delelott', 'este')
order by idopont_utc desc
limit 20;
