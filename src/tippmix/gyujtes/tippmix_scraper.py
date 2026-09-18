"""1. lépés — Esemény-begyűjtés a Tippmix Pro-ról.

Ez a lista a rendszer UNIVERZUMA: ami itt nincs benne, arra soha nem kapsz
javaslatot.

Forrás: a `wss://sportsapi.tippmixpro.hu/v2` WAMP-végpont (lásd
[wamp_kliens.py](wamp_kliens.py) és docs/OPEN_QUESTIONS.md NY-11). A lekérés
három hívásból áll bajnokságonként:

    1. tournaments/<sportId>          → a bajnokságok listája
    2. matches/<tournamentId>         → a bajnokság meccsei
    3. <matchId>/match-odds/<piacok>  → a meccs piacai és szorzói

Döntések (spec 1. lépés):
  1. Hiba vagy üres válasz → 3 újrapróbálkozás 30 mp szünettel. Ha mind
     elbukik: nincs futás, hibalevél, kilépés. NEM találgat, NEM használ
     tegnapi szorzót.
  2. Csak a legalább `min_perc_kezdésig` perc múlva kezdődő események.
  3. Csak a config/ligak.yaml-ban engedélyezett bajnokságok.
  4. Csak a támogatott piactípusok.
  5. A nyers válasz elmentésre kerül data/raw/tippmix_YYYYMMDD_HHMM.json néven.

ToS: alacsony frekvenciájú, tiszteletteljes lekérés. A robots.txt egyik
hoszton sem tiltja a fogadási kínálat olvasását (NY-14).
"""

from __future__ import annotations

import asyncio
import csv
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tippmix.gyujtes.wamp_kliens import WampKliens, rekordok_tipus_szerint
from tippmix.kozos import ido
from tippmix.kozos.config import Beallitasok, Ligak, beallitasok, gyoker_ut, ligak
from tippmix.kozos.hibak import AdatgyujtesHiba
from tippmix.kozos.naplo import naplo
from tippmix.kozos.tipusok import NyersEsemeny

log = naplo(__name__)

# Évadjelölés a bajnokság nevének végén: "2026/2027" vagy "2026".
_EVAD_MINTA = re.compile(r"\s+\d{4}(?:/\d{4})?\s*$")


def letolt(most: datetime | None = None) -> list[NyersEsemeny]:
    """A Tippmix Pro teljes kínálatának letöltése és szűrése.

    Raises:
        AdatgyujtesHiba: 3 sikertelen próbálkozás után
    """
    beall = beallitasok()
    liga_config = ligak()
    most = most or ido.most_utc()

    utolso_hiba: Exception | None = None
    for probalkozas in range(1, beall.gyujtes.ujraprobalkozas_db + 1):
        try:
            nyers = asyncio.run(_letolt_egyszer(beall, liga_config, most))
        except Exception as hiba:
            utolso_hiba = hiba
            log.warning(
                "gyujtes_sikertelen",
                probalkozas=probalkozas,
                osszes=beall.gyujtes.ujraprobalkozas_db,
                hiba=str(hiba),
            )
            if probalkozas < beall.gyujtes.ujraprobalkozas_db:
                # Az utolsó próbálkozás után nincs értelme várni.
                time.sleep(beall.gyujtes.ujraprobalkozas_szunet_mp)
            continue

        if nyers:
            log.info(
                "gyujtes_kesz",
                esemeny_db=len({n.tippmix_event_id for n in nyers}),
                sor_db=len(nyers),
            )
            return nyers

        utolso_hiba = AdatgyujtesHiba("A Tippmix üres kínálatot adott vissza.")
        log.warning("gyujtes_ures", probalkozas=probalkozas)

    raise AdatgyujtesHiba(
        f"{beall.gyujtes.ujraprobalkozas_db} próbálkozás után sem sikerült adatot "
        f"szerezni a Tippmix Pro-ról. Utolsó hiba: {utolso_hiba}"
    )


