"""Fonte primaria: feeds RSS de podcast.

Porque esta e a fonte principal e nao o scraping do site: o feed traz
a duracao declarada pelo publicador em `itunes:duration` e a data em
`pubDate`. Nao ha heuristica, nao ha parsing de HTML que parta a cada
redesenho, e o historico vem no mesmo pedido, pagina a pagina.

Limitacao assumida e publicada na metodologia: a duracao do podcast
pode nao ser exactamente igual a duracao emitida em antena.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable

from .base import RawItem, SourcePlugin, register
from ..http import get_text

ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
ATOM = "{http://www.w3.org/2005/Atom}"
MAX_PAGES = 20


def parse_duration(value: str | None) -> int:
    """Aceita 'HH:MM:SS', 'MM:SS' ou segundos. Devolve 0 se ilegivel."""
    if not value:
        return 0
    value = value.strip()
    if value.isdigit():
        return int(value)
    parts = value.split(":")
    if not all(p.strip().isdigit() for p in parts if p.strip()):
        return 0
    total = 0
    for part in parts:
        total = total * 60 + int(part or 0)
    return total


def parse_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).date().isoformat()


def _text(node, tag: str) -> str:
    found = node.find(tag)
    return (found.text or "").strip() if found is not None and found.text else ""


def strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value)


def _next_page(root: ET.Element) -> str | None:
    """Alguns feeds paginam com <atom:link rel="next">.

    Verificado nos feeds usados por este projeto: expoem paginacao Atom e
    devolvem o historico quase completo desde 2022. Nao assumir limites de
    pagina a partir de documentacao generica do alojamento; verificar no
    feed concreto com --dry-run."""
    channel = root.find("channel")
    if channel is None:
        return None
    for link in channel.findall(f"{ATOM}link"):
        if link.get("rel") == "next":
            return link.get("href") or None
    return None


@register
class PodcastRssSource(SourcePlugin):
    type = "podcast_rss"

    def fetch(self) -> Iterable[RawItem]:
        if not self.source.url:
            return []

        items: list[RawItem] = []
        seen_guids: set[str] = set()
        url = self.source.url

        for _ in range(MAX_PAGES):
            xml = get_text(url)
            root = ET.fromstring(xml)
            page_had_new = False

            for item in root.iter("item"):
                guid = _text(item, "guid") or _text(item, "link")
                if not guid or guid in seen_guids:
                    continue

                duration = parse_duration(_text(item, f"{ITUNES}duration"))
                published = parse_date(_text(item, "pubDate"))
                if not published or duration <= 0:
                    # Sem data ou sem duração não entra. Melhor um dataset
                    # incompleto do que um número inventado.
                    continue

                description = strip_html(
                    _text(item, "description") or _text(item, f"{ITUNES}summary")
                )

                seen_guids.add(guid)
                page_had_new = True
                items.append(
                    RawItem(
                        native_id=guid,
                        date=published,
                        duration_s=duration,
                        title=_text(item, "title"),
                        url=_text(item, "link"),
                        description=description,
                        channel=self.source.channel,
                        program=self.source.program,
                        segment=self.source.segment,
                        extra={"fetched_at": datetime.now(timezone.utc).isoformat()},
                    )
                )

            next_url = _next_page(root)
            if not next_url or not page_had_new:
                break
            url = next_url

        return items
