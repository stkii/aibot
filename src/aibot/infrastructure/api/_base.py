from dataclasses import dataclass


@dataclass(frozen=True)
class ParamsBase:
    """Base class for API parameters."""

    model: str
    max_tokens: int
    temperature: float
    top_p: float
