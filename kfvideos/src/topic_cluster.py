"""
Kampus Filter — Topic Clustering & Niche Filter
Groups competitor videos into trending topics and filters for niche relevance.
"""

from collections import defaultdict
from typing import Dict, List

from models import (
    CompetitorVideo,
    ContentOpportunity,
    ContentType,
    Priority,
    TrendDirection,
    TrendingTopic,
    VideoType,
)


# ---------------------------------------------------------------------------
# Niche Keyword Registry
# ---------------------------------------------------------------------------

# Topic taxonomy: topic label → list of title keywords (lowercase)
TOPIC_TAXONOMY: Dict[str, List[str]] = {
    "JEE & IIT Admissions": [
        "jee", "jee main", "jee advanced", "iit", "nit", "iiit",
        "josaa", "csab", "joint entrance",
    ],
    "NEET & Medical Admissions": [
        "neet", "mbbs", "medical college", "mcc counselling",
        "aiims", "jipmer", "bds",
    ],
    "CUET & Central Universities": [
        "cuet", "central university", "du admission", "jnu", "bhu", "amu",
    ],
    "Board Exams": [
        "board exam", "class 10", "class 12", "cbse", "icse", "state board",
        "10th", "12th",
    ],
    "Scholarships": [
        "scholarship", "fellowship", "grant", "stipend", "free education",
        "nsp", "national scholarship",
    ],
    "Government Internships": [
        "internship", "niti aayog", "government intern", "ministry intern",
        "sarkari internship",
    ],
    "Private University Admissions": [
        "lpu", "manipal", "chandigarh university", "bennett", "upes",
        "amity", "sharda", "private university",
    ],
    "Placement Trends": [
        "placement", "campus placement", "package", "ctc", "lpa",
        "off campus", "hiring", "fresher job",
    ],
    "AI & Tech Careers": [
        "ai", "artificial intelligence", "machine learning", "chatgpt",
        "generative ai", "llm", "prompt engineering",
    ],
    "Future Skills": [
        "skills", "upskill", "python", "data science", "cloud",
        "devops", "mlops", "cybersecurity",
    ],
    "Study Abroad": [
        "study abroad", "ms program", "mba abroad", "usa university",
        "uk university", "canada university", "visa",
    ],
    "Hackathons & Contests": [
        "hackathon", "contest", "olympiad", "competition", "challenge",
        "coding contest", "smart india",
    ],
    "Student Opportunities": [
        "ambassador", "student program", "youth program", "opportunity",
        "apply now", "registration open",
    ],
    "College Reviews": [
        "college review", "campus life", "hostel", "fees structure",
        "ranking", "review",
    ],
    "Exam Results & Notifications": [
        "result", "answer key", "admit card", "notification",
        "latest update", "cut off", "merit list",
    ],
}

# All niche keywords flattened (for fast O(n) relevance check)
ALL_NICHE_KEYWORDS: List[str] = [
    kw for keywords in TOPIC_TAXONOMY.values() for kw in keywords
] + [
    "exam", "university", "college", "career", "job",
    "salary", "tech", "startup", "drop year", "aspirant", "admit",
]

# Keywords that signal urgency / time sensitivity
TIME_SENSITIVE_KEYWORDS: List[str] = [
    "scholarship", "deadline", "last date", "admission", "result",
    "notification", "internship", "application", "registration",
    "closing", "hurry", "limited seats", "apply now", "window",
]

