from __future__ import annotations

import asyncio
import os
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import discord

from src.aibot.discord.client import BotClient
from src.aibot.infrastructure.tts.voicevox import VoiceVoxTTS
from src.aibot.logger import logger

client = BotClient.get_instance()


@dataclass(slots=True)
class GuildPlaybackState:
    worker_lock: asyncio.Lock
    worker_task: asyncio.Task[None] | None = None


class TTSService:
    """Service for TTS playback orchestration."""

    _instance: TTSService | None = None

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return

        voicevox_host = os.getenv("VOICEVOX_HOST", "127.0.0.1")
        voicevox_port = os.getenv("VOICEVOX_PORT", "50021")
        voicevox_url = f"http://{voicevox_host}:{voicevox_port}"

        self.voicevox = VoiceVoxTTS(server_url=voicevox_url)
        self._guild_states: dict[int, GuildPlaybackState] = {}
        self._started = False
        self._initialized = True

    @classmethod
    def get_instance(cls) -> TTSService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def startup(self) -> None:
        """Initialize runtime state."""
        if self._started:
            return
        self._started = True
        logger.info("TTS service started")

    async def shutdown(self) -> None:
        """Stop all workers and release resources."""
        if not self._started:
            return

        for guild_id in list(self._guild_states.keys()):
            await self.stop_guild(guild_id)

        await self.voicevox.close()
        self._started = False
        logger.info("TTS service stopped")

    def _get_or_create_state(self, guild_id: int) -> GuildPlaybackState:
        state = self._guild_states.get(guild_id)
        if state is None:
            state = GuildPlaybackState(
                worker_lock=asyncio.Lock(),
            )
            self._guild_states[guild_id] = state
        return state

    def _on_worker_done(self, guild_id: int, task: asyncio.Task[None]) -> None:
        state = self._guild_states.get(guild_id)
        if state and state.worker_task is task:
            state.worker_task = None

        if task.cancelled():
            return

        exc = task.exception()
        if exc is not None:
            logger.error("TTS worker failed in guild %s: %s", guild_id, exc)

    async def _play_once(
        self,
        text: str,
        speaker: str,
        guild_id: int,
        style: str | None = "ノーマル",
    ) -> None:
        try:
            await self._read_text(text, speaker, guild_id, style)
        except Exception as e:
            logger.exception("Failed to process TTS playback in guild %s: %s", guild_id, e)

    async def _read_text(
        self,
        text: str,
        name: str,
        guild_id: int,
        style: str | None = "ノーマル",
    ) -> None:
        try:
            audio_data = await self.voicevox.synthesize(text, name, style)
        except Exception as e:
            logger.exception("Failed to synthesize audio: %s", e)
            return

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_data)
            temp_path = Path(f.name)

        try:
            guild = client.get_guild(guild_id)
            if guild is None:
                return

            voice_client = guild.voice_client
            if not isinstance(voice_client, discord.VoiceClient):
                return
            if not voice_client.is_connected():
                return

            audio_source = discord.FFmpegPCMAudio(str(temp_path))
            playback_finished = asyncio.Event()
            loop = asyncio.get_running_loop()

            def _after_playing(error: Any):  # noqa: ANN202, ANN401
                if error:
                    logger.error("Playback error in guild %s: %s", guild_id, error)
                loop.call_soon_threadsafe(playback_finished.set)

            voice_client.play(audio_source, after=_after_playing)
            try:
                await asyncio.wait_for(playback_finished.wait(), timeout=120)
            except TimeoutError:
                logger.warning("Playback timed out in guild %s; stopping current audio", guild_id)
                voice_client.stop()
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
        """Play message if idle. Drop new message while already playing."""
        if not self._started:
            await self.startup()

        state = self._get_or_create_state(guild_id)
        async with state.worker_lock:
            if state.worker_task and not state.worker_task.done():
                logger.debug(
                    "Skip TTS message in guild %s because playback is already running",
                    guild_id,
                )
                return

            task = asyncio.create_task(
                self._play_once(text, name, guild_id, style),
                name=f"tts-worker:{guild_id}",
            )
            state.worker_task = task
            task.add_done_callback(lambda t, gid=guild_id: self._on_worker_done(gid, t))

    async def stop_guild(self, guild_id: int) -> None:
        """Stop current playback task for a guild."""
        state = self._guild_states.get(guild_id)
        if state is None:
            return

        guild = client.get_guild(guild_id)
        if guild is not None:
            voice_client = guild.voice_client
            if (
                isinstance(voice_client, discord.VoiceClient)
                and voice_client.is_connected()
                and voice_client.is_playing()
            ):
                voice_client.stop()

        task: asyncio.Task[None] | None = None
        async with state.worker_lock:
            if state.worker_task and not state.worker_task.done():
                state.worker_task.cancel()
                task = state.worker_task
            state.worker_task = None

        if task is not None:
            with suppress(asyncio.CancelledError):
                await task

        self._guild_states.pop(guild_id, None)

    def clear_queue(self, guild_id: int) -> None:
        """No-op: queueing is disabled and messages are dropped while playing."""

    def is_running(self, guild_id: int) -> bool:
        state = self._guild_states.get(guild_id)
        if state is None or state.worker_task is None:
            return False
        return not state.worker_task.done()