async def _letolt_egyszer(
    beall: Beallitasok, liga_config: Ligak, most: datetime
) -> list[NyersEsemeny]:
    wamp = beall.gyujtes.wamp
    nyers_rekordok: dict[str, Any] = {"lekerdezve_utc": most.isoformat(), "bajnoksagok": []}
    esemenyek: list[NyersEsemeny] = []

    async with WampKliens(
        wamp, beall.gyujtes.user_agent, beall.gyujtes.keres_idokorlat_mp
    ) as kliens:
        for sport, ligak_neve in (
            ("foci", _aktiv_futball_nevek(liga_config)),
            ("kosar", _aktiv_kosar_nevek(liga_config)),
        ):
            if not ligak_neve:
                continue
            sport_id = wamp.sport_id.get(sport)
            if sport_id is None:
                continue

            piac_kodok = _piac_kodok(beall, liga_config, sport)
            if not piac_kodok:
                continue

            tornak = await kliens.lekerdez(wamp.topic("tournaments", sport_id))
            await asyncio.sleep(beall.gyujtes.keresek_kozti_szunet_mp)

            for torna in rekordok_tipus_szerint(tornak).get("TOURNAMENT", []):
                if not _bajnoksag_engedelyezett(str(torna.get("name", "")), ligak_neve):
                    continue

                meccs_rekordok = await kliens.lekerdez(wamp.topic("matches", torna["id"]))
                await asyncio.sleep(beall.gyujtes.keresek_kozti_szunet_mp)
                meccsek = rekordok_tipus_szerint(meccs_rekordok).get("MATCH", [])

                nyers_rekordok["bajnoksagok"].append(
                    {"nev": torna.get("name"), "id": torna.get("id"), "meccsek": meccsek}
                )

                for meccs in meccsek:
                    kezdes = _kezdes_utc(meccs)
                    if kezdes is None:
                        continue
                    if not ido.eleg_ido_kezdesig(kezdes, beall.futás.min_perc_kezdésig, most=most):
                        continue

                    odds_rekordok = await kliens.lekerdez(
                        wamp.topic(meccs["id"], "match-odds", ",".join(piac_kodok))
                    )
                    await asyncio.sleep(beall.gyujtes.keresek_kozti_szunet_mp)
                    nyers_rekordok["bajnoksagok"][-1].setdefault("oddsok", []).append(odds_rekordok)

                    esemenyek.extend(
                        _esemenyekke(
                            meccs,
                            odds_rekordok,
                            sport,
                            _evad_nelkul(str(torna.get("name", ""))),
                            kezdes,
                            wamp.kimenetel_kod,
                        )
                    )

    nyers_valasz_mentes(json.dumps(nyers_rekordok, ensure_ascii=False), most=most)
    return esemenyek


def _aktiv_futball_nevek(liga_config: Ligak) -> set[str]:
    return {liga.tippmix_nev for liga in liga_config.futball if liga.aktiv and liga.tippmix_nev}


def _aktiv_kosar_nevek(liga_config: Ligak) -> set[str]:
    return {liga.tippmix_nev for liga in liga_config.kosarlabda if liga.aktiv and liga.tippmix_nev}


def _piac_kodok(beall: Beallitasok, liga_config: Ligak, sport: str) -> list[str]:
    """A sport aktív piacainak Tippmix-oldali kódjai."""
    kodok = []
    for piac_kod in sorted(liga_config.aktiv_piacok(sport)):
        tippmix_kod = beall.gyujtes.wamp.piac_kod.get(piac_kod)
        if tippmix_kod:
            kodok.append(tippmix_kod)
    return kodok


def _evad_nelkul(torna_nev: str) -> str:
    """Levágja az évadot a bajnokság nevéről.

    "Premier Liga 2026/2027" → "Premier Liga", "NBA 2026/2027" → "NBA".
    """
    return _EVAD_MINTA.sub("", torna_nev).strip()


def _bajnoksag_engedelyezett(torna_nev: str, engedelyezett: set[str]) -> bool:
    """Pontos egyezés az évad levágása után.

    SZÁNDÉKOSAN nem részstring és nem fuzzy. A részstring-egyezés a
    2026-09-18-i próbán csendben beengedte az "Angol Isthmian Premier Ligát",
    a "Bundesliga 2."-t és egy indiai ligát is — miközben az angol Premier
    League kimaradt, mert a Tippmix "Premier Liga"-ként írja. A 3. szabály
    szerint egy téves párosítás rosszabb, mint egy kihagyott meccs.
    """
    return _evad_nelkul(torna_nev).casefold() in {nev.casefold() for nev in engedelyezett}


def _kezdes_utc(meccs: dict[str, Any]) -> datetime | None:
    ezredmasodperc = meccs.get("startTime")
    if not isinstance(ezredmasodperc, int | float):
        return None
    return datetime.fromtimestamp(ezredmasodperc / 1000, UTC)


