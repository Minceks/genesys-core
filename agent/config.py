from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv


DEFAULT_GENESYS_MODEL = "openai/gpt-oss-120b"
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
DEFAULT_AGENT_TIMEOUT_SECONDS = 120

VALID_PROVIDERS = {
    "groq",
    "gemini",
}


MIN_PYTHON_VERSION = (3, 14)


def validate_python_runtime() -> None:
    if sys.version_info < MIN_PYTHON_VERSION:
        required = ".".join(
            str(part)
            for part in MIN_PYTHON_VERSION
        )

        current = ".".join(
            str(part)
            for part in sys.version_info[:3]
        )

        raise RuntimeError(
            f"Python {required}+ is required. "
            f"Current runtime is Python {current}."
        )
    

load_dotenv()


@dataclass(frozen=True)
class Settings:
    daytona_api_key: str
    groq_api_key: str
    gemini_api_key: str

    genesys_model: str = DEFAULT_GENESYS_MODEL
    genesys_gemini_model: str = DEFAULT_GEMINI_MODEL
    agent_timeout_seconds: int = DEFAULT_AGENT_TIMEOUT_SECONDS

    provider_name: str = "groq"
    fallback_provider: str = "gemini"
    cors_origins: str = "*"
    api_key: str = ""


def _required_env(name: str) -> str:
    value = os.getenv(name)

    if value is None or not value.strip():
        raise ValueError(
            f"{name} is required but is not configured."
        )

    return value.strip()


def _optional_env(
    name: str,
    default: str,
) -> str:
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    return value.strip()


def _provider_env(
    name: str,
    default: str,
) -> str:
    value = _optional_env(
        name,
        default,
    ).lower()

    if value not in VALID_PROVIDERS:
        allowed = ", ".join(
            sorted(VALID_PROVIDERS)
        )

        raise ValueError(
            f"{name} must be one of: {allowed}."
        )

    return value


def _positive_int_env(
    name: str,
    default: int,
) -> int:
    value = os.getenv(
        name,
        str(default),
    )

    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(
            f"{name} must be a positive integer."
        ) from exc

    if parsed <= 0:
        raise ValueError(
            f"{name} must be a positive integer."
        )

    return parsed


def load_settings() -> Settings:
    validate_python_runtime()

    return Settings(
        daytona_api_key=_required_env(
            "DAYTONA_API_KEY"
        ),
        groq_api_key=_required_env(
            "GROQ_API_KEY"
        ),
        gemini_api_key=_required_env(
            "GEMINI_API_KEY"
        ),
        genesys_model=_optional_env(
            "GENESYS_MODEL",
            DEFAULT_GENESYS_MODEL,
        ),
        genesys_gemini_model=_optional_env(
            "GENESYS_GEMINI_MODEL",
            DEFAULT_GEMINI_MODEL,
        ),
        agent_timeout_seconds=_positive_int_env(
            "GENESYS_AGENT_TIMEOUT_SECONDS",
            DEFAULT_AGENT_TIMEOUT_SECONDS,
        ),
        provider_name=_provider_env(
            "GENESYS_PROVIDER",
            "groq",
        ),
        fallback_provider=_provider_env(
            "GENESYS_FALLBACK_PROVIDER",
            "gemini",
        ),
        cors_origins=_optional_env(
            "GENESYS_CORS_ORIGINS",
            "*",
        ),
        api_key=_optional_env(
            "GENESYS_API_KEY",
            "",
        ),
    )

def validate_settings(
    settings: Settings,
) -> None:
    if settings.provider_name not in VALID_PROVIDERS:
        raise ValueError(
            "Configured provider is invalid."
        )

    if settings.fallback_provider not in VALID_PROVIDERS:
        raise ValueError(
            "Configured fallback provider is invalid."
        )

    if (
        settings.provider_name
        == settings.fallback_provider
    ):
        raise ValueError(
            "Fallback provider must differ from the active provider."
        )

    if settings.agent_timeout_seconds <= 0:
        raise ValueError(
            "Agent timeout must be positive."
        )

    if not settings.genesys_model.strip():
        raise ValueError(
            "GENESYS_MODEL must be configured."
        )

    if not settings.genesys_gemini_model.strip():
        raise ValueError(
            "GENESYS_GEMINI_MODEL must be configured."
        )