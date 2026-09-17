"""Időkezelés tesztjei.

A nyári időszámítás a leggyakoribb csendes hibaforrás: a 09:00 CET télen
08:00 UTC, nyáron 07:00 UTC. Ha ezt elrontjuk, a futás évente kétszer
elcsúszik egy órát, és senki nem veszi észre.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tippmix.kozos import ido


def test_most_utc_idozona_tudatos() -> None:
    assert ido.most_utc().tzinfo is not None


def test_utc_ra_naiv_datetime() -> None:
    """A naiv datetime-ot UTC-nek tekintjük."""
    naiv = datetime(2026, 9, 17, 12, 0)
    assert ido.utc_ra(naiv).tzinfo == UTC


def test_cet_ido_nyari_idoszamitas() -> None:
    """Nyáron (CEST, UTC+2) a 09:00 CET = 07:00 UTC."""
    nyar = datetime(2026, 7, 15, 10, 0, tzinfo=UTC)
    eredmeny = ido.cet_ido_ma_utc_ban("09:00", nyar)
    assert eredmeny.hour == 7
    assert eredmeny.minute == 0


def test_cet_ido_teli_idoszamitas() -> None:
    """Télen (CET, UTC+1) a 09:00 CET = 08:00 UTC."""
    tel = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)
    eredmeny = ido.cet_ido_ma_utc_ban("09:00", tel)
    assert eredmeny.hour == 8
    assert eredmeny.minute == 0


def test_esti_futas_nyaron_es_telen() -> None:
    """A 18:00 CET nyáron 16:00 UTC, télen 17:00 UTC."""
    nyar = datetime(2026, 7, 15, 16, 0, tzinfo=UTC)
    tel = datetime(2026, 1, 15, 17, 0, tzinfo=UTC)
    assert ido.cet_ido_ma_utc_ban("18:00", nyar).hour == 16
    assert ido.cet_ido_ma_utc_ban("18:00", tel).hour == 17


def test_helyes_idoben_fut_pontosan() -> None:
    """Nyáron a 07:00 UTC futás a 09:00 CET-nek felel meg."""
    most = datetime(2026, 7, 15, 7, 0, tzinfo=UTC)
    assert ido.helyes_idoben_fut("09:00", 75, most)


def test_helyes_idoben_fut_tureshataron_belul() -> None:
    """Az Actions cron 15+ percet késhet — ezt tolerálnunk kell."""
    most = datetime(2026, 7, 15, 7, 20, tzinfo=UTC)
    assert ido.helyes_idoben_fut("09:00", 75, most)


def test_helyes_idoben_fut_rossz_cron_kilep() -> None:
    """Nyáron a téli cron (08:00 UTC = 10:00 CEST) 60 perccel csúszik.

    75 perces tűréssel ez még belefér — ezért a valós védelem a workflow
    feltétele, nem csak ez. De a 2 órás eltérés már biztosan kiesik.
    """
    most = datetime(2026, 7, 15, 9, 30, tzinfo=UTC)  # 11:30 CEST
    assert not ido.helyes_idoben_fut("09:00", 75, most)


def test_futas_tipusa_delelott() -> None:
    most = datetime(2026, 7, 15, 7, 5, tzinfo=UTC)  # 09:05 CEST
    assert ido.futas_tipusa("09:00", "18:00", most) == "delelott"


def test_futas_tipusa_este() -> None:
    most = datetime(2026, 7, 15, 16, 5, tzinfo=UTC)  # 18:05 CEST
    assert ido.futas_tipusa("09:00", "18:00", most) == "este"


def test_eleg_ido_kezdesig() -> None:
    most = datetime(2026, 9, 17, 18, 0, tzinfo=UTC)
    kezdes = datetime(2026, 9, 17, 19, 0, tzinfo=UTC)  # 60 perc múlva
    assert ido.eleg_ido_kezdesig(kezdes, 45, most)


def test_nem_eleg_ido_kezdesig() -> None:
    """A spec 1. lépés 2. pontja: ami 45 percnél hamarabb kezdődik, kiesik."""
    most = datetime(2026, 9, 17, 18, 30, tzinfo=UTC)
    kezdes = datetime(2026, 9, 17, 19, 0, tzinfo=UTC)  # 30 perc múlva
    assert not ido.eleg_ido_kezdesig(kezdes, 45, most)


def test_megjelenites_helyi_ido() -> None:
    """Az EGYETLEN hely, ahol helyi idő keletkezik."""
    utc = datetime(2026, 7, 15, 17, 0, tzinfo=UTC)
    assert ido.megjelenites(utc, "%H:%M") == "19:00"  # CEST = UTC+2


def test_fajlnev_kulcsok() -> None:
    dt = datetime(2026, 9, 17, 18, 30, tzinfo=UTC)
    assert ido.nap_kulcs(dt) == "20260917"
    assert ido.perc_kulcs(dt) == "20260917_1830"


@pytest.mark.parametrize("cet_ido", ["09:00", "18:00"])
def test_oda_vissza_konzisztens(cet_ido: str) -> None:
    """A CET→UTC→CET oda-vissza konverzió ugyanazt adja."""
    most = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)
    utc = ido.cet_ido_ma_utc_ban(cet_ido, most)
    assert ido.megjelenites(utc, "%H:%M") == cet_ido
