# cogs/setup.py
import logging
import discord
from discord import app_commands
from discord.ext import commands

from ..bot import PontoBot

logger = logging.getLogger(__name__)


# ==============================================================================
# UI COMPONENTS 
# ==============================================================================

class SetupWizardView(discord.ui.View):
    def __init__(self, bot: PontoBot):
        super().__init__(timeout=300)
        self.bot = bot
        
        # Configuration state
        self.nome_cargo_mestre = None
        self.nome_cargo_especial = None
        self.id_canal_ponto = None
        self.fuso_horario = "America/Sao_Paulo"
        
        # Initialize Step 1
        self.add_item(discord.ui.RoleSelect(placeholder="Select the Master Role...", custom_id="select_mestre"))

    def _update_view(self, interaction: discord.Interaction, content: str, item: discord.ui.Item):
        """Helper method to clear items, add a new component, and edit the message."""
        self.clear_items()
        self.add_item(item)
        return interaction.response.edit_message(content=content, view=self)

    async def _handle_mestre(self, interaction: discord.Interaction, values: list):
        role = interaction.guild.get_role(int(values[0]))
        self.nome_cargo_mestre = role.name if role else "Mestre"
        
        await self._update_view(
            interaction,
            content="Great! Now, select the **Special Role**.",
            item=discord.ui.RoleSelect(placeholder="Select the Special Role...", custom_id="select_especial")
        )

    async def _handle_especial(self, interaction: discord.Interaction, values: list):
        role = interaction.guild.get_role(int(values[0]))
        self.nome_cargo_especial = role.name if role else "Especial"
        
        await self._update_view(
            interaction,
            content="Awesome. Next, choose the **text channel** where points will be logged.",
            item=discord.ui.ChannelSelect(
                placeholder="Select the tracking channel...", 
                channel_types=[discord.ChannelType.text], 
                custom_id="select_canal"
            )
        )

    async def _handle_canal(self, interaction: discord.Interaction, values: list):
        self.id_canal_ponto = int(values[0])
        
        timezone_select = discord.ui.Select(
            placeholder="Select your Timezone...",
            options=[
                discord.SelectOption(label="Brasília (UTC-3)", value="America/Sao_Paulo"),
                discord.SelectOption(label="Amazonas (UTC-4)", value="America/Manaus"),
                discord.SelectOption(label="Fernando de Noronha (UTC-2)", value="America/Noronha")
            ],
            custom_id="select_timezone"
        )
        await self._update_view(
            interaction,
            content="Almost done! Lastly, select your server's **timezone**.",
            item=timezone_select
        )

    async def _handle_timezone(self, interaction: discord.Interaction, values: list):
        self.fuso_horario = values[0]
        
        try:
            await self.bot.db.adicionar_guilda(
                guild_id=interaction.guild.id,
                nome_cargo_mestre=self.nome_cargo_mestre,
                nome_cargo_especial=self.nome_cargo_especial,
                id_canal_ponto=self.id_canal_ponto,
                fuso_horario=self.fuso_horario
            )
            self.bot.dispatch("guild_setup", interaction.guild)
            
            self.clear_items()
            await interaction.response.edit_message(
                content="✅ **Setup Complete!** Your server has been successfully registered in the database.",
                view=self
            )
        except Exception as e:
            logger.error(f"Error saving guild setup: {e}")
            await interaction.response.edit_message(
                content="❌ An error occurred while saving the configuration. Please try again later.",
                view=None
            )
        finally:
            self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")
        values = interaction.data.get("values", [])

        if not values:
            return True

        # Action map to eliminate the long if/elif chain
        handlers = {
            "select_mestre": self._handle_mestre,
            "select_especial": self._handle_especial,
            "select_canal": self._handle_canal,
            "select_timezone": self._handle_timezone
        }

        handler = handlers.get(custom_id)
        if handler:
            await handler(interaction, values)

        return True


# ==============================================================================
# COG CLASS
# ==============================================================================

class Setup(commands.Cog):
    def __init__(self, bot: PontoBot):
        self.bot = bot
    
    @app_commands.command(name="setup_pontobot", description="Configure o PontoBot no seu servidor.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        """Initializes the bot configuration."""
        guild_data = await self.bot.db.get_guilda(interaction.guild.id)
        if guild_data:
            await interaction.response.send_message("⚙️ This server is already configured.", ephemeral=True)
            return

        view = SetupWizardView(self.bot)
        await interaction.response.send_message(
            "Let's configure PontoBot! First, select the **Master Role** (the role that will manage the system).",
            view=view,
            ephemeral=True
        )


async def setup(bot: PontoBot) -> None:
    await bot.add_cog(Setup(bot))