# Suggested Kampus Filter angles per topic (educator tone, Hinglish-ready)
KAMPUS_ANGLES: Dict[str, str] = {
    "JEE & IIT Admissions": (
        "JEE counselling ka yeh step bahut important hai — "
        "is ek clear action plan ke saath aap sahi college secure kar sakte hain."
    ),
    "NEET & Medical Admissions": (
        "NEET ke baad medical counselling ki poori timeline — "
        "step by step guide ek hi video mein."
    ),
    "CUET & Central Universities": (
        "CUET score ke baad central university admission kaise secure karein — "
        "poora process clearly samjhiye."
    ),
    "Board Exams": (
        "Board exams ke baad next steps — "
        "aapke paas ek clear roadmap hona chahiye."
    ),
    "Scholarships": (
        "Yeh scholarship opportunity miss mat kijiye — "
        "eligibility, deadline aur application process sabkuch yahan hai."
    ),
    "Government Internships": (
        "Government internship mein selected hone ke liye "
        "in steps ko zaroor follow kijiye."
    ),
    "Private University Admissions": (
        "Private university choose karne se pehle "
        "in important parameters ko zaroor check kijiye."
    ),
    "Placement Trends": (
        "2026 placements ka sach — "
        "is trend ko samajhna aapke career ke liye zaroori hai."
    ),
    "AI & Tech Careers": (
        "AI career ke liye aaj se hi in skills par focus kijiye — "
        "ek practical aur actionable roadmap."
    ),
    "Future Skills": (
        "Yeh skills seekhna aapko job market mein genuinely alag position dega — "
        "aaj se start kijiye."
    ),
    "Study Abroad": (
        "Study abroad ke liye ek realistic roadmap — "
        "scholarship se leke application process tak."
    ),
    "Hackathons & Contests": (
        "Is competition mein participate karke "
        "apna resume aur portfolio genuinely strong banayein."
    ),
    "Student Opportunities": (
        "Yeh student opportunity aapke career ko genuinely help kar sakti hai — "
        "is information ko seriously lijiye."
    ),
    "College Reviews": (
        "College choose karne se pehle "
        "in important factors ko consider karna zaroori hai."
    ),
    "Exam Results & Notifications": (
        "Is update ke baad aapko kya action lena chahiye — "
        "ek clear aur step-by-step guide."
    ),
}


# ---------------------------------------------------------------------------
# Niche Filter Functions
# ---------------------------------------------------------------------------

def is_niche_relevant(title: str, description: str = "") -> bool:
    """
    Return True if the video title/description relates to Kampus Filter niches.
    """
    text = (title + " " + description[:200]).lower()
    return any(kw in text for kw in ALL_NICHE_KEYWORDS)


def is_time_sensitive(title: str, description: str = "") -> bool:
    """Return True if the video content appears time-sensitive."""
    text = (title + " " + description[:150]).lower()
    return any(kw in text for kw in TIME_SENSITIVE_KEYWORDS)


def classify_topic(title: str, description: str = "") -> str:
    """Map a video title/description to one of the defined topic clusters."""
    text = (title + " " + description[:300]).lower()
    for topic_label, keywords in TOPIC_TAXONOMY.items():
        if any(kw in text for kw in keywords):
            return topic_label
    return "General Education"


# ---------------------------------------------------------------------------
# Topic Clustering
# ---------------------------------------------------------------------------

def cluster_trending_topics(videos: List[CompetitorVideo]) -> List[TrendingTopic]:
    """
    Group a flat list of CompetitorVideo objects into TrendingTopic clusters.

    Algorithm:
      1. Group videos by topic label.
      2. Compute aggregate metrics per topic.
      3. Determine content type (Shorts / Long-form / Both).
      4. Infer trend direction from average viral score of the 3 most recent videos.
      5. Assign priority based on competitor coverage and total views.
      6. Sort clusters: HIGH → MEDIUM → LOW, then by total views descending.
    """
    groups: Dict[str, List[CompetitorVideo]] = defaultdict(list)
    for video in videos:
        groups[video.topic].append(video)

    trending: List[TrendingTopic] = []

    for topic_name, topic_videos in groups.items():
        shorts = [v for v in topic_videos if v.video_type == VideoType.SHORT]
        longs = [v for v in topic_videos if v.video_type == VideoType.LONG]

        if shorts and longs:
            content_type = ContentType.BOTH
        elif shorts:
            content_type = ContentType.SHORTS
        else:
            content_type = ContentType.LONG_FORM

        total_views = sum(v.views for v in topic_videos)
        avg_eng = (
            sum(v.engagement_rate for v in topic_videos) / len(topic_videos)
            if topic_videos else 0.0
        )
        competitors = sorted({v.channel_name for v in topic_videos})

        # Trend direction: compare recent videos' viral scores to overall average
        sorted_by_date = sorted(topic_videos, key=lambda v: v.published_at, reverse=True)
        recent_3 = sorted_by_date[:3]
        recent_avg = sum(v.viral_score for v in recent_3) / len(recent_3)
        overall_avg = sum(v.viral_score for v in topic_videos) / len(topic_videos)

        if recent_avg > overall_avg * 1.10:
            direction = TrendDirection.RISING
        elif recent_avg < overall_avg * 0.85:
            direction = TrendDirection.DECLINING
        else:
            direction = TrendDirection.STABLE

        # Priority
        if len(competitors) >= 3 or total_views >= 500_000:
            priority = Priority.HIGH
        elif len(competitors) >= 2 or total_views >= 100_000:
            priority = Priority.MEDIUM
        else:
            priority = Priority.LOW

        angle = KAMPUS_ANGLES.get(
            topic_name,
            f"Kampus Filter perspective: {topic_name} ke baare mein aapko yeh zaroor pata hona chahiye.",
        )

        trending.append(TrendingTopic(
            topic_name=topic_name,
            competitors=competitors,
            total_videos=len(topic_videos),
            total_views=total_views,
            avg_engagement=round(avg_eng, 4),
            trend_direction=direction,
            content_type=content_type,
            priority=priority,
            kampus_filter_angle=angle,
            related_video_ids=[v.video_id for v in sorted_by_date[:5]],
        ))

    # Sort: priority first, then total views
    _priority_order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
    trending.sort(key=lambda t: (_priority_order[t.priority], -t.total_views))
    return trending


