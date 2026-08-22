# cogs/attendance/__init__.py
from typing import TYPE_CHECKING

from .cog import Attendance
from .views import PaginationView

if TYPE_CHECKING:
    from pontobot import PontoBot


async def setup(bot: "PontoBot") -> None:
    await bot.add_cog(Attendance(bot))


__all__ = ["Attendance", "PaginationView", "setup"]
