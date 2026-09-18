"""Fázis 0 — a Tippmix Pro WebSocket-forgalmának felderítése Playwright-tal.

FIGYELEM — CSAK GITHUB ACTIONSBEN FUTTATHATÓ (lásd CLAUDE.md és D-011).


Megnyitja a sports2.tippmixpro.hu oldalt egy valódi böngészőmotorban, és
minden WebSocket-üzenetet fájlba ír. A cél a `wss://sportsapi.tippmixpro.hu/v2`
protokolljának megismerése: milyen subscribe-üzenet megy ki, milyen formában
jön vissza az odds.

Ez felderítő eszköz, nem a pipeline része — ezért a scripts/ könyvtárban van.

Használat:
    uv run playwright install chromium     # egyszer, a böngészőmotor letöltése
    uv run python scripts/ws_felderites.py
    uv run python scripts/ws_felderites.py --fejjel --varakozas 60

Kimenet (data/raw/ws_felderites_<időbélyeg>/):
    uzenetek.jsonl   minden WS-keret egy-egy JSON soron
    osszefoglalo.txt  emberi olvasásra szánt összegzés
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))
import _csak_actionsben

CEL_URL = "https://sports2.tippmixpro.hu/hu"
KIMENET_GYOKER = Path("data/raw")

# A kiírt üzenettörzs maximális hossza. A teljes törzs mindig a JSONL-be kerül;
# ez csak a konzolra írt előnézetet vágja le.
ELONEZET_HOSSZ = 200


def _most_belyeg() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


async def felderit(
    url: str, varakozas_mp: float, fejjel: bool, kimenet_konyvtar: Path, csatorna: str
) -> dict[str, int]:
    kimenet_konyvtar.mkdir(parents=True, exist_ok=True)
    uzenetek_fajl = kimenet_konyvtar / "uzenetek.jsonl"

    szamlalo = {"ws": 0, "kuldott": 0, "kapott": 0, "hiba": 0}
    ws_urlek: list[str] = []

    with uzenetek_fajl.open("w", encoding="utf-8") as kimenet:

        def ir(rekord: dict) -> None:
            rekord["ido"] = datetime.now(UTC).isoformat()
            kimenet.write(json.dumps(rekord, ensure_ascii=False) + "\n")
            kimenet.flush()

        async with async_playwright() as p:
            inditas: dict = {"headless": not fejjel}
            if csatorna:
                inditas["channel"] = csatorna
            bongeszo = await p.chromium.launch(**inditas)
            kontextus = await bongeszo.new_context(locale="hu-HU")
            oldal = await kontextus.new_page()

            def ws_kezelo(ws) -> None:
                szamlalo["ws"] += 1
                ws_urlek.append(ws.url)
                print(f"[WS megnyitva] {ws.url}")
                ir({"esemeny": "megnyitva", "ws_url": ws.url})

                def kuldott(adat) -> None:
                    szamlalo["kuldott"] += 1
                    torzs = adat if isinstance(adat, str) else repr(adat)
                    print(f"  → küldött: {torzs[:ELONEZET_HOSSZ]}")
                    ir({"esemeny": "kuldott", "ws_url": ws.url, "torzs": torzs})

                def kapott(adat) -> None:
                    szamlalo["kapott"] += 1
                    torzs = adat if isinstance(adat, str) else repr(adat)
                    if szamlalo["kapott"] <= 20:
                        print(f"  ← kapott: {torzs[:ELONEZET_HOSSZ]}")
                    ir({"esemeny": "kapott", "ws_url": ws.url, "torzs": torzs})

                ws.on("framesent", kuldott)
                ws.on("framereceived", kapott)
                ws.on("socketerror", lambda h: ir({"esemeny": "hiba", "ws_url": ws.url, "hiba": h}))
                ws.on("close", lambda _: ir({"esemeny": "lezarva", "ws_url": ws.url}))

            oldal.on("websocket", ws_kezelo)

            print(f"Megnyitás: {url}")
            try:
                await oldal.goto(url, wait_until="domcontentloaded", timeout=60_000)
            except Exception as hiba:
                szamlalo["hiba"] += 1
                print(f"HIBA az oldal megnyitásakor: {hiba}")
                ir({"esemeny": "oldal_hiba", "hiba": str(hiba)})

            print(f"Figyelés {varakozas_mp:.0f} másodpercig…")
            await asyncio.sleep(varakozas_mp)

            cim = await oldal.title()
            ir({"esemeny": "oldal_cim", "cim": cim})
            print(f"Oldal címe: {cim}")

            await bongeszo.close()

    osszefoglalo = [
        f"Cél URL:          {url}",
        f"Figyelés:         {varakozas_mp:.0f} mp",
        f"WS-kapcsolatok:   {szamlalo['ws']}",
        f"Küldött keretek:  {szamlalo['kuldott']}",
        f"Kapott keretek:   {szamlalo['kapott']}",
        "",
        "WS-URL-ek:",
        *(f"  {u}" for u in dict.fromkeys(ws_urlek)),
    ]
    (kimenet_konyvtar / "osszefoglalo.txt").write_text(
        "\n".join(osszefoglalo) + "\n", encoding="utf-8"
    )
    print("\n" + "\n".join(osszefoglalo))
    return szamlalo


def main() -> None:
    ertelmezo = argparse.ArgumentParser(description=__doc__)
    ertelmezo.add_argument("--url", default=CEL_URL)
    ertelmezo.add_argument("--varakozas", type=float, default=45.0, help="figyelés hossza mp-ben")
    ertelmezo.add_argument("--fejjel", action="store_true", help="látható böngészőablak")
    ertelmezo.add_argument(
        "--csatorna",
        default="chrome",
        help="böngésző-csatorna: chrome, msedge, vagy üres a Playwright saját Chromiumjához",
    )
    argumentumok = ertelmezo.parse_args()

    kimenet_konyvtar = KIMENET_GYOKER / f"ws_felderites_{_most_belyeg()}"
    szamlalo = asyncio.run(
        felderit(
            argumentumok.url,
            argumentumok.varakozas,
            argumentumok.fejjel,
            kimenet_konyvtar,
            argumentumok.csatorna,
        )
    )
    print(f"\nKimenet: {kimenet_konyvtar}")
    if szamlalo["ws"] == 0:
        print("\nNem jött létre WebSocket-kapcsolat — vagy blokkolt a hálózat,")
        print("vagy hosszabb várakozás kell, vagy az oldal más útvonalon tölt.")


if __name__ == "__main__":
    _csak_actionsben.ellenoriz()
    main()
