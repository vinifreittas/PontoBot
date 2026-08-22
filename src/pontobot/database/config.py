# database/config.py
import os


def get_tortoise_config(db_url: str | None = None) -> dict:
    """Builds Tortoise ORM configuration dictionary. Used by both runtime and Aerich CLI."""
    if not db_url:
        db_url = os.environ.get("DATABASE_URL", "sqlite://db.sqlite3")
    elif db_url == ":memory:":
        db_url = "sqlite://:memory:"
    elif not db_url.startswith("sqlite://"):
        db_url = f"sqlite://{db_url}"

    return {
        "connections": {"default": db_url},
        "apps": {
            "models": {
                "models": ["aerich.models", "pontobot.database.models"],
                "default_connection": "default",
            }
        },
    }


# Aerich reads this module-level constant
TORTOISE_ORM = get_tortoise_config()
