from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from pontobot.cogs.attendance import PaginationView


@pytest.fixture
def sample_embeds():
    embed1 = discord.Embed(title="Page 1")
    embed2 = discord.Embed(title="Page 2")
    embed3 = discord.Embed(title="Page 3")
    return [embed1, embed2, embed3]


def test_pagination_view_initial_state(sample_embeds):
    view = PaginationView(sample_embeds, owner_id=123)
    assert view.current == 0
    assert view.owner_id == 123
    assert len(view.pages) == 3
    assert view.prev_btn.disabled is True
    assert view.next_btn.disabled is False


def test_pagination_view_single_page():
    single_embed = [discord.Embed(title="Single Page")]
    view = PaginationView(single_embed, owner_id=123)
    assert view.current == 0
    assert view.prev_btn.disabled is True
    assert view.next_btn.disabled is True


@pytest.mark.asyncio
async def test_pagination_view_interaction_check_owner(sample_embeds):
    view = PaginationView(sample_embeds, owner_id=123)
    interaction = MagicMock(spec=discord.Interaction)
    interaction.user.id = 123

    res = await view.interaction_check(interaction)
    assert res is True


@pytest.mark.asyncio
async def test_pagination_view_interaction_check_non_owner(sample_embeds):
    view = PaginationView(sample_embeds, owner_id=123)
    interaction = MagicMock(spec=discord.Interaction)
    interaction.user.id = 999
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()

    res = await view.interaction_check(interaction)
    assert res is False
    interaction.response.send_message.assert_called_once_with(
        "⛔ Only the user who requested this report can navigate pages.",
        ephemeral=True,
    )


@pytest.mark.asyncio
async def test_pagination_view_next_prev_navigation(sample_embeds):
    view = PaginationView(sample_embeds, owner_id=123)
    interaction = MagicMock(spec=discord.Interaction)
    interaction.response = MagicMock()
    interaction.response.edit_message = AsyncMock()

    # Move Next -> Page 2 (index 1)
    await view.next_btn.callback(interaction)
    assert view.current == 1
    assert view.prev_btn.disabled is False
    assert view.next_btn.disabled is False
    interaction.response.edit_message.assert_called_with(embed=sample_embeds[1], view=view)

    # Move Next -> Page 3 (index 2)
    await view.next_btn.callback(interaction)
    assert view.current == 2
    assert view.prev_btn.disabled is False
    assert view.next_btn.disabled is True
    interaction.response.edit_message.assert_called_with(embed=sample_embeds[2], view=view)

    # Move Prev -> Page 2 (index 1)
    await view.prev_btn.callback(interaction)
    assert view.current == 1
    assert view.prev_btn.disabled is False
    assert view.next_btn.disabled is False
    interaction.response.edit_message.assert_called_with(embed=sample_embeds[1], view=view)
