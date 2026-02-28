import asyncio
import json
from pathlib import Path

import requests

from src.aibot.logger import logger

from ._base import TTSBase


class VoiceVoxTTS(TTSBase):
    def __init__(
        self,
        server_url: str = "http://127.0.0.1:50021",
        speakers: dict[str, dict[str, int]] | None = None,
    ) -> None:
        self.server_url = server_url
        self.speakers = speakers if speakers is not None else self._load_speakers()

    def _load_speakers(self) -> dict[str, dict[str, int]]:
        """Load speaker configuration from JSON file."""
        current_path = Path(__file__).resolve()
        speakers_path = None

        for parent in current_path.parents:
            if (parent / "pyproject.toml").exists():
                speakers_path = parent / "resources" / "speakers.json"
                break

        if speakers_path is None or not speakers_path.exists():
            msg = "pyproject.toml or speakers.json is not found"
            logger.error(msg)
            raise FileNotFoundError(msg)

        with speakers_path.open(encoding="utf-8") as f:
            return json.load(f)

    def _resolve_speaker_id(self, name: str, style: str | None = "ノーマル") -> int | None:
        """Get speaker ID from name and style."""
        style_key = style or "ノーマル"
        try:
            return self.speakers[name][style_key]
        except KeyError:
            msg = f"Speaker not found: {name} ({style_key})"
            logger.warning(msg)
            return None

    def _synthesize_sync(self, text: str, name: str, style: str | None = None) -> bytes:
        speaker_id = self._resolve_speaker_id(name, style)
        if speaker_id is None:
            msg = f"Cannot synthesize: invalid speaker {name} ({style})"
            logger.error(msg)
            raise ValueError(msg)

        # audio query
        query_resp = requests.post(
            f"{self.server_url}/audio_query",
            params={"text": text, "speaker": speaker_id},
            timeout=10,
        )
        query_resp.raise_for_status()
        query = query_resp.json()

        # synthesis
        synthesis_resp = requests.post(
            f"{self.server_url}/synthesis",
            params={"speaker": speaker_id},
            headers={"Content-Type": "application/json"},
            data=json.dumps(query, ensure_ascii=False),
            timeout=20,
        )
        synthesis_resp.raise_for_status()
        return synthesis_resp.content

    async def synthesize(
        self,
        text: str,
        name: str,
        style: str | None = None,
    ) -> bytes:
        """Synthesize text into audio and return as wav binary."""
        return await asyncio.to_thread(self._synthesize_sync, text, name, style)

    async def close(self) -> None:
        """No-op: per-request HTTP connection is used."""
