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
```bash
# Run the Discord bot
uv run python -m src.aibot

# Or using the module directly
uv run python src/aibot/__main__.py
```

## Architecture Overview

### High-Level Structure
This is a Discord AI bot built with discord.py that integrates multiple LLM providers (Anthropic Claude, OpenAI GPT, Google Gemini). The architecture follows a layered pattern with clear separation of concerns:

```
src/aibot/
├── discord/           # Discord-specific layer
│   ├── client.py      # Singleton bot client
│   ├── command/       # Slash commands
│   └── decorator/     # Access control and usage decorators
├── service/           # Business logic layer
├── infrastructure/    # Data access layer
│   ├── api/          # LLM provider integrations
│   └── dao/          # Database operations
└── model/            # Data models
```

### Key Components

**Discord Layer (`discord/`)**
- `BotClient`: Singleton Discord client with slash command tree
- Commands: `/chat` (AI responses), `/create` (custom instructions), `/provider` (model selection)
- Decorators: `@is_admin_user`, `@is_restricted`, `@usage_limit` for access control

**Service Layer (`service/`)**
- `InstructionService`: Manages custom system instructions (stored in `resources/instructions/`)
- `ResponseFactory`: Multi-provider LLM response generation with unified interface
- `TaskScheduler`: Background task management (usage limit resets)

**Infrastructure Layer (`infrastructure/`)**
- `api/`: Provider-specific implementations for Anthropic, OpenAI, Google AI
- `dao/`: SQLite database operations for instructions and usage tracking

**Configuration**
- `resources/llm-models.json`: Model configurations with parameters (temperature, max_tokens, top_p)
- Environment variables: `DISCORD_BOT_TOKEN`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ADMIN_USER_IDS`

### Key Patterns

**Singleton Pattern**: Used extensively for `BotClient`, `InstructionService`, `ResponseFactory` to maintain single instances

**Factory Pattern**: `ResponseFactory` abstracts LLM provider differences behind unified interface

**Decorator Pattern**: Access control through decorators that check admin status, restrictions, and usage limits

**DAO Pattern**: Database operations abstracted through Data Access Objects with base class validation

### Database Schema
- `custom_instruction`: Stores user-created system instructions with metadata
- `user_limits`: Daily usage limits per user
- `usage_tracking`: Usage history for rate limiting

### Custom Instructions System
- Static instructions: `resources/instructions/instructions.yml` (YAML format)
- Dynamic instructions: Generated in `resources/instructions/gen/` (text files)
- UI: Discord select menus populated from filesystem, admin-only creation/management

### Multi-Provider LLM Support
The bot supports three LLM providers with automatic failover and consistent parameter handling:
- Anthropic Claude (default)
- Google Gemini
- OpenAI GPT

Model selection is admin-controlled via `/provider` command, with configurations stored in `llm-models.json`.
