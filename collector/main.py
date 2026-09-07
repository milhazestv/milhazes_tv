"""Ponto de entrada da recolha.

    python -m collector.main              # recolhe tudo o que esta enabled
    python -m collector.main --source X   # so uma fonte
    python -m collector.main --dry-run    # nao escreve nada em disco

Uma fonte que falhe nao derruba as outras. O objectivo e que a corrida
diaria nunca fique sem resultado por causa de um feed offline.
"""

from __future__ import annotations

import argparse
import sys

from . import aggregate, attribute, store
from .models import load_config
from .sources import base as source_base
from .sources import podcast_rss, youtube  # noqa: F401  (registo dos plugins)


def run(only: str | None = None, dry_run: bool = False) -> int:
    config = load_config()
    existing = store.load()
    collected = []
    failures = []

    for source in config.sources:
        if not source.enabled or (only and source.id != only):
            continue
        if not config.topics.get(source.topic, None) or not config.topics[source.topic].enabled:
            continue

        plugin = source_base.get_plugin(source)
        if plugin is None:
            failures.append(f"{source.id}: tipo desconhecido '{source.type}'")
            continue

        try:
            items = list(plugin.fetch())
        except Exception as exc:  # noqa: BLE001 - uma fonte nao derruba a corrida
            failures.append(f"{source.id}: {exc}")
            continue

        appearances = []
        for item in items:
            appearances.extend(attribute.build(item, source, config))
        collected.extend(appearances)
        print(f"{source.id}: {len(items)} itens, {len(appearances)} aparicoes")

    merged, added, updated = store.merge(existing, collected)
    stats = aggregate.build(list(merged.values()), config)

    if dry_run:
        print(f"[dry-run] +{added} novas, {updated} actualizadas, {len(merged)} no total")
    else:
        store.save(merged)
        aggregate.save(stats)
        print(f"+{added} novas, {updated} actualizadas, {len(merged)} no total")

    for failure in failures:
        print(f"AVISO {failure}", file=sys.stderr)

    # Falha explicita apenas se nada foi recolhido de todo.
    return 0 if collected or not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Recolha de tempo de emissao")
    parser.add_argument("--source", help="correr apenas esta fonte")
    parser.add_argument("--dry-run", action="store_true", help="nao escrever em disco")
    args = parser.parse_args()
    return run(only=args.source, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
