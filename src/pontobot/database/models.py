# database/models.py
from datetime import datetime
from dateutil.parser import isoparse
from tortoise import fields
from tortoise.models import Model


# ----------------------------------------------------------------------
# CUSTOM FIELDS
# ----------------------------------------------------------------------

class SafeDateTimeField(fields.TextField):
    """Custom field to safely parse SQLite ISO timestamps into Python datetime objects."""

    def to_python_value(self, value: any) -> datetime | None:
        if value is None or isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            try:
                return isoparse(value.strip())
            except (ValueError, TypeError):
                return None
                
        return super().to_python_value(value)


# ----------------------------------------------------------------------
# TABLES
# ----------------------------------------------------------------------

class Guild(Model):
    guild_id = fields.BigIntField(pk=True) 
    nome_cargo_mestre = fields.CharField(max_length=255, null=False)
    nome_cargo_especial = fields.CharField(max_length=255, null=False)
    id_canal_ponto = fields.BigIntField(null=False)
    fuso_horario = fields.CharField(max_length=100, null=False)

    class Meta:
        table = "guilds"


class Usuario(Model):
    usuario_id = fields.BigIntField(pk=True)
    usuario = fields.CharField(max_length=255, null=False)

    class Meta:
        table = "usuarios"


class Membro(Model):
    id = fields.IntField(pk=True)
    usuario = fields.ForeignKeyField("models.Usuario", related_name="membro_guildas", on_delete=fields.CASCADE)
    guild = fields.ForeignKeyField("models.Guild", related_name="membro_usuarios", on_delete=fields.CASCADE)
    
    nick = fields.CharField(max_length=255, null=False)
    data_cadastro = fields.DateField(auto_now_add=False) 

    class Meta:
        table = "membros"
        unique_together = (("usuario", "guild"),)


class Presenca(Model):
    id = fields.IntField(pk=True)
    data = fields.DateField(null=False)
    membro = fields.ForeignKeyField("models.Membro", related_name="presencas", on_delete=fields.CASCADE)
    hora = SafeDateTimeField(null=False) 

    class Meta:
        table = "presencas"
        unique_together = (("data", "membro"),)


class Metadados(Model):
    guild = fields.ForeignKeyField("models.Guild", related_name="metadados", on_delete=fields.CASCADE)
    chave = fields.CharField(max_length=255, null=False)
    valor = SafeDateTimeField(null=False)

    class Meta:
        table = "metadados"
        unique_together = (("guild", "chave"),)