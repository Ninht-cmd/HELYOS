"""Connecteur SMTP — l'envoi RÉEL d'e-mails, verrouillé par la gouvernance.

C'est le connecteur qui rend l'agent de relance de factures livrable :
HELYOS rédige (A1), l'humain valide, et SEULEMENT alors l'e-mail part (GR-2 :
action externe sensible -> validation obligatoire, même en A5).

Configuration :
- ``HELYOS_SMTP_HOST``, ``HELYOS_SMTP_PORT`` (587), ``HELYOS_SMTP_USER``,
  ``HELYOS_SMTP_PASSWORD``, ``HELYOS_SMTP_FROM``
"""

from __future__ import annotations

import os
import smtplib
from collections.abc import Callable
from email.message import EmailMessage

from ..governance.autonomy import AutonomyLevel
from ..governance.policy import Action, ActionType, PolicyVerdict
from ..governance.service import GovernanceService
from .base import Connector, ConnectorStatus


class SMTPConnector(Connector):
    name = "smtp"
    kind = "email"

    def __init__(self, host: str | None = None, port: int | None = None,
                 user: str | None = None, password: str | None = None,
                 sender: str | None = None,
                 smtp_factory: Callable | None = None) -> None:
        env = os.environ.get
        self.host = host or env("HELYOS_SMTP_HOST", "")
        self.port = port or int(env("HELYOS_SMTP_PORT", "587") or 587)
        self.user = user or env("HELYOS_SMTP_USER", "")
        self.password = password or env("HELYOS_SMTP_PASSWORD", "")
        self.sender = sender or env("HELYOS_SMTP_FROM", "") or self.user
        self.smtp_factory = smtp_factory or smtplib.SMTP  # injectable pour les tests

    @property
    def configured(self) -> bool:
        return bool(self.host and self.sender)

    def status(self) -> ConnectorStatus:
        if not self.configured:
            return ConnectorStatus(
                self.name, self.kind, "not_configured",
                detail="envoi réel des relances — GR-2 : validation humaine obligatoire",
                requires="HELYOS_SMTP_HOST/PORT/USER/PASSWORD/FROM")
        return ConnectorStatus(self.name, self.kind, "connected",
                               detail=f"{self.host} · chaque envoi exige ta validation (GR-2)")

    def send_email(self, governance: GovernanceService, *, to: str, subject: str,
                   body: str, granted: AutonomyLevel = AutonomyLevel.A2,
                   validated: bool = False, actor: str = "connector.smtp",
                   ) -> tuple[PolicyVerdict, bool]:
        """Soumet PUIS envoie. Sans ``validated=True`` explicite, rien ne part (GR-2)."""
        action = Action(
            type=ActionType.EXTERNAL_SENSITIVE,
            description=f"Envoyer un e-mail à {to} : {subject}",
            target=to, actor=actor, sensitive=True, validated=validated,
        )
        verdict = governance.submit(action, granted)
        if not verdict.allowed:
            return verdict, False                     # le refus fait partie du contrat
        if not self.configured:
            return verdict, False                     # autorisé mais pas branché : honnête

        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = self.sender, to, subject
        msg.set_content(body)
        smtp = self.smtp_factory(self.host, self.port, timeout=15)
        try:
            smtp.starttls()
            if self.user:
                smtp.login(self.user, self.password)
            smtp.send_message(msg)
        finally:
            smtp.quit()
        return verdict, True
