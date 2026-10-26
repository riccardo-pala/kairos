"""Model-provider adapters and their shared prompt."""

from kairos.providers.huggingface import HuggingFaceEventProvider
from kairos.providers.ollama import OllamaEventProvider, OllamaMetrics
from kairos.providers.prompts import SYSTEM_PROMPT
from kairos.providers.scripted import ScriptedEventProvider

__all__ = [
    "HuggingFaceEventProvider",
    "OllamaEventProvider",
    "OllamaMetrics",
    "SYSTEM_PROMPT",
    "ScriptedEventProvider",
]
