<div align="center" id="top">
  <h1>🎯 PontoBot</h1>

  <p align="center">
    <b>An enterprise-grade automated attendance tracker, frequency reporter, and timesheet manager engineered for Discord servers.</b>
  </p>

  <!-- Shields and Badges Gallery -->
  <p align="center">
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version"></a>
    <a href="https://discordpy.readthedocs.io/"><img src="https://img.shields.io/badge/Discord.py-2.4%2B-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord.py"></a>
    <a href="https://tortoise.github.io/"><img src="https://img.shields.io/badge/Database-Tortoise%20ORM-EE6C4D?style=for-the-badge&logo=sqlite&logoColor=white" alt="Database ORM"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-F5A623?style=for-the-badge" alt="License"></a>
  </p>

  <p align="center">
    <img src="https://img.shields.io/github/stars/vinifreittas/pontobot?style=flat-square&color=40c463" alt="Stars">
    <img src="https://img.shields.io/github/issues/vinifreittas/pontobot?style=flat-square&color=ea4335" alt="Issues">
    <img src="https://img.shields.io/github/last-commit/vinifreittas/pontobot?style=flat-square&color=059669" alt="Last Commit">
  </p>

</div>

---

## 📖 Introduction

**PontoBot** is a reliable, high-performance Discord bot engineered to track team attendance, generate comprehensive frequency reports, and streamline organizational data management directly inside your server ecosystem.

Built on modern asynchronous architectures utilizing **discord.py** and **Tortoise ORM**, it provides seamless multi-tenant isolation per Discord guild. All server rules, access layers, and operational histories are securely persisted to a zero-configuration SQLite local instance (upgradeable to PostgreSQL). The bot also ships with a full internationalization layer supporting **English** and **Brazilian Portuguese** out of the box, with native Discord slash-command locale integration.

---

## 🚀 Key Value Propositions

* **⚡ Zero-Friction Onboarding:** Automated server configuration executed by an intuitive, step-by-step interactive configuration wizard.
* **⏰ Legacy & Slash Support:** Supports lightning-fast classic text commands (`!ponto`) for active workflows and rich Slash Commands for data inspection.
* **📊 Granular Reporting Modules:** Export highly customizable timesheet profiles filtered by targeted user, distinct dates, or specific community milestones.
* **🏆 Leaderboards & Engagement:** Dynamic ranking grids showcasing your most consistent community or team operators.
* **🛡️ Resilient Recovery Layer:** Built-in fault tolerance that queues and logs disrupted events during brief internet drops or system outages.
* **🌐 Multilingual:** Native Discord locale detection with full English and Brazilian Portuguese support.

---

## ⌨️ Command Reference

### Text Commands

| Command | Operational Scope | Context Description |
| :--- | :--- | :--- |
| `!ponto` (alias `!checkin`) | 📍 Tracking Channel Only | Creates a chronological attendance timestamp for the message author. |

### Slash Commands (`/`)

| Command | Access Layer | Functional Execution |
| :--- | :--- | :--- |
| `/setup_pontobot` | ⚙️ Administrator | Initializes the interactive server configuration engine. |
| `/attendance` | 👥 Member / Admin | Extracts specific historical logs over customizable intervals. |
| `/ranking` | 🌍 Public | Visualizes community interaction metrics in real-time. |
| `/management` | 💼 Manager Role | Displays telemetry parameters and raw diagnostic streams. |

---

## 🛠️ Prerequisites

Ensure your host machine fits the following baselines:

* **Runtime Engine:** Python version `3.12` or higher installed.
* **Package Manager:** [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`.
* **Gateway Credentials:** A distinct Discord Token derived from the official [Discord Developer Portal](https://discord.com/developers/applications).
* **Gateway Privileges:** Explicit validation for `Message Content` and `Guild Members` Privileged Intents inside your application control panel.

---

## 📦 Quick Start

### 1. Clone & Install

```bash
# Clone the repository
git clone https://github.com/vinifreittas/pontobot.git
cd pontobot

# Install dependencies via uv (recommended)
uv sync
```

### 2. Configuration

> [!IMPORTANT]
> Never persist raw API credentials directly inside code files. Always supply environment configurations via system environment variables or a secure secret manager.

```bash
export DISCORD_TOKEN="your-super-secret-bot-token"
```

Optional environment variables:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DISCORD_TOKEN` | *(required)* | Bot authentication token |
| `DATABASE_URL` | `sqlite://db.sqlite3` | Tortoise ORM database URL |
| `SYNC_COMMANDS` | `false` | Sync global slash commands on startup |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### 3. Run

```bash
uv run python main.py
```

---

## 🗺️ System Initialization Guide

When PontoBot joins your Discord server, complete these setup steps:

1. Target a safe operational tracking text channel.
2. Call the administrative initialization command: `/setup_pontobot`.
3. Provide the following configuration arguments via the interactive wizard:

```
├── Manager Role    --> Authorized group allowed to call management views
├── Tag Role        --> Target users subjected to tracking parameters
├── Target Channel  --> The restricted channel allocated for text check-ins (!ponto)
└── Timezone        --> Dynamic time offset (e.g., America/Sao_Paulo, Europe/London)
```

---

## 📁 Repository Structure

```
src/
└── pontobot/
    ├── bot.py                    # PontoBot client bootstrap & cog auto-loader
    ├── cogs/                     # Discord Cog subpackages
    │   ├── attendance/           # !ponto check-in, /attendance reports, /ranking
    │   ├── management/           # /management dashboard & log stream
    │   └── setup/                # /setup_pontobot configuration wizard
    ├── database/                 # Tortoise ORM models, DatabaseManager DAL, migrations
    ├── i18n/                     # Internationalization (TranslationManager, PontoBotTranslator, locales/)
    └── utils/                    # Shared utilities (embeds, logger, views, constants)
tests/                            # pytest test suite
main.py                           # Entry point
```

---

## 🏗️ Architectural Notes

* **Data Isolation:** Configuration schemes are parsed per guild. Multiple Discord servers can share a single bot instance completely independently, without data pollution.
* **Default Database Engine:** Uses SQLite for local zero-configuration deployment. Easily upgradeable to PostgreSQL via the `DATABASE_URL` environment variable and Tortoise ORM configuration.
* **Internationalization:** The `PontoBotTranslator` integrates with Discord's native locale detection to render slash command descriptions and response strings in the user's locale. The guild's configured language (`Guild.language`) is persisted in the database and used as a fallback when a Discord locale is not available.
* **Dependency Direction:** `database / utils / i18n` ← `cogs` ← `bot` ← `main.py`. Lower layers never import from higher ones.

---

## ⚖️ License

Distributed completely open-source under the guidelines of the **MIT License**. For complete compliance requirements, see the full [LICENSE](LICENSE) file.
