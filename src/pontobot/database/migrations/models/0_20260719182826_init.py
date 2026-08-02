from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);
CREATE TABLE IF NOT EXISTS "guilds" (
    "guild_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "master_role_name" VARCHAR(255) NOT NULL,
    "special_role_name" VARCHAR(255) NOT NULL,
    "clock_channel_id" BIGINT NOT NULL,
    "timezone" VARCHAR(100) NOT NULL
);
CREATE TABLE IF NOT EXISTS "metadata" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "key" VARCHAR(255) NOT NULL,
    "value" TEXT NOT NULL,
    "guild_id" BIGINT NOT NULL REFERENCES "guilds" ("guild_id") ON DELETE CASCADE,
    CONSTRAINT "uid_metadata_guild_i_b84e1c" UNIQUE ("guild_id", "key")
);
CREATE TABLE IF NOT EXISTS "users" (
    "user_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "username" VARCHAR(255) NOT NULL
);
CREATE TABLE IF NOT EXISTS "members" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "nick" VARCHAR(255) NOT NULL,
    "registered_at" DATE NOT NULL,
    "guild_id" BIGINT NOT NULL REFERENCES "guilds" ("guild_id") ON DELETE CASCADE,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("user_id") ON DELETE CASCADE,
    CONSTRAINT "uid_members_user_id_908e8e" UNIQUE ("user_id", "guild_id")
);
CREATE TABLE IF NOT EXISTS "attendances" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "date" DATE NOT NULL,
    "checked_in_at" TEXT NOT NULL,
    "member_id" INT NOT NULL REFERENCES "members" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_attendances_date_e47ba8" UNIQUE ("date", "member_id")
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJztmltP2zAUgP8K6tMmsYkVWNneCgzGLiBBN01CKHKT09Sq43SxM9ZN/PfZzsWJkwYykt"
    "JsfYPjcxL749xyzO+e5ztA2MshBNie9t5u/e5R5IH4wVjZ3uqh+VzLpYCjMVGqSOuMGQ+Q"
    "zYV0gggDIXKA2QGec+xTIaUhIVLo20IRU1eLQoq/h2Bx3wU+hUAsXN8IMaYO/ASW/DqfWR"
    "MMxMltFTvy3Upu8cVcyc4oP1GK8m1jy/ZJ6FGtPF/wqU9TbUy5lLpAIUAc5ON5EMrty93F"
    "50xOFO1Uq0RbzNg4MEEh4ZnjPpCB7VPJT+yGqQO68i0v+q/2BnsHu6/3DoSK2kkqGdxFx9"
    "NnjwwVgfNR706tI44iDYVRc/sBAZNbKsA7mqKgnF7GxEAoNm4iTIBVMUwEGqJ2nIYoeuin"
    "RYC6XDp4f3+/gtnX4eXR++HlM6H1XJ7GF84c+fh5vNSP1iRYDVKGRg2IsXo3Ab7a2XkAQK"
    "G1FKBaywMUb+QQxWAe4oeri/NyiBkTA+QXKg547WCbb28RzPjNemKtoChPLTftMfadZOE9"
    "+zz8ZnI9+nRxqCj4jLuBeop6wKFgLFPmZJYJfikYI3t2iwLHKqz4fX+ZbnHJ63umBFHkKl"
    "byxPJ8SRHh4k/lIGpDaYnRq9VlJtVjzdeaa5km1QY88MZCdrOpPu1Wn4R3ntyxkJajS/QN"
    "eFLMsQcvk/VORfrxcPTOzIVTsGfgWJhaqCQjXqEJSEgjceYlmdF8QFcKTQWn0btvo+qM6C"
    "3ilU8X56eJupkm86SjSLdqBXDO5v44Xg+wTYRyoZSYHIsQT/wAsEs/wkKxPBN7SrK8QS6u"
    "BJ/TB60fw7vEExKpzrgBuk3rQt5BxBHFwYBHDeHw6mh4LML9aYrwaYiNypVbqCy9rlRpoe"
    "o+tMaq95cG6iF2l8Zq1qpLJfdNv7+7O+jv7L4+2N8bDPYPdtKALS5VRe7h2akM3lwivL8w"
    "e4hx4cGBT8BSsgL05Z82ZbZdKT8r+FBkc7AxIn/HttR4A1c3TsS3Z5Y9RZQCqZ0syqw7Vt"
    "9Xkjc0b9l1//JpLR/O2nTTdRubf9T4NjcLYdRjsBIHj81PPl4CQbx8UtfhZsto3zmSReyx"
    "GPRTOgSizU4x9oySVlH7zPJeMeOcTY9oQhY7rOpYNxOalic0FNuzOsk90e9mYm+lJwnAxb"
    "IjBqd0mLN82lUw/NfHXqv4xFsPLk/TrcncWRtvxmhD16RbMRFLCtUj52FfWNcatG1jGpZx"
    "oPJZWCEFNIAtHWh1l1s2r9UdImbupfM3Zn/fJOev6LqDteU2Of5yKG2U9VdFVauc0Wq4V0"
    "6DaQaLTavcdqssIdfolGP1TaOs/xcJkbBkknT/bWdq2BWYq77l3DTWK239Nk1MI01Mm4Vb"
    "tdUlRTtpt5cXbNnOPuE1aPvfcOtTqp/4ElRSq3tBl7XpSjVqqbQ//nJjiuf/4wVH83nv7g"
    "+6yl84"
)
