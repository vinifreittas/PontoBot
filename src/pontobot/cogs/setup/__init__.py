# cogs/setup/__init__.py
from typing import TYPE_CHECKING

from .cog import Setup
from .views import ReconfigureConfirmationView, SetupWizardView, TimezoneModal

if TYPE_CHECKING:
    from pontobot import PontoBot


async def setup(bot: "PontoBot") -> None:
    await bot.add_cog(Setup(bot))


__all__ = ["ReconfigureConfirmationView", "Setup", "SetupWizardView", "TimezoneModal", "setup"]
