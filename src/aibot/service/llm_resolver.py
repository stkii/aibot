import json
from pathlib import Path
from typing import Any

from discord import app_commands

from src.aibot.logger import logger
from src.aibot.service.provider import ProviderManager, ProviderType


class LlmConfig:
    """LLM model configuration class."""

    def __init__(self, config_dict: dict[str, Any]) -> None:
        """Initialize LLM model config from dictionary.

        Parameters
        ----------
        config_dict : dict[str, Any]
            LLM model configuration dictionary from JSON.

        """
        self.id: str = config_dict["id"]
        self.display_name: str = config_dict["display_name"]
        self.provider: ProviderType = config_dict["provider"]
        self.params: dict[str, Any] = config_dict["params"]


class LlmResolver:
    """Resolves LLM model selection for Discord commands based on configuration."""

    _config_cache: dict[str, Any] | None = None
    _instance: "LlmResolver | None" = None

    def __new__(cls) -> "LlmResolver":
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "LlmResolver":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_llm_model_config(self) -> dict[str, Any]:
        """Load LLM model configuration from JSON file."""
        if self._config_cache is not None:
            return self._config_cache

        current_path = Path(__file__).resolve()
        config_path = None

        for parent in current_path.parents:
            if (parent / "pyproject.toml").exists():
                config_path = parent / "resources" / "llm-models.json"
                break

        if config_path is None or not config_path.exists():
            msg = "pyproject.toml or llm-models.json is not found"
            logger.error(msg)
            raise FileNotFoundError(msg)

        with config_path.open() as f:
            self._config_cache = json.load(f)

        return self._config_cache

    def _get_default_model_for_provider(self, provider: ProviderType) -> LlmConfig:
        """Get default model for specified provider.

        Parameters
        ----------
        provider : ProviderType
            The provider type.

        Returns
        -------
        LlmConfig
            Default model for the provider.

        Raises
        ------
        ValueError
            If no default LLM models are available.

        """
        default_models = self.get_default_llm_models()

        # Find model matching provider
        for model in default_models:
            if model.provider == provider:
                return model

        # This should not happen with proper configuration
        msg = "No default LLM models available"
        logger.error(msg)
        raise ValueError(msg)

    def get_llm_models_for_command(self, command_name: str) -> list[LlmConfig]:
        """Get available LLM models for a specific command.

        Parameters
        ----------
        command_name : str
            The name of the Discord command.

        Returns
        -------
        list[LlmConfig]
            List of available LLM models for the command.

        """
        config = self._load_llm_model_config()
        command_key = f"{command_name}_models"

        if command_key in config:
            return [LlmConfig(model_dict) for model_dict in config[command_key]]

        # Return empty list if no specific models for command
        return []

    def get_default_llm_models(self) -> list[LlmConfig]:
        """Get default LLM models.

        Returns
        -------
        list[LlmConfig]
            List of default LLM models.

        """
        config = self._load_llm_model_config()
        return [LlmConfig(model_dict) for model_dict in config.get("default_models", [])]

    def resolve_llm_model_for_command(
        self,
        command_name: str,
        selected_model_id: str | None = None,
    ) -> LlmConfig:
        """Resolve the appropriate LLM model for a command based on selection logic.

        Parameters
        ----------
        command_name : str
            The name of the Discord command.
        selected_model_id : str | None
            Optionally selected LLM model ID from UI choices.

        Returns
        -------
        LlmConfig
            The resolved LLM model configuration.

        """
        command_models = self.get_llm_models_for_command(command_name)
        provider_manager = ProviderManager.get_instance()
        current_provider = provider_manager.get_provider()

        # If specific model is selected from UI choices, use it
        if selected_model_id is not None and command_models:
            for model in command_models:
                if model.id == selected_model_id:
                    return model

        # If command has specific models
        if command_models and len(command_models) == 1:
            # Single model - check provider compatibility
            model = command_models[0]
            if model.provider == current_provider:
                return model
            # Provider mismatch - fallback to default
            return self._get_default_model_for_provider(current_provider)

        # No command-specific models - use default for current provider
        return self._get_default_model_for_provider(current_provider)

    def get_llm_model_choices_for_command(
        self,
        command_name: str,
    ) -> list[app_commands.Choice[str]]:
        """Get Discord app_commands choices for a command.

        Parameters
        ----------
        command_name : str
            The name of the Discord command.

        Returns
        -------
        list[app_commands.Choice[str]]
            List of choices for the command.

        """
        command_models = self.get_llm_models_for_command(command_name)
        return [
            app_commands.Choice(name=model.display_name, value=model.id)
            for model in command_models
        ]


def get_llm_model_choices(command_name: str) -> list[app_commands.Choice[str]]:
    """Get model choices for use with @app_commands.choices() decorator.

    This function provides a convenient way to get model choices for commands
    that need to use the @app_commands.choices() decorator.

    Parameters
    ----------
    command_name : str
        The name of the Discord command.

    Returns
    -------
    list[app_commands.Choice[str]]
        List of choices for use with @app_commands.choices().

    Examples
    --------
    ```python
    @app_commands.choices(model=get_model_choices("key_name"))
    async def some_command(interaction: Interaction, model: str | None = None):
        # model parameter will have choices automatically applied
        pass
    ```

    """
    resolver = LlmResolver.get_instance()
    return resolver.get_llm_model_choices_for_command(command_name)
