from abc import ABC, abstractmethod


class TTSBase(ABC):
    @abstractmethod
    async def synthesize(self, text: str, name: str, style: str | None = None) -> bytes:
        """Synthesize text into audio and return as wav/mp3 binary."""

    async def close(self) -> None:
        """Release allocated resources if needed."""
        return
