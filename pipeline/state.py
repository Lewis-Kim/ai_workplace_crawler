# pipeline/state.py
from __future__ import annotations

from watchdog.observers import Observer   # ✅ 유일한 정답
from datetime import datetime

observer: Observer | None = None
started_at: datetime | None = None
