# cogs/frequencia.py
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
import logging

from ..bot import PontoBot

logger = logging.getLogger(__name__)


class Frequencia(commands.Cog):
    """Cog responsible for managing user attendance records and synchronization."""
    MAX_EMBED_CHARS = 1020

    def __init__(self, bot: PontoBot):
        self.bot = bot
        self.db = self.bot.db
        self.embed_colors = self.bot.embed_colors

        self.period_days: dict[str, int] = {"hoje": 1, "7dias": 7, "30dias": 30}
        self.labels: dict[str, str] = {
            "geral": "Todo o histórico",
            "hoje": "Hoje",
            "7dias": "Últimos 7 dias",
            "30dias": "Últimos 30 dias",
            "custom": "Dia específico"
        }

    # -------------------------- Funções Auxiliares --------------------------

    async def _get_tz(self, guild_id: int) -> ZoneInfo:
        """Returns the ZoneInfo for a guild, falling back to the default."""
        guild_data = await self.db.get_guilda(guild_id)
        return ZoneInfo(guild_data.fuso_horario)

    def _filtrar_datas_por_periodo(self, periodo: str, tz: ZoneInfo) -> list[date]:
        """Calculates a list of targeted dates based on the defined period window."""
        if periodo not in self.period_days:
            return []
        hoje_dt = datetime.now(tz)
        return [(hoje_dt - timedelta(days=i)).date() for i in range(self.period_days[periodo])]

    def _parse_data_customizada(self, data_str: str) -> date | None:
        """Validates and parses a custom date string into a date object."""
        try:
            return datetime.strptime(data_str.strip(), "%d/%m/%Y").date()
        except ValueError:
            return None

    @classmethod
    def _truncate_text(cls, text: str) -> str:
        """Safely truncates string contents to respect strict Discord API limits."""
        return f"{text[:cls.MAX_EMBED_CHARS]}..." if len(text) > cls.MAX_EMBED_CHARS else text

    def _criar_embed_base(self, title: str, description: str, color_key: str, timestamp: datetime | None = None) -> discord.Embed:
        """Helper to create a unified standard embed structure."""
        return discord.Embed(title=title, description=description, color=self.embed_colors[color_key], timestamp=timestamp)

    async def _enviar_embed_erro(self, interaction: discord.Interaction, title: str, desc: str, color_key: str = "error") -> None:
        """Standard helper to respond with error or warning messages quickly."""
        embed = self._criar_embed_base(title, desc, color_key)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------------- Eventos de Ciclo de Vida --------------------------

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Executado APENAS quando o bot liga. Sincroniza o passado das guildas já existentes."""
        logger.info("🔄 Bot iniciado. Executando rotina de recuperação pós-offline...")
        for guild in self.bot.guilds:
            if guild_data := await self.db.get_guilda(guild.id):
                await self._rotina_recuperacao_pos_offline(guild, guild_data)
        logger.info("✅ Varredura de sincronização inicial concluída.")

    @commands.Cog.listener()
    async def on_guild_setup(self, guild: discord.Guild) -> None:
        """Executado APENAS quando uma nova guilda conclui o /setup. Faz o 'Onboarding' da guilda."""
        logger.info(f"⚡ Primeiro setup detectado para a guilda: {guild.name} ({guild.id})")
        if guild_data := await self.db.get_guilda(guild.id):
            await self._primeiro_onboarding_guilda(guild, guild_data)

    # -------------------------- Rotinas de Sincronização --------------------------

    async def _rotina_recuperacao_pos_offline(self, guild: discord.Guild, guild_data) -> None:
        """Rotina para servidores antigos: lida estritamente com o tempo que o bot passou desligado."""
        canal = self.bot.get_channel(guild_data.id_canal_ponto)
        if not isinstance(canal, discord.TextChannel):
            return

        membros_servidor: set[int] = {member.id for member in guild.members}
        try:
            await self._remover_usuarios_ausentes(guild.id, membros_servidor)
            await self._sincronizar_pontos_offline(guild, canal, membros_servidor, guild_data)
        except Exception as e:
            logger.error(f"❌ Erro na recuperação da guilda {guild.id}: {e}", exc_info=True)

    async def _primeiro_onboarding_guilda(self, guild: discord.Guild, guild_data) -> None:
        """Rotina para novos servidores: popula o banco de dados do zero sem enviar relatórios de erro."""
        try:
            logger.info(f"📥 Populando banco de dados inicial para a guilda: {guild.name}")
            for member in guild.members:
                if not member.bot:
                    await self.db.assegurar_membro(guild.id, member.id)
            
            tz = ZoneInfo(guild_data.fuso_horario)
            await self.db.set_ultima_verificacao(guild.id, datetime.now(tz))
            logger.info(f"✅ Onboarding concluído com sucesso para {guild.name}.")
        except Exception as e:
            logger.error(f"❌ Erro no onboarding da guilda {guild.id}: {e}", exc_info=True)

    async def _remover_usuarios_ausentes(self, guild_id: int, membros_servidor: set[int]) -> None:
        logger.info("🧹 Starting database cleanup for left server members...")
        membros_banco = await self.db.get_membros_guilda(guild_id)
        removidos = [m for m in membros_banco if m.usuario.usuario_id not in membros_servidor]

        for membro in removidos:
            await self.db.remover_membro(guild_id, membro.usuario.usuario_id)
            logger.info(f"🗑️ Member {membro.nick} ({membro.usuario.usuario_id}) removed from guild {guild_id}.")

        logger.info(f"✅ Cleanup finished. {len(removidos)} member(s) removed.")

    async def _sincronizar_pontos_offline(self, guild: discord.Guild, canal: discord.TextChannel, membros_servidor: set[int], guild_data) -> None:
        logger.info("🔎 Scanning text history for missed '!ponto' commands...")
        tz = ZoneInfo(guild_data.fuso_horario)
        desde_quando = await self.db.get_ultima_verificacao(guild.id) or (datetime.now(tz) - timedelta(days=7))

        novos_registros = 0
        detalhes_relatorio = []

        async for msg in canal.history(after=desde_quando, limit=300, oldest_first=True):
            if msg.author.bot or msg.content.strip().lower() != "!ponto" or msg.author.id not in membros_servidor:
                continue

            member = await self.db.assegurar_membro(guild.id, msg.author.id, msg.author.name, msg.author.display_name)
            if await self.db.registrar_presenca(member, msg.created_at):
                novos_registros += 1
                horario_formatado = msg.created_at.astimezone(tz).strftime('%d/%m/%Y às %H:%M:%S')
                detalhes_relatorio.append(f"⏰ {msg.author.mention} (`{msg.author.display_name}`) — {horario_formatado}")

        if novos_registros > 0:
            embed_relatorio = discord.Embed(
                title="📥 Relatório de Sincronização Offline",
                description="Identifiquei que alguns colaboradores registraram ponto enquanto eu estava indisponível:",
                color=self.embed_colors["info"],
                timestamp=datetime.now(tz)
            ).add_field(
                name=f"📋 Registros Recuperados ({novos_registros})",
                value=self._truncate_text("\n".join(detalhes_relatorio)),
                inline=False
            )
            try:
                await canal.send(embed=embed_relatorio)
            except discord.Forbidden:
                logger.error("❌ Insufficient permissions to dispatch offline reports to the tracking channel.")

        await self.db.set_ultima_verificacao(guild.id, datetime.now(tz))
        logger.info(f"✅ Sync finalized: {novos_registros} skipped records recovered.")

    # -------------------------- Comandos --------------------------

    @commands.command(name="ponto")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ponto(self, ctx: commands.Context) -> None:
        """Text alternative method to record presence parameters."""
        guild_data = await self.db.get_guilda(ctx.guild.id)
        if not guild_data:
            return await ctx.message.reply("⚠️ Este servidor ainda não foi configurado.", delete_after=10)

        if ctx.channel.id != guild_data.id_canal_ponto:
            embed = self._criar_embed_base("⛔ Canal Incorreto", "Este comando só pode ser utilizado no canal destinado ao registro de pontos.", "error")
            return await ctx.message.reply(embed=embed, delete_after=10)

        tz = ZoneInfo(guild_data.fuso_horario)
        agora = datetime.now(tz)

        member = await self.db.assegurar_membro(ctx.guild.id, ctx.author.id, ctx.author.name, ctx.author.display_name)
        if not await self.db.registrar_presenca(member, agora):
            embed = self._criar_embed_base("⚠️ Registro Duplicado", f"Olá {ctx.author.mention}, você já registrou sua presença hoje!", "warning")
            return await ctx.message.reply(embed=embed, delete_after=10)

        await self.db.set_ultima_verificacao(ctx.guild.id, agora)

        embed_sucesso = discord.Embed(title="✅ Presença Confirmada!", color=self.embed_colors["success"], timestamp=agora)
        embed_sucesso.set_thumbnail(url=ctx.author.display_avatar.url)
        embed_sucesso.set_footer(text="Registro de Ponto Eletrônico")

        fields = [
            ("👤 Colaborador", ctx.author.mention),
            ("🏷️ Nickname", ctx.author.display_name),
            ("📅 Data", agora.strftime('%d/%m/%Y')),
            ("⏰ Horário", agora.strftime('%H:%M:%S'))
        ]
        for name, value in fields:
            embed_sucesso.add_field(name=name, value=value, inline=True)

        await ctx.message.reply(embed=embed_sucesso)

    async def periodo_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Provides dynamic suggestions for the periodo argument."""
        opcoes = [
            app_commands.Choice(name="Geral (Todo o Histórico)", value="geral"),
            app_commands.Choice(name="Hoje", value="hoje"),
            app_commands.Choice(name="Últimos 7 dias", value="7dias"),
            app_commands.Choice(name="Últimos 30 dias", value="30dias")
        ]
        return [op for op in opcoes if current.lower() in op.name.lower() or current.lower() in op.value.lower()][:25]

    @app_commands.command(name="frequencia", description="Consulta frequências e relatórios filtrados por usuário, período ou geral.")
    @app_commands.describe(
        usuario="Selecione um usuário específico (Opcional).",
        periodo="Escolha um período da lista ou digite uma data no formato DD/MM/AAAA."
    )
    @app_commands.autocomplete(periodo=periodo_autocomplete)
    @app_commands.checks.cooldown(1, 5)
    async def frequencia(self, interaction: discord.Interaction, usuario: discord.Member | None = None, periodo: str = "geral") -> None:
        """Slash command processor for tracking analytics outputs."""
        guild_data = await self.db.get_guilda(interaction.guild.id)
        if not guild_data:
            return await interaction.response.send_message("⚠️ Este servidor ainda não foi configurado.", ephemeral=True)

        if not await self.bot.has_acess(interaction.user, interaction.guild) and interaction.user != usuario:
            desc = f"Você precisa do cargo `{guild_data.nome_cargo_mestre}` para ver a frequência de outros membros."
            return await self._enviar_embed_erro(interaction, "⛔ Permissão Negada", desc)

        tz = ZoneInfo(guild_data.fuso_horario)

        if periodo in ["geral", "hoje", "7dias", "30dias"]:
            label_periodo = self.labels[periodo]
            datas_alvo = self._filtrar_datas_por_periodo(periodo, tz)
        else:
            data_validada = self._parse_data_customizada(periodo)
            if not data_validada:
                desc = "Por favor, utilize o formato padrão brasileiro: **DD/MM/AAAA**.\n*Exemplo: 23/06/2026*"
                return await self._enviar_embed_erro(interaction, "❌ Formato de Data Inválido", desc)

            if data_validada > datetime.now(tz).date():
                return await self._enviar_embed_erro(interaction, "⏳ Data no Futuro", "Não é possível consultar dados de frequência para datas futuras.", "warning")

            periodo = "custom"
            label_periodo = f"Dia Específico ({data_validada.strftime('%d/%m/%Y')})"
            datas_alvo = [data_validada]

        if usuario is None:
            await self._processar_relatorio_geral(interaction, label_periodo, periodo, datas_alvo, guild_data)
        else:
            await self._processar_relatorio_individual(interaction, usuario, label_periodo, periodo, datas_alvo)

    async def _processar_relatorio_geral(self, interaction: discord.Interaction, label: str, periodo: str, datas: list[date], guild_data) -> None:
        """Internal processor for general global logs output."""
        todos_membros = await self.db.get_membros_guilda(interaction.guild.id)
        dias_com_ponto = await self.db.get_dias_com_ponto(interaction.guild.id, periodo, datas)
        
        embed = self._criar_embed_base("📋 Relatório Geral de Frequência", f"🗓️ **Filtro:** {label}\n*Exibindo o status de presença organizado por dia.*", "info")
        nome_cargo_especial = guild_data.nome_cargo_especial if guild_data else None

        if not todos_membros or not dias_com_ponto:
            embed.description += "\n\n*Nenhum registro ou usuário elegível encontrado para este período.*"
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        guild = interaction.guild
        for dia in sorted(dias_com_ponto, reverse=True):
            presentes, ausentes = [], []
            presencas_dia = await self.db.get_presencas_dia(interaction.guild.id, dia)

            for membro_db in todos_membros:
                uid = membro_db.usuario.usuario_id
                nick = membro_db.nick or membro_db.usuario.usuario
                discord_member = guild.get_member(uid) if guild else None

                if discord_member and nome_cargo_especial and any(role.name == nome_cargo_especial for role in discord_member.roles):
                    presentes.append(f"✅ **{nick}** (`Isento/Especial`)")
                elif uid in presencas_dia:
                    presentes.append(f"✅ **{nick}** (`{presencas_dia[uid]}`)")
                elif dia >= membro_db.data_cadastro:
                    ausentes.append(f"❌ {nick}")

            texto_presentes = "\n".join(presentes) if presentes else "*Ninguém compareceu*"
            texto_ausentes = "\n".join(ausentes) if ausentes else "*Nenhuma falta*"
            valor_campo = f"**Presentes:**\n{texto_presentes}\n\n**Ausentes:**\n{texto_ausentes}\n"

            embed.add_field(name=f"📅 Data: {dia.strftime("%d/%m/%Y")}", value=self._truncate_text(valor_campo), inline=False)

        await interaction.response.send_message(embed=embed)

    async def _processar_relatorio_individual(self, interaction: discord.Interaction, usuario: discord.Member, label: str, periodo: str, datas: list[date]) -> None:
        """Internal processor for single target user performance profiles."""
        total_dias, presencas = await self.db.get_estatisticas_usuario(interaction.guild.id, usuario.id, periodo, datas)
        faltas = max(0, total_dias - presencas)
        taxa = (presencas / total_dias * 100) if total_dias else 0.0

        embed = self._criar_embed_base("📊 Estatísticas Detalhadas de Frequência", f"👤 **Usuário:** {usuario.mention}\n🗓️ **Janela:** {label}", "info")
        embed.set_thumbnail(url=usuario.display_avatar.url)
        embed.add_field(name="✅ Dias Presente", value=f"`{presencas} dias`", inline=True)
        embed.add_field(name="❌ Dias Ausente", value=f"`{faltas} dias`", inline=True)
        embed.add_field(name="📈 Rendimento", value=f"`{taxa:.1f}% de presença`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ranking", description="Mostra o ranking global de presenças.")
    async def ranking(self, interaction: discord.Interaction) -> None:
        lista = await self.db.get_ranking(interaction.guild.id)
        embed = self._criar_embed_base("🏆 Quadro de Honra — Ranking de Presenças", "Lista dos colaboradores com maior engajamento nos check-ins.", "success")

        podio_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
        linhas_ranking = [
            f"{podio_emojis.get(pos, '🔹')} `{pos:02d}º` **{nick}** — `{qtd} presenças`"
            for pos, (nick, qtd) in enumerate(lista, start=1)
        ]
        texto_ranking = "\n".join(linhas_ranking) if linhas_ranking else "*Nenhum dado registrado até o momento.*"

        embed.add_field(name="Classificação", value=self._truncate_text(texto_ranking), inline=False)
        embed.set_footer(text="Atualizado em tempo real")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: PontoBot):
    await bot.add_cog(Frequencia(bot))