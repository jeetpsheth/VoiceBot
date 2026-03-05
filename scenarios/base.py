"""Base scenario and turn types."""
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Turn:
    """One exchange: agent said X, patient should say Y (or use a function)."""
    # If set, patient says this exactly (or TTS of it).
    patient_says: Optional[str] = None
    # If set, called with (agent_transcript, conversation_so_far) -> next patient line.
    patient_response_fn: Optional[Callable[[str, list], Optional[str]]] = None
    # Optional: after this turn, consider scenario "done" for logging.
    is_final: bool = False


@dataclass
class Scenario:
    """A patient scenario: name, opener, and optional scripted/flexible turns."""
    id: str
    name: str
    description: str
    # First thing the patient says when the call connects.
    opener: str
    # Ordered list of turns. If patient_says is set, use it; else use LLM/fn.
    turns: list[Turn] = field(default_factory=list)
    # If True, use LLM to generate responses from context when no scripted line.
    use_llm_fallback: bool = True
