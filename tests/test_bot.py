from pontobot.bot import PontoBot


def test_bot_sync_on_startup_default():
    bot = PontoBot(db_path=":memory:")
    assert bot.sync_on_startup is False


def test_bot_sync_on_startup_explicit():
    bot = PontoBot(db_path=":memory:", sync_on_startup=True)
    assert bot.sync_on_startup is True


def test_bot_sync_on_startup_env_var(monkeypatch):
    monkeypatch.setenv("SYNC_COMMANDS", "true")
    bot = PontoBot(db_path=":memory:")
    assert bot.sync_on_startup is True