# ---------------------------------------------------------------------------
# Opportunity Scoring
# ---------------------------------------------------------------------------

def _student_value(topic_name: str) -> float:
    """Heuristic student value score (0–10) based on topic category."""
    HIGH_VALUE = {
        "Scholarships", "Government Internships", "JEE & IIT Admissions",
        "NEET & Medical Admissions", "CUET & Central Universities",
        "Exam Results & Notifications",
    }
    MED_VALUE = {
        "Board Exams", "Placement Trends", "AI & Tech Careers",
        "Future Skills", "Hackathons & Contests", "Student Opportunities",
    }
    if topic_name in HIGH_VALUE:
        return 9.5
    if topic_name in MED_VALUE:
        return 7.5
    return 5.5


def generate_opportunities(
    trending_topics: List[TrendingTopic],
) -> List[ContentOpportunity]:
    """
    Rank trending topics as content creation opportunities for Kampus Filter.

    Scoring weights:
      - 30%: Student value
      - 25%: Viral potential (avg engagement + trend direction)
      - 25%: Alignment with Kampus Filter brand
      - 20%: Search demand (proxied by total views)
    """
    opportunities: List[ContentOpportunity] = []
    _priority_order = {Priority.HIGH: 10.0, Priority.MEDIUM: 7.0, Priority.LOW: 4.0}

    for topic in trending_topics:
        student_val = _student_value(topic.topic_name)

        # Viral potential: based on engagement and trend direction
        direction_bonus = (
            2.0 if topic.trend_direction == TrendDirection.RISING
            else 0.0 if topic.trend_direction == TrendDirection.STABLE
            else -1.0
        )
        viral_pot = min(10.0, (topic.avg_engagement * 200) + direction_bonus + 4.0)

        # Search demand: log-scaled total views
        import math
        demand = min(10.0, math.log10(max(topic.total_views, 1)) * 1.5)

        # Brand alignment
        alignment = _priority_order[topic.priority]

        # Weighted composite
        overall = (
            student_val * 0.30
            + viral_pot * 0.25
            + alignment * 0.25
            + demand * 0.20
        )

        opportunities.append(ContentOpportunity(
            rank=0,  # assigned after sorting
            topic=topic.topic_name,
            student_value_score=round(student_val, 2),
            search_demand_score=round(demand, 2),
            viral_potential_score=round(viral_pot, 2),
            time_sensitive=is_time_sensitive(topic.topic_name),
            alignment_score=round(alignment, 2),
            overall_score=round(overall, 2),
            recommended_angle=topic.kampus_filter_angle,
            related_video_ids=topic.related_video_ids,
        ))

    # Time-sensitive topics get a bonus rank boost
    opportunities.sort(
        key=lambda o: (not o.time_sensitive, -o.overall_score)
    )
    for rank, opp in enumerate(opportunities, start=1):
        opp.rank = rank

    return opportunities
