from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guilds" ADD "language" VARCHAR(10) NOT NULL DEFAULT 'en';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guilds" DROP COLUMN "language";"""


MODELS_STATE = (
    "eJztmm1P2zAQx78K6qtNYhMrsLK9KzAYewAJumkSQpGbXFOrjtPFzlg38d1nOw9OnDSQkZ"
    "Rm6zs43yX2D/vunzO/e57vAGEvhxBge9p7u/W7R5EH4gdjZHurh+ZzbZcGjsZEuSLtM2Y8"
    "QDYX1gkiDITJAWYHeM6xT4WVhoRIo28LR0xdbQop/h6CxX0X+BQCMXB9I8yYOvATWPLrfG"
    "ZNMBAnN1XsyHcru8UXc2U7o/xEOcq3jS3bJ6FHtfN8wac+Tb0x5dLqAoUAcZCP50Eopy9n"
    "F68zWVE0U+0STTET48AEhYRnlvtABrZPJT8xG6YW6Mq3vOi/2hvsHey+3jsQLmomqWVwFy"
    "1Prz0KVATOR707NY44ijwURs3tBwRMTqkA72iKgnJ6mRADoZi4iTABVsUwMWiIeuM0RNFD"
    "Py0C1OVyg/f39yuYfR1eHr0fXj4TXs/lanyxmaM9fh4P9aMxCVaDlEejBsTYvZsAX+3sPA"
    "Cg8FoKUI3lAYo3cojOYB7ih6uL83KImRAD5BcqFnjtYJtvbxHM+M16Yq2gKFctJ+0x9p1k"
    "4T37PPxmcj36dHGoKPiMu4F6inrAoWAsU+Zkljn80jBG9uwWBY5VGPH7/jLf4pDX90wLos"
    "hVrOSK5fqSIsLFn8pB1IbSEqNHq8tM6searzXXMk2qCXjgjYXtZlN92q0+Ce88uWNhLUeX"
    "+BvwpJljD14m45066cfD0TszF07BnoFjYWqhkox4hSYgIY3EmpdkRvMBXSk0FZxG776Nqj"
    "Oit4hHPl2cnybuZprMk45OulXrAOdi7j/H6wG2iaNcKCUmxyLEEz8A7NKPsFAsz8Sckixv"
    "kIsrwef0QevH8C7ZCYlVZ9wA3aZ1Ib9BxBLFwoBHgnB4dTQ8Fsf9aYrwaYiNypUbqCy9rn"
    "Rpoeo+tMaq95ce1EPsLj2r2aguldw3/f7u7qC/s/v6YH9vMNg/2EkPbHGo6uQenp3Kw5tL"
    "hPcXZg8xLnZw4BOwlK0AffmnTVlsV8rPCj4U2RxsjMjfsS0N3sDVwon49syyp4hSILWTRV"
    "l0x+r7SvKG5i1V9y+f1trD2Zhubt1W+h8EUTcUZbsOymzM6lD2QDX/GkL5IJIVIJ/X63GY"
    "giLSaqwkUcThJx8vgSBe3vHssGg1PoM4kmLgsRj0UzoEok3FHe+MEsmt98xyzZ3ZnE23uk"
    "IWb1il/DedrpY7XRTbszqZPfHvZoFsRdsF4GL5ZQFOaVNsedewEPivtw9X8am8HlyeRvXK"
    "3FkbbyZoQ9ekW9FZTArVI/uKX1jXBNq20VXMbKDynmIhBTSALW0MdpdbNq/VbcZm7vfzN4"
    "9/L5LzV53dwdqyTI6/HEqFsv6qqJLKGa+GtXJ6mGaw2EjltqWyhFxDKcfuG6Gs/6cLkbCk"
    "jXT/rXEa2BWYq74t3gjrlUq/jYhpRMS0WbiVrC4p2oncXl6wpZx9wuvk9r/h1qdUP/Flsq"
    "RW96IzG9OVatRSaX/85cYUz//HC47m897dH4Frxyk="
)
