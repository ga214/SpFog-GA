"""11. lépés — E-mail küldés.

A küldő absztrahált interfész mögött van, hogy a Gmail SMTP később egy sor
cserével lecserélhető legyen (Resend, SendGrid, transactional SMTP).

BIZTONSÁG: az app-jelszó SOHA nem kerül naplóba, és soha nem kerül a repóba.
A `titkok.py`-n keresztül jön, környezeti változóból.

GMAIL SMTP: az app_jelszo NEM a Google-fiók jelszava, hanem külön generált
app-jelszó, amihez 2FA kell a fiókon. Lásd docs/SECRETS.md.
"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

from tippmix.kozos.config import beallitasok
from tippmix.kozos.naplo import naplo
from tippmix.kozos.titkok import email_titkok

log = naplo(__name__)


@dataclass(frozen=True, slots=True)
class Level:
    """Egy kiküldendő levél."""

    targy: str
    szoveg: str  # egyszerű szöveg (a spec példája ilyen)
    html: str | None = None


class Kuldo(Protocol):
    """E-mail-küldő interfész. Így cserélhető a háttér egy sorral."""

    def kuld(self, level: Level) -> None: ...


class GmailSmtpKuldo:
    """Gmail SMTP küldő app-jelszóval.

    Napi 500 levél limit — nekünk napi 3 kell.
    """

    def kuld(self, level: Level) -> None:
        beall = beallitasok()
        titkok = email_titkok()

        uzenet = EmailMessage()
        uzenet["Subject"] = level.targy
        uzenet["From"] = f"{beall.email.felado_nev} <{titkok.felhasznalo}>"
        uzenet["To"] = titkok.cimzett
        uzenet.set_content(level.szoveg)
        if level.html:
            uzenet.add_alternative(level.html, subtype="html")

        log.info(
            "email_kuldes_kezdet",
            targy=level.targy,
            cimzett=titkok.cimzett,
            smtp=beall.email.smtp_host,
        )

        with smtplib.SMTP(beall.email.smtp_host, beall.email.smtp_port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(titkok.felhasznalo, titkok.app_jelszo)
            smtp.send_message(uzenet)

        log.info("email_elkuldve", targy=level.targy)


class NaploKuldo:
    """Teszt-küldő: nem küld semmit, csak naplóz.

    Ezt használja a smoke-teszt és a `--szarazon` futtatás.
    """

    def __init__(self) -> None:
        self.elkuldott: list[Level] = []

    def kuld(self, level: Level) -> None:
        self.elkuldott.append(level)
        log.info("email_szarazon", targy=level.targy, hossz=len(level.szoveg))


def alapertelmezett_kuldo(szarazon: bool = False) -> Kuldo:
    """A konfigurációnak megfelelő küldő."""
    return NaploKuldo() if szarazon else GmailSmtpKuldo()


def hibalevel(hibauzenet: str, futas_id: str, kuldo: Kuldo | None = None) -> None:
    """Hibalevél sikertelen futás esetén (spec 1. lépés, 1. pont).

    A hibaüzenetből eltávolítjuk az esetleges titkokat, mielőtt kimenne.
    """
    beall = beallitasok()
    if not beall.naplozas.hibalevel_kuldese:
        log.warning("hibalevel_kikapcsolva", hiba=hibauzenet)
        return

    k = kuldo or alapertelmezett_kuldo()
    k.kuld(
        Level(
            targy=f"{beall.email.targy_elotag} — HIBA",
            szoveg=(
                f"A futás sikertelen volt.\n\n"
                f"Futás azonosító: {futas_id}\n\n"
                f"Hiba:\n{hibauzenet}\n\n"
                f"Nem ment ki javaslat. A program nem használ tegnapi szorzót "
                f"és nem találgat.\n"
            ),
        )
    )
