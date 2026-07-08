"""
Kampus Filter — Pipeline Orchestrator Core Engine
Contains the shared pipeline execution logic, scanning, ranking, and storage functions.
This is imported by individual brand fetch scripts.
"""

import json
import logging
import os
import sys
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Core imports from sibling src files
# ---------------------------------------------------------------------------
from logger_config import RunStats, setup_logger
from models import (
    Competitor,
    CompetitorVideo,
    ContentOpportunity,
    TrendingTopic,
    VideoType,
)
from scorer import calculate_viral_score, classify_video_type, parse_duration
from topic_cluster import (
    classify_topic,
    cluster_trending_topics,
    generate_opportunities,
    is_niche_relevant,
)
from youtube_client import YouTubeClient

logger = logging.getLogger("kampus_filter")

# ---------------------------------------------------------------------------
# Default Pipeline Parameters
# ---------------------------------------------------------------------------
MIN_VIEWS_SHORTS: int = 10_000
MIN_VIEWS_LONG: int = 10_000
TOP_N: int = 20
MAX_WORKERS: int = 5           # concurrent channel fetches
PLAYLIST_MAX: int = 25         # newest uploads per channel
SEARCH_MAX: int = 25           # top-viewed search results per channel
SKIP_SEARCH: bool = True       # Toggle expensive search API (100 units/call)


# ===========================================================================
# Helper Core Functions
# ===========================================================================

def load_competitors(config_path: str) -> List[Competitor]:
    """Load competitor list from configuration JSON."""
    with open(config_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    competitors = []
    for item in data.get("competitors", []):
        competitors.append(Competitor(
            name=item["name"],
            channel_id=item.get("channel_id", ""),
            priority=int(item.get("priority", 3)),
            category=item.get("category", ""),
            handle=item.get("handle", ""),
        ))

    competitors.sort(key=lambda c: c.priority)
    logger.info("Loaded %d competitors from config.", len(competitors))
    return competitors


def resolve_competitor(competitor: Competitor, client: YouTubeClient) -> Optional[Competitor]:
    """Resolve channel ID and uploads playlist ID from handle."""
    channel_item = client.resolve_channel(
        channel_id=competitor.channel_id,
        handle=competitor.handle,
    )
    if not channel_item:
        logger.warning("Could not resolve channel: %s (handle=%s)", competitor.name, competitor.handle)
        return None

    competitor.channel_id = channel_item["id"]
    competitor.uploads_playlist_id = client.get_uploads_playlist_id(channel_item)

    if not competitor.uploads_playlist_id:
        logger.warning("No uploads playlist found for: %s", competitor.name)
        return None

    logger.info("Resolved: %-30s → channel_id=%s", competitor.name, competitor.channel_id)
    return competitor


def fetch_channel_videos(
    competitor: Competitor,
    client: YouTubeClient,
    stats: RunStats,
    skip_search: bool = True,
) -> List[CompetitorVideo]:
    """Fetch recent uploads and optionally search for top-viewed videos."""
    video_ids: List[str] = []

    # Newest uploads
    if competitor.uploads_playlist_id:
        ids = client.get_playlist_video_ids(competitor.uploads_playlist_id, PLAYLIST_MAX)
        video_ids.extend(ids)

    # Top-viewed search
    if not skip_search and competitor.channel_id:
        ids = client.search_channel_videos(competitor.channel_id, SEARCH_MAX, order="viewCount")
        video_ids.extend(ids)

    # De-duplicate IDs
    seen = set()
    unique_ids = []
    for vid in video_ids:
        if vid not in seen:
            seen.add(vid)
            unique_ids.append(vid)

    if not unique_ids:
        return []

    # Batch retrieve details
    raw_items = []
    for i in range(0, len(unique_ids), 50):
        batch = unique_ids[i : i + 50]
        raw_items.extend(client.get_video_details(batch))

    stats.videos_fetched += len(raw_items)
    results: List[CompetitorVideo] = []

    for item in raw_items:
        video = _build_video(item, competitor)
        if video is None:
            stats.filtered_out += 1
            continue

        if video.views < MIN_VIEWS_SHORTS:
            stats.filtered_out += 1
            continue

        if not is_niche_relevant(video.title, video.description):
            stats.filtered_out += 1
            continue

        if video.video_type == VideoType.SHORT:
            stats.shorts_found += 1
        else:
            stats.long_videos_found += 1

        results.append(video)

    return results


def _build_video(raw: Dict, competitor: Competitor) -> Optional[CompetitorVideo]:
    """Build competitor video dataclass from raw api dict."""
    try:
        snippet = raw["snippet"]
        stats_raw = raw.get("statistics", {})
        content = raw.get("contentDetails", {})

        duration_sec = parse_duration(content.get("duration", "PT0S"))
        video_type = classify_video_type(duration_sec)

        views = int(stats_raw.get("viewCount", 0))
        likes = int(stats_raw.get("likeCount", 0))
        comments = int(stats_raw.get("commentCount", 0))
        published_at = snippet.get("publishedAt", "")
        title = snippet.get("title", "")
        description = snippet.get("description", "")

        viral_score, velocity, engagement = calculate_viral_score(
            views, likes, comments, published_at
        )
        topic = classify_topic(title, description)

        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
            or ""
        )

        video_id = raw["id"]
        url = (
            f"https://youtube.com/shorts/{video_id}"
            if video_type == VideoType.SHORT
            else f"https://youtube.com/watch?v={video_id}"
        )

        return CompetitorVideo(
            channel_name=competitor.name,
            channel_id=competitor.channel_id,
            video_id=video_id,
            video_type=video_type,
            title=title,
            description=description,
            views=views,
            likes=likes,
            comments=comments,
            duration=duration_sec,
            published_at=published_at,
            viral_score=viral_score,
            topic=topic,
            thumbnail=thumbnail_url,
            url=url,
            tags=snippet.get("tags", []),
            category_id=snippet.get("categoryId", ""),
            engagement_rate=engagement,
            view_velocity=velocity,
        )
    except Exception:
        return None


