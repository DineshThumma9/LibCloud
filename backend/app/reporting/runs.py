"""Per-run identity for scan records stored in MongoDB."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

_INVALID_USERNAME_CHARS = re.compile(r"[^a-z0-9-]+")
_REPEATED_HYPHENS = re.compile(r"-{2,}")


def sanitize_username(username: str) -> str:
    """Return a safe, lowercased GitHub username."""
    cleaned = _INVALID_USERNAME_CHARS.sub("-", (username or "").strip().lower())
    cleaned = _REPEATED_HYPHENS.sub("-", cleaned).strip("-")
    return cleaned[:39] or "unknown"


@dataclass(frozen=True)
class RunContext:
    """Identity for one scan."""

    username: str
    run_id: str
    started_at: datetime

    @classmethod
    def create(cls, username: str) -> "RunContext":
        started_at = datetime.now(timezone.utc)
        return cls(
            username=sanitize_username(username),
            run_id=f"{started_at.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}",
            started_at=started_at,
        )
