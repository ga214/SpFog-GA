"""Védőkorlát: a Tippmixet hívó szkriptek csak CI-ben futhatnak.

A fejlesztő munkahelyi gépet használ, ahol az IT-szabályzat tiltja a
tippmixpro.hu elérését. A nyers WebSocket átmegy a céges proxyn, ezért egy
figyelmeztető komment önmagában nem elég — ez a modul ténylegesen megállítja
a futást.

Lásd CLAUDE.md „A Tippmix felé SOHA nem indul forgalom a fejlesztő gépéről"
és docs/DECISIONS.md D-011.
"""

from __future__ import annotations

import os
import sys

UZENET = """
MEGÁLLÍTVA — ez a szkript a Tippmixet hívja, és nem CI-ben fut.

A Tippmix felé irányuló forgalom soha nem indulhat a fejlesztő céges gépéről:
a munkahelyi IT-szabályzat tiltja a tippmixpro.hu elérését, és ennek
munkajogi következménye lehet.

Futtasd GitHub Actionsben:

    gh workflow run gyujtes-proba.yml
    gh run list --workflow=gyujtes-proba.yml --limit 1
    gh run download <run-id> -n gyujtes-proba

Ha tényleg lokálisan akarod futtatni (NEM ajánlott, és a felhasználó
kifejezett kérése nélkül soha), állítsd be: TIPPMIX_ENGEDEM_A_LOKALIS_HIVAST=1
"""


def ellenoriz() -> None:
    """Kilép, ha nem CI-ben futunk és nincs kifejezett felülbírálás."""
    if os.environ.get("CI") == "true":
        return
    if os.environ.get("TIPPMIX_ENGEDEM_A_LOKALIS_HIVAST") == "1":
        print("FIGYELEM: lokális Tippmix-hívás kifejezett felülbírálással.", file=sys.stderr)
        return
    print(UZENET, file=sys.stderr)
    raise SystemExit(2)
