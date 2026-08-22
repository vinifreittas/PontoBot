# 🤖 AGENTS.md — AI Agent Guidelines for PontoBot

This document provides high-level architectural context, coding conventions, repository navigation, and operational rules for AI agents working in the **PontoBot** repository.

---

## 📌 1. Project Overview & Tech Stack

**PontoBot** is an enterprise-grade automated attendance tracker, frequency reporter, and timesheet manager engineered for Discord servers. Built on modern asynchronous architectures utilizing `discord.py` and `Tortoise ORM`, it provides multi-tenant guild isolation, classic text command check-ins (`!ponto`), interactive setup wizards, slash commands (`/attendance`, `/ranking`, `/management`), leaderboards, and historical attendance reports.

* **Language:** Python >= 3.12 (managed via `uv`)
* **Bot Framework:** [discord.py](https://discordpy.readthedocs.io/) 2.4+ (`discord.ext.commands.Bot`, `app_commands`, Cogs)
* **Database & ORM:** [Tortoise ORM](https://tortoise.github.io/) + SQLite / PostgreSQL (Async ORM)
* **Database Migrations:** [Aerich](https://github.com/tortoise/aerich)
* **Date & Timezone:** `python-dateutil`, `tzdata`
* **Tooling:** `ruff` (linter/formatter), `pytest` / `pytest-asyncio` (testing), `deadcode`, `pre-commit`

### Environment & Configuration Files
* **Database Location / Connection:** Configured via `DATABASE_URL` (defaults to `sqlite://db.sqlite3` or local path passed to `PontoBot(db_path=...)`)
* **Discord Token:** `DISCORD_TOKEN` environment variable or passed directly to `bot.run(...)`
* **Command Sync Flag:** `SYNC_COMMANDS` (`true`/`false`, default `false`) for global slash command synchronization on startup
* **Logging Level:** `LOG_LEVEL` (`INFO`, `DEBUG`, `WARNING`, `ERROR`)
* **Aerich Migration Config:** Configured in `pyproject.toml` (`[tool.aerich]`) pointing to `pontobot.database.manager.TORTOISE_ORM` and `./src/pontobot/database/migrations`

---

## 🏗️ 2. Architecture & System Data Flow

PontoBot strictly follows a modular, layered architecture:

```
src/pontobot/
├── database/         # Tortoise ORM models, DatabaseManager DAL, Aerich migrations configuration
├── i18n/             # Internationalization layer (TranslationManager, PontoBotTranslator, locales)
├── utils/            # Shared utilities (DequeLogHandler, setup_logging, embeds, views, constants)
├── cogs/             # Discord event handlers & commands (setup, attendance, management)
└── bot.py            # PontoBot client setup (Intents, interaction checks, setup_hook, cog auto-loader)
```

### ⚠️ The Golden Dependency Rule
```
database / utils / i18n  ←  cogs  ←  bot (PontoBot)  ←  main entrypoint (main.py)
```

### Data & Execution Flow Pattern
`Discord User (!ponto or Slash Command)` ➔ `discord.py Gateway` ➔ `PontoBot._is_configured Check` ➔ `Cog Handler (setup/attendance/management)` ➔ `DatabaseManager DAL` ➔ `Tortoise ORM Models (Guild/User/Member/Attendance/Metadata)` ➔ `SQLite Database` ➔ `Discord Embed Response`

---

## 🗺️ 3. Repository Directory Map

```
src/pontobot/
├── __init__.py                      # Package initialization (exports PontoBot)
├── bot.py                           # PontoBot client setup (commands.Bot subclass, intents, cogs loading, error handling)
├── cogs/                            # Discord Cogs / Command extensions (Feature Subpackages)
│   ├── __init__.py
│   ├── attendance/                  # Attendance check-in (!ponto), period reports (/attendance), and rankings (/ranking)
│   │   ├── __init__.py              # Subpackage Cog registration
│   │   ├── cog.py                   # Attendance Cog command definitions
│   │   ├── helpers.py               # Date filtering, offline recovery, and report rendering helpers
│   │   └── views.py                 # PaginationView & embed creation UI components
│   ├── setup/                       # Interactive server configuration wizard (/setup_pontobot)
│   │   ├── __init__.py              # Subpackage Cog registration
│   │   ├── cog.py                   # Setup Cog command definition
│   │   └── views.py                 # SetupWizardView, TimezoneModal, ReconfigureConfirmationView
│   └── management/                  # Manager role telemetry, status dashboard, and raw log view (/management)
│       ├── __init__.py              # Subpackage Cog registration
│       ├── cog.py                   # Management Cog command definition
│       └── views.py                 # Dashboard UI & User Management control panels
├── database/                        # Database DAL & ORM layer
│   ├── __init__.py                  # Exports DatabaseManager, get_tortoise_config, TORTOISE_ORM
│   ├── config.py                    # get_tortoise_config & Aerich TORTOISE_ORM config
│   ├── manager.py                   # DatabaseManager DAL API
│   ├── models.py                    # Tortoise ORM models (Guild, User, Member, Attendance, Metadata) & SafeDateTimeField
│   └── migrations/                  # Aerich migration schema files
├── i18n/                            # Internationalization layer
│   ├── __init__.py                  # Exports TranslationManager, PontoBotTranslator
│   ├── manager.py                   # TranslationManager: loads and resolves locale strings
│   ├── translator.py                # PontoBotTranslator: discord.app_commands.Translator implementation
│   └── locales/                     # Locale JSON files (en, pt-BR, …)
└── utils/                           # Core utilities
    ├── __init__.py
    ├── constants.py                 # Shared constants (e.g. color codes, limits)
    ├── embeds.py                    # Reusable Discord Embed factory helpers
    ├── logger.py                    # DequeLogHandler memory log handler & setup_logging
    └── views.py                     # Reusable discord.ui.View base components
```

---

## ⚙️ 4. Subsystems Overview

1. **Client & Extension Subsystem (`bot.py`, `cogs/`)**:
   `PontoBot` subclasses `commands.Bot` with `message_content` and `members` intents. Configures global slash interaction check (`_is_configured`), dynamically auto-loads extension cogs from `cogs/`, handles prefix and slash command error callbacks, and executes slash command syncing on startup when enabled (`SYNC_COMMANDS`).
   * `cogs/setup.py`: Interactive configuration wizard (`/setup_pontobot`) to bind manager role, track role, clock-in channel, timezone, and language per guild.
   * `cogs/attendance.py`: Text check-in command `!ponto` (alias `!checkin`), customizable historical timesheet reports (`/attendance`), and ranking leaderboards (`/ranking`).
   * `cogs/management.py`: Manager role telemetry dashboard and log stream inspection (`/management`).
2. **Database & Data Access Layer (`database/`)**:
   `DatabaseManager` provides a unified Data Access Layer (DAL) wrapping Tortoise ORM and Aerich migrations. Manages guild setup (`Guild`), user profiles (`User`), server member links (`Member`), attendance check-ins (`Attendance`), and guild metadata (`Metadata`). Features `SafeDateTimeField` for robust SQLite ISO timestamp parsing.
3. **Internationalization Subsystem (`i18n/`)**:
   `TranslationManager` loads locale JSON files and resolves translation strings keyed by locale code. `PontoBotTranslator` implements `discord.app_commands.Translator` to integrate native Discord locale detection into slash command descriptions and choices. Supported locales: `en`, `pt-BR`.
4. **Logging & Utility Subsystem (`utils/`)**:
   `DequeLogHandler` provides an in-memory ring-buffer logger (default max 500 lines) with error callbacks to prevent memory leaks and track runtime errors. `setup_logging` configures root logger formats and output streams. Additional utilities include `embeds.py` (Discord Embed factories), `views.py` (reusable `discord.ui.View` components), and `constants.py` (shared constants).

---

## 🛠️ 5. Development & Validation Commands

All commands must be executed using `uv`:

```bash
# Install dependencies
uv sync

# Run test suite
uv run --no-sync pytest

# Run linter and auto-fix code style (ALWAYS use --fix)
uv run --no-sync ruff check --fix src/ tests/

# Format code
uv run --no-sync ruff format src/ tests/

# Detect dead code
uv run --no-sync deadcode

# Aerich database migration commands
uv run aerich migrate
uv run aerich upgrade

# Run PontoBot main script
uv run python main.py
```

---

## 📍 6. Quick Extension Guide

* **Add a New Command or Cog:** Create a new Python file in `src/pontobot/cogs/` (e.g. `src/pontobot/cogs/analytics.py`), define a subclass of `commands.Cog`, and implement an `async def setup(bot)` function. `PontoBot.setup_hook` will automatically load it.
* **Add or Modify Database Models:** Edit `src/pontobot/database/models.py`, update `DatabaseManager` in `src/pontobot/database/manager.py`, and generate/apply migrations via Aerich (`uv run aerich migrate && uv run aerich upgrade`).
* **Modify Server Setup Settings:** Update the `Guild` model in `src/pontobot/database/models.py`, update `add_guild` in `src/pontobot/database/manager.py`, and update the configuration wizard in `src/pontobot/cogs/setup.py`.

---

## 🎯 7. Non-Negotiable Operational Rules for Agents

Any AI agent working on PontoBot must strictly adhere to these 5 rules:

### 1. Pragmatic Simplicity (KISS)
* Solve problems with the minimum necessary code, abstraction, and complexity.
* Avoid over-engineering. NEVER create generic abstractions or unnecessary helper utilities for simple tasks.

### 2. Zero Tolerance for Ambiguity
* Never assume requirements, business logic, architectures, or unstated behaviors.
* If instructions or contracts are unclear, **STOP IMMEDIATELY** and ask for clarification.

### 3. Surgical Scope
* Keep focus strictly restricted to the requested task. Modify only target files and lines.
* NEVER perform peripheral refactoring, formatting edits in adjacent code, or modifications outside the target module.

### 4. Double-Check Verification Protocol
* Verify delivery before completing:
  1. Does the diff strictly address the requested scope?
  2. Are syntax, typing, and imports correct?
  3. Was static verification executed with `uv run --no-sync ruff check --fix src/ tests/`?
  4. Were tests executed with `uv run --no-sync pytest` and verified to pass?

### 5. Continuous Documentation Maintenance (Keep AGENTS.md Updated)
* Always keep `AGENTS.md` updated whenever architectural patterns, conventions, commands, or workflows evolve.

### 6. Maximum File Length Constraint (<250 lines)
* No single Python source file in `src/` or `tests/` may exceed 250 lines of code. Subdivide modules logically by feature into clean subpackages when files approach this limit. Enabled via `tests/test_code_quality.py`.
