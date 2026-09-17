"""1. lépés — Esemény-begyűjtés a Tippmix Pro-ról.

Ez a lista a rendszer UNIVERZUMA: ami itt nincs benne, arra soha nem kapsz
javaslatot.

Forrás: `sports2.tippmixpro.hu` JSON-végpont. A pontos útvonalat a Fázis 0
empirikus tesztje deríti ki (böngésző hálózati fül). Lásd
docs/OPEN_QUESTIONS.md.

Döntések (spec 1. lépés):
  1. Hiba vagy üres válasz → 3 újrapróbálkozás 30 mp szünettel. Ha mind
     elbukik: nincs futás, hibalevél, kilépés. NEM találgat, NEM használ
     tegnapi szorzót.
  2. Csak a legalább `min_perc_kezdésig` perc múlva kezdődő események.
  3. Csak a config/ligak.yaml-ban engedélyezett bajnokságok.
  4. Csak a támogatott piactípusok.
  5. A nyers válasz elmentésre kerül data/raw/tippmix_YYYYMMDD_HHMM.json néven.

ToS: alacsony frekvenciájú, tiszteletteljes lekérés. A robots.txt tényleges
ellenőrzése a Fázis 0 feladata.

VÁZ: a függvények szignatúrája végleges, a törzs még nincs megírva.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from tippmix.kozos.naplo import naplo
from tippmix.kozos.tipusok import NyersEsemeny

log = naplo(__name__)


def letolt(most: datetime | None = None) -> list[NyersEsemeny]:
    """A Tippmix Pro teljes kínálatának letöltése és szűrése.

    Raises:
        AdatgyujtesHiba: 3 sikertelen próbálkozás után
    """
    raise NotImplementedError("1. lépés — a Fázis 0/4-ben készül el")


def nyers_valasz_mentes(nyers: bytes | str, most: datetime | None = None) -> Path:
    """A nyers választ menti data/raw/tippmix_YYYYMMDD_HHMM.json néven.

    Ez kell a hibakereséshez és ahhoz, hogy visszamenőleg ellenőrizni tudd,
    mit láttunk akkor.
    """
    raise NotImplementedError("1. lépés — a Fázis 0/4-ben készül el")


def kezi_tartalek_olvas(most: datetime | None = None) -> list[NyersEsemeny] | None:
    """Kézi tartalék: data/manual/tippmix_YYYYMMDD.csv olvasása.

    A program automatikusan ezt használja, ha a scraping elbukott, de a kézi
    fájl mai dátummal létezik.

    Returns:
        None, ha nincs mai kézi fájl.
    """
    raise NotImplementedError("1. lépés — a Fázis 0/4-ben készül el")


def zaro_odds_lekeres(event_idk: list[str]) -> dict[str, float]:
    """Záró szorzók lekérése a CLV-hez (spec 12. lépés).

    Külön napi futás, kezdés előtt kb. 5 perccel.
    """
    raise NotImplementedError("1. lépés — a Fázis 5-ben készül el")
