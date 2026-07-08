"""
Kampus Filter — Viral Scoring Engine
Pure functions for computing engagement metrics and virality scores.
"""

import re
from datetime import datetime, timezone
from typing import Tuple


# ---------------------------------------------------------------------------
# Duration Parsing
# ---------------------------------------------------------------------------

_DURATION_RE = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def parse_duration(iso_duration: str) -> int:
    """
    Convert ISO 8601 duration string (e.g. PT1M34S) to total seconds.

    Args:
        iso_duration: ISO 8601 duration string from YouTube API.

    Returns:
        Total duration in seconds.
    """
    match = _DURATION_RE.match(iso_duration or "PT0S")
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


# ---------------------------------------------------------------------------
# Video Classification
# ---------------------------------------------------------------------------

def classify_video_type(duration_seconds: int):
    """
    Classify a video as SHORT or LONG based on duration.
    Imports VideoType at call time to avoid circular imports.
    """
    from models import VideoType
    return VideoType.SHORT if duration_seconds <= 60 else VideoType.LONG


# ---------------------------------------------------------------------------
# Core Virality Formula
# ---------------------------------------------------------------------------

def calculate_viral_score(
    views: int,
    likes: int,
    comments: int,
    published_at_str: str,
) -> Tuple[float, float, float]:
    """
    Compute a composite Viral Score (0–100) for a video.

    Scoring breakdown:
      - 40%: View Velocity (views per hour since publish)
      - 30%: Engagement Rate ((likes + comments) / views)
      - 20%: Freshness (how recent the video is, within 7 days)
      - 10%: Like Ratio (likes / views)

    Args:
        views:           Total view count.
        likes:           Total like count.
        comments:        Total comment count.
        published_at_str: ISO 8601 publish timestamp.

    Returns:
        Tuple of (viral_score, view_velocity, engagement_rate_pct).
    """
    if views == 0:
        return 0.0, 0.0, 0.0

    # Hours since publication
    try:
        published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        hours_since = max((now - published_at).total_seconds() / 3600.0, 0.5)
    except Exception:
        hours_since = 720.0  # default: ~30 days

    # Core metrics
    view_velocity = views / hours_since
    engagement_rate = (likes + comments) / views
    like_ratio = likes / views

    # Freshness (1.0 if brand-new, 0.0 after 7 days)
    freshness = max(0.0, 1.0 - (hours_since / (7.0 * 24.0)))

    # Composite score (capped at 100)
    score = (
        (min(view_velocity, 10_000.0) / 10_000.0) * 40.0
        + (min(engagement_rate, 0.30) / 0.30) * 30.0
        + freshness * 20.0
        + (min(like_ratio, 0.10) / 0.10) * 10.0
    )

    return (
        round(min(score, 100.0), 2),
        round(view_velocity, 2),
        round(engagement_rate * 100.0, 4),
    )
