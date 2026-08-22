# utils/embeds.py
from datetime import datetime

import discord

MAX_EMBED_CHARS = 1020


def truncate_text(text: str) -> str:
    """Safely truncates string contents to respect strict Discord API limits."""
    return f"{text[:MAX_EMBED_CHARS]}..." if len(text) > MAX_EMBED_CHARS else text


def create_base_embed(
    embed_colors: dict[str, int], title: str, description: str, color_key: str, timestamp: datetime | None = None
) -> discord.Embed:
    """Helper to create a unified standard embed structure."""
    return discord.Embed(title=title, description=description, color=embed_colors[color_key], timestamp=timestamp)


async def send_error_embed(
    embed_colors: dict[str, int], interaction: discord.Interaction, title: str, desc: str, color_key: str = "error"
) -> None:
    """Standard helper to respond with error or warning messages."""
    embed = create_base_embed(embed_colors, title, desc, color_key)
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)