def scan_all_competitors(
    competitors: List[Competitor],
    client: YouTubeClient,
    stats: RunStats,
    skip_search: bool = True,
) -> List[CompetitorVideo]:
    """Scan all channels using a concurrent thread pool."""
    all_videos: List[CompetitorVideo] = []

    def _process(competitor: Competitor) -> Tuple[str, List[CompetitorVideo]]:
        resolved = resolve_competitor(competitor, client)
        if resolved is None:
            return competitor.name, []
        videos = fetch_channel_videos(resolved, client, stats, skip_search)
        return competitor.name, videos

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_process, c): c for c in competitors}
        for future in as_completed(futures):
            comp = futures[future]
            try:
                name, videos = future.result()
                stats.channels_scanned += 1
                all_videos.extend(videos)
                logger.info("Processed competitor: %-30s → %d videos", name, len(videos))
            except Exception as exc:
                stats.channels_failed += 1
                stats.add_error(comp.name, str(exc))
                logger.error("Error processing competitor %s: %s", comp.name, exc)

    return all_videos


def rank_shorts(videos: List[CompetitorVideo]) -> List[CompetitorVideo]:
    shorts = [v for v in videos if v.video_type == VideoType.SHORT]
    return sorted(shorts, key=lambda v: v.viral_score, reverse=True)[:TOP_N]


def rank_long_videos(videos: List[CompetitorVideo]) -> List[CompetitorVideo]:
    longs = [v for v in videos if v.video_type == VideoType.LONG]
    return sorted(longs, key=lambda v: v.viral_score, reverse=True)[:TOP_N]


