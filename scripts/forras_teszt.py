"""Külső sportadat-források elérhetőségének tesztje.

Azért van, mert a fejlesztő céges hálózatáról néhány forrás nem érhető el
(a proxy 502-t ad vagy timeoutol). Ez a szkript eldönti, hogy a forrás
halott-e, vagy csak a helyi hálózat blokkolja.

Futtatás: a `forras-teszt.yml` workflow, vagy lokálisan is — ezek NYILVÁNOS
sportadat-források, nem szerencsejáték-platform, tehát a D-011 megkötés
rájuk nem vonatkozik.
"""

from __future__ import annotations

import traceback


def _probal(nev: str, fuggveny) -> bool:
    try:
        eredmeny = fuggveny()
    except Exception:
        print(f"HIBA  {nev}")
        print("      " + traceback.format_exc().strip().replace("\n", "\n      ")[-600:])
        return False
    print(f"OK    {nev}: {eredmeny}")
    return True


def _clubelo() -> str:
    import soccerdata as sd

    df = sd.ClubElo().read_by_date("2024-08-16")
    return f"{len(df)} csapat, oszlopok={list(df.columns)[:6]}"


def _understat() -> str:
    from understatapi import UnderstatClient

    with UnderstatClient() as kliens:
        meccsek = kliens.league(league="EPL").get_match_data(season="2023")
    return f"{len(meccsek)} meccs, elso xG={meccsek[0]['xG']}"


def _footballdata() -> str:
    import soccerdata as sd

    df = sd.MatchHistory(leagues="ENG-Premier League", seasons="2324").read_games()
    return f"{len(df)} meccs"


def main() -> int:
    eredmenyek = [
        _probal("football-data.co.uk (soccerdata)", _footballdata),
        _probal("Understat (understatapi)", _understat),
        _probal("ClubElo (soccerdata)", _clubelo),
    ]
    print(f"\n{sum(eredmenyek)}/{len(eredmenyek)} forrás elérhető.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
