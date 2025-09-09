from abc import ABC, abstractmethod


class TTSBase(ABC):
    @abstractmethod
    def synthesize(self, text: str, name: str, style: str | None = None) -> bytes:
        """Synthesize text into audio and return as wav/mp3 binary."""
