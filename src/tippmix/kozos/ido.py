"""Időkezelés.

SZABÁLY: minden időbélyeg UTC-ben tárolódik és UTC-ben utazik a kódban.
A CET/CEST (Europe/Budapest) konverzió KIZÁRÓLAG a megjelenítésnél történik
— az e-mailben és a naplóban.

Miért: a magyar nyári időszámítás miatt a 09:00 CET télen 08:00 UTC, nyáron
07:00 UTC. Ha helyi időt tárolnánk, évente kétszer elcsúszna minden.

A GitHub Actions cron csak UTC-t ismer, ezért minden workflow KÉT cron-
bejegyzést tartalmaz (téli és nyári), és a `helyes_idoben_fut()` ellenőrzi,
hogy az aktuális futás a kívánt CET-időpontban van-e. Ami nem, az kilép.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

BUDAPEST = ZoneInfo("Europe/Budapest")


def most_utc() -> datetime:
    """A jelenlegi idő UTC-ben, időzóna-tudatosan."""
    return datetime.now(UTC)


def utc_ra(dt: datetime) -> datetime:
    """Bármilyen időzóna-tudatos vagy naiv datetime → UTC.

    A naiv datetime-ot UTC-nek tekintjük. Ez szándékos: a rendszerben nem
    keletkezhet naiv helyi idő, és ha mégis, az hiba — de csendben rossz
    eredmény helyett legalább következetes.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def megjelenites(dt: datetime, formatum: str = "%Y-%m-%d %H:%M") -> str:
    """UTC időbélyeg → magyar helyi idő, megjelenítésre.

    Ez az EGYETLEN hely, ahol helyi idő keletkezik.
    """
    return utc_ra(dt).astimezone(BUDAPEST).strftime(formatum)


def cet_ido_ma_utc_ban(cet_ido: str, alap: datetime | None = None) -> datetime:
    """Egy "HH:MM" CET-időpont a mai napon, UTC-ben kifejezve.

    Példa: cet_ido_ma_utc_ban("09:00") nyáron 07:00 UTC-t ad, télen 08:00-t.

    Args:
        cet_ido: "HH:MM" alakú helyi (Europe/Budapest) időpont
        alap: melyik napra (alapértelmezés: ma). UTC-ben értendő.
    """
    alap = alap or most_utc()
    ora, perc = (int(x) for x in cet_ido.split(":"))
    helyi_nap = utc_ra(alap).astimezone(BUDAPEST).date()
    helyi = datetime(helyi_nap.year, helyi_nap.month, helyi_nap.day, ora, perc, tzinfo=BUDAPEST)
    return helyi.astimezone(UTC)


def helyes_idoben_fut(cel_cet_ido: str, tures_perc: int, most: datetime | None = None) -> bool:
    """Igaz, ha a jelenlegi idő a cél CET-időpont tűréshatárán belül van.

    A GitHub Actions cron UTC-ben fut, és a DST miatt két bejegyzés van
    workflow-nként. A workflow mindkettőre elindul, de csak az fut végig,
    amelyik a helyes CET-időben van. A másik itt kilép.

    Args:
        cel_cet_ido: "09:00" vagy "18:00"
        tures_perc: ennyi percet fogadunk el eltérésként (az Actions cron
            nagy terhelésnél 15+ percet késhet)
        most: teszteléshez felülírható
    """
    most = most or most_utc()
    cel = cet_ido_ma_utc_ban(cel_cet_ido, most)
    elteres = abs((most - cel).total_seconds()) / 60
    return elteres <= tures_perc


def futas_tipusa(beall_delelott: str, beall_este: str, most: datetime | None = None) -> str:
    """Melyik napi futásban vagyunk: "delelott" vagy "este".

    A döntés a CET-idő alapján történik: a két konfigurált időpont közül a
    közelebbi nyer. Ez határozza meg a `min_edge` küszöböt (spec 8. lépés).
    """
    most = most or most_utc()
    delelott = cet_ido_ma_utc_ban(beall_delelott, most)
    este = cet_ido_ma_utc_ban(beall_este, most)
    tav_de = abs((most - delelott).total_seconds())
    tav_este = abs((most - este).total_seconds())
    return "delelott" if tav_de <= tav_este else "este"


def eleg_ido_kezdesig(kezdes_utc: datetime, min_perc: int, most: datetime | None = None) -> bool:
    """Igaz, ha a meccs kezdéséig legalább `min_perc` van hátra.

    Spec 1. lépés 2. pontja és a döntési fa 3. pontja (KESO) használja.
    """
    most = most or most_utc()
    return utc_ra(kezdes_utc) - most >= timedelta(minutes=min_perc)


def nap_kulcs(dt: datetime | None = None) -> str:
    """A nap azonosítója fájlnevekhez: "20260917" (UTC szerint)."""
    return utc_ra(dt or most_utc()).strftime("%Y%m%d")


def perc_kulcs(dt: datetime | None = None) -> str:
    """Perc-pontos azonosító fájlnevekhez: "20260917_1830" (UTC szerint).

    Spec 1. lépés 5. pont: data/raw/tippmix_YYYYMMDD_HHMM.json
    """
    return utc_ra(dt or most_utc()).strftime("%Y%m%d_%H%M")
