"""Tippmix tipprendszer — automatizált sportfogadási javaslatrendszer.

A csomag a döntési logika specifikáció 12 lépését követi, alcsomagonként:

    gyujtes    — 1. lépés: esemény- és szorzóbegyűjtés a Tippmix Pro-ról
    illesztes  — 2. lépés: névillesztés
    jellemzok  — 3. lépés: feature-építés jövőbe látás nélkül
    modellek   — 4-6. lépés: futball-, kosármodell, kalibráció, zsugorítás
    dontes     — 7-8. lépés: vig-eltávolítás, él, döntési fa
    tetezes    — 9-10. lépés: Kelly-tétezés, kombináció-építés
    kimenet    — 11. lépés: napi limitek, e-mail
    adattar    — 12. lépés: naplózás, CLV
    kozos      — közös: konfiguráció, naplózás, hibák, idő
    backteszt  — walk-forward backteszt-keretrendszer
"""

__version__ = "0.1.0"
