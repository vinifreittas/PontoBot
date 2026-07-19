<div align="center" id="top">
  <h1>🎯 PontoBot</h1>

  <p align="center">
    <b>An enterprise-grade automated attendance tracker, frequency reporter, and timesheet manager engineered for Discord servers.</b>
  </p>

  <!-- Shields and Badges Gallery -->
  <p align="center">
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version"></a>
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

Built on modern asynchronous architectures utilizing **discord.py** and **Tortoise ORM**, it provides seamless multi-tenant isolation. All server rules, access layers, and operational histories are securely committed to a zero-configuration SQLite local instance.

---

## 🚀 Key Value Propositions

* **⚡ Zero-Friction Onboarding:** Automated server configuration executed by an intuitive, step-by-step interactive configuration wizard.
* **⏰ Legacy & Slash Support:** Supports lightning-fast classic text commands (`!ponto`) for active workflows and rich Slash Commands for data inspection.
* **📊 Granular Reporting Modules:** Export highly customizable timesheet profiles filtered by targeted user, distinct dates, or specific community milestones.
* **🏆 Leaderboards & Engagement:** Dynamic ranking grids showcasing your most consistent community or team operators.
* **🛡️ Resilient Recovery Layer:** Built-in fault tolerance that queues and logs disrupted events during brief internet drops or system outages.

---

## ⌨️ Command Reference

### Text Commands

| Command | Operational Scope | Context Description |
| :--- | :--- | :--- |
| `!ponto` | 📍 Tracking Channel Only | Creates a chronological attendance timestamp for the message author. |

### Slash Commands (`/`)

| Command | Access Layer | Functional Execution |
| :--- | :--- | :--- |
| `/setup_pontobot` | ⚙️ Administrator | Initializes the interactive server configuration engine. |
| `/frequencia` | 👥 Member / Admin | Extracts specific historical logs over customizable intervals. |
| `/ranking` | 🌍 Public | Visualizes community interaction metrics in real-time. |
| `/gerenciamento` | 💼 Manager Role | Displays telemetry parameters and raw diagnostic streams. |

---

## 🛠️ Prerequisites

Ensure your host container or dedicated machine fits the following operating baselines:

* **Runtime Engine:** Python version `3.10` or higher installed.
* **Gateway Credentials:** A distinct Discord Token derived from the official [Discord Developer Portal](https://discord.com/developers/applications).
* **Gateway Privileges:** Explicit validation for `Message Content` and `Guild Members` Privileged Intents inside your application control array.

---

## 📦 Quick Start Execution

### 1. Installation

Isolate dependencies using an execution container or local virtual package sandbox:

```bash
# Clone the remote code matrix
git clone [https://github.com/vinifreittas/pontobot.git](https://github.com/vinifreittas/pontobot.git)
cd pontobot

# Establish your dedicated virtual sandbox
python -m venv .venv
source .venv/bin/activate  # Windows users run: .venv\Scripts\activate

# Install package architecture in an editable state
pip install -e .

```

### 2. Configuration Matrix

> [!IMPORTANT]
> Never persist raw API credentials directly inside code files. Always supply environment configurations via system environment parameters or secure secret lockers.

```bash
# Append your live token key to active memory
export DISCORD_TOKEN="your-super-secret-bot-token"

```

Construct an entry execution module (e.g., `run_bot.py`):

```python
import os
from pontobot import PontoBot

if __name__ == "__main__":
    # Instantiate the application wrapper
    bot = PontoBot()
    
    # Fire up the persistent event cluster
    bot.run(os.environ["DISCORD_TOKEN"])

```

Boot the service runtime:

```bash
python run_bot.py

```

---

## 🗺️ System Initialization Guide

When PontoBot maps to your target Guild cluster, complete these setup parameters:

1. Target a safe operational tracking text channel.
2. Call the administrative initialization module: `/setup_pontobot`.
3. Provide the context arguments requested by the prompt matrix:

```
├── Manager Role    --> Authorized group allowed to call management views
├── Tag Role        --> Target users subjected to tracking parameters
├── Target Channel  --> The restricted viewport allocated for text log check-ins
└── Timezone        --> Dynamic time offset configurations (e.g., America/Sao_Paulo)

```

---

## 📁 Repository Blueprint

```directory
src/
└── pontobot/
    ├── bot.py             # Client pipeline bootstrap configuration
    ├── cogs/              # Asynchronous command structures
    │   ├── frequencia.py
    │   ├── gerenciamento.py
    │   └── setup.py
    └── database/          # Persistent schema models
        ├── manager.py
        ├── models.py
        └── migrations/

```

---

## 🏗️ Architectural Notes

* **Data Isolation:** Configuration schemes are parsed per guild. Multiple Discord servers can host a single bot instance completely independently without data pollution.
* **Default Database Engine:** Uses SQLite for local zero-configuration deployment. Can easily be updated via Tortoise ORM configuration mappings to scale up to PostgreSQL or MySQL if required.

---

## ⚖️ License

Distributed completely open-source under the guidelines of the **MIT License**. For complete compliance requirements, see the full [LICENSE](https://www.google.com/search?q=LICENSE) asset wrapper.
