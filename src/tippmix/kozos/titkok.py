"""Titkok betöltése — API-kulcsok, jelszavak, tokenek.

BIZTONSÁGI SZABÁLYOK:

1. Titok SOHA nem kerül YAML-be, kódba, commitba vagy naplóba.
2. Lokálisan a `.env` fájlból jön (ami a `.gitignore`-ban van).
3. GitHub Actionsben környezeti változóból jön, GitHub Secretsből injektálva.
4. A `.env.example` csak a kulcsok NEVÉT tartalmazza, értéket soha.
5. A repó PUBLIKUS — egy véletlenül commitolt kulcs azonnal kompromittált.

Ez a modul a titkokat kizárólag környezeti változóból olvassa, és soha nem
írja ki őket. A `maszkol()` függvény naplózáshoz való.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from tippmix.kozos.config import PROJEKT_GYOKER
from tippmix.kozos.hibak import KonfiguracioHiba

_BETOLTVE = False


def _betolt_env() -> None:
    """A .env betöltése, ha létezik. Actionsben nincs .env, ott a környezet ad mindent."""
    global _BETOLTVE
    if _BETOLTVE:
        return
    env_ut = PROJEKT_GYOKER / ".env"
    if env_ut.exists():
        load_dotenv(env_ut, override=False)
    _BETOLTVE = True


def titok(nev: str, kotelezo: bool = True, alapertelmezett: str | None = None) -> str | None:
    """Egy titok értéke környezeti változóból.

    Args:
        nev: a környezeti változó neve (pl. "SUPABASE_SERVICE_ROLE_KEY")
        kotelezo: ha True és hiányzik, KonfiguracioHiba
        alapertelmezett: ha nem kötelező és hiányzik, ez jön vissza

    Raises:
        KonfiguracioHiba: kötelező titok hiányzik. A hibaüzenet a titok
            NEVÉT tartalmazza, az ÉRTÉKÉT soha.
    """
    _betolt_env()
    ertek = os.environ.get(nev)
    if ertek is None or ertek.strip() == "":
        if kotelezo:
            raise KonfiguracioHiba(
                f"Hiányzó kötelező titok: {nev}\n"
                f"  Lokálisan: tedd be a .env fájlba (lásd .env.example)\n"
                f"  GitHub Actionsben: Settings → Secrets and variables → Actions"
            )
        return alapertelmezett
    return ertek


def maszkol(ertek: str | None) -> str:
    """Titok naplózható alakja: csak a hossz és az első 3 karakter.

    Naplóba SOHA ne kerüljön nyers titok. Használat:

        log.info("supabase_kapcsolat", kulcs=maszkol(kulcs))
        → kulcs="eyJ…(216 karakter)"
    """
    if ertek is None:
        return "<nincs>"
    if len(ertek) <= 6:
        return f"…({len(ertek)} karakter)"
    return f"{ertek[:3]}…({len(ertek)} karakter)"


@dataclass(frozen=True)
class SupabaseTitkok:
    url: str
    service_role_key: str


@dataclass(frozen=True)
class EmailTitkok:
    felhasznalo: str
    app_jelszo: str
    cimzett: str


def supabase_titkok() -> SupabaseTitkok:
    """Supabase kapcsolati adatok.

    FIGYELEM: a service role kulcs MEGKERÜLI a row level security-t. Csak
    szerveroldalon (itt, a pipeline-ban) és GitHub Secretsben élhet. Ha
    valaha frontend kerül a projektbe, oda KIZÁRÓLAG az anon kulcs mehet,
    RLS mellett.
    """
    return SupabaseTitkok(
        url=titok("SUPABASE_URL"),  # type: ignore[arg-type]
        service_role_key=titok("SUPABASE_SERVICE_ROLE_KEY"),  # type: ignore[arg-type]
    )


def email_titkok() -> EmailTitkok:
    """Gmail SMTP adatok.

    Az app_jelszo NEM a Google-fiók jelszava, hanem külön generált
    app-jelszó (2FA mellett kötelező). Lásd docs/SECRETS.md.
    """
    return EmailTitkok(
        felhasznalo=titok("EMAIL_FELHASZNALO"),  # type: ignore[arg-type]
        app_jelszo=titok("EMAIL_APP_JELSZO"),  # type: ignore[arg-type]
        cimzett=titok("EMAIL_CIMZETT"),  # type: ignore[arg-type]
    )


def env_fajl_letezik() -> bool:
    """Van-e .env fájl. Diagnosztikához."""
    return (PROJEKT_GYOKER / ".env").exists()


def env_fajl_utvonal() -> Path:
    return PROJEKT_GYOKER / ".env"
