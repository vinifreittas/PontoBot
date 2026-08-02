import pytest
from tortoise import Tortoise


@pytest.fixture(autouse=True)
async def init_db():
    """Initialize an in-memory SQLite database for each test."""
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["pontobot.database.models"]},
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()
