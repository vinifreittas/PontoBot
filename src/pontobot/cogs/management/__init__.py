# cogs/management/__init__.py
from typing import TYPE_CHECKING

from .cog import Management
from .views import ManagementView, OwnedView, UserManagementView

if TYPE_CHECKING:
    from pontobot import PontoBot


async def setup(bot: "PontoBot") -> None:
    await bot.add_cog(Management(bot))


__all__ = ["Management", "ManagementView", "OwnedView", "UserManagementView", "setup"]
