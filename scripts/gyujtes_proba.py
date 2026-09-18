"""Az 1. lépés kipróbálása — a GitHub Actions runneren, nem a fejlesztő gépén.

A `gyujtes-proba.yml` workflow futtatja. Csak olvas: nem küld e-mailt, nem ír
adatbázisba, nem igényel titkot.

Miért nem lokálisan: a fejlesztő munkahelyi gépén a céges szabályzat tiltja a
tippmixpro.hu elérését (docs/DECISIONS.md D-011).
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

from tippmix.gyujtes import tippmix_scraper

sys.path.insert(0, str(Path(__file__).parent))
import _csak_actionsben


def main() -> None:
    minta_sor = int(os.environ.get("MINTA_SOR", "25"))

    sorok = tippmix_scraper.letolt()

    esemenyek = {s.tippmix_event_id for s in sorok}
    print(f"\nÖSSZESEN {len(sorok)} odds-sor, {len(esemenyek)} esemény\n")

    print("Bajnokságonként:")
    for bajnoksag, db in Counter(s.bajnoksag for s in sorok).most_common():
        print(f"  {bajnoksag:28} {db:5} sor")

    print("\nPiaconként:")
    for piac, db in Counter(s.piac_nev for s in sorok).most_common():
        print(f"  {piac:36} {db:5} sor")

    print(f"\nElső {minta_sor} sor:")
    for s in sorok[:minta_sor]:
        print(
            f"  {s.bajnoksag[:18]:18} | {s.hazai_nev[:18]:18} - {s.vendeg_nev[:18]:18} "
            f"| {s.kimenetel_nev:9} | {s.odds}"
        )


if __name__ == "__main__":
    _csak_actionsben.ellenoriz()
    main()
