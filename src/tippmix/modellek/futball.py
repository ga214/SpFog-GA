"""4. lépés — Futballmodell (Dixon-Coles).

AZ ALAPGONDOLAT: a hazai és a vendég gólszáma két (majdnem) független
Poisson-eloszlású szám. Minden csapatnak van támadó- és védőereje, és van
általános hazaipálya-előny:

    log(λ_hazai)  = támadás[hazai]  + védelem[vendég] + hazai_előny
    log(λ_vendég) = támadás[vendég] + védelem[hazai]

A paraméterek ligánként illesztve, IDŐSÚLYOZVA: a súly exp(-ξ · napok),
ahol ξ = 0.0035 (kb. fél év alatt felezi a súlyt). A ξ végleges értékét a
backteszt adja.

DIXON-COLES KORREKCIÓ: a tiszta Poisson alulbecsli a nagyon alacsony
eredményeket (0-0, 1-0, 0-1, 1-1). A korrekció ezt a négy cellát megszorozza
egy τ(x, y, λ_h, λ_v, ρ) tényezővel. A ρ az eredeti tanulmányban ≈ −0,13 volt
angol adatokra; nálunk LIGÁNKÉNT ÚJRAILLESZTJÜK.

Hivatkozás: Dixon, M.J. & Coles, S.G. (1997), "Modelling Association Football
Scores and Inefficiencies in the Football Betting Market", JRSS-C 46(2):265-280.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln
from scipy.stats import poisson

from tippmix.kozos.hibak import ModellHiba
from tippmix.kozos.naplo import naplo

log = naplo(__name__)

# Az eredménymátrix mérete: 0-10 gól mindkét oldalon (spec 4. lépés)
MATRIX_MERET = 11

# A τ korrekció csak ezen a négy cellán tér el 1-től.
_ALACSONY_CELLAK = {(0, 0), (0, 1), (1, 0), (1, 1)}

# A ρ-t ebbe a sávba szorítjuk. A τ-nak pozitívnak kell maradnia minden
# érintett cellán; szélsőséges ρ mellett negatívvá válna, és a
# log-likelihood értelmetlenné.
_RHO_HATAR = (-0.9, 0.9)

# A támadás/védelem paraméterek határa. Egy feljutott csapat, ami 4 meccsen
# nem kapott hazai gólt, e nélkül -11-es védelmet kapna ("soha nem kap gólt"),
# ami képtelenség, és elrontja az ellenfelei becslését is. Az e^±2 sáv bőven
# elég: a valódi csapaterősségek ±0,8-on belül maradnak.
_EROSSEG_HATAR = (-2.0, 2.0)

# Gyenge L2-regularizáció a csapatparaméterekre. A kevés meccsel rendelkező
# csapatokat a liga átlaga felé húzza, ahelyett hogy a kevés meccs zaját
# valódi erősségnek vennénk. Nem helyettesíti az adatelégségességi kaput
# (min_meccs_csapatonként) — az a 8. lépésben szűr, ez az illesztést védi.
_REGULARIZACIO = 0.01


@dataclass(frozen=True, slots=True)
class DixonColesParameterek:
    """Egy liga illesztett paraméterei."""

    liga_kod: str
    illesztes_idopont_utc: datetime
    tamadas: dict[str, float]
    vedelem: dict[str, float]
    hazai_elony: float
    rho: float
    xi: float
    tanito_meccs_db: int
    konvergalt: bool
    log_likelihood: float

    def kor_nap(self, most: datetime) -> float:
        """Hány napos az illesztés. A MODELL_ELAVULT kapu ezt nézi."""
        return (most - self.illesztes_idopont_utc).total_seconds() / 86400

    @property
    def csapatok(self) -> set[str]:
        return set(self.tamadas)


def tau(x: int, y: int, lambda_h: float, lambda_v: float, rho: float) -> float:
    """A Dixon-Coles korrekciós tényező a négy alacsony eredményre.

    Csak a (0,0), (0,1), (1,0), (1,1) cellákra tér el 1-től.
    """
    if (x, y) == (0, 0):
        return 1.0 - lambda_h * lambda_v * rho
    if (x, y) == (0, 1):
        return 1.0 + lambda_h * rho
    if (x, y) == (1, 0):
        return 1.0 + lambda_v * rho
    if (x, y) == (1, 1):
        return 1.0 - rho
    return 1.0


def _utc_ra(dt: datetime) -> datetime:
    """Időzóna nélküli dátumot UTC-nek tekint.

    A történelmi Parquet naiv dátumokat tárol (a forrás így adja), az
    `asof_utc` viszont tudatos. Enélkül a kivonás TypeError-t dob.
    """
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def idosuly(meccs_datum: datetime, asof_utc: datetime, xi: float) -> float:
    """Időbeli súly: exp(-ξ · eltelt_napok).

    Egy tavalyi meccs kevesebbet számít, mint a múlt hetiek. A jövőbeli
    meccsek súlya 0 — ez a jövőbe látás elleni védelem utolsó vonala.
    """
    napok = (_utc_ra(asof_utc) - _utc_ra(meccs_datum)).total_seconds() / 86400
    if napok < 0:
        return 0.0
    return float(np.exp(-xi * napok))


def _cel_ertekek(
    tanito: pd.DataFrame, hazai_gol: np.ndarray, vendeg_gol: np.ndarray, xg_suly: float
) -> tuple[np.ndarray, np.ndarray]:
    """Az illesztés célértékei: a gólok és az xG keveréke.

    Ahol nincs xG (hiányzó adat), ott a tényleges gól marad — nem találgatunk
    és nem dobjuk el a meccset.
    """
    if xg_suly <= 0 or "hazai_xg" not in tanito.columns:
        return hazai_gol.astype(float), vendeg_gol.astype(float)

    hazai_xg = pd.to_numeric(tanito["hazai_xg"], errors="coerce").to_numpy(dtype=float)
    vendeg_xg = pd.to_numeric(tanito["vendeg_xg"], errors="coerce").to_numpy(dtype=float)
    hazai_xg = np.where(np.isfinite(hazai_xg), hazai_xg, hazai_gol)
    vendeg_xg = np.where(np.isfinite(vendeg_xg), vendeg_xg, vendeg_gol)

    return (
        (1 - xg_suly) * hazai_gol + xg_suly * hazai_xg,
        (1 - xg_suly) * vendeg_gol + xg_suly * vendeg_xg,
    )


def _log_poisson(k: np.ndarray, lam: np.ndarray) -> np.ndarray:
    """Poisson log-sűrűség, nem egész `k`-ra is értelmezve.

    A `scipy.stats.poisson.logpmf` csak egész `k`-t fogad el, de az xG-vel
    kevert célérték tört. A képlet (k·log λ − λ − log Γ(k+1)) a faktoriális
    gamma-kiterjesztésével folytonosan értelmes; ez a szokásos megoldás
    (kvázi-Poisson likelihood). Egész `k`-ra pontosan a szokásos Poissont adja.
    """
    return k * np.log(lam) - lam - gammaln(k + 1.0)


def _tau_matrix(
    x: np.ndarray, y: np.ndarray, lambda_h: np.ndarray, lambda_v: np.ndarray, rho: float
) -> np.ndarray:
    """A τ vektorizált változata — az illesztés belső ciklusához."""
    ki = np.ones_like(lambda_h, dtype=float)
    ki = np.where((x == 0) & (y == 0), 1.0 - lambda_h * lambda_v * rho, ki)
    ki = np.where((x == 0) & (y == 1), 1.0 + lambda_h * rho, ki)
    ki = np.where((x == 1) & (y == 0), 1.0 + lambda_v * rho, ki)
    ki = np.where((x == 1) & (y == 1), 1.0 - rho, ki)
    return ki


def illeszt(
    meccsek: pd.DataFrame,
    liga_kod: str,
    asof_utc: datetime,
    xi: float,
    xg_suly: float = 0.0,
) -> DixonColesParameterek:
    """Dixon-Coles illesztés egy ligára, az asof időpontig ismert meccsekből.

    A backtesztben MINDEN FORDULÓRA újra kell hívni — ez lassabb, de ez az
    egyetlen becsületes módszer.

    A `meccsek` tábla oszlopai: datum, hazai, vendeg, hazai_gol, vendeg_gol,
    és opcionálisan hazai_xg, vendeg_xg.
    Az `asof_utc` UTÁNI meccsek kizárva — jövőbe látás elleni védelem.

    Args:
        xg_suly: 0 = csak a tényleges gólok számítanak, 1 = csak az xG.
            Az xG a szakirodalom szerint jobb előrejelző, mert kiszűri a
            befejezés szerencséjét: egy 0-3-ra elvesztett meccs 2,1 xG-vel
            mást mond a csapat erejéről, mint egy 0-3 0,3 xG-vel. A köztes
            értékek a kettő keverékét használják célértékként. A végleges
            értéket a backteszt adja.

    Raises:
        ModellHiba: az optimalizálás nem konvergált (ILLESZTES_SIKERTELEN)
    """
    tanito = _tanito_halmaz(meccsek, asof_utc)
    if tanito.empty:
        raise ModellHiba(f"{liga_kod}: nincs egyetlen meccs sem {asof_utc:%Y-%m-%d} előtt.")

    csapatok = sorted(set(tanito["hazai"]) | set(tanito["vendeg"]))
    if len(csapatok) < 2:
        raise ModellHiba(f"{liga_kod}: legalább két csapat kell az illesztéshez.")

    index = {csapat: i for i, csapat in enumerate(csapatok)}
    hazai_idx = tanito["hazai"].map(index).to_numpy()
    vendeg_idx = tanito["vendeg"].map(index).to_numpy()
    hazai_gol = tanito["hazai_gol"].to_numpy(dtype=int)
    vendeg_gol = tanito["vendeg_gol"].to_numpy(dtype=int)
    hazai_cel, vendeg_cel = _cel_ertekek(tanito, hazai_gol, vendeg_gol, xg_suly)
    sulyok = np.array(
        [idosuly(d.to_pydatetime(), asof_utc, xi) for d in tanito["datum"]], dtype=float
    )

    n = len(csapatok)
    # Paramétervektor: [támadás (n-1 szabad), védelem (n), hazai_előny, rho].
    # A támadás utolsó eleme nem szabad: az összeg 0-ra van rögzítve, különben
    # a modell túlparaméterezett (minden támadáshoz hozzáadhatnánk c-t, ha
    # minden védelemből levonnánk).
    kezdo = np.concatenate([np.zeros(n - 1), np.zeros(n), [0.25], [-0.05]])

    def szetszed(p: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, float]:
        tamadas = np.empty(n)
        tamadas[: n - 1] = p[: n - 1]
        tamadas[n - 1] = -p[: n - 1].sum()
        vedelem = p[n - 1 : 2 * n - 1]
        return tamadas, vedelem, float(p[-2]), float(p[-1])

    def negativ_log_likelihood(p: np.ndarray) -> float:
        tamadas, vedelem, hazai_elony, rho = szetszed(p)
        log_lh = tamadas[hazai_idx] + vedelem[vendeg_idx] + hazai_elony
        log_lv = tamadas[vendeg_idx] + vedelem[hazai_idx]
        # A kitevőt korlátozzuk: illesztés közben az optimalizáló
        # elszaladhat, és a np.exp túlcsordulna.
        lambda_h = np.exp(np.clip(log_lh, -10, 10))
        lambda_v = np.exp(np.clip(log_lv, -10, 10))

        log_p = _log_poisson(hazai_cel, lambda_h) + _log_poisson(vendeg_cel, lambda_v)
        # A τ a TÉNYLEGES eredményre vonatkozik: a Dixon-Coles korrekció az
        # alacsony gólszámok empirikus együttmozgását írja le, nem az xG-ét.
        korrekcio = _tau_matrix(hazai_gol, vendeg_gol, lambda_h, lambda_v, rho)
        # A τ negatívvá válhat szélsőséges ρ-nál; ilyenkor a log
        # értelmezhetetlen, ezért nagy büntetést adunk vissza.
        if np.any(korrekcio <= 0):
            return 1e10
        loglik = float(np.sum(sulyok * (log_p + np.log(korrekcio))))
        buntetes = _REGULARIZACIO * float(np.sum(tamadas**2) + np.sum(vedelem**2))
        return -loglik + buntetes

    hatarok = (
        [_EROSSEG_HATAR] * (2 * n - 1)  # támadás (n-1 szabad) + védelem (n)
        + [(None, None), _RHO_HATAR]  # hazai_előny, rho
    )
    eredmeny = minimize(
        negativ_log_likelihood,
        kezdo,
        method="L-BFGS-B",
        bounds=hatarok,
        options={"maxiter": 2000, "maxfun": 200_000},
    )

    tamadas, vedelem, hazai_elony, rho = szetszed(eredmeny.x)
    # A `fun` a büntetést is tartalmazza; a naplóba a tiszta illeszkedés kell.
    buntetes = _REGULARIZACIO * float(np.sum(tamadas**2) + np.sum(vedelem**2))

    # A határon ülő paraméter nem becslés, hanem a korlát műve: az adott
    # csapatnak túl kevés meccse van. A 8. lépés KEVES_ADAT kapuja szűri ki
    # őket, de itt is jelezzük, mert némán félrevezető lenne.
    hataron = _hataron_ulo_csapatok(csapatok, tamadas, vedelem)
    if hataron:
        log.warning("dixon_coles_hataron_ulo_parameter", liga=liga_kod, csapatok=sorted(hataron))

    if not eredmeny.success:
        log.warning(
            "dixon_coles_nem_konvergalt",
            liga=liga_kod,
            uzenet=str(eredmeny.message),
            meccsek=len(tanito),
        )

    return DixonColesParameterek(
        liga_kod=liga_kod,
        illesztes_idopont_utc=asof_utc,
        tamadas=dict(zip(csapatok, tamadas.tolist(), strict=True)),
        vedelem=dict(zip(csapatok, vedelem.tolist(), strict=True)),
        hazai_elony=hazai_elony,
        rho=rho,
        xi=xi,
        tanito_meccs_db=len(tanito),
        konvergalt=bool(eredmeny.success),
        log_likelihood=float(-eredmeny.fun + buntetes),
    )


def _hataron_ulo_csapatok(
    csapatok: list[str], tamadas: np.ndarray, vedelem: np.ndarray, tures: float = 1e-3
) -> set[str]:
    """Azok a csapatok, amiknek valamelyik paramétere a korláton ragadt."""
    also, felso = _EROSSEG_HATAR
    hataron: set[str] = set()
    for i, csapat in enumerate(csapatok):
        for ertek in (tamadas[i], vedelem[i]):
            if abs(ertek - also) < tures or abs(ertek - felso) < tures:
                hataron.add(csapat)
    return hataron


def _tanito_halmaz(meccsek: pd.DataFrame, asof_utc: datetime) -> pd.DataFrame:
    """Kizárólag az `asof_utc` előtt LEJÁTSZOTT meccsek.

    Ez a jövőbe látás elleni védelem legfontosabb pontja. Ha ez elromlik, a
    backteszt csodálatos eredményt ad, élesben meg buksz.
    """
    hasznalhato = meccsek["hazai_gol"].notna() & meccsek["vendeg_gol"].notna()
    hatar = pd.Timestamp(_utc_ra(asof_utc)).tz_convert(None)
    korabbi = pd.to_datetime(meccsek["datum"]) < hatar
    return meccsek.loc[hasznalhato & korabbi]


def meccs_szamok(meccsek: pd.DataFrame, asof_utc: datetime) -> dict[str, int]:
    """Csapatonként hány lejátszott meccs van az `asof_utc` előtt.

    A 8. lépés KEVES_ADAT kapuja ezt hasonlítja a `min_meccs_csapatonként`
    küszöbhöz. Szezonelején ezért hetekig kevés tipp lesz — ez helyes
    viselkedés, nem hiba (spec 3. lépés, adatelégségességi kapu).
    """
    tanito = _tanito_halmaz(meccsek, asof_utc)
    szamok = pd.concat([tanito["hazai"], tanito["vendeg"]]).value_counts()
    return {str(csapat): int(db) for csapat, db in szamok.items()}


def lambdak(par: DixonColesParameterek, hazai_id: str, vendeg_id: str) -> tuple[float, float]:
    """A két várható gólszám egy meccsre.

    Raises:
        ModellHiba: ha valamelyik csapat nem szerepelt a tanítóhalmazban
            (feljebb ez KEVES_ADAT kiesés lesz, nem hiba).
    """
    hianyzo = [cs for cs in (hazai_id, vendeg_id) if cs not in par.tamadas]
    if hianyzo:
        raise ModellHiba(f"{par.liga_kod}: ismeretlen csapat az illesztésben: {', '.join(hianyzo)}")

    log_h = par.tamadas[hazai_id] + par.vedelem[vendeg_id] + par.hazai_elony
    log_v = par.tamadas[vendeg_id] + par.vedelem[hazai_id]
    return float(np.exp(log_h)), float(np.exp(log_v))


def eredmenymatrix(lambda_h: float, lambda_v: float, rho: float) -> np.ndarray:
    """11x11-es mátrix: P(hazai i gólt lő ÉS vendég j gólt lő).

    Dixon-Coles korrekcióval, 1-re normalizálva.
    """
    golok = np.arange(MATRIX_MERET)
    p_h = poisson.pmf(golok, lambda_h)
    p_v = poisson.pmf(golok, lambda_v)
    matrix = np.outer(p_h, p_v)

    for x, y in _ALACSONY_CELLAK:
        matrix[x, y] *= tau(x, y, lambda_h, lambda_v, rho)

    # A korrekció elronthatja az összeget (és a levágott 10+ gólos farok is),
    # ezért 1-re normalizálunk. Enélkül az összes valószínűség torzulna.
    matrix = np.clip(matrix, 0.0, None)
    osszeg = matrix.sum()
    if osszeg <= 0:
        raise ModellHiba("Az eredménymátrix összege nem pozitív — érvénytelen paraméterek.")
    return matrix / osszeg


def piac_valoszinusegek(matrix: np.ndarray) -> dict[str, float]:
    """Piaci valószínűségek az eredménymátrixból — egyszerű összeadás.

    Returns:
        {"1": p, "X": p, "2": p, "OU25_Tobb": p, "OU25_Kevesebb": p,
         "BTTS_Igen": p, "BTTS_Nem": p}

    Első verzióban csak az 1X2 és az OU25 aktív (config/ligak.yaml).
    """
    meret = matrix.shape[0]
    i = np.arange(meret)[:, None]
    j = np.arange(meret)[None, :]

    osszgol = i + j
    return {
        "1": float(matrix[i > j].sum()),
        "X": float(np.trace(matrix)),
        "2": float(matrix[i < j].sum()),
        "OU25_Tobb": float(matrix[osszgol >= 3].sum()),
        "OU25_Kevesebb": float(matrix[osszgol <= 2].sum()),
        "BTTS_Igen": float(matrix[1:, 1:].sum()),
        "BTTS_Nem": float(matrix[0, :].sum() + matrix[:, 0].sum() - matrix[0, 0]),
    }
