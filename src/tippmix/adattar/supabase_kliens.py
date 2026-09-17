"""Supabase kliens — a projekt egyetlen adatbázis-kapcsolata.

BIZTONSÁG: ez a modul a SERVICE ROLE kulcsot használja, ami MEGKERÜLI a
row level security-t. Ez csak szerveroldalon (a pipeline-ban) és GitHub
Secretsben élhet. Frontendbe SOHA nem kerülhet — oda az anon kulcs való,
RLS-policy-kkal.

A kapcsolat lusta: az első használatkor épül fel, és a folyamat élettartamáig
újrahasznosul.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from tippmix.kozos.hibak import AdattarHiba
from tippmix.kozos.naplo import naplo
from tippmix.kozos.titkok import maszkol, supabase_titkok

log = naplo(__name__)


@lru_cache(maxsize=1)
def kliens() -> Client:
    """A megosztott Supabase-kliens. Első híváskor épül fel.

    Raises:
        KonfiguracioHiba: hiányzó SUPABASE_URL vagy SUPABASE_SERVICE_ROLE_KEY
        AdattarHiba: a kliens létrehozása sikertelen
    """
    titkok = supabase_titkok()
    log.debug(
        "supabase_kliens_epites",
        url=titkok.url,
        kulcs=maszkol(titkok.service_role_key),
    )
    try:
        return create_client(titkok.url, titkok.service_role_key)
    except Exception as e:
        raise AdattarHiba(f"Nem sikerült a Supabase-klienst létrehozni: {e}") from e


def kapcsolat_teszt() -> dict[str, Any]:
    """Ellenőrzi, hogy a kapcsolat él és a séma a helyén van.

    Returns:
        Diagnosztikai szótár: mely táblák érhetők el, hány sorral.

    Raises:
        AdattarHiba: a kapcsolat nem él
    """
    varhato_tablak = [
        "futasok",
        "tippek",
        "kombinaciok",
        "kiesesek",
        "ismeretlen_csapatok",
        "bankroll_naplo",
        "modell_illesztesek",
    ]

    c = kliens()
    eredmeny: dict[str, Any] = {"kapcsolat": "ok", "tablak": {}}

    for tabla in varhato_tablak:
        try:
            valasz = c.table(tabla).select("*", count="exact").limit(0).execute()
            eredmeny["tablak"][tabla] = {"allapot": "ok", "sorok": valasz.count}
        except Exception as e:
            eredmeny["tablak"][tabla] = {"allapot": "hiba", "uzenet": str(e)[:200]}

    hibas = [t for t, a in eredmeny["tablak"].items() if a["allapot"] != "ok"]
    eredmeny["hianyzo_tablak"] = hibas
    eredmeny["sema_kesz"] = not hibas

    return eredmeny


def beszur(tabla: str, sorok: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sorok beszúrása. Üres lista esetén nem hív hálózatot.

    Raises:
        AdattarHiba: a beszúrás sikertelen
    """
    if not sorok:
        return []
    try:
        valasz = kliens().table(tabla).insert(sorok).execute()
    except Exception as e:
        raise AdattarHiba(f"Beszúrás sikertelen ({tabla}, {len(sorok)} sor): {e}") from e
    log.debug("beszuras", tabla=tabla, darab=len(sorok))
    return valasz.data or []


def felulir_vagy_beszur(
    tabla: str, sorok: list[dict[str, Any]], utkozes_mezok: str
) -> list[dict[str, Any]]:
    """Upsert: beszúr, vagy ütközés esetén frissít.

    Args:
        utkozes_mezok: vesszővel elválasztott oszlopnevek, pl. "tippmix_nev,sport"
    """
    if not sorok:
        return []
    try:
        valasz = kliens().table(tabla).upsert(sorok, on_conflict=utkozes_mezok).execute()
    except Exception as e:
        raise AdattarHiba(f"Upsert sikertelen ({tabla}, {len(sorok)} sor): {e}") from e
    log.debug("upsert", tabla=tabla, darab=len(sorok))
    return valasz.data or []
