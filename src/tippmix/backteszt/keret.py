"""Walk-forward backteszt-keretrendszer.

"A 2. és 3. fázis a lényeg. Ha ezeken átjutunk és a backteszt nem mutat
pozitív CLV-t, akkor a 4-6. fázist nem érdemes megépíteni ebben a formában.
Jobb ezt a 2. héten megtudni, mint a 8-on." (spec, Fejlesztési sorrend)

AZ ALAPSZABÁLY, AMI MINDENT ELDÖNT:

Ugyanaz a kódfüggvény építi a jellemzőket élesben és backtesztben, egyetlen
`asof_utc` paraméterrel. A modellparamétereket MINDEN FORDULÓRA újra kell
illeszteni az addigi adatokból. Ez lassabb, de ez az egyetlen becsületes
módszer.

Ha ezt elrontod, a backteszt csodálatos eredményt ad, élesben meg buksz.

A FŐ MÉRCE A CLV, NEM A P&L:
  - a nyereség rövid távon szinte teljesen a szerencsén múlik
  - a CLV-hez jóval kevesebb minta kell: pár száz fogadáson már értelmezhető
  - a 3%-os ROI statisztikai igazolásához n ≈ 4400 fogadás kellene

A CLV-t a Pinnacle záró vonalához mérjük (football-data.co.uk PSCH/PSCD/PSCA
oszlopok), mert az a legélesebb, legalacsonyabb margójú referencia.

FONTOS KORLÁT — mit mér ez a backteszt és mit nem:

A történelmi adatunkban CSAK a záró odds van meg, a nyitó nem. A rendszer
élesben a NYITÓ (vagy legalábbis a meccs előtti) áron fogadna, és a záróhoz
mérné a CLV-t. Itt viszont ugyanazt az árat használjuk fogadásra és
referenciaként, így a "CLV" definíció szerint nulla lenne.

Ezért ez a keret a modell **valószínűség-minőségét** méri a záró vonalhoz
képest: a záró árból vig-mentesítéssel kapott piaci valószínűséget tekintjük
az igazság legjobb becslésének, és azt nézzük, a modellünk ehhez képest
ad-e információt (Brier-pontszám), illetve hogy a modell által talált "él"
irányában a tényleges kimenetel gyakoribb-e. Ez a becsületes válasz arra,
amit ezzel az adattal mérni lehet.

Valódi CLV-mérés a Fázis 6-tól lesz, éles futásból: a `zaro-odds` workflow
gyűjti a záró árat a ténylegesen javasolt fogadásokhoz.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pandas as pd

from tippmix.dontes import vig
from tippmix.gyujtes import tortenelmi
from tippmix.kozos.hibak import ModellHiba
from tippmix.kozos.naplo import naplo
from tippmix.modellek import futball, kalibracio

log = naplo(__name__)

# A backteszt által vizsgált piacok és a hozzájuk tartozó oszlopok a
# történelmi táblában. A kulcs a modell `piac_valoszinusegek()` kimenetének
# neve, az érték a záró odds oszlopa.
_PIACOK = {
    "1X2": (("1", "zaro_1x2_h"), ("X", "zaro_1x2_d"), ("2", "zaro_1x2_a")),
    "OU25": (("OU25_Tobb", "zaro_ou25_tobb"), ("OU25_Kevesebb", "zaro_ou25_kevesebb")),
}


@dataclass(frozen=True, slots=True)
class BacktesztEredmeny:
    """Egy backteszt-futás eredménye."""

    fogadas_db: int
    osszes_tet: float
    nyereseg: float
    roi: float
    atlag_clv: float
    pozitiv_clv_arany: float
    brier: float
    max_drawdown: float
    parameterek: dict
    # A kiértékelt jelöltek soronként — ebből készül a kalibrációs görbe és
    # a paraméterkeresés. Nem a fogadások, hanem MINDEN megvizsgált kimenetel.
    jeloltek: pd.DataFrame = field(default_factory=pd.DataFrame, repr=False)


def _illesztesi_napok(kezdet: date, veg: date, ujrafittelés_naponta: int) -> list[date]:
    napok = []
    mostani = kezdet
    while mostani <= veg:
        napok.append(mostani)
        mostani += timedelta(days=ujrafittelés_naponta)
    return napok


def _jeloltek_egy_ablakra(
    par: futball.DixonColesParameterek,
    meccs_szamok: dict[str, int],
    ablak: pd.DataFrame,
    min_meccs: int,
    w: float,
) -> list[dict]:
    """Egy időablak meccseinek kiértékelése a már illesztett modellel."""
    sorok: list[dict] = []
    for _, meccs in ablak.iterrows():
        # Adatelégségességi kapu (spec 3. lépés): kevés meccsnél a
        # csapaterősség nem megbízható. Ez a KEVES_ADAT kiesés.
        if min(meccs_szamok.get(meccs.hazai, 0), meccs_szamok.get(meccs.vendeg, 0)) < min_meccs:
            continue
        try:
            lambda_h, lambda_v = futball.lambdak(par, meccs.hazai, meccs.vendeg)
        except ModellHiba:
            continue

        matrix = futball.eredmenymatrix(lambda_h, lambda_v, par.rho)
        modell_p = futball.piac_valoszinusegek(matrix)
        tenyleges = _tenyleges_kimenetelek(meccs)

        for piac_kod, kimenetelek in _PIACOK.items():
            oddsok = [float(meccs[oszlop]) for _, oszlop in kimenetelek]
            if any(not np.isfinite(o) or o <= 1 for o in oddsok):
                continue

            vig_eredmeny = vig.vig_eltavolitas(oddsok)
            for i, (nev, oszlop) in enumerate(kimenetelek):
                p_piac = vig_eredmeny.p_fair[i]
                # Piaci zsugorítás (spec 6. lépés): a modellt a piac felé
                # húzzuk. Ez a védelem a hamis élek ellen.
                p_vegleges = kalibracio.zsugorit(modell_p[nev], p_piac, w)
                sorok.append(
                    {
                        "datum": meccs.datum,
                        "liga_kod": meccs.liga_kod,
                        "hazai": meccs.hazai,
                        "vendeg": meccs.vendeg,
                        "piac": piac_kod,
                        "kimenetel": nev,
                        "odds": float(meccs[oszlop]),
                        "p_modell": modell_p[nev],
                        "p_piac_fair": p_piac,
                        "p_vegleges": p_vegleges,
                        "edge": vig.edge(p_vegleges, p_piac),
                        "ev": vig.ev(p_vegleges, float(meccs[oszlop])),
                        "bekovetkezett": tenyleges[nev],
                        "gyanus_piac": vig_eredmeny.gyanus,
                    }
                )
    return sorok


def _tenyleges_kimenetelek(meccs: pd.Series) -> dict[str, int]:
    """Melyik kimenetel következett be ténylegesen."""
    h, v = int(meccs.hazai_gol), int(meccs.vendeg_gol)
    return {
        "1": int(h > v),
        "X": int(h == v),
        "2": int(h < v),
        "OU25_Tobb": int(h + v >= 3),
        "OU25_Kevesebb": int(h + v <= 2),
    }


def walk_forward(
    kezdet: date,
    veg: date,
    ligak: list[str],
    ujrafittelés_naponta: int = 7,
    xi: float = 0.0035,
    w: float = 0.35,
    xg_suly: float = 0.0,
    min_edge: float = 0.03,
    min_meccs: int = 12,
    min_odds: float = 1.30,
    max_odds: float = 6.00,
) -> BacktesztEredmeny:
    """Walk-forward backteszt.

    Minden fordulóra:
      1. Illeszd a modellt KIZÁRÓLAG az addigi adatokból
      2. Építsd a jellemzőket asof_utc = a meccs kezdése
      3. Számold a valószínűségeket, a vig-mentes fair árat, az élt
      4. Alkalmazd a döntési fát és a tétezést
      5. Rögzítsd a CLV-t a Pinnacle záró vonalához

    Args:
        ujrafittelés_naponta: hány naponta illesszük újra a modellt.
            A specifikáció "minden fordulóra" ír, ez a gyakorlati közelítés;
            a végleges értéket mérni kell.
    """
    osszes_jelolt: list[dict] = []

    for liga_kod in ligak:
        meccsek = tortenelmi.olvas(liga_kod)
        napok = _illesztesi_napok(kezdet, veg, ujrafittelés_naponta)

        for nap in napok:
            asof = datetime(nap.year, nap.month, nap.day, tzinfo=UTC)
            ablak_veg = min(nap + timedelta(days=ujrafittelés_naponta), veg + timedelta(days=1))

            datumok = pd.to_datetime(meccsek["datum"])
            ablak = meccsek.loc[
                (datumok >= pd.Timestamp(nap)) & (datumok < pd.Timestamp(ablak_veg))
            ]
            if ablak.empty:
                continue

            try:
                par = futball.illeszt(meccsek, liga_kod, asof, xi=xi, xg_suly=xg_suly)
            except ModellHiba as hiba:
                log.warning(
                    "backteszt_illesztes_sikertelen", liga=liga_kod, nap=str(nap), hiba=str(hiba)
                )
                continue

            osszes_jelolt.extend(
                _jeloltek_egy_ablakra(par, futball.meccs_szamok(meccsek, asof), ablak, min_meccs, w)
            )

    jeloltek = pd.DataFrame(osszes_jelolt)
    log.info("backteszt_kesz", jelolt_db=len(jeloltek), ligak=ligak)
    return _ertekel(
        jeloltek,
        min_edge=min_edge,
        min_odds=min_odds,
        max_odds=max_odds,
        parameterek={
            "kezdet": str(kezdet),
            "veg": str(veg),
            "ligak": ligak,
            "xi": xi,
            "w": w,
            "xg_suly": xg_suly,
            "min_edge": min_edge,
            "min_meccs": min_meccs,
            "ujrafittelés_naponta": ujrafittelés_naponta,
        },
    )


def _ertekel(
    jeloltek: pd.DataFrame,
    min_edge: float,
    min_odds: float,
    max_odds: float,
    parameterek: dict,
) -> BacktesztEredmeny:
    """A jelöltekből fogadásokat választ és kiértékeli őket."""
    if jeloltek.empty:
        return BacktesztEredmeny(0, 0.0, 0.0, 0.0, 0.0, 0.0, float("nan"), 0.0, parameterek)

    brier = kalibracio.brier_pontszam(
        jeloltek["p_vegleges"].to_numpy(), jeloltek["bekovetkezett"].to_numpy()
    )

    # A döntési fa lényege: csak a kellően nagy élű, ésszerű szorzósávba eső
    # jelöltekből lesz fogadás.
    fogadasok = jeloltek.loc[
        (jeloltek["edge"] >= min_edge)
        & (jeloltek["odds"] >= min_odds)
        & (jeloltek["odds"] <= max_odds)
        & (~jeloltek["gyanus_piac"])
    ].copy()

    if fogadasok.empty:
        return BacktesztEredmeny(0, 0.0, 0.0, 0.0, 0.0, 0.0, brier, 0.0, parameterek, jeloltek)

    # Egységnyi tét minden fogadásra: a tétezés hatását külön mérjük,
    # itt a jelválasztás minőségét akarjuk látni.
    fogadasok["hozam"] = np.where(fogadasok["bekovetkezett"] == 1, fogadasok["odds"] - 1.0, -1.0)
    nyereseg = float(fogadasok["hozam"].sum())
    osszes_tet = float(len(fogadasok))

    # "CLV" itt: mennyivel jobb árat kaptunk a modell szerinti fair árnál.
    # A korlátokról lásd a modul docstringjét.
    clv = fogadasok["odds"] * fogadasok["p_piac_fair"] - 1.0

    egyenleg = fogadasok["hozam"].cumsum()
    csucs = egyenleg.cummax()
    max_drawdown = float((csucs - egyenleg).max()) if len(egyenleg) else 0.0

    return BacktesztEredmeny(
        fogadas_db=len(fogadasok),
        osszes_tet=osszes_tet,
        nyereseg=nyereseg,
        roi=nyereseg / osszes_tet,
        atlag_clv=float(clv.mean()),
        pozitiv_clv_arany=float((clv > 0).mean()),
        brier=brier,
        max_drawdown=max_drawdown,
        parameterek=parameterek,
        jeloltek=jeloltek,
    )


def parameter_kereses(
    kezdet: date,
    veg: date,
    ligak: list[str],
    w_racs: list[float],
    xi_racs: list[float],
) -> pd.DataFrame:
    """A zsugorítási súly (w) és az időbeli felejtés (ξ) keresése.

    "A w-t nem én találom ki, a backteszt adja meg: azt az értéket keressük,
    ami a validációs időszakon a legjobb CLV-t hozza."

    FIGYELEM: a keresést a VALIDÁCIÓS szeleten kell futtatni, és a végleges
    értékelést egy külön, érintetlen teszt-szeleten. Különben a paraméterek
    ráilleszkednek a zajra.
    """
    sorok = []
    for xi in xi_racs:
        for w in w_racs:
            eredmeny = walk_forward(kezdet, veg, ligak, xi=xi, w=w)
            sorok.append(
                {
                    "xi": xi,
                    "w": w,
                    "fogadas_db": eredmeny.fogadas_db,
                    "roi": eredmeny.roi,
                    "atlag_clv": eredmeny.atlag_clv,
                    "pozitiv_clv_arany": eredmeny.pozitiv_clv_arany,
                    "brier": eredmeny.brier,
                }
            )
            log.info("parameter_racs_pont", xi=xi, w=w, fogadasok=eredmeny.fogadas_db)
    return pd.DataFrame(sorok)


def cache_feltoltes(ligak: list[str], szezonok: list[str]) -> None:
    """Az adat lehúzása Supabase-ből lokális Parquet-cache-be.

    A backteszt több százezer sort olvas — ezt hálózaton keresztül nem
    érdemes. A Supabase marad az igazságforrás, ez csak gyorsítótár.
    """
    raise NotImplementedError(
        "A backteszt jelenleg közvetlenül a data/tortenelmi/ Parquet-ből olvas "
        "(D-012), Supabase-cache nem kell hozzá."
    )
