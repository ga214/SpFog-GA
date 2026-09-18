"""Fázis 0 verifikáció — megy-e a WAMP böngésző nélkül, sima websockets-szel?

FIGYELEM — CSAK GITHUB ACTIONSBEN FUTTATHATÓ.
A Tippmix felé irányuló forgalom soha nem indulhat a fejlesztő céges gépéről,
mert az IT-szabályzat tiltja a tippmixpro.hu elérését. Lásd CLAUDE.md
„A Tippmix felé SOHA nem indul forgalom a fejlesztő gépéről" és
docs/DECISIONS.md D-011.

Ez a szkript a felderítés dokumentációja: bizonyítja, hogy a WAMP-kézfogás
autentikáció nélküli, és hogy nem kell Playwright. Ha újra kell futtatni,
tedd Actions-workflow-ba (lásd gyujtes-proba.yml mintájára).
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import websockets

sys.path.insert(0, str(Path(__file__).parent))
import _csak_actionsben

WS_URL = "wss://sportsapi.tippmixpro.hu/v2"
REALM = "www.tippmixpro.hu"
ORIGIN = "https://sports2.tippmixpro.hu"

# WAMP üzenettípusok (wamp-proto.org)
HELLO, WELCOME, ABORT, CHALLENGE, CALL, RESULT, ERROR = 1, 2, 3, 4, 48, 50, 8

# Az eljárás neve fix; a kért adat útvonala a `topic` kwargban megy — NEM az
# eljárásnév helyén. Ezt a rögzített böngésző-forgalomból tudjuk.
ELJARAS = "/sports#initialDump"

# Sportágfa élő nélkül — ez a legkisebb hasznos hívás a verifikációhoz.
PROBA_UTVONAL = "/sports/2901/hu/disciplines/NOT_LIVE/NOT_VIRTUAL/NOT_SIMULATED"

HELLO_UZENET = [
    HELLO,
    REALM,
    {
        "agent": "Wampy.js v6.2.2",
        "roles": {
            "publisher": {},
            "subscriber": {},
            "caller": {"features": {"progressive_call_results": True}},
            "callee": {},
        },
        "authmethods": ["wampcra"],
        "authid": "webapi-wampy",
    },
]


async def proba() -> int:
    print(f"Kapcsolódás: {WS_URL}")
    async with websockets.connect(
        WS_URL,
        subprotocols=["wamp.2.json"],
        origin=ORIGIN,
        user_agent_header="Mozilla/5.0 (Windows NT 10.0; Win64; x64) TippmixTipprendszer/0.1",
        open_timeout=30,
    ) as ws:
        print(f"WS kapcsolat él. Alprotokoll: {ws.subprotocol}")

        await ws.send(json.dumps(HELLO_UZENET))
        valasz = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
        print(f"HELLO válasz típusa: {valasz[0]}")

        if valasz[0] == CHALLENGE:
            print("CHALLENGE jött — a szerver mégis autentikációt kér.")
            print(json.dumps(valasz, ensure_ascii=False)[:400])
            return 2
        if valasz[0] == ABORT:
            print("ABORT — a szerver elutasította a kapcsolatot.")
            print(json.dumps(valasz, ensure_ascii=False)[:400])
            return 3
        if valasz[0] != WELCOME:
            print(f"Váratlan válasz: {json.dumps(valasz, ensure_ascii=False)[:400]}")
            return 4

        print(f"WELCOME — sessionId={valasz[1]}, autentikáció nélkül.")

        await ws.send(json.dumps([CALL, 1, {}, ELJARAS, [], {"topic": PROBA_UTVONAL}]))
        while True:
            uzenet = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
            if uzenet[0] == ERROR:
                print(f"ERROR a hívásra: {json.dumps(uzenet, ensure_ascii=False)[:400]}")
                return 5
            if uzenet[0] == RESULT and uzenet[1] == 1:
                break

        rekordok = (uzenet[-1] if isinstance(uzenet[-1], dict) else {}).get("records", [])
        print(f"RESULT megérkezett: {len(rekordok)} rekord.")
        for r in rekordok[:5]:
            print(f"  {r.get('_type')}: {r.get('name')} (események: {r.get('numberOfEvents')})")

        if not rekordok:
            print("A válasz üres — a hívás lement, de nincs adat.")
            return 6

        print("\nSIKER: a WAMP böngésző nélkül is működik. Nem kell Playwright.")
        return 0


if __name__ == "__main__":
    _csak_actionsben.ellenoriz()
    try:
        sys.exit(asyncio.run(proba()))
    except Exception as hiba:
        print(f"HIBA: {type(hiba).__name__}: {hiba}")
        sys.exit(1)
