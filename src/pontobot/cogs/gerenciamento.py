# cogs/gerenciamento.py
import asyncio
import logging
import time
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from ..bot import PontoBot

logger = logging.getLogger(__name__)
VIEW_TIMEOUT = 300


# ==============================================================================
# UI COMPONENTS 
# ==============================================================================

class UserManagementView(discord.ui.View):
    """View used for managing individual guild members."""

    def __init__(self, cog: "Gerenciamento"):
        super().__init__(timeout=VIEW_TIMEOUT)
        self.cog = cog
        self.selected_member: discord.Member | None = None

        # Select menu built directly inline to keep components cohesive
        self.select_menu = discord.ui.UserSelect(
            placeholder="Selecione um membro para gerenciar...", 
            min_values=1, max_values=1, row=0
        )
        self.select_menu.callback = self._user_select_callback
        self.add_item(self.select_menu)

    async def _user_select_callback(self, inter: discord.Interaction):
        self.selected_member = self.select_menu.values[0]
        
        embed = discord.Embed(
            title="👥 Painel de Controle de Gerenciamento de Usuários",
            description=f"Membro Alvo: {self.selected_member.mention}\n\nEscolha uma ação abaixo:",
            color=discord.Color.blue()
        )
        
        # Enable the action buttons now that a user is selected
        self.special_tag_btn.disabled = False
        await inter.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Tag Especial", style=discord.ButtonStyle.primary, emoji="✨", row=1, disabled=True)
    async def special_tag_btn(self, inter: discord.Interaction, button: discord.ui.Button):
        if not self.selected_member or not inter.guild:
            return await inter.response.send_message("❌ Nenhum membro selecionado.", ephemeral=True)
        
        guild_data = await self.cog.db.get_guilda(inter.guild.id)
        cargo_especial = guild_data.nome_cargo_especial
        
        role = discord.utils.get(inter.guild.roles, name=cargo_especial)
        if not role:
            return await inter.response.send_message(f"❌ Cargo '{cargo_especial}' não encontrado.", ephemeral=True)

        await self.selected_member.add_roles(role)
        await inter.response.send_message(f"⭐ Tag especial **{role.name}** atribuída a {self.selected_member.mention}.", ephemeral=True)

    @discord.ui.button(label="Voltar ao Menu", style=discord.ButtonStyle.gray, emoji="⬅️", row=1)
    async def back_button(self, inter: discord.Interaction, button: discord.ui.Button):
        await inter.response.edit_message(embed=self.cog.get_main_embed(), view=ManagementView(self.cog))
        self.stop()

class ManagementView(discord.ui.View):
    """Main administrative dashboard view."""

    def __init__(self, cog: "Gerenciamento"):
        super().__init__(timeout=VIEW_TIMEOUT)  
        self.cog = cog
        self.lock = asyncio.Lock()

        # Dropdown built inline to save vertical space and keep scope close
        self.dropdown = discord.ui.Select(
            placeholder="Selecione uma categoria administrativa...",
            min_values=1, max_values=1, row=0,
            options=[
                discord.SelectOption(label="Gerenciamento de Usuários", description="Gerencie membros e regras de moderação.", emoji="👥"),
                discord.SelectOption(label="Configurações do Bot", description="Configure modos lentos e categorias do servidor.", emoji="⚙️"),
                discord.SelectOption(label="Logs de Atividade do Bot", description="Revise tarefas do sistema e operações em tempo real.", emoji="📜")
            ]
        )
        self.dropdown.callback = self._dropdown_callback
        self.add_item(self.dropdown)

    def _disable_all_items(self):
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = True

    async def _dropdown_callback(self, inter: discord.Interaction):
        embed = discord.Embed().set_footer(text=f"Solicitado por {inter.user.name}", icon_url=inter.user.display_avatar.url)
        target_view = self

        match self.dropdown.values[0]:
            case "Gerenciamento de Usuários":
                embed.title = "👥 Painel de Gerenciamento de Usuários"
                embed.description = "Selecione um usuário no menu suspenso abaixo e, em seguida, escolha uma ação para processar."
                embed.color = discord.Color.blue()
                target_view = UserManagementView(self.cog)
            
            case "Configurações do Bot":
                embed.title = "⚙️ Painel de Configuração do Bot"
                embed.description = "Nada pra ver por aqui."
                embed.color = discord.Color.orange()
                
            case "Logs de Atividade do Bot":
                embed.title = "📜 Logs de Atividade do Sistema (Tempo Real)"
                embed.description = f"```yaml\n{self.cog._get_last_logs()}```"
                embed.color = discord.Color.dark_gray()

        await inter.response.edit_message(embed=embed, view=target_view)

    @discord.ui.button(label="Menu Inicial", style=discord.ButtonStyle.secondary, emoji="🏠", row=1)
    async def home_button(self, inter: discord.Interaction, button: discord.ui.Button):
        await inter.response.edit_message(embed=self.cog.get_main_embed(), view=self)

    @discord.ui.button(label="Bloqueio de Emergência", style=discord.ButtonStyle.danger, emoji="🚨", row=1)
    async def lock_button(self, inter: discord.Interaction, button: discord.ui.Button):
        async with self.lock:
            embed = discord.Embed(
                title="🚨 BLOQUEIO DE EMBARGOS/EMERGÊNCIA", 
                description="❌ Esse botão ainda não é funcional.", 
                color=discord.Color.red()
            ).set_footer(text=f"Iniciado por {inter.user.name}", icon_url=inter.user.display_avatar.url)
            await inter.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Fechar Console", style=discord.ButtonStyle.gray, emoji="🔒", row=1)
    async def close_button(self, inter: discord.Interaction, button: discord.ui.Button):
        self._disable_all_items()
        await inter.response.edit_message(content="❌ *Sessão administrativa encerrada.*", embed=None, view=self)
        self.stop()


