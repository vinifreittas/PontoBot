from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guilds" RENAME COLUMN "master_role_name" TO "master_role_id";
        ALTER TABLE "guilds" RENAME COLUMN "special_role_name" TO "special_role_id";
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guilds" RENAME COLUMN "master_role_id" TO "master_role_name";
        ALTER TABLE "guilds" RENAME COLUMN "special_role_id" TO "special_role_name";
        """


MODELS_STATE = (
    "eJztmttu2zgQhl/F8FUKZItEOTjtnXNqvd0ki8TtLhIEAi3RMmGKciWqqbfIu5dDnSlZiR"
    "optra6s4dDifxMzvwc+kffdkxMvbdD7BJj1n/f+9FnyMbig9Ky3eujxSKxg4GjCZWuKPGZ"
    "eNxFBhfWKaIeFiYTe4ZLFpw4TFiZTykYHUM4EmYlJp+Rrz7WuWNhPsOuaLi7F2bCTPwde9"
    "HXxVyfEkzNzFCJCe+Wdp0vF9I2YvxcOsLbJrrhUN9mifNiyWcOi70J42C1MMMu4hgez10f"
    "hg+jC+cZzSgYaeISDDHVx8RT5FOemu4zGRgOA35iNJ6coAVv+UPb3R/sH+0d7h8JFzmS2D"
    "J4DKaXzD3oKAlcjvuPsh1xFHhIjAm3b9j1YEg5eCcz5BbTS3VREIqBqwgjYGUMI0MCMVk4"
    "NVG00XedYmZxWODawUEJsy/D65OPw+st4fUGZuOIxRys8cuwSQvaAGwCErZGBYihezsB7u"
    "7sPAOg8FoJULZlAYo3chzswSzEP2+uLoshprooID8zMcE7kxh8u0eJx+83E2sJRZg1DNr2"
    "vK80DW/rYvivyvXkr6tjScHxuOXKp8gHHAvGEDKn89TmB8MEGfMH5Jp6rsXRnFW++SZbs1"
    "ULYsiSrGDGML8oiXDxU5mIGbgwxSSt5Wkm9vPqzzV3ECblAGxsT4Ttvss+zWafiHeW3Kmw"
    "FqOL/BV4YObExm+j9lbt9NPh+EyNhTNszLGpE6ajgoh4g6YYII3FnFdERvUBZcTgQ+uojU"
    "cXZzfj4cXfmSAJLKFFk9alYt06VAJn/JDeP6Pxxx587d1eXZ6psTT2G9/2YUzI547OnAcd"
    "melpR+bIlPlNg5iiVwoVmT5PR4zN+NHqCBq5pKVyzEM8d1xMLPYJLyXLkRhTlE8UcmHOuY"
    "gftHkMH6OVEFmT2O6ihzgDZReImKKYGOaB9BzenAxPRWBZT7r/4BMlR2YaSpO8BS4N5Pfn"
    "ZnP5/sKNekyslXs13atNyf2dpu3tDbSdvcOjg/3B4OBoJ96w+aaynXs8+gCbNxNgn5YANv"
    "K4WMGuQ3Fl5Pm+LYuRr8I+Ye0tsEEQ/TXYBZ072mW0DeoYc92YIcYwrYy7qHfHu4w3yNj/"
    "HFZwoFhdhkn36WoxMUqKmOWLxF4FZbrP66HsY1mIrAnls0iWgHxTrd6iSo5AzXkFgSLsfv"
    "7pGlPEi6uvLZa1ykGJI5ALL8WQPKVFIJrU5OHKKBDlyZpZrcpTi7PuspvvhQtWng26qlvD"
    "VTdGjHmVyB75tzNBNnLb42KLwNkDm4UFutUVzFzH/3sp8zUO05vBZT2qF2JnZbypTh1dlW"
    "5J7TFKVC+sPH722ibQtpW6Y2oBFVcdcyGgBmxx6bC93NJxrWq5NvVfg+wt6K+L5Oy1a3uw"
    "NiyTw5NDoVBOThVlUjnlVbNWjjfTHC87qdy0VAbIFZRy6N4J5eT/ZYj6BWWkp2+w447dzf"
    "W6b647Cf+qIrOTS7XIpSYlghTwBfIgEvarpQEI5zVebTd/WtwcUbDmi22gJj9X0A/pPr+5"
    "iHj5NcqMLH7Hq5T6497jT/JxDOo="
)