def save_report(
    all_videos: List[CompetitorVideo],
    top_shorts: List[CompetitorVideo],
    top_long: List[CompetitorVideo],
    trending: List[TrendingTopic],
    opportunities: List[ContentOpportunity],
    stats: RunStats,
    output_path: str,
) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execution_time_seconds": round(stats.elapsed_seconds(), 2),
        "summary": {
            "channels_scanned": stats.channels_scanned,
            "total_videos_analyzed": len(all_videos),
            "total_shorts": stats.shorts_found,
            "total_long_videos": stats.long_videos_found,
            "filtered_out": stats.filtered_out,
            "api_quota_used_estimate": stats.api_quota_used,
        },
        "top_viral_shorts": [v.to_dict() for v in top_shorts],
        "top_viral_long_videos": [v.to_dict() for v in top_long],
        "trending_topics": [t.to_dict() for t in trending],
        "content_opportunities": [o.to_dict() for o in opportunities],
        "errors": stats.errors,
    }

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    logger.info("Report successfully saved to %s", output_path)


def print_top5(top_shorts: List[CompetitorVideo]) -> None:
    print("\n" + "=" * 80)
    print("  TOP 5 VIRAL SHORTS — Competitor Intelligence Report")
    print("=" * 80)
    for idx, s in enumerate(top_shorts[:5], 1):
        print(f"\n#{idx} [{s.channel_name}] {s.title}")
        print(f"   URL           : {s.url}")
        print(f"   Topic         : {s.topic}")
        print(f"   Views         : {s.views:,}")
        print(f"   Likes         : {s.likes:,}   Comments: {s.comments:,}")
        print(f"   Velocity      : {s.view_velocity} views/hr")
        print(f"   Engagement    : {s.engagement_rate}%")
        print(f"   Viral Score   : {s.viral_score}/100")
        print("-" * 80)


def print_top_opportunities(opportunities: List[ContentOpportunity]) -> None:
    print("\n" + "=" * 80)
    print("  TOP CONTENT OPPORTUNITIES — Recommended for Today")
    print("=" * 80)
    for opp in opportunities[:3]:
        sensitive = "⏰ TIME-SENSITIVE" if opp.time_sensitive else ""
        print(f"\n  #{opp.rank}  {opp.topic}  {sensitive}")
        print(f"      Overall Score   : {opp.overall_score}/10")
        print(f"      Student Value   : {opp.student_value_score}/10")
        print(f"      Viral Potential : {opp.viral_potential_score}/10")
        print(f"      Angle           : {opp.recommended_angle}")
        print("-" * 80)


# ===========================================================================
# Shared Main Runner
# ===========================================================================

def run_pipeline(
    config_path: str,
    output_path: str,
    skip_search: bool = True,
) -> None:
    """Executes the complete YouTube research pipeline from end to end."""
    setup_logger("kampus_filter")
    stats = RunStats()

    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        logger.error("YOUTUBE_API_KEY is not set. Cannot run pipeline.")
        sys.exit(1)

    logger.info("Executing competitor intelligence pipeline…")

    # 1. Load competitors
    competitors = load_competitors(config_path)

    # 2. Build API client
    client = YouTubeClient(api_key=api_key)

    # 3. Scan all channels
    all_videos = scan_all_competitors(competitors, client, stats, skip_search=skip_search)
    stats.api_quota_used = client.quota_used

    if not all_videos:
        logger.warning("No qualifying videos found. Check settings.")
        print(stats.summary())
        return

    # 4. Rank Shorts and Long videos
    top_shorts = rank_shorts(all_videos)
    top_long = rank_long_videos(all_videos)
    stats.viral_shorts = len(top_shorts)
    stats.viral_longs = len(top_long)

    # 5. Cluster trending topics
    trending = cluster_trending_topics(all_videos)
    stats.trending_topics = len(trending)

    # 6. Generate opportunity report
    opportunities = generate_opportunities(trending)
    stats.opportunities = len(opportunities)

    # 7. Save local report
    save_report(all_videos, top_shorts, top_long, trending, opportunities, stats, output_path)

    # 8. Print summaries to console
    print_top5(top_shorts)
    print_top_opportunities(opportunities)
    print(stats.summary())
