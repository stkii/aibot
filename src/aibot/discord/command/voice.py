import json
from pathlib import Path

from discord import Interaction, SelectOption, VoiceClient
from discord.ui import Select, View

from src.aibot.discord.client import BotClient
from src.aibot.infrastructure.dao.connection import ConnectionDAO
from src.aibot.infrastructure.dao.tts import TTSSessionDAO
from src.aibot.logger import logger
from src.aibot.service.tts import TTSService

client = BotClient.get_instance()
connection_dao = ConnectionDAO()
tts_session_dao = TTSSessionDAO()
tts_service = TTSService()


# Load speakers configuration
def _load_speakers() -> dict[str, dict[str, int]]:
    """Load speaker configuration from JSON file.

    Returns
    -------
    dict[str, dict[str, int]]
        Dictionary mapping speaker names to their styles and IDs

    """
    current_path = Path(__file__).resolve()
    speakers_path = None

    for parent in current_path.parents:
        if (parent / "pyproject.toml").exists():
            speakers_path = parent / "resources" / "speakers.json"
            break

    if speakers_path is None or not speakers_path.exists():
        logger.error("speakers.json not found")
        return {}

    try:
        with speakers_path.open(encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        logger.error(f"Failed to load speakers.json: {e}")
        return {}


def _get_default_speaker_settings() -> dict[str, str]:
    """Get default speaker settings from speakers.json.

    Returns
    -------
    dict[str, str]
        Default speaker and style settings

    """
    speakers = _load_speakers()
    if not speakers:
        logger.warning("No speakers data available, using fallback defaults")
        return {"speaker": "四国めたん", "style": "ノーマル"}

    # Get first speaker and first style from speakers.json
    first_speaker = next(iter(speakers.keys()))
    first_style = next(iter(speakers[first_speaker].keys()))

    return {"speaker": first_speaker, "style": first_style}


def _get_guild_speaker_settings(guild_id: int) -> dict[str, str]:
    """Get speaker settings for a guild.

    Parameters
    ----------
    guild_id : int
        Discord guild ID

    Returns
    -------
    dict[str, str]
        Speaker and style settings for the guild

    """
    return guild_speaker_settings.get(guild_id, _get_default_speaker_settings())


# Guild speaker settings storage
guild_speaker_settings: dict[int, dict[str, str]] = {}


class SpeakerSelector(Select):
    """Discord UI selector for choosing speaker settings with two-stage selection."""

    def __init__(
        self,
        guild_id: int,
        stage: str = "speaker",
        selected_speaker: str | None = None,
    ) -> None:
        """Initialize the speaker selector.

        Parameters
        ----------
        guild_id : int
            Guild ID for settings
        stage : str, optional
            Selection stage ("speaker" or "style"), by default "speaker"
        selected_speaker : str | None, optional
            Selected speaker (for style selection), by default None

        """
        self.guild_id = guild_id
        self.stage = stage
        self.selected_speaker = selected_speaker
        self.speakers_data = _load_speakers()

        if stage == "speaker":
            options = self._create_speaker_options()
            placeholder = "話者を選択してください..."
        else:  # style
            options = self._create_style_options()
            placeholder = f"{selected_speaker} のスタイルを選択してください..."

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
        )

    def _create_speaker_options(self) -> list[SelectOption]:
        """Create speaker selection options.

        Returns
        -------
        list[SelectOption]
            List of speaker options for dropdown menu

        """
        options = []
        options = [
            SelectOption(
                label=speaker_name,
                value=speaker_name,
                description=f"{speaker_name} を選択",
            )
            for speaker_name in self.speakers_data
        ]
        return options[:25]  # Discord limit

    def _create_style_options(self) -> list[SelectOption]:
        """Create style selection options for the selected speaker.

        Returns
        -------
        list[SelectOption]
            List of style options for the selected speaker

        """
        if not self.selected_speaker or self.selected_speaker not in self.speakers_data:
            return []

        options = []
        styles = self.speakers_data[self.selected_speaker]
        options = [
            SelectOption(
                label=style_name,
                value=style_name,
                description=f"{self.selected_speaker} の {style_name} スタイル",
            )
            for style_name in styles
        ]
        return options[:25]  # Discord limit

    async def callback(self, interaction: Interaction) -> None:
        """Handle user selection in the dropdown menu.

        Parameters
        ----------
        interaction : Interaction
            Discord interaction object

        """
        try:
            await interaction.response.defer(ephemeral=True)

            if self.stage == "speaker":
                # Speaker selected, move to style selection
                selected_speaker = self.values[0]

                # Create new selector for style selection
                style_selector = SpeakerSelector(
                    guild_id=self.guild_id,
                    stage="style",
                    selected_speaker=selected_speaker,
                )
                view = View()
                view.add_item(style_selector)

                await interaction.edit_original_response(
                    content=f"**話者選択:** {selected_speaker}\n\nスタイルを選択してください:",
                    view=view,
                )

            else:  # style
                # Style selected, save settings and complete
                selected_style = self.values[0]

                # Save guild settings
                guild_speaker_settings[self.guild_id] = {
                    "speaker": self.selected_speaker,
                    "style": selected_style,
                }

                await interaction.edit_original_response(
                    content=f"話者設定を更新しました!\n"
                    f"**話者:** {self.selected_speaker}\n"
                    f"**スタイル:** {selected_style}",
                    view=None,
                )

                logger.info(
                    "Speaker settings updated for guild %s: speaker=%s, style=%s",
                    self.guild_id,
                    self.selected_speaker,
                    selected_style,
                )

        except Exception as e:
            logger.error("Failed to handle voice selection: %s", e)
            await interaction.edit_original_response(
                content="設定の更新中にエラーが発生しました",
                view=None,
            )


