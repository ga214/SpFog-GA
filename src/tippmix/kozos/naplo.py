"""Strukturált naplózás.

Minden pipeline-lépés ezen keresztül naplóz. Két kimeneti mód:

  - `konzol`: ember által olvasható, színes, fejlesztéshez
  - `json`: soronként egy JSON-objektum, GitHub Actionshez és géppel
            feldolgozható elemzéshez

A naplóbejegyzések mindig tartalmazzák a `futas_id`-t, hogy egy futás
összes sora utólag összefűzhető legyen.
"""

from __future__ import annotations

import logging
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

# A futás egyedi azonosítója. Minden naplósorba bekerül, és ez kerül az
# adatbázis `futas_id` mezőjébe is (spec 12. lépés).
_FUTAS_ID: str | None = None


def futas_id() -> str:
    """A jelenlegi futás azonosítója. Első híváskor generálódik."""
    global _FUTAS_ID
    if _FUTAS_ID is None:
        idopont = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        _FUTAS_ID = f"{idopont}-{uuid.uuid4().hex[:8]}"
    return _FUTAS_ID


def beallit(
    szint: str = "INFO",
    formatum: str = "konzol",
    fajl_konyvtar: str | Path | None = None,
) -> None:
    """Naplózás inicializálása. A program indulásakor egyszer kell hívni.

    Args:
        szint: DEBUG | INFO | WARNING | ERROR
        formatum: "konzol" (ember) vagy "json" (gép, GitHub Actions)
        fajl_konyvtar: ha meg van adva, ide is ír egy napi naplófájlt
    """
    szint_szam = getattr(logging, szint.upper(), logging.INFO)

    kezelok: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if fajl_konyvtar is not None:
        konyvtar = Path(fajl_konyvtar)
        konyvtar.mkdir(parents=True, exist_ok=True)
        nap = datetime.now(UTC).strftime("%Y%m%d")
        kezelok.append(logging.FileHandler(konyvtar / f"tippmix_{nap}.log", encoding="utf-8"))

    logging.basicConfig(format="%(message)s", level=szint_szam, handlers=kezelok, force=True)

    kozos_feldolgozok: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _futas_id_hozzaad,
    ]

    if formatum == "json":
        feldolgozok = [*kozos_feldolgozok, structlog.processors.JSONRenderer()]
    else:
        feldolgozok = [
            *kozos_feldolgozok,
            structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty()),
        ]

    structlog.configure(
        processors=feldolgozok,
        wrapper_class=structlog.make_filtering_bound_logger(szint_szam),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _futas_id_hozzaad(_logger: Any, _nev: str, esemeny: dict[str, Any]) -> dict[str, Any]:
    """Minden naplósorba beteszi a futás azonosítóját."""
    esemeny["futas_id"] = futas_id()
    return esemeny


def naplo(nev: str) -> structlog.stdlib.BoundLogger:
    """Naplózó egy modulhoz.

    Használat:

        from tippmix.kozos.naplo import naplo
        log = naplo(__name__)
        log.info("esemenyek_letoltve", darab=42, sport="foci")
    """
    return structlog.get_logger(nev)


def lepes_kezdet(log: structlog.stdlib.BoundLogger, szam: int, nev: str) -> None:
    """Pipeline-lépés kezdetének naplózása, egységes formában."""
    log.info("lepes_kezdet", lepes_szam=szam, lepes_nev=nev)


def lepes_veg(
    log: structlog.stdlib.BoundLogger,
    szam: int,
    nev: str,
    **eredmeny: Any,
) -> None:
    """Pipeline-lépés végének naplózása, az eredmény összefoglalójával."""
    log.info("lepes_veg", lepes_szam=szam, lepes_nev=nev, **eredmeny)
