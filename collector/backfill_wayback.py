"""Backfill histórico a partir do Wayback Machine.

Não corre na recolha diária. É um comando manual, executado uma vez por
fonte (ou de vez em quando, se se quiser alargar a cobertura), porque o
feed RSS ao vivo só expõe os últimos 100 episódios — um limite escolhido
pelo publicador do feed, não pelo consumidor. Sem isto, o dataset nunca
chegaria a 2022-02-24.

Como funciona: o Wayback Machine guardou o feed RSS em vários momentos
desde 2022. Cada captura mostra os "últimos 100" episódios NAQUELE
momento — uma janela diferente da de hoje. Ao juntar várias capturas
espaçadas no tempo, as janelas sobrepõem-se o suficiente para reconstruir
o histórico contínuo. O motor de atribuição (attribute.build) é o mesmo
usado na recolha diária: as mesmas regras de segmento, de prova de
emissão e de corte de data aplicam-se aqui sem exceção.

Uso:
    python -m collector.backfill_wayback omny-guerra-fria
    python -m collector.backfill_wayback omny-rogeiro-show --from 2022-02-24

--from/--to aceitam AAAA-MM-DD. Por omissão cobre desde o `since` do
tema até hoje.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date
from urllib.parse import quote

from . import aggregate, attribute, store
from .http import get_text
from .models import load_config
from .sources.base import RawItem
from .sources.podcast_rss import ITUNES, _text, parse_date, parse_duration, strip_html

CDX_API = "https://web.archive.org/cdx/search/cdx"
REQUEST_DELAY_S = 1.0  # cortesia para com o Internet Archive


def cdx_snapshots(url: str, date_from: str, date_to: str, attempts: int = 4) -> list[str]:
    """Devolve os timestamps (AAAAMMDDhhmmss) das capturas únicas do feed
    no Wayback Machine, uma por conteúdo distinto (collapse=digest).

    O CDX API do Internet Archive é conhecido por devolver erros
    intermitentes (403/502/503) sob carga, sem que isso signifique um
    bloqueio permanente. `get_text` já tenta 3 vezes por pedido; aqui
    tentamos o pedido completo mais vezes, com pausas maiores, porque
    esta chamada só acontece uma vez por corrida e vale a pena insistir.
    """
    params = {
        "url": url,
        "output": "json",
        "from": date_from.replace("-", ""),
        "to": date_to.replace("-", ""),
        "filter": "statuscode:200",
        "collapse": "digest",
        "fl": "timestamp",
    }
    query = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    full_url = f"{CDX_API}?{query}"

    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            raw = get_text(full_url)
            rows = json.loads(raw)
            if len(rows) <= 1:
                return []
            return [row[0] for row in rows[1:]]  # primeira linha é o cabeçalho
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < attempts - 1:
                wait = 5 * (attempt + 1)
                print(f"  CDX falhou ({exc}), a tentar outra vez em {wait}s...")
                time.sleep(wait)

    raise RuntimeError(
        "O Internet Archive não respondeu ao pedido de capturas depois de "
        f"{attempts} tentativas. Isto costuma ser um bloqueio temporário do "
        "lado deles a pedidos vindos de redes de centros de dados (inclui "
        "GitHub Actions) — correr o mesmo comando a partir de uma rede "
        f"doméstica costuma resolver. Erro original: {last_error}"
    )


def fetch_snapshot(url: str, timestamp: str) -> list[RawItem]:
    """Lê uma captura arquivada do feed e devolve os itens tal como o
    parser normal de podcast_rss os leria. `id_` pede a versão crua da
    página, sem a barra de ferramentas do Wayback injetada."""
    snapshot_url = f"https://web.archive.org/web/{timestamp}id_/{url}"
    xml = get_text(snapshot_url)
    root = ET.fromstring(xml)
    items = []

    for item in root.iter("item"):
        guid = _text(item, "guid") or _text(item, "link")
        if not guid:
            continue
        duration = parse_duration(_text(item, f"{ITUNES}duration"))
        published = parse_date(_text(item, "pubDate"))
        if not published or duration <= 0:
            continue
        description = strip_html(_text(item, "description") or _text(item, f"{ITUNES}summary"))
        items.append(
            RawItem(
                native_id=guid,
                date=published,
                duration_s=duration,
                title=_text(item, "title"),
                url=_text(item, "link"),
                description=description,
            )
        )
    return items


def backfill(source_id: str, date_from: str | None, date_to: str | None) -> int:
    config = load_config()
    sources = [s for s in config.sources if s.id == source_id]
    if not sources:
        print(f"fonte desconhecida: {source_id}", file=sys.stderr)
        return 2
    source = sources[0]
    if source.type != "podcast_rss":
        print("o backfill via Wayback só serve fontes podcast_rss", file=sys.stderr)
        return 2

    topic = config.topics.get(source.topic)
    date_from = date_from or (topic.since if topic else "2022-01-01")
    date_to = date_to or date.today().isoformat()

    print(f"a listar capturas de {source.url}")
    print(f"entre {date_from} e {date_to}")
    try:
        timestamps = cdx_snapshots(source.url, date_from, date_to)
    except RuntimeError as exc:
        print(f"\nERRO: {exc}", file=sys.stderr)
        return 1
    print(f"{len(timestamps)} capturas únicas encontradas")

    if not timestamps:
        print("Nada para processar — sem capturas nesse intervalo de datas.")
        return 0

    existing = store.load()
    collected = []
    quarantine: list[dict] = []
    seen_native: set[str] = set()

    for i, ts in enumerate(timestamps, 1):
        print(f"[{i}/{len(timestamps)}] {ts}", end=" ")
        try:
            items = fetch_snapshot(source.url, ts)
        except Exception as exc:  # noqa: BLE001
            print(f"falhou: {exc}")
            time.sleep(REQUEST_DELAY_S)
            continue

        new_here = 0
        for item in items:
            if item.native_id in seen_native:
                continue
            seen_native.add(item.native_id)
            new_here += 1
            collected.extend(attribute.build(item, source, config, quarantine))

        print(f"{len(items)} itens, {new_here} novos")
        time.sleep(REQUEST_DELAY_S)

    merged, added, updated = store.merge(existing, collected)
    store.save(merged)
    stats = aggregate.build(list(merged.values()), config)
    aggregate.save(stats)
    store.save_quarantine(quarantine)

    print(f"\n+{added} novas, {updated} actualizadas, {len(merged)} no total")
    print(f"{len(quarantine)} itens em quarentena")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill histórico via Wayback Machine")
    parser.add_argument("source_id", help="id da fonte em config/trackers.yml")
    parser.add_argument("--from", dest="date_from", help="AAAA-MM-DD, por omissão o since do tema")
    parser.add_argument("--to", dest="date_to", help="AAAA-MM-DD, por omissão hoje")
    args = parser.parse_args()
    return backfill(args.source_id, args.date_from, args.date_to)


if __name__ == "__main__":
    raise SystemExit(main())