# ==============================================================================
# COG CLASS
# ==============================================================================

class Gerenciamento(commands.Cog):
    """Cog responsible for managing the bot."""

    def __init__(self, bot: PontoBot):
        self.bot = bot
        self.db = self.bot.db
        self.embed_colors = self.bot.embed_colors
        self.log_stream = self.bot.log_stream
        self.start_time = self.bot.start_time
        self.has_errors = self.bot.has_errors

    def _get_last_logs(self, lines: int = 12) -> str:
        """Extracts the last N lines from the memory logging stream."""
        log_lines = self.log_stream.getvalue().splitlines()
        return "\n".join(log_lines[-lines:]) if log_lines else "Nenhum log registrado ainda."

    def get_main_embed(self) -> discord.Embed:
        """Generates a dynamic, professional unified main dashboard embed interface."""
        latency = round(self.bot.latency * 1000)
        total_guilds = len(self.bot.guilds)
        total_users = sum(g.member_count for g in self.bot.guilds if g.member_count)
        uptime = str(timedelta(seconds=int(time.time() - self.start_time)))
        
        embed = discord.Embed(
            title="🛠️ Sistema de Controle Central | PontoBot",
            description="Painel operacional seguro de administração. Utilize as ferramentas e menus abaixo para monitorar métricas e gerenciar configurações globais.",
            color=self.embed_colors.get("default", discord.Color.blue())
        )

        status_msg = "🔴 **Atenção:** Erros detectados nos logs do sistema!" if self.has_errors else "🟢 Todos os sistemas operacionais estão operando normalmente."
        embed.add_field(name="📌 Status do Sistema", value=status_msg, inline=False)
        embed.add_field(name="📊 Desempenho", value=f"⚡ **Latência:** `{latency}ms`\n⏱️ **Uptime:** `{uptime}`", inline=True)
        embed.add_field(name="🌐 Escopo", value=f"🖥️ **Servidores:** `{total_guilds}`\n👥 **Usuários:** `{total_users}`", inline=True)

        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            embed.set_footer(text="Acesso Restrito • Console do Administrator", icon_url=self.bot.user.display_avatar.url)
        return embed

    @app_commands.command(name="gerenciamento", description="Menu de gerenciamento do bot.")
    @app_commands.guild_only()
    async def gerenciamento(self, interaction: discord.Interaction):
        guild_config = await self.db.get_guilda(interaction.guild_id)

        if not await self.bot.has_acess(interaction.user, interaction.guild):
            embed = discord.Embed(
                title="⛔ Permissão Negada", 
                description=f"Você precisa do cargo `{guild_config.nome_cargo_mestre}` para gerenciar o bot.", 
                color=self.embed_colors.get("error", discord.Color.red())
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        await interaction.response.send_message(embed=self.get_main_embed(), view=ManagementView(self), ephemeral=True)


async def setup(bot: PontoBot):
    await bot.add_cog(Gerenciamento(bot))