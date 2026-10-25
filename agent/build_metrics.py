"""Request-local measurements; shared safely by parallel drafting workers."""
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import Lock
from time import perf_counter

current = ContextVar('genesys_build_metrics', default=None)


@dataclass
class BuildMetrics:
    started: float = field(default_factory=perf_counter)
    responses: int = 0
    tokens: int = 0
    repairs: int = 0
    lock: Lock = field(default_factory=Lock)

    def record(self, response):
        usage = getattr(response, 'usage', None) or getattr(response, 'usage_metadata', None)
        tokens = getattr(usage, 'total_tokens', None) or getattr(usage, 'total_token_count', None)
        with self.lock:
            self.responses += 1
            if isinstance(tokens, int) and tokens >= 0:
                self.tokens += tokens

    def summary(self, result):
        return {'durationSeconds': round(perf_counter() - self.started, 2),
                'modelResponses': self.responses, 'reportedTokens': self.tokens,
                'filesChanged': len(result.get('modifiedFiles') or []),
                'repairAttempts': max(self.repairs, (result.get('selfHealing') or {}).get('attempts', 0)),
                'scope': 'Provider-reported responses/tokens; excludes unreported failed calls. No estimated monetary cost.'}


def record_repair():
    metrics = current.get()
    if metrics is not None:
        with metrics.lock:
            metrics.repairs += 1