def _esemenyekke(
    meccs: dict[str, Any],
    odds_rekordok: list[dict[str, Any]],
    sport: str,
    bajnoksag: str,
    kezdes: datetime,
    kimenetel_kod: dict[str, str],
) -> list[NyersEsemeny]:
    """A normalizált Tippmix-rekordokból `NyersEsemeny` sorokat épít.

    Az összekapcsolás: MARKET → MARKET_OUTCOME_RELATION → OUTCOME, és
    OUTCOME → BETTING_OFFER adja a szorzót.
    """
    csoportok = rekordok_tipus_szerint(odds_rekordok)
    piacok = {p["id"]: p for p in csoportok.get("MARKET", [])}
    kimenetelek = {o["id"]: o for o in csoportok.get("OUTCOME", [])}
    ajanlatok = {b["outcomeId"]: b for b in csoportok.get("BETTING_OFFER", [])}

    hazai = str(meccs.get("homeParticipantName", ""))
    vendeg = str(meccs.get("awayParticipantName", ""))
    if not hazai or not vendeg:
        return []

    sorok: list[NyersEsemeny] = []
    for relacio in csoportok.get("MARKET_OUTCOME_RELATION", []):
        piac = piacok.get(relacio.get("marketId"))
        kimenetel = kimenetelek.get(relacio.get("outcomeId"))
        ajanlat = ajanlatok.get(relacio.get("outcomeId"))
        if not piac or not kimenetel or not ajanlat:
            continue
        if not ajanlat.get("isAvailable", True):
            continue

        odds = ajanlat.get("odds")
        if not isinstance(odds, int | float) or odds <= 1:
            continue

        # A `headerNameKey` nyelvfüggetlen ("home"/"draw"/"over"…); a
        # `translatedName` az 1X2-nél a csapat nevét adja, ami piaconként
        # változik, ezért a döntési logika nem építhet rá.
        kod = kimenetel_kod.get(str(kimenetel.get("headerNameKey", "")))
        if kod is None:
            continue

        sorok.append(
            NyersEsemeny(
                tippmix_event_id=str(meccs["id"]),
                sport=sport,
                bajnoksag=bajnoksag,
                hazai_nev=hazai,
                vendeg_nev=vendeg,
                kezdes_utc=kezdes,
                piac_nev=str(piac.get("name", "")),
                kimenetel_nev=kod,
                odds=float(odds),
            )
        )
    return sorok


def nyers_valasz_mentes(nyers: bytes | str, most: datetime | None = None) -> Path:
    """A nyers választ menti data/raw/tippmix_YYYYMMDD_HHMM.json néven.

    Ez kell a hibakereséshez és ahhoz, hogy visszamenőleg ellenőrizni tudd,
    mit láttunk akkor.
    """
    beall = beallitasok()
    most = most or ido.most_utc()
    konyvtar = gyoker_ut(beall.gyujtes.nyers_mentes_konyvtar)
    konyvtar.mkdir(parents=True, exist_ok=True)

    utvonal = konyvtar / f"tippmix_{ido.perc_kulcs(most)}.json"
    if isinstance(nyers, bytes):
        utvonal.write_bytes(nyers)
    else:
        utvonal.write_text(nyers, encoding="utf-8")
    log.debug("nyers_valasz_mentve", utvonal=str(utvonal))
    return utvonal


def kezi_tartalek_olvas(most: datetime | None = None) -> list[NyersEsemeny] | None:
    """Kézi tartalék: data/manual/tippmix_YYYYMMDD.csv olvasása.

    A program automatikusan ezt használja, ha a scraping elbukott, de a kézi
    fájl mai dátummal létezik.

    Returns:
        None, ha nincs mai kézi fájl.
    """
    beall = beallitasok()
    most = most or ido.most_utc()
    utvonal = gyoker_ut(beall.gyujtes.kezi_tartalek_konyvtar) / f"tippmix_{ido.nap_kulcs(most)}.csv"
    if not utvonal.exists():
        return None

    sorok: list[NyersEsemeny] = []
    with utvonal.open(encoding="utf-8", newline="") as fajl:
        for sor in csv.DictReader(fajl):
            sorok.append(
                NyersEsemeny(
                    tippmix_event_id=sor["tippmix_event_id"],
                    sport=sor["sport"],
                    bajnoksag=sor["bajnoksag"],
                    hazai_nev=sor["hazai_nev"],
                    vendeg_nev=sor["vendeg_nev"],
                    kezdes_utc=ido.utc_ra(datetime.fromisoformat(sor["kezdes_utc"])),
                    piac_nev=sor["piac_nev"],
                    kimenetel_nev=sor["kimenetel_nev"],
                    odds=float(sor["odds"]),
                    kotestiltas=sor.get("kotestiltas", "").strip().lower() in {"1", "igen", "true"},
                )
            )
    log.info("kezi_tartalek_hasznalva", utvonal=str(utvonal), sor_db=len(sorok))
    return sorok


def zaro_odds_lekeres(event_idk: list[str]) -> dict[str, float]:
    """Záró szorzók lekérése a CLV-hez (spec 12. lépés).

    Külön napi futás, kezdés előtt kb. 5 perccel.
    """
    raise NotImplementedError("1. lépés — a Fázis 5-ben készül el")
