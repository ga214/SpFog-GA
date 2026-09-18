"""Történelmi adatok letöltése a modellezéshez és a backteszthez.

Források (kutatási jelentés 2-3. szakasz):

  FUTBALL
    football-data.co.uk  — eredmény + NYITÓ ÉS ZÁRÓ odds, ~22 liga.
                           Ez az EGYETLEN ingyenes forrás, ami eredményt ÉS
                           záró oddsot egyben ad → a CLV-mérés alapja.
    Understat            — xG 2014/15-től, 6 liga
    ClubElo              — napi Elo-értékelés, CSV API
    (mind elérhető a `soccerdata` wrapperen keresztül)

  KOSÁR
    nba_api              — FIGYELEM: a stats.nba.com blokkolja az
                           adatközponti IP-ket → GitHub Actionsből
                           valószínűleg nem megy. Tartalék:
                           Basketball-Reference.
    euroleague-api       — EuroLeague/EuroCup
    sportsbookreviewsonline.com — történelmi NBA záró odds (Excel)

Ezek NYILVÁNOS sportadat-források, nem szerencsejáték-platform — a D-011
megkötés (Tippmix csak Actionsből) rájuk NEM vonatkozik, lokálisan is
futtathatók.

A letöltött adat `data/tortenelmi/` alá kerül Parquet-ben. A soccerdata saját
HTTP-cache-t is visz (`~/soccerdata`), ezért az ismételt futás gyors.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from tippmix.kozos.config import Beallitasok, beallitasok, gyoker_ut, ligak
from tippmix.kozos.hibak import AdatgyujtesHiba
from tippmix.kozos.naplo import naplo

log = naplo(__name__)

# A football-data.co.uk oszlopnevei. A "C" a záró (closing) árat jelöli:
# PSCH = Pinnacle Closing Home. Enélkül nincs CLV-mérés.
_ZARO_1X2 = {"H": "{iroda}CH", "D": "{iroda}CD", "A": "{iroda}CA"}
_ZARO_OU25 = {"Tobb": "{iroda}C>2.5", "Kevesebb": "{iroda}C<2.5"}

# A Pinnacle rövidítése a gólszám-oszlopokban "P", az 1X2-ben "PS" — a
# football-data.co.uk következetlensége, nem a miénk.
_IRODA_OU_ALIAS = {"PS": "P"}


def szezon_kodok(szezonok_szama: int, ma: date | None = None) -> list[str]:
    """A soccerdata szezonkódjai visszamenőleg: ["2324", "2425", …].

    A szezon a naptári év közepén fordul: augusztustól az új szezon megy.
    """
    ma = ma or date.today()
    kezdo_ev = ma.year if ma.month >= 8 else ma.year - 1
    kodok = []
    for eltolas in range(szezonok_szama):
        ev = kezdo_ev - eltolas
        kodok.append(f"{ev % 100:02d}{(ev + 1) % 100:02d}")
    return sorted(kodok)


def footballdata_letoltes(liga_kod: str, szezonok: list[str]) -> pd.DataFrame:
    """football-data.co.uk CSV letöltése egy ligára, több szezonra.

    A záró oddsokat "C" jelöli az oszlopnevekben (B365CH, PSCH), a Pinnacle
    ázsiai hendikepet PAHH/PAHA. A CLV-t a Pinnacle záró vonalához mérjük,
    mert az a legélesebb, legalacsonyabb margójú referencia.

    Returns:
        Normalizált tábla: liga_kod, szezon, datum, hazai, vendeg, gólok és a
        záró szorzók (1X2 + gólszám 2.5).

    Raises:
        AdatgyujtesHiba: ha a ligához nincs `soccerdata_liga` a configban.
    """
    import soccerdata as sd

    liga_config = ligak()
    liga = next((x for x in liga_config.futball if x.kod == liga_kod), None)
    if liga is None:
        raise AdatgyujtesHiba(f"Ismeretlen liga: {liga_kod!r}")
    if not liga.soccerdata_liga:
        raise AdatgyujtesHiba(
            f"A(z) {liga_kod!r} ligához nincs `soccerdata_liga` a config/ligak.yaml-ban, "
            "ezért nem tölthető le. Ki kell deríteni a pontos nevet."
        )

    log.info("footballdata_letoltes", liga=liga_kod, szezonok=szezonok)
    nyers = sd.MatchHistory(leagues=liga.soccerdata_liga, seasons=szezonok).read_games()
    return _normalizal(nyers, liga_kod)


def _oszlop(nyers: pd.DataFrame, minta: str, iroda: str) -> pd.Series:
    """Egy odds-oszlop kiolvasása, hiányzó oszlopnál NaN-sorozattal."""
    nev = minta.format(iroda=iroda)
    if nev in nyers.columns:
        return pd.to_numeric(nyers[nev], errors="coerce")
    return pd.Series(pd.NA, index=nyers.index, dtype="Float64")


def _zaro_odds(nyers: pd.DataFrame, beall: Beallitasok) -> dict[str, pd.Series]:
    """Záró szorzók az elsődleges irodától, hiányzó értéknél a tartalékkal.

    A Pinnacle 1X2-je gyakorlatilag hiánytalan, a gólszámnál viszont
    előfordul hiány — ezért van a visszaesés.
    """
    elsodleges = beall.tortenelmi.zaro_odds_iroda
    tartalek = beall.tortenelmi.zaro_odds_tartalek

    ki: dict[str, pd.Series] = {}
    for kimenetel, minta in _ZARO_1X2.items():
        elso = _oszlop(nyers, minta, elsodleges)
        ki[f"zaro_1x2_{kimenetel.lower()}"] = elso.fillna(_oszlop(nyers, minta, tartalek))

    for kimenetel, minta in _ZARO_OU25.items():
        elso = _oszlop(nyers, minta, _IRODA_OU_ALIAS.get(elsodleges, elsodleges))
        masodik = _oszlop(nyers, minta, _IRODA_OU_ALIAS.get(tartalek, tartalek))
        ki[f"zaro_ou25_{kimenetel.lower()}"] = elso.fillna(masodik)

    return ki


def _normalizal(nyers: pd.DataFrame, liga_kod: str) -> pd.DataFrame:
    """A football-data nyers tábláját a projekt oszlopneveire hozza."""
    beall = beallitasok()
    index = nyers.index.to_frame(index=False)

    tabla = pd.DataFrame(
        {
            "liga_kod": liga_kod,
            "szezon": index["season"].to_numpy(),
            "datum": pd.to_datetime(nyers["date"]).to_numpy(),
            "hazai": nyers["home_team"].to_numpy(),
            "vendeg": nyers["away_team"].to_numpy(),
            "hazai_gol": pd.to_numeric(nyers["FTHG"], errors="coerce").to_numpy(),
            "vendeg_gol": pd.to_numeric(nyers["FTAG"], errors="coerce").to_numpy(),
        }
    )
    for nev, ertek in _zaro_odds(nyers, beall).items():
        tabla[nev] = ertek.to_numpy()

    # Le nem játszott vagy hiányos meccs nem használható sem illesztésre, sem
    # backtesztre — csendben félrevezetne.
    ervenyes = tabla["hazai_gol"].notna() & tabla["vendeg_gol"].notna()
    eldobva = int((~ervenyes).sum())
    if eldobva:
        log.warning("hianyos_meccsek_eldobva", liga=liga_kod, db=eldobva)

    return tabla.loc[ervenyes].sort_values("datum").reset_index(drop=True)


def mentes(tabla: pd.DataFrame, liga_kod: str) -> Path:
    """A letöltött ligát Parquet-be menti `data/tortenelmi/<liga>.parquet` néven."""
    beall = beallitasok()
    konyvtar = gyoker_ut(beall.tortenelmi.konyvtar)
    konyvtar.mkdir(parents=True, exist_ok=True)
    utvonal = konyvtar / f"{liga_kod}.parquet"
    tabla.to_parquet(utvonal, index=False)
    log.info("tortenelmi_mentve", liga=liga_kod, sorok=len(tabla), utvonal=str(utvonal))
    return utvonal


def olvas(liga_kod: str) -> pd.DataFrame:
    """Egy korábban letöltött liga beolvasása.

    Raises:
        AdatgyujtesHiba: ha még nem töltöttük le.
    """
    beall = beallitasok()
    utvonal = gyoker_ut(beall.tortenelmi.konyvtar) / f"{liga_kod}.parquet"
    if not utvonal.exists():
        raise AdatgyujtesHiba(
            f"Nincs letöltött történelmi adat: {liga_kod}. "
            "Futtasd: uv run tippmix tortenelmi-letoltes"
        )
    return pd.read_parquet(utvonal)


def osszes_aktiv_letoltes(szezonok_szama: int | None = None) -> dict[str, int]:
    """Minden aktív futball-liga letöltése és mentése.

    Returns:
        Ligánként a letöltött meccsek száma.
    """
    beall = beallitasok()
    liga_config = ligak()
    szezonok = szezon_kodok(szezonok_szama or beall.tortenelmi.szezonok_szama)

    eredmeny: dict[str, int] = {}
    for liga in liga_config.futball:
        if not liga.aktiv or not liga.soccerdata_liga:
            continue
        tabla = footballdata_letoltes(liga.kod, szezonok)

        if liga.understat_liga:
            xg = understat_xg_letoltes(liga.understat_liga, szezonok)
            tabla = xg_hozzafuzes(tabla, liga.kod, xg)

        mentes(tabla, liga.kod)
        eredmeny[liga.kod] = len(tabla)
    return eredmeny


def understat_szezon_kodok(szezonok: list[str]) -> list[str]:
    """A "2425" alakú kódokból az Understat négyjegyű kezdőévét adja: "2024"."""
    return [f"20{kod[:2]}" for kod in szezonok]


def _nev_leképezés(liga_kod: str) -> dict[str, str]:
    """Understat → football-data csapatnevek (data/understat_nevek.csv).

    VERZIÓZOTT, kézi munka. A fuzzy illesztés csak javaslatot adott; a fájl
    fejlécében ott a konkrét példa, ahol a fuzzy rossz csapatot választott
    volna (CLAUDE.md 3. szabály).
    """
    utvonal = gyoker_ut("data/understat_nevek.csv")
    if not utvonal.exists():
        return {}
    tabla = pd.read_csv(utvonal, comment="#")
    liga = tabla.loc[tabla["liga_kod"] == liga_kod]
    return dict(zip(liga["understat_nev"], liga["footballdata_nev"], strict=True))


def understat_xg_letoltes(understat_liga: str, szezonok: list[str]) -> pd.DataFrame:
    """Understat xG-adat letöltése.

    Args:
        szezonok: "2425" alakú kódok, mint a football-data letöltésnél.

    Returns:
        datum, hazai, vendeg, hazai_xg, vendeg_xg — football-data csapatnevekkel.
    """
    from understatapi import UnderstatClient

    sorok: list[dict[str, Any]] = []
    with UnderstatClient() as kliens:
        for ev in understat_szezon_kodok(szezonok):
            try:
                meccsek = kliens.league(league=understat_liga).get_match_data(season=ev)
            except Exception as hiba:
                # Egy hiányzó szezon nem állíthatja meg a többit — a legrégebbi
                # évek egyes ligáknál nincsenek meg.
                log.warning("understat_szezon_kihagyva", liga=understat_liga, ev=ev, hiba=str(hiba))
                continue
            for meccs in meccsek:
                if not meccs.get("isResult"):
                    continue
                sorok.append(
                    {
                        "datum": pd.to_datetime(meccs["datetime"]),
                        "hazai": meccs["h"]["title"],
                        "vendeg": meccs["a"]["title"],
                        "hazai_xg": float(meccs["xG"]["h"]),
                        "vendeg_xg": float(meccs["xG"]["a"]),
                    }
                )

    log.info("understat_letoltve", liga=understat_liga, meccsek=len(sorok))
    return pd.DataFrame(sorok)


def xg_hozzafuzes(meccsek: pd.DataFrame, liga_kod: str, xg: pd.DataFrame) -> pd.DataFrame:
    """Az xG-t a meccstáblához köti csapatnév + dátum alapján.

    A dátum órára nem egyezik a két forrásban (időzóna, átütemezés), ezért
    NAPRA kerekítve párosítunk. Ez a párosítás szándékosan szigorú: ami nem
    illeszkedik pontosan, az NaN marad, nem "körülbelül jó" értéket kap.
    """
    if xg.empty:
        meccsek = meccsek.copy()
        meccsek["hazai_xg"] = pd.NA
        meccsek["vendeg_xg"] = pd.NA
        return meccsek

    leképezés = _nev_leképezés(liga_kod)
    xg = xg.copy()
    xg["hazai"] = xg["hazai"].replace(leképezés)
    xg["vendeg"] = xg["vendeg"].replace(leképezés)
    xg["nap"] = pd.to_datetime(xg["datum"]).dt.normalize()

    bal = meccsek.copy()
    bal["nap"] = pd.to_datetime(bal["datum"]).dt.normalize()

    egyesitett = bal.merge(
        xg[["nap", "hazai", "vendeg", "hazai_xg", "vendeg_xg"]],
        on=["nap", "hazai", "vendeg"],
        how="left",
    ).drop(columns=["nap"])

    talalat = int(egyesitett["hazai_xg"].notna().sum())
    log.info(
        "xg_parositas",
        liga=liga_kod,
        meccsek=len(egyesitett),
        talalat=talalat,
        arany=f"{talalat / max(len(egyesitett), 1):.1%}",
    )
    return egyesitett


def clubelo_letoltes(datum: date) -> pd.DataFrame:
    """ClubElo napi pillanatkép — feature-nek."""
    raise NotImplementedError("Fázis 2-ben készül el")


def nba_meccsek_letoltes(szezonok: list[str]) -> pd.DataFrame:
    """NBA meccsadatok. Adatközponti IP-ről valószínűleg blokkolt."""
    raise NotImplementedError("Fázis 7-ben készül el")


def euroleague_meccsek_letoltes(szezonok: list[str]) -> pd.DataFrame:
    """EuroLeague meccsadatok."""
    raise NotImplementedError("Fázis 7-ben készül el")
