import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

import discord

from src.aibot.discord.client import BotClient
from src.aibot.infrastructure.tts.voicevox import VoiceVoxTTS
from src.aibot.logger import logger

client = BotClient.get_instance()


class TTSService:
    """Service for TTS."""

    def __init__(self) -> None:
        voicevox_host = os.getenv("VOICEVOX_HOST", "127.0.0.1")
        voicevox_port = os.getenv("VOICEVOX_PORT", "50021")
        voicevox_url = f"http://{voicevox_host}:{voicevox_port}"
        self.voicevox = VoiceVoxTTS(server_url=voicevox_url)
        self.play_queues: dict[int, asyncio.Queue] = {}  # guild_id -> メッセージキュー
        self.playing: dict[int, bool] = {}  # guild_id -> 再生中フラグ

    async def _process_queue(
        self,
        name: str,
        guild_id: int,
        style: str | None = "ノーマル",
    ) -> None:
        self.playing[guild_id] = True
        queue = self.play_queues[guild_id]

        try:
            while not queue.empty():
                text = await queue.get()
                await self._read_text(text, name, guild_id, style)
        finally:
            self.playing[guild_id] = False

    async def _read_text(
        self,
        text: str,
        name: str,
        guild_id: int,
        style: str | None = "ノーマル",
    ) -> None:
        try:
            audio_data = self.voicevox.synthesize(text, name, style)
        except Exception as e:
            logger.exception(f"Failed to synthesize audio: {e}")
            return

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_data)
            temp_path = Path(f.name)

        try:
            guild = client.get_guild(guild_id)
            voice_client = guild.voice_client

            if voice_client and voice_client.is_connected():
                audio_source = discord.FFmpegPCMAudio(str(temp_path))
                playback_finished = asyncio.Event()

                def _after_playing(error: Any):  # noqa: ANN202, ANN401
                    if error:
                        msg = f"Playback error: {error}"
                        logger.error(msg)
                    playback_finished.set()

                voice_client.play(audio_source, after=_after_playing)
                await playback_finished.wait()
        finally:
            if temp_path.exists():
                temp_path.unlink()

    async def queue_message(
        self,
        text: str,
        name: str,
        guild_id: int,
        style: str | None = "ノーマル",
    ) -> None:
        """Queue a message."""
        if guild_id not in self.play_queues:
            self.play_queues[guild_id] = asyncio.Queue()
            self.playing[guild_id] = False

        # Add message to queue
        await self.play_queues[guild_id].put(text)

        if not self.playing[guild_id]:
            task = asyncio.create_task(self._process_queue(name, guild_id, style))
            # Keep reference to prevent garbage collection
            task.add_done_callback(lambda _: None)

    def clear_queue(self, guild_id: int) -> None:
        """Clear the queue."""
        # セッション終了時にキューをクリア
        if guild_id in self.play_queues:
            # キューを空にする
            while not self.play_queues[guild_id].empty():
                try:
                    self.play_queues[guild_id].get_nowait()
                except asyncio.QueueEmpty:
                    break
            self.playing[guild_id] = False
