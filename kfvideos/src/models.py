"""
Kampus Filter — Data Models
Typed dataclasses for all entities in the competitor intelligence pipeline.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class VideoType(str, Enum):
    SHORT = "short"
    LONG = "long"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ContentType(str, Enum):
    SHORTS = "Shorts"
    LONG_FORM = "Long-form"
    BOTH = "Both"


class TrendDirection(str, Enum):
    RISING = "Rising"
    STABLE = "Stable"
    DECLINING = "Declining"


# ---------------------------------------------------------------------------
# Core Models
# ---------------------------------------------------------------------------

@dataclass
class Competitor:
    """Represents a configured competitor YouTube channel."""
    name: str
    channel_id: str
    priority: int
    category: str
    handle: str = ""
    uploads_playlist_id: Optional[str] = None

    def __repr__(self) -> str:
        return f"Competitor(name={self.name!r}, priority={self.priority})"


@dataclass
class CompetitorVideo:
    """Full metadata and analytics for a single competitor video."""
    channel_name: str
    channel_id: str
    video_id: str
    video_type: VideoType
    title: str
    description: str
    views: int
    likes: int
    comments: int
    duration: int           # seconds
    published_at: str       # ISO 8601
    viral_score: float      # 0–100
    topic: str              # Clustered topic label
    thumbnail: str          # URL
    url: str                # YouTube URL
    tags: List[str] = field(default_factory=list)
    category_id: str = ""
    engagement_rate: float = 0.0   # percentage
    view_velocity: float = 0.0     # views per hour

    def to_dict(self) -> dict:
        """Serialize to plain dictionary for JSON output."""
        return {
            "channel_name": self.channel_name,
            "channel_id": self.channel_id,
            "video_id": self.video_id,
            "video_type": self.video_type.value,
            "title": self.title,
            "description": self.description[:300],
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "duration_seconds": self.duration,
            "published_at": self.published_at,
            "viral_score": self.viral_score,
            "topic": self.topic,
            "thumbnail": self.thumbnail,
            "url": self.url,
            "tags": self.tags[:10],
            "engagement_rate_pct": self.engagement_rate,
            "view_velocity": self.view_velocity,
        }


@dataclass
class TrendingTopic:
    """A clustered topic identified across multiple competitor videos."""
    topic_name: str
    competitors: List[str]
    total_videos: int
    total_views: int
    avg_engagement: float
    trend_direction: TrendDirection
    content_type: ContentType
    priority: Priority
    kampus_filter_angle: str
    related_video_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "topic_name": self.topic_name,
            "competitors": self.competitors,
            "total_videos": self.total_videos,
            "total_views": self.total_views,
            "avg_engagement_pct": self.avg_engagement,
            "trend_direction": self.trend_direction.value,
            "content_type": self.content_type.value,
            "priority": self.priority.value,
            "kampus_filter_angle": self.kampus_filter_angle,
            "related_video_ids": self.related_video_ids[:5],
        }


@dataclass
class ContentOpportunity:
    """A ranked content opportunity for Kampus Filter to create a Short on."""
    rank: int
    topic: str
    student_value_score: float      # 0–10
    search_demand_score: float      # 0–10
    viral_potential_score: float    # 0–10
    time_sensitive: bool
    alignment_score: float          # 0–10 (brand fit)
    overall_score: float            # weighted composite
    recommended_angle: str
    related_video_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "topic": self.topic,
            "student_value_score": self.student_value_score,
            "search_demand_score": self.search_demand_score,
            "viral_potential_score": self.viral_potential_score,
            "time_sensitive": self.time_sensitive,
            "alignment_score": self.alignment_score,
            "overall_score": self.overall_score,
            "recommended_angle": self.recommended_angle,
            "related_video_ids": self.related_video_ids[:5],
        }
