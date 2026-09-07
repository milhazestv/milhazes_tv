"""Fonte secundaria: YouTube Data API v3.

Apanha intervencoes fora das rubricas fixas. Duracao real do video em
`contentDetails.duration`, formato ISO 8601.

Nota de quota: `search.list` custa 100 unidades por chamada, `videos.list`
custa 1. O limite diario por omissao e 10.000. A recolha e incremental
via `publishedAfter`, por isso uma corrida diaria fica muito abaixo do tecto.

Sem YT_API_KEY no ambiente a fonte devolve zero itens e o resto da
recolha corre na mesma. Nunca falha a pipeline inteira por causa disto.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Iterable
from urllib.parse import urlencode

from .base import RawItem, SourcePlugin, register
from ..http import get_text

API = "https://www.googleapis.com/youtube/v3"
ISO_DURATION = re.compile(
    r"P(?:(?P<days>\d+)D)?T(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?"
)


def parse_iso_duration(value: str) -> int:
    match = ISO_DURATION.fullmatch(value or "")
    if not match:
        return 0
    g = {k: int(v) for k, v in match.groupdict(default="0").items()}
    return g["days"] * 86400 + g["h"] * 3600 + g["m"] * 60 + g["s"]


def _call(endpoint: str, params: dict) -> dict:
    return json.loads(get_text(f"{API}/{endpoint}?{urlencode(params)}"))


@register
class YouTubeSource(SourcePlugin):
    type = "youtube"

    def __init__(self, source, lookback_days: int = 45):
        super().__init__(source)
        self.key = os.environ.get("YT_API_KEY", "")
        self.lookback_days = lookback_days

    def _channel_id(self) -> str:
        handle = self.source.handle.lstrip("@")
        data = _call("channels", {"part": "id", "forHandle": handle, "key": self.key})
        items = data.get("items") or []
        return items[0]["id"] if items else ""

    def fetch(self) -> Iterable[RawItem]:
        if not self.key or not self.source.handle:
            return []

        channel_id = self._channel_id()
        if not channel_id:
            return []

        after = (
            datetime.now(timezone.utc) - timedelta(days=self.lookback_days)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        video_ids: dict[str, dict] = {}
        for term in self.source.query_terms or [""]:
            page = None
            while True:
                params = {
                    "part": "snippet",
                    "channelId": channel_id,
                    "type": "video",
                    "order": "date",
                    "maxResults": 50,
                    "publishedAfter": after,
                    "key": self.key,
                }
                if term:
                    params["q"] = term
                if page:
                    params["pageToken"] = page

                data = _call("search", params)
                for item in data.get("items", []):
                    vid = item["id"].get("videoId")
                    if vid:
                        video_ids[vid] = item["snippet"]

                page = data.get("nextPageToken")
                if not page:
                    break

        items = []
        ids = list(video_ids)
        for chunk_start in range(0, len(ids), 50):
            chunk = ids[chunk_start : chunk_start + 50]
            data = _call(
                "videos",
                {"part": "contentDetails,snippet", "id": ",".join(chunk), "key": self.key},
            )
            for video in data.get("items", []):
                duration = parse_iso_duration(
                    video.get("contentDetails", {}).get("duration", "")
                )
                snippet = video.get("snippet", {})
                published = (snippet.get("publishedAt") or "")[:10]
                if duration <= 0 or not published:
                    continue
                items.append(
                    RawItem(
                        native_id=video["id"],
                        date=published,
                        duration_s=duration,
                        title=snippet.get("title", ""),
                        url=f"https://www.youtube.com/watch?v={video['id']}",
                        description=snippet.get("description", ""),
                        channel=self.source.channel,
                        program=self.source.program,
                        segment=self.source.segment,
                    )
                )

        return items
