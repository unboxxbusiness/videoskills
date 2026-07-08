"""
Kampus Filter — Structured Logger
Configures consistent logging with timestamps and structured output.
"""

import logging
import sys
from datetime import datetime


def setup_logger(name: str = "kampus_filter", level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return the root Kampus Filter logger.

    Format: [TIMESTAMP] LEVEL | logger_name — message

    Args:
        name:  Logger name.
        level: Logging level (default: INFO).

    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s | %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    return logger


class RunStats:
    """
    Lightweight execution statistics collector for a single pipeline run.
    Logged at the end of each execution for observability.
    """

    def __init__(self) -> None:
        self.start_time = datetime.now()
        self.channels_scanned: int = 0
        self.channels_failed: int = 0
        self.videos_fetched: int = 0
        self.shorts_found: int = 0
        self.long_videos_found: int = 0
        self.filtered_out: int = 0
        self.viral_shorts: int = 0
        self.viral_longs: int = 0
        self.trending_topics: int = 0
        self.opportunities: int = 0
        self.api_quota_used: int = 0
        self.errors: list = []

    def add_error(self, channel: str, error: str) -> None:
        self.errors.append({"channel": channel, "error": error})

    def elapsed_seconds(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()

    def summary(self) -> str:
        lines = [
            "=" * 65,
            "  Kampus Filter — Execution Summary",
            "=" * 65,
            f"  Channels scanned      : {self.channels_scanned}",
            f"  Channels failed       : {self.channels_failed}",
            f"  Videos fetched        : {self.videos_fetched}",
            f"  ├── Shorts found      : {self.shorts_found}",
            f"  └── Long videos found : {self.long_videos_found}",
            f"  Filtered out (niche)  : {self.filtered_out}",
            f"  Viral Shorts (≥10k)   : {self.viral_shorts}",
            f"  Viral Long Videos     : {self.viral_longs}",
            f"  Trending Topics       : {self.trending_topics}",
            f"  Opportunities ranked  : {self.opportunities}",
            f"  API quota used (est.) : {self.api_quota_used} units",
            f"  Execution time        : {self.elapsed_seconds():.1f}s",
        ]
        if self.errors:
            lines.append(f"  Errors                : {len(self.errors)}")
            for err in self.errors[:5]:
                lines.append(f"    • {err['channel']}: {err['error']}")
        lines.append("=" * 65)
        return "\n".join(lines)
