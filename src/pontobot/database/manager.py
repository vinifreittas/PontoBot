# database/manager.py
from datetime import datetime, date, time
from pathlib import Path
import logging
import copy
import os

from tortoise import Tortoise
from tortoise.exceptions import IntegrityError
from tortoise.functions import Count
from tortoise.expressions import Q
from aerich import Command

from .models import Guild, Usuario, Membro, Presenca, Metadados

logger = logging.getLogger(__name__)

TORTOISE_ORM = {
    "connections": {
        "default": f"sqlite://db.sqlite3"   
    },
    "apps": {
        "models": {
            "models": ["aerich.models", "pontobot.database.models"],
            "default_connection": "default",
        }
    },
}


class DatabaseManager:
    """Acts as a Data Access Layer (DAL) API for the rest of the application."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.config = copy.deepcopy(TORTOISE_ORM)
        self.config["connections"]["default"] = f"sqlite://{self.db_path}"

    async def connect(self) -> None:
        """Initializes Tortoise ORM with centralized configurations."""
        try:
            await Tortoise.init(config=self.config)

            package_dir = Path(__file__).parent.resolve()
            migrations_path = os.path.join(package_dir, "migrations")
            
            command = Command(tortoise_config=self.config, app="models", location=migrations_path)
            await command.init()
            
            try:
                await command.upgrade(run_in_transaction=True)
                logger.info("✅ Aerich upgraded or create the database with success.")
            except Exception as upgrade_err:
                logger.error(f"❌ Aerich failed to upgrade or create the database: {upgrade_err}")
                raise

            logger.info("💾 Database connection via Tortoise ORM established.")
        except Exception as e:
            logger.error(f"❌ Structural error connecting to database: {e}")
            raise

    async def disconnect(self) -> None:
        """Safely closes all open database connections."""
        await Tortoise.close_connections()
        logger.info("💾 Database connections closed.")


    # ------- GUILD MANAGEMENT -------

    async def get_guilda(self, guild_id: int) -> Guild | None:
        """Retrieves a specific guild from the database."""
        return await Guild.get_or_none(guild_id=guild_id)

    async def adicionar_guilda(self, guild_id: int, nome_cargo_mestre: str, nome_cargo_especial: str, id_canal_ponto: int, fuso_horario: str) -> None:
        """Ensures a guild exists in the database, creating it with defaults if not."""
        await Guild.get_or_create(guild_id=guild_id, nome_cargo_mestre=nome_cargo_mestre, nome_cargo_especial=nome_cargo_especial, id_canal_ponto=id_canal_ponto, fuso_horario=fuso_horario)

    async def remover_guilda(self, guild_id: int) -> None:
        """Removes a guild from the database."""
        await Guild.filter(guild_id=guild_id).delete()


    # ------- MEMBER MANAGEMENT -------

    async def assegurar_membro(self, guild_id: int, usuario_id: int, username: str, nick: str) -> Membro:
        """Ensures a user exists, and they are linked as a member."""
        usuario, _ = await Usuario.update_or_create(usuario_id=usuario_id, usuario=username)
        
        membro, _ = await Membro.get_or_create(
            usuario=usuario,
            guild_id=guild_id,
            defaults={"nick": nick or username, "data_cadastro": date.today()}
        )
        return membro

    async def remover_membro(self, guild_id: int, usuario_id: int) -> None:
        """Removes a member relationship when they leave a specific server."""
        await Membro.filter(guild_id=guild_id, usuario_id=usuario_id).delete()

    async def get_membro(self, guild_id: int, usuario_id: int) -> Membro | None:
        """Retrieves a specific member from a server."""
        return await Membro.get_or_none(guild_id=guild_id, usuario_id=usuario_id)

    async def get_membros_guilda(self, guild_id: int) -> list[Membro]:
        """Retrieves all members of a specific server."""
        return await Membro.filter(guild_id=guild_id).prefetch_related("usuario")


    # ------- PRESENCE MANAGEMENT -------

    async def registrar_presenca(self, member: Membro, data: datetime) -> bool:
        """Registers a member's daily attendance securely using Time and Date objects."""
        try:
            await Presenca.create(membro=member, data=data.date(), hora=data)
            return True
        except IntegrityError:
            return False
        except Exception as e:
            logger.error(f"❌ Error registering presence: {e}")
            return False

    async def get_presencas_dia(self, guild_id: int, dia: date) -> dict[int, time]:
        """Returns a mapping of user IDs to check-in times for a specific guild and date."""
        presencas = await Presenca.filter(
            membro__guild_id=guild_id, 
            data=dia
        ).prefetch_related("membro__usuario")
        
        return {p.membro.usuario_id: p.hora for p in presencas}

    async def get_dias_com_ponto(self, guild_id: int, periodo: str, datas_alvo: list[date]) -> list[date]:
        """Returns all dates where at least one attendance occurred within a specific guild context."""
        base_query = Presenca.filter(membro__guild_id=guild_id)

        if periodo != "geral" and datas_alvo:
            base_query = base_query.filter(data__in=datas_alvo)
            
        return await base_query.distinct().values_list("data", flat=True)


    # ------- STATS & METADATA -------

    async def get_estatisticas_usuario(self, guild_id: int, usuario_id: int, periodo: str, datas_alvo: list[date]) -> tuple[int, int]:
        """Calculates the total expected attendance days versus the specific user's attendance records."""
        membro = await Membro.get_or_none(guild_id=guild_id, usuario_id=usuario_id)
        if not membro:
            return 0, 0

        # 1. Determinar o total de dias esperado para a janela de tempo consultada
        if periodo != "geral" and datas_alvo:
            dias_validos = [d for d in datas_alvo if d >= membro.data_cadastro]
            total_dias = len(dias_validos)
        else:
            total_dias = await Presenca.filter(
                membro__guild_id=guild_id, 
                data__gte=membro.data_cadastro
            ).distinct().values_list("data", flat=True)
            total_dias = len(total_dias)

        # 2. Total de presenças marcadas por este usuário específico
        user_filter = Q(membro=membro)
        if periodo != "geral" and datas_alvo:
            user_filter &= Q(data__in=datas_alvo)

        user_total = await Presenca.filter(user_filter).count()

        return total_dias, user_total

    async def get_ranking(self, guild_id: int, limite: int = 20) -> list[tuple[str, int]]:
        """Returns top users in a specific guild ranked by attendance count."""
        membros_com_presencas = await Membro.filter(guild_id=guild_id).annotate(
            qtd=Count("presencas")
        ).order_by("-qtd").limit(limite).select_related("usuario")
        
        return [(m.nick or m.usuario.usuario, m.qtd) for m in membros_com_presencas]
        
    async def get_ultima_verificacao(self, guild_id: int) -> datetime | None:
        meta = await Metadados.get_or_none(guild_id=guild_id, chave="ultima_verificacao")
        return meta.valor if meta else None

    async def set_ultima_verificacao(self, guild_id: int, valor: datetime) -> None:
        await Metadados.update_or_create(
            guild_id=guild_id,
            chave="ultima_verificacao",
            defaults={"valor": valor}
        )