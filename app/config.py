import os
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ProviderConfig:
    name: str
    model: str
    litellm_prefix: str
    priority: int


@dataclass
class PricingConfig:
    input_per_token: float
    output_per_token: float


PROVIDERS: List[ProviderConfig] = [
    ProviderConfig(
        name="bedrock",
        model="anthropic.claude-3-haiku-20240307-v1:0",
        litellm_prefix="bedrock/",
        priority=1,
    ),
    ProviderConfig(
        name="groq",
        model="llama-3.3-70b-versatile",
        litellm_prefix="groq/",
        priority=2,
    ),
    ProviderConfig(
        name="gemini",
        model="gemini-1.5-flash",
        litellm_prefix="gemini/",
        priority=3,
    ),
]

PRICING: Dict[str, PricingConfig] = {
    "bedrock": PricingConfig(input_per_token=0.00000025, output_per_token=0.00000125),
    "groq": PricingConfig(input_per_token=0.0, output_per_token=0.0),
    "gemini": PricingConfig(input_per_token=0.0, output_per_token=0.0),
}

MAX_OUTPUT_TOKENS_DEFAULT = 1024
MAX_OUTPUT_CAP = 4096

GUARDRAIL_INPUT_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?prior\s+instructions",
    r"ignore\s+above",
    r"disregard\s+above",
    r"system\s*prompt\s*:",
    r"you\s+are\s+now\s+",
    r"act\s+as\s+if\s+you\s+have\s+no\s+restrictions",
    r"pretend\s+you\s+are\s+",
    r"bypass\s+(all\s+)?safety",
    r"override\s+(your\s+)?instructions",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"what\s+(is|are)\s+your\s+(system|initial)\s+(prompt|instructions)",
    r"repeat\s+(everything|all)\s+above",
    r"new\s+instructions\s*:",
    r"forget\s+(everything|all)\s+you\s+know",
]

GUARDRAIL_OUTPUT_PATTERNS = [
    r"(?i)api[_\-\s]?key\s*[:=]\s*[A-Za-z0-9_\-]{20,}",
    r"(?i)secret[_\-\s]?key\s*[:=]\s*[A-Za-z0-9_\-]{20,}",
    r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}",
    r"(?i)(?:AKIA|ASIA|AGPA|AIDA)[0-9A-Z]{12,16}",
]


def aws_credentials_present() -> bool:
    return bool(os.environ.get("AWS_ACCESS_KEY_ID")) and bool(
        os.environ.get("AWS_SECRET_ACCESS_KEY")
    )
