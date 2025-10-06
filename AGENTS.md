# Repository Guidelines

## Project Structure & Module Organization
- `src/aibot/`: Discord bot source (client, commands, events, services, DAOs).
  - Entry point: `src/aibot/__main__.py` (`python -m src.aibot`).
  - Config: `resources/agents.yml` (agent definitions). 
- `docs/`: Project documentation.
- `logs/`: Runtime logs.
- `aibot.db`: Local SQLite database (created on first run).
- Containerization: `Dockerfile`, `docker-compose.yml` (includes VoiceVox).

## Build, Test, and Development Commands
- Setup (uv recommended):
  - `uv sync --dev` — create venv and install deps.
  - `source .venv/bin/activate` — activate shell (if needed).
- Run locally:
  - `uv run python -m src.aibot`
- Lint and Type Check:
  - `uv run ruff check .` and `uv run ruff format .`
  - `uv run mypy src`
- Docker:
  - `docker compose up --build` — start VoiceVox and the bot.

## Coding Style & Naming Conventions
- Python 3.12; PEP 8 with 4‑space indents; line length 99.
- Prefer double quotes; no tabs; trailing commas allowed.
- Use `ruff` and `mypy` (strict). Avoid `print`; use `src/aibot/logger.py`.
- Naming: modules `snake_case.py`; classes `CapWords`; funcs/vars `snake_case`; constants `UPPER_SNAKE`.

## Testing Guidelines
- No test suite yet. Prefer `pytest` with files in `tests/test_*.py`.
- Keep unit tests fast and isolated; mock external APIs.
- Example: `uv run pytest -q` (once tests are added).

## Commit & Pull Request Guidelines
- Use conventional prefixes (see `.github/.gitmessage`): `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, `test:`, etc. Indicate breaking changes explicitly.
- PRs must include: clear description, rationale, screenshots/logs when UI/behavior changes, and linked issues.
- Before opening a PR: run `ruff` and `mypy`; update docs and `resources/agents.yml` if behavior changes.

## Security & Configuration Tips
- Provide `.env` with: `DISCORD_BOT_TOKEN`, optional `ADMIN_USER_IDS`, `TIMEZONE`, `VOICEVOX_HOST/PORT`, and model API keys as needed (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`). Do not commit `.env`.
- SQLite file (`aibot.db`) may contain user/usage data; handle responsibly.

## Agent-Specific Instructions
- Define agents in `resources/agents.yml` (keys under `agents:` with `model` and `instruction`).
- The app creates a triage agent at runtime and hands off to configured agents. You do not need to define triage in YAML.
- Tools: the current loader does not resolve string tool names to SDK `Tool` objects; omit `tools` unless you wire real tools in code.
