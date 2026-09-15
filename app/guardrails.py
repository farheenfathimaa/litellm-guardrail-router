import re
import time
from dataclasses import dataclass
from typing import List, Optional

from app.config import (
    GUARDRAIL_INPUT_PATTERNS,
    GUARDRAIL_OUTPUT_PATTERNS,
    MAX_OUTPUT_CAP,
)


@dataclass
class GuardrailEvent:
    timestamp: float
    stage: str
    reason: str
    flagged_content: str = ""


_block_events: List[GuardrailEvent] = []


def _get_input_patterns():
    return [re.compile(p, re.IGNORECASE) for p in GUARDRAIL_INPUT_PATTERNS]


def _get_output_patterns():
    return [re.compile(p) for p in GUARDRAIL_OUTPUT_PATTERNS]


_input_patterns = _get_input_patterns()
_output_patterns = _get_output_patterns()


def check_input(messages: list) -> Optional[str]:
    text_parts = []
    for msg in messages:
        if isinstance(msg, dict):
            text_parts.append(msg.get("content", ""))
        elif isinstance(msg, str):
            text_parts.append(msg)
    combined = " ".join(text_parts)

    for pattern in _input_patterns:
        match = pattern.search(combined)
        if match:
            reason = f"Prompt injection detected: matched pattern '{match.group()}'"
            _block_events.append(
                GuardrailEvent(
                    timestamp=time.time(),
                    stage="input",
                    reason=reason,
                    flagged_content=match.group(),
                )
            )
            return reason
    return None


def check_output(response_text: str) -> List[str]:
    flags = []
    if len(response_text) > MAX_OUTPUT_CAP:
        flag = f"Response length {len(response_text)} exceeds cap of {MAX_OUTPUT_CAP}"
        flags.append(flag)
        _block_events.append(
            GuardrailEvent(
                timestamp=time.time(),
                stage="output",
                reason=flag,
            )
        )

    for pattern in _output_patterns:
        match = pattern.search(response_text)
        if match:
            flag = f"Output contains suspicious pattern: '{match.group()}'"
            flags.append(flag)
            _block_events.append(
                GuardrailEvent(
                    timestamp=time.time(),
                    stage="output",
                    reason=flag,
                    flagged_content=match.group(),
                )
            )
    return flags


def get_events() -> List[dict]:
    return [
        {
            "timestamp": e.timestamp,
            "stage": e.stage,
            "reason": e.reason,
            "flagged_content": e.flagged_content,
        }
        for e in _block_events
    ]
