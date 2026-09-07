"""Ajuda a encontrar o feed RSS de um programa alojado em Omny Studio.

    python -m collector.discover https://omny.fm/shows/<slug>

Existe porque os slugs nem sempre correspondem ao nome do programa e o
URL directo do feed poupa uma dependencia de scraping na recolha diaria.
Corre-se a mao, uma vez, quando se acrescenta uma fonte.
"""

from __future__ import annotations

import re
import sys

from .http import get_text

FEED = re.compile(r'https://[^"\'\s]+?(?:podcast|playlists/[^"\'\s/]+)\.rss')


def discover(url: str) -> list[str]:
    html = get_text(url)
    found = []
    for match in FEED.findall(html):
        if match not in found:
            found.append(match)
    if not found and "/shows/" in url:
        found.append(url.rstrip("/") + "/playlists/podcast.rss")
    return found


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    for feed in discover(sys.argv[1]):
        print(feed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
