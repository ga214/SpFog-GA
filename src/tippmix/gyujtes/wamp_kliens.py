"""WAMP v2 kliens a Tippmix Pro sportadat-végpontjához.

A platform szabványos [WAMP v2](https://wamp-proto.org/)-t beszél JSON
szerializációval, autentikáció nélkül: a HELLO-ra azonnal WELCOME jön,
CHALLENGE nélkül. Ezért nem kell böngésző (Playwright) és nem kell nehéz
WAMP-könyvtár sem — a protokollnak az a szelete, amit használunk, néhány
JSON-tömb.

Felderítés és a teljes protokoll-leírás: docs/OPEN_QUESTIONS.md NY-11.

Csak olvasásra használjuk: bejelentkezés nincs, fogadást nem adunk le.
"""

from __future__ import annotations

import asyncio
import json
from types import TracebackType
from typing import Any, Self

import websockets

from tippmix.kozos.config import Wamp
from tippmix.kozos.hibak import AdatgyujtesHiba
from tippmix.kozos.naplo import naplo

log = naplo(__name__)

# WAMP üzenettípus-kódok (wamp-proto.org, 6.1. szakasz)
HELLO = 1
WELCOME = 2
ABORT = 3
CHALLENGE = 4
ERROR = 8
CALL = 48
RESULT = 50


class WampKliens:
    """Egy WAMP-munkamenet a Tippmix sportadat-végpontjához.

    Kontextuskezelőként használandó:

        async with WampKliens(beallitasok.gyujtes) as kliens:
            rekordok = await kliens.lekerdez(topic)
    """

    def __init__(self, wamp: Wamp, user_agent: str, idokorlat_mp: int) -> None:
        self._wamp = wamp
        self._user_agent = user_agent
        self._idokorlat_mp = idokorlat_mp
        self._ws: Any = None
        self._kovetkezo_azonosito = 1

    async def __aenter__(self) -> Self:
        await self._kapcsolodas()
        return self

    async def __aexit__(
        self,
        tipus: type[BaseException] | None,
        ertek: BaseException | None,
        nyom: TracebackType | None,
    ) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    async def _kapcsolodas(self) -> None:
        w = self._wamp
        log.debug("wamp_kapcsolodas", url=w.url)
        self._ws = await websockets.connect(
            w.url,
            subprotocols=[w.alprotokoll],
            origin=w.origin,
            user_agent_header=self._user_agent,
            open_timeout=self._idokorlat_mp,
            max_size=w.max_keret_meret_mb * 1024 * 1024,
        )

        hello = [
            HELLO,
            w.realm,
            {
                "agent": self._user_agent,
                "roles": {"publisher": {}, "subscriber": {}, "caller": {}, "callee": {}},
                "authid": w.authid,
            },
        ]
        await self._ws.send(json.dumps(hello))
        valasz = await self._fogad()

        if valasz[0] == CHALLENGE:
            # A felderítéskor nem jött CHALLENGE, de az authmethods jelenléte
            # miatt elképzelhető, hogy a szerver egyes esetekben kér egyet.
            # Jelszavunk nincs (nem jelentkezünk be), így ez valódi akadály.
            raise AdatgyujtesHiba(
                "A Tippmix WAMP-végpont autentikációt kér (CHALLENGE), "
                "amire ennek a rendszernek nincs hitelesítő adata."
            )
        if valasz[0] != WELCOME:
            raise AdatgyujtesHiba(f"A WAMP-kézfogás elutasítva: {valasz!r}")

        log.debug("wamp_kapcsolat_kesz", session_id=valasz[1])

    async def _fogad(self) -> list[Any]:
        nyers = await asyncio.wait_for(self._ws.recv(), timeout=self._idokorlat_mp)
        return json.loads(nyers)

    async def lekerdez(self, topic: str) -> list[dict[str, Any]]:
        """Egy topic lekérdezése, a válasz rekordjainak visszaadásával.

        Raises:
            AdatgyujtesHiba: ha a szerver ERROR-t küld a hívásra.
        """
        if self._ws is None:
            raise AdatgyujtesHiba("A WAMP-kliens nincs csatlakoztatva.")

        azonosito = self._kovetkezo_azonosito
        self._kovetkezo_azonosito += 1

        await self._ws.send(
            json.dumps([CALL, azonosito, {}, self._wamp.eljaras, [], {"topic": topic}])
        )

        # A szerver közben más üzeneteket is küldhet (pl. feliratkozási
        # eseményeket), ezért a saját hívásazonosítónkra várunk.
        while True:
            uzenet = await self._fogad()
            if uzenet[0] == ERROR and len(uzenet) > 2 and uzenet[2] == azonosito:
                raise AdatgyujtesHiba(f"A Tippmix elutasította a lekérdezést ({topic}): {uzenet}")
            if uzenet[0] == ABORT:
                raise AdatgyujtesHiba(f"A Tippmix megszakította a munkamenetet: {uzenet}")
            if uzenet[0] == RESULT and uzenet[1] == azonosito:
                torzs = uzenet[-1] if isinstance(uzenet[-1], dict) else {}
                return torzs.get("records", [])


def rekordok_tipus_szerint(
    rekordok: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """A lapos rekordlistát `_type` szerint csoportosítja.

    A Tippmix normalizált rekordokat ad vissza (MATCH, MARKET, OUTCOME,
    MARKET_OUTCOME_RELATION, BETTING_OFFER), nem egymásba ágyazott JSON-t.
    """
    ki: dict[str, list[dict[str, Any]]] = {}
    for rekord in rekordok:
        ki.setdefault(str(rekord.get("_type")), []).append(rekord)
    return ki
