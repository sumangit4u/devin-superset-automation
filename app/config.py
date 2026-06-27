"""Runtime configuration, loaded from environment variables.

Nothing secret is hard-coded. Copy `.env.example` to `.env` and fill in values.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

try:  # optional convenience for local dev
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional
    pass


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    # --- Devin API ---
    devin_api_key: str = os.getenv("DEVIN_API_KEY", "")
    devin_api_base: str = os.getenv("DEVIN_API_BASE", "https://api.devin.ai/v1")

    # --- GitHub ---
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    webhook_secret: str = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    target_repo: str = os.getenv("TARGET_REPO", "sumangit4u/superset")
    trigger_label: str = os.getenv("TRIGGER_LABEL", "devin-fix")

    # --- Behaviour ---
    # SIMULATE=true runs the whole pipeline against an in-process fake Devin,
    # so the system can be demoed end-to-end with no API key.
    simulate: bool = _bool("SIMULATE", False)
    poll_interval_seconds: int = int(os.getenv("POLL_INTERVAL_SECONDS", "15"))
    db_path: str = os.getenv("DB_PATH", "data/runs.db")

    @property
    def effective_simulate(self) -> bool:
        """Fall back to simulation automatically when no key is configured."""
        return self.simulate or not self.devin_api_key


CONFIG = Config()
