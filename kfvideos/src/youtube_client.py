"""
Kampus Filter — YouTube API Client
Thin wrapper around YouTube Data API v3 with retry logic and quota tracking.
"""

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

BASE_URL = "https://www.googleapis.com/youtube/v3"


class YouTubeClient:
    """
    Thread-safe YouTube Data API v3 client.

    Supports:
        - channels.list
        - playlistItems.list
        - search.list
        - videos.list
    """

    def __init__(self, api_key: str, max_retries: int = 3, timeout: int = 15) -> None:
        self.api_key = api_key
        self.max_retries = max_retries
        self.timeout = timeout
        self.quota_used: int = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
        """
        Execute a GET request against the YouTube API.
        Retries on transient errors with exponential back-off.
        """
        params = dict(params)
        params["key"] = self.api_key
        query_string = urllib.parse.urlencode(params)
        url = f"{BASE_URL}/{endpoint}?{query_string}"

        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "KampusFilter-Intelligence/2.0"},
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    data: Dict = json.loads(response.read().decode("utf-8"))
                    # Rough quota estimation (1 unit per call)
                    self.quota_used += 1
                    logger.debug("API call %s — quota used so far: %d", endpoint, self.quota_used)
                    return data

            except urllib.error.HTTPError as exc:
                if exc.code == 403:
                    logger.error("API quota exceeded or access forbidden (HTTP 403). Stopping.")
                    return None
                if exc.code == 404:
                    logger.warning("Resource not found (HTTP 404): %s", url)
                    return None
                logger.warning("HTTP %d on attempt %d/%d for %s", exc.code, attempt, self.max_retries, endpoint)

            except urllib.error.URLError as exc:
                logger.warning("Network error on attempt %d/%d: %s", attempt, self.max_retries, exc.reason)

            except Exception as exc:
                logger.warning("Unexpected error on attempt %d/%d: %s", attempt, self.max_retries, exc)

            if attempt < self.max_retries:
                sleep_sec = 2 ** (attempt - 1)
                logger.info("Retrying in %ds…", sleep_sec)
                time.sleep(sleep_sec)

        logger.error("All %d attempts failed for endpoint: %s", self.max_retries, endpoint)
        return None

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def resolve_channel(self, channel_id: str = "", handle: str = "") -> Optional[Dict]:
        """
        Resolve a channel by ID or @handle.
        Returns the channel item dict or None.
        """
        if channel_id:
            params: Dict[str, Any] = {
                "part": "id,contentDetails,statistics",
                "id": channel_id,
            }
        elif handle:
            clean = handle.lstrip("@")
            params = {
                "part": "id,contentDetails,statistics",
                "forHandle": clean,
            }
        else:
            return None

        data = self._request("channels", params)
        if data and data.get("items"):
            return data["items"][0]
        return None

    def get_uploads_playlist_id(self, channel_item: Dict) -> Optional[str]:
        """Extract the uploads playlist ID from a resolved channel item."""
        try:
            return channel_item["contentDetails"]["relatedPlaylists"]["uploads"]
        except KeyError:
            return None

    def get_playlist_video_ids(self, playlist_id: str, max_results: int = 25) -> List[str]:
        """Fetch up to max_results video IDs from a playlist (newest first)."""
        data = self._request("playlistItems", {
            "part": "contentDetails",
            "playlistId": playlist_id,
            "maxResults": min(max_results, 50),
        })
        if data and data.get("items"):
            return [
                item["contentDetails"]["videoId"]
                for item in data["items"]
                if item.get("contentDetails", {}).get("videoId")
            ]
        return []

    def search_channel_videos(
        self,
        channel_id: str,
        max_results: int = 25,
        order: str = "viewCount",
    ) -> List[str]:
        """
        Search for videos in a channel, sorted by `order`.
        `order` values: date | rating | relevance | title | videoCount | viewCount
        """
        data = self._request("search", {
            "part": "id",
            "channelId": channel_id,
            "type": "video",
            "order": order,
            "maxResults": min(max_results, 50),
        })
        if data and data.get("items"):
            return [
                item["id"]["videoId"]
                for item in data["items"]
                if item.get("id", {}).get("videoId")
            ]
        return []

    def get_video_details(self, video_ids: List[str]) -> List[Dict]:
        """
        Fetch full snippet, statistics, and contentDetails for up to 50 videos.
        """
        if not video_ids:
            return []
        ids_str = ",".join(video_ids[:50])
        data = self._request("videos", {
            "part": "snippet,statistics,contentDetails",
            "id": ids_str,
        })
        if data and data.get("items"):
            return data["items"]
        return []
