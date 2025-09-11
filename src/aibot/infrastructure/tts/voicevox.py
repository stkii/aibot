import json
from pathlib import Path

import requests

from src.aibot.logger import logger

from ._base import TTSBase


class VoiceVoxTTS(TTSBase):  # noqa: D101
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

        with speakers_path.open() as f:
            return json.load(f)

    def _resolve_speaker_id(self, name: str, style: str | None = "ノーマル") -> int | None:
        """Get speaker ID from name and style."""
        try:
            return self.speakers[name][style]
        except KeyError:
            msg = f"Speaker not found: {name} ({style})"
            logger.warning(msg)
            return None

    def synthesize(
        self,
        text: str,
        name: str,
        style: str | None = None,
    ) -> bytes:
        """Synthesize text into audio and return as wav/mp3 binary."""
        speaker_id = self._resolve_speaker_id(name, style)

        if speaker_id is None:
            msg = f"Cannot synthesize: invalid speaker {name} ({style})"
            logger.error(msg)
            raise ValueError(msg)

        # audio query
        resp = requests.post(
            f"{self.server_url}/audio_query",
            params={"text": text, "speaker": speaker_id},
            timeout=10,
        )
        resp.raise_for_status()
        query = resp.json()

        # synthesis
        try:
            res = requests.post(
                f"{self.server_url}/synthesis",
                params={"speaker": speaker_id},
                headers={"Content-Type": "application/json"},
                data=json.dumps(query, ensure_ascii=False),
                timeout=20,
            )
        except Exception as e:
            msg = f"Failed to synthesize audio: {e}"
            logger.error(msg)
            raise
        else:
            return res.content
