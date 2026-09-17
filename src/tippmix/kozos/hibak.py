"""Kivétel-hierarchia és kiesési okok.

A kiesési okok (`KiesesiOk`) a döntési logika specifikáció 8. lépésének
döntési fájából származnak, szó szerint. Ezek nem hibák: egy jelölt kiesése
normális működés. A programnak minden kiesést naplóznia kell, mert az e-mail
"NEM JAVASOLT, DE MEGVIZSGÁLVA" szakasza ezekből épül.
"""

from __future__ import annotations

from enum import StrEnum


class KiesesiOk(StrEnum):
    """Miért nem lett egy jelöltből javaslat.

    A sorrend megegyezik a specifikáció 8. lépésének döntési fájával.
    Az első bukott feltételnél esik ki a jelölt.
    """

    # 1-7. — technikai kapuk
    NINCS_ODDS = "NINCS_ODDS"
    ODDS_TARTOMANY = "ODDS_TARTOMANY"
    KESO = "KESO"
    NEVILLESZTES_HIANY = "NEVILLESZTES_HIANY"
    KEVES_ADAT = "KEVES_ADAT"
    MODELL_ELAVULT = "MODELL_ELAVULT"
    NEM_TAMOGATOTT_PIAC = "NEM_TAMOGATOTT_PIAC"

    # 8-10. — érték-kapuk
    KIS_EL = "KIS_EL"
    KIS_EV = "KIS_EV"
    REFERENCIA_ELTERES = "REFERENCIA_ELTERES"

    # 11-12. — hír és duplikátum
    HIRVETO = "HIRVETO"
    DUPLIKATUM = "DUPLIKATUM"

    # 9. lépés (tétezés) — a fán túli kiesés
    TUL_KIS_TET = "TUL_KIS_TET"

    # 4. lépés — modellillesztés
    ILLESZTES_SIKERTELEN = "ILLESZTES_SIKERTELEN"

    # 11. lépés — napi limit vágta le
    NAPI_LIMIT = "NAPI_LIMIT"


# =============================================================================
# Kivételek
# =============================================================================


class TippmixHiba(Exception):
    """Minden projekt-specifikus kivétel őse."""


class KonfiguracioHiba(TippmixHiba):
    """Hiányzó vagy érvénytelen konfiguráció, hiányzó titok."""


class AdatgyujtesHiba(TippmixHiba):
    """Az 1. lépés nem tudott adatot szerezni.

    A spec szerint: 3 újrapróbálkozás után nincs futás, hibalevél megy ki,
    a program kilép. Nem találgat, nem használ tegnapi szorzót.
    """


class AdattarHiba(TippmixHiba):
    """Supabase-kapcsolat vagy -művelet hibája."""


class ModellHiba(TippmixHiba):
    """A modell illesztése vagy alkalmazása sikertelen."""


class LeallitasiFeltetel(TippmixHiba):
    """Automatikus leállítási feltétel teljesült (spec 12. lépés).

    Ilyenkor a program nem küld javaslatot, csak riasztást.
    """

    def __init__(self, feltetel: str, reszletek: str) -> None:
        self.feltetel = feltetel
        self.reszletek = reszletek
        super().__init__(f"Leállítási feltétel teljesült: {feltetel} — {reszletek}")
