from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "guilds" (
    "guild_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "nome_cargo_mestre" VARCHAR(255) NOT NULL,
    "nome_cargo_especial" VARCHAR(255) NOT NULL,
    "id_canal_ponto" BIGINT NOT NULL,
    "fuso_horario" VARCHAR(100) NOT NULL
);
CREATE TABLE IF NOT EXISTS "metadados" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "chave" VARCHAR(255) NOT NULL,
    "valor" TIMESTAMP NOT NULL,
    "guild_id" BIGINT NOT NULL REFERENCES "guilds" ("guild_id") ON DELETE CASCADE,
    CONSTRAINT "uid_metadados_guild_i_528e9f" UNIQUE ("guild_id", "chave")
);
CREATE TABLE IF NOT EXISTS "usuarios" (
    "usuario_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "usuario" VARCHAR(255) NOT NULL
);
CREATE TABLE IF NOT EXISTS "membros" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "nick" VARCHAR(255) NOT NULL,
    "data_cadastro" DATE NOT NULL,
    "guild_id" BIGINT NOT NULL REFERENCES "guilds" ("guild_id") ON DELETE CASCADE,
    "usuario_id" BIGINT NOT NULL REFERENCES "usuarios" ("usuario_id") ON DELETE CASCADE,
    CONSTRAINT "uid_membros_usuario_da39e4" UNIQUE ("usuario_id", "guild_id")
);
CREATE TABLE IF NOT EXISTS "presencas" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "data" DATE NOT NULL,
    "hora" TIME NOT NULL,
    "membro_id" INT NOT NULL REFERENCES "membros" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_presencas_data_a81a45" UNIQUE ("data", "membro_id")
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJztmltvmzAUx79KlKdO2qaOXpLtLb1t2dZ2arOLVlXIAYdYBZuBaVdN+e6zzc0Yw5IlaU"
    "DNWzj2wfYvh3P+NvzpesSGbvj6fYRcu/uu86eLgQfZj2LDy04X+H5u5gYKxq7o6fAuwgTG"
    "IQ2ARZl1AtwQMpMNQytAPkUEMyuOXJcbicU6IuzkpgijXxE0KXEgncKANdzcMjPCNvwNw/"
    "TSvzMnCCozFeObSMxStJr00RctR8gZYnomPPiwY9MibuRh1ct/pFOCMzeEKbc6EMMAUMhH"
    "o0HEV8Mnmyw7XWA88bxLPGPJx4YTELlUWv2cSCyCOU42m1Cs1+GjvHprGHt7PWN377B/sN"
    "/rHfR3+6yvmFK5qTeLl51jiW8l4AzfDy9GfKGE/WfxX8kNM+EDKIi9BPscNiYeNC0QOMT0"
    "IJseLFM/noJAz1zrrMBnZhV+irqOfmrI8ecRuCL+HvhtuhA7dMoujYODGrbfBlfHHwZXO6"
    "zXiyLhi6TJiNs4bC1cGPrQQsD9T7yy+xZwBhjZjA8GrukTTMliCaPs+++00RCwT5g5ctaT"
    "KCTmlPUIkIZ0dRSrfu0M3ze7u3OEL+tVGb6ibTbjZW9yJ+VibhgD6+4BBLZZaJGKN/TGAT"
    "GjMOIUQ02gJzc4+3QFXSCWWkadSIBzcbNmQp+l0ZNak7pbiEQPUmADe3kO0m1ahIIHDDFI"
    "VQiVmzzDUy0s8Tli1nxsPlIxNjTCMY+aauUYh+kapONNNwl98VcJCXs7r5zUCcmaotA2/W"
    "i82e/t9/cO97Pkn1nqcv4cyhBZdwuplaR/O/P7WuSJYGuxJMPG1dTME8ZDz7LkqEBl7ZAi"
    "D77mP5qJt4bmyWB0qpB6ij1fM7hsRrwl6XNhwkW/LWOVcUnNlZCXeZ+RACIHf4KPgvmQTR"
    "1gS7d3TkrvV6n2NY51lUxh5gA8ZPVYiSS2SLY0SOOaMrg+HpywlFDKCCuAlx14tRednOb0"
    "4ObZQ/gBDCG2wJKq+Utym3YhXbNoTjcSWt0s7TLqpLPcbcXiOXuWrCm4h1vpvG7pHGNeQD"
    "tnDlvxnEG8By4J9KKZS189yMypTjDzH83EWkNxNDw/vR4Nzr/wmXth+MvtJlKatxjC+qhY"
    "dw4V4NlNOt+How8dftn5eXlxKoiRkDqBGDHvN/rJq3IXRJSYmDyYwJaXnZpT01bSb05ubv"
    "XSSvTSOnVCJp00MkGWVdUqoaDhVq0SeDkTaSQ+6duqhDWrhJT3IodCz+EsiL8rKnMZVdb8"
    "tH8Vl9aW+0JN19bzXED1X+hqOC/fyqsT8SJpoUe24NOymrzUw1tTbb3sbciS5baNL+PUel"
    "sIkCYV3PTgTFNvpTO16nIrv2/dzLdQT3Vu25xyu+HvoSpPbas375LLM9++L/NtgxDtyx5O"
    "tjGbrvVocgADZE11CTBpqc1/IO+zkey33Vn8387iHgZh8pzMm8Qkl2eexGS5zB+NBSAm3d"
    "sJcGVfuMkA2YgUxs9gEeLH68uLirPw3EUB+RWzBd7YyKIvOy4K6W0zsdZQ5KsunN+m8HbO"
    "Bz9UrsefL4/UTR2/wdFilXb15WX2F/pUjBo="
)
