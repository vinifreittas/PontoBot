from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> None:
    await db.execute_script('ALTER TABLE "guilds" ADD "language" VARCHAR(10) NOT NULL DEFAULT \'en\';')


async def downgrade(db: BaseDBAsyncClient) -> None:
    await db.execute_script('ALTER TABLE "guilds" DROP COLUMN "language";')
