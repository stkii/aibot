# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Dependencies
```bash
# Install dependencies using uv (Python package manager)
uv sync

# Run with development dependencies
uv sync --group dev
```

### Code Quality
```bash
# Lint code with ruff
uv run ruff check

# Format code with ruff
uv run ruff format

# Type checking with mypy
uv run mypy src/
```

### Running the Bot

#### Local Development
```bash
# Run the Discord bot locally
uv run python -m src.aibot

# Or using the module directly
uv run python src/aibot/__main__.py

# With custom log level
uv run python -m src.aibot --log DEBUG
```

#### Docker Development
```bash
# Start all services (AIBot + VOICEVOX TTS engine)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Individual service operations
docker-compose up -d voicevox        # Start only VOICEVOX
docker-compose restart aibot         # Restart only AIBot
docker-compose logs -f aibot         # View only AIBot logs
```

## Architecture Overview

### High-Level Structure
This is a Discord AI bot built with discord.py that uses OpenAI Agents API for AI responses and includes Japanese text-to-speech capabilities via VOICEVOX. The architecture follows a layered pattern:

```
src/aibot/
├── discord/           # Discord-specific layer
│   ├── client.py      # Singleton bot client
│   ├── command/       # Slash commands (/ai, /voice, /limit)
│   ├── decorator/     # Access control and usage decorators
│   └── event.py       # Discord event handlers
├── service/           # Business logic layer
│   ├── agents.py      # OpenAI Agents service
│   ├── scheduler.py   # Background task scheduling
│   ├── restriction.py # User restriction management
│   └── tts.py         # Text-to-speech service
├── infrastructure/    # Data access layer
│   ├── api/agents.py  # OpenAI Agents API integration
│   ├── dao/           # Database operations (agents, usage, TTS)
│   └── tts/           # VOICEVOX TTS implementation
├── model/             # Data models
└── logger.py          # Centralized logging
```

### Key Components

**Discord Commands**
- `/ai <message>`: Main AI interaction using OpenAI Agents
- `/voice`: Text-to-speech commands with speaker selection
- `/limit`: Usage limit management for administrators

**Agent System**
- Agents defined in `resources/agents.yml` with custom instructions per agent type
- Current agents: `general` (casual conversation), `code` (code assistance)
- Uses OpenAI GPT-4o-mini model by default
- Supports character-based responses with Japanese language focus

**TTS Integration**
- VOICEVOX engine integration for Japanese text-to-speech
- Speaker configuration in `resources/speakers.json`
- Supports multiple voice characters (四国めたん, ずんだもん, etc.)
- Docker-based VOICEVOX engine deployment

**Usage Control**
- Daily usage limits per user with SQLite persistence
- Usage tracking across all bot interactions
- Administrator controls for limit management

### Configuration Files

**Agent Configuration (`resources/agents.yml`)**
- Defines agent personalities and system instructions
- Model selection per agent type
- Character-specific response guidelines

**Speaker Configuration (`resources/speakers.json`)**
- VOICEVOX speaker definitions and voice parameters
- Character-to-voice mapping for TTS functionality

**Environment Variables**
- `DISCORD_BOT_TOKEN`: Discord bot authentication
- `OPENAI_API_KEY`: OpenAI API access for agents
- `VOICEVOX_HOST`, `VOICEVOX_PORT`: TTS engine connection
- `ADMIN_USER_IDS`: Bot administrator Discord user IDs

### Database Schema
- `agent_conversations`: Tracks agent conversation history and usage
- `user_limits`: Daily usage limits per user
- `usage_tracking`: Usage history for rate limiting
- `tts_requests`: TTS request logging and speaker preferences

### Docker Integration
Uses docker-compose for orchestrated deployment:
- `voicevox` service: TTS engine with health checks
- `aibot` service: Main Discord bot with volume mounts for configuration

### Development Patterns
- **Singleton Pattern**: Used for `BotClient` to maintain single Discord connection
- **DAO Pattern**: Database operations abstracted through Data Access Objects
- **Decorator Pattern**: Usage limiting and access control via decorators (`@has_daily_usage_left`)
- **Service Layer**: Business logic separated from Discord and infrastructure concerns
