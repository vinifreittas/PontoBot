# bot.py
import logging
import time
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from .database import DatabaseManager
from .utils.logger import log_stream, setup_logging

# Initialize logging configuration
setup_logging()
logger = logging.getLogger(__name__)

# Configuration Constants
EMBED_COLORS = {
    "default": 0x2B2D31,
    "success": 0x2ECC71,
    "info": 0x3498DB,
    "warning": 0xF1C40F,
    "error": 0xE74C3C,
}


class PontoBot(commands.Bot):
    """Custom Discord Bot client managed via cogs and an external database."""

    def __init__(self, db_path: str = "bot.db"):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(command_prefix="!", intents=intents)

        # Core Systems
        self.db = DatabaseManager(db_path)
        self.log_stream = log_stream

        # State & Metrics
        self.start_time: float = time.time()
        self.has_errors: bool = False
        self.embed_colors: dict[str, int] = EMBED_COLORS

        # Bind Error Callbacks
        self.log_stream.on_error_callback = self._mark_error

        # Set up the global interaction check
        self.tree.interaction_check = self._is_configured

    def _mark_error(self) -> None:
        """Flags that an error occurred in the log stream."""
        self.has_errors = True

    async def _is_configured(self, interaction: discord.Interaction) -> bool:
        """Global check that runs before every slash command."""
        if interaction.command and interaction.command.name == "setup_pontobot":
            return True

        guild_data = await self.db.get_guild(interaction.guild_id)
        if guild_data:
            return True

        raise app_commands.CheckFailure("This server has not been configured yet! Use `/setup` first.")

    async def has_access(self, member: discord.Member, guild: discord.Guild) -> bool:
        """Checks if a member has administrative access to the guild based on roles."""
        guild_data = await self.db.get_guild(guild.id)
        role_name_target = guild_data.master_role_name.casefold()

        return any(role.name.casefold() == role_name_target for role in member.roles)

    async def setup_hook(self) -> None:
        """Asynchronous initialization before the bot connects to the Gateway."""
        await self.db.connect()

        # Set up global slash command error handling
        self.tree.on_error = self.on_app_command_error

        # Dynamically load extensions from the 'cogs' directory
        base_dir = Path(__file__).resolve().parent
        cogs_dir = base_dir / "cogs"
        package_name = self.__module__.split(".")[0]

        for path in cogs_dir.glob("*.py"):
            if not path.name.startswith("_"):
                try:
                    await self.load_extension(f"{package_name}.cogs.{path.stem}")
                    logger.info(f"📦 Extension loaded successfully: {path.stem}")
                except Exception as e:
                    logger.error(f"❌ Failed to load extension {path.stem}: {e}")

        try:
            logger.info("🔄 Syncing global application commands...")
            synced = await self.tree.sync()
            logger.info(f"✅ {len(synced)} global slash commands synced successfully.")
        except Exception as e:
            logger.error(f"❌ Error syncing global slash commands: {e}")

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Handles errors raised during prefix command execution."""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(f"Wait {error.retry_after:.2f}s to use the command.", delete_after=5)
        else:
            logger.error(f"Error in command '{ctx.command}': {error}")

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        """Handles errors raised during application (slash) command execution."""

        # 1. Handle our custom configuration check failure (if the guild is not configured)
        if isinstance(error, app_commands.CheckFailure):
            error_message = str(error)

            if not interaction.response.is_done():
                await interaction.response.send_message(f"⚠️ {error_message}", ephemeral=True)
            else:
                await interaction.followup.send(
                    f"⚠️ {error_message}",
                    ephemeral=True,
                )
            return

        # 2. Handle generic unexpected errors (Log them and notify user)
        logger.error(f"Error in slash command '{interaction.command}': {error}")

        if not interaction.response.is_done():
            await interaction.response.send_message("❌ An unexpected error occurred.", ephemeral=True)
        else:
            await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=True)

    async def on_ready(self):
        """Handles the bot's successful connection to Discord."""
        logger.info(f"✅ Bot is online as: {self.user}")

    async def close(self) -> None:
        """Gracefully shuts down external resources and disconnects the bot."""
        logger.info("🛑 Bot is shutting down. Cleaning up resources...")
        await self.db.disconnect()
        logger.info("🔌 Database connection closed cleanly.")
        await super().close()