@client.tree.command(name="join", description="ボイスチャンネルに接続します")
async def join_command(interaction: Interaction) -> None:
    """Join a voice channel and start TTS session.

    Parameters
    ----------
    interaction : Interaction
        Discord interaction object

    """
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message(
            "このコマンドはボイスチャンネルに接続しているユーザーのみ使用できます。",
            ephemeral=True,
        )
        return

    await interaction.response.defer()

    try:
        voice_channel = interaction.user.voice.channel
        await voice_channel.connect()
        await interaction.followup.send("接続しました!")
    except Exception as e:
        msg = f"Error in join command: {e!s}"
        logger.exception(msg)
        await interaction.followup.send(
            "ボイスチャンネルに接続できませんでした",
            ephemeral=True,
        )
        return

    try:
        await connection_dao.log_connect(
            str(voice_channel.id),
            str(interaction.guild.id),
        )
        await tts_session_dao.create_tts_session(
            str(interaction.guild.id),
            str(interaction.channel.id),
            str(voice_channel.id),
        )

        tts_start_message = "接続しました"
        settings = _get_guild_speaker_settings(interaction.guild.id)
        await tts_service.queue_message(
            tts_start_message,
            settings["speaker"],
            interaction.guild.id,
            settings["style"],
        )
    except Exception as e:
        msg = f"Error in join command: {e!s}"
        logger.exception(msg)
        await interaction.followup.send(
            "TTSを開始できませんでした",
            ephemeral=True,
        )


@client.tree.command(name="leave", description="ボイスチャンネルから切断します")
async def leave_command(interaction: Interaction) -> None:
    """Leave from voice channel and end TTS session.

    Parameters
    ----------
    interaction : Interaction
        Discord interaction object

    """
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message(
            "このコマンドはボイスチャンネルに接続しているユーザーのみ使用できます。",
            ephemeral=True,
        )
        return

    await interaction.response.defer()

    try:
        voice_client = interaction.guild.voice_client
        # VoiceClient is a subclass of VoiceProtocol
        if voice_client and isinstance(voice_client, VoiceClient) and voice_client.is_connected():
            await voice_client.disconnect()
            await tts_session_dao.end_tts_session(str(interaction.guild.id))
            tts_service.clear_queue(interaction.guild.id)
            await interaction.followup.send("ボイスチャンネルから切断しました", ephemeral=True)
        else:
            await interaction.followup.send(
                "ボイスチャンネルに接続していません",
                ephemeral=True,
            )
    except Exception as e:
        msg = f"Error in leave command: {e!s}"
        logger.exception(msg)
        await interaction.followup.send(
            "ボイスチャンネルから切断できませんでした",
            ephemeral=True,
        )


@client.tree.command(name="read", description="テキスト読み上げ機能をオン/オフします")
async def read_command(interaction: Interaction) -> None:
    """Toggle text-to-speech reading for the current text channel.

    Parameters
    ----------
    interaction : Interaction
        Discord interaction object

    """
    # Check if user is in a voice channel
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message(
            "このコマンドはボイスチャンネルに接続しているユーザーのみ使用できます。",
            ephemeral=True,
        )
        return

    # Check if bot is connected to voice channel in this guild
    voice_client = interaction.guild.voice_client
    if (
        not voice_client
        or not isinstance(voice_client, VoiceClient)
        or not voice_client.is_connected()
    ):
        await interaction.response.send_message(
            "ボイスチャンネルに接続していません。先に `/join` コマンドを使用してください。",
            ephemeral=True,
        )
        return

    await interaction.response.defer()

    try:
        # Toggle reading status
        new_status = await tts_session_dao.toggle_reading(
            str(interaction.guild.id),
            str(interaction.channel.id),
        )

        if new_status:
            await interaction.followup.send(
                "読み上げを開始しました",
            )
        else:
            await interaction.followup.send(
                "読み上げを開始できませんでした",
                ephemeral=True,
            )

    except Exception as e:
        msg = f"Error in read command: {e!s}"
        logger.exception(msg)
        await interaction.followup.send(
            "読み上げ開始プロセスにおいてエラーが発生しました",
            ephemeral=True,
        )


@client.tree.command(name="speaker", description="音声合成の話者とスタイルを設定します")
async def speaker_command(interaction: Interaction) -> None:
    """Configure voice synthesis speaker and style settings.

    Parameters
    ----------
    interaction : Interaction
        Discord interaction object

    """
    try:
        # Get current settings
        current_settings = _get_guild_speaker_settings(interaction.guild.id)
        current_speaker = current_settings["speaker"]
        current_style = current_settings["style"]

        # Check if speakers data is available
        speakers_data = _load_speakers()
        if not speakers_data:
            await interaction.response.send_message(
                "話者データを読み込めませんでした",
                ephemeral=True,
            )
            return

        # Create speaker selector
        speaker_selector = SpeakerSelector(guild_id=interaction.guild.id, stage="speaker")
        view = View()
        view.add_item(speaker_selector)

        await interaction.response.send_message(
            f"===== 現在の話者設定 =====\n"
            f"話者: {current_speaker}\n"
            f"スタイル: {current_style}\n\n"
            f"新しい話者を選択してください:",
            view=view,
            ephemeral=True,
        )

    except Exception as e:
        msg = f"Error in speaker command: {e!s}"
        logger.exception(msg)
        await interaction.response.send_message(
            "コマンドの処理中にエラーが発生しました",
            ephemeral=True,
        )
