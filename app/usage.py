import threading
import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ProviderUsage:
    request_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_cost: float = 0.0


class UsageTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self._providers: Dict[str, ProviderUsage] = {}
        self._total_requests: int = 0

    def record(
        self,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
    ):
        with self._lock:
            if provider not in self._providers:
                self._providers[provider] = ProviderUsage()
            p = self._providers[provider]
            p.request_count += 1
            p.total_input_tokens += input_tokens
            p.total_output_tokens += output_tokens
            p.estimated_cost += cost
            self._total_requests += 1

    def get_summary(self) -> dict:
        with self._lock:
            by_provider = {}
            total_tokens = 0
            total_cost = 0.0
            for name, p in self._providers.items():
                provider_tokens = p.total_input_tokens + p.total_output_tokens
                total_tokens += provider_tokens
                total_cost += p.estimated_cost
                by_provider[name] = {
                    "request_count": p.request_count,
                    "input_tokens": p.total_input_tokens,
                    "output_tokens": p.total_output_tokens,
                    "total_tokens": provider_tokens,
                    "estimated_cost": round(p.estimated_cost, 6),
                }
            return {
                "total_requests": self._total_requests,
                "total_tokens": total_tokens,
                "total_estimated_cost": round(total_cost, 6),
                "by_provider": by_provider,
            }


tracker = UsageTracker()
