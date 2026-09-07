"""Ponto de entrada da recolha.

    python -m collector.main              # recolhe tudo o que esta enabled
    python -m collector.main --source X   # so uma fonte
    python -m collector.main --dry-run    # nao escreve nada em disco

Uma fonte que falhe nao derruba as outras. O objetivo e que a corrida
diaria nunca fique sem resultado por causa de um feed offline.

Deduplicação entre fontes: se duas fontes configuradas alguma vez
devolverem o mesmo native_id (o guid do clipe de origem), só a primeira
conta, e a segunda vai para a quarentena com o motivo
"duplicado_entre_fontes". Isto é a rede de segurança contra o cenário que
já aconteceu uma vez neste projeto: duas fontes a apontar, sem se saber,
para o mesmo episódio.
"""

from __future__ import annotations

import argparse
import sys

from . import aggregate, attribute, store
from .models import load_config
from .sources import base as source_base
from .sources import podcast_rss, youtube  # noqa: F401  (registo dos plugins)


def dedupe_native(
    items: list, source_id: str, seen_native: dict[str, str]
) -> tuple[list, list[dict]]:
    """Separa os itens já vistos, com outro source_id, nesta corrida.
    `seen_native` é partilhado e mutado entre chamadas sucessivas, uma
    por fonte, na ordem em que as fontes são processadas."""
    accepted = []
    duplicates = []
    for item in items:
        prior_source = seen_native.get(item.native_id)
        if prior_source and prior_source != source_id:
            duplicates.append(
                {
                    "source": source_id,
                    "native_id": item.native_id,
                    "date": item.date,
                    "title": item.title,
                    "url": item.url,
                    "reason": f"duplicado_entre_fontes (já visto em {prior_source})",
                }
            )
            continue
        seen_native[item.native_id] = source_id
        accepted.append(item)
    return accepted, duplicates


def run(only: str | None = None, dry_run: bool = False) -> int:
    config = load_config()
    existing = store.load()
    collected = []
    quarantine: list[dict] = []
    failures = []
    seen_native: dict[str, str] = {}

    for source in config.sources:
        if not source.enabled or (only and source.id != only):
            continue
        topic = config.topics.get(source.topic)
        if not topic or not topic.enabled:
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

        accepted, duplicates = dedupe_native(items, source.id, seen_native)
        quarantine.extend(duplicates)

        appearances = []
        for item in accepted:
            appearances.extend(attribute.build(item, source, config, quarantine))

        collected.extend(appearances)
        print(f"{source.id}: {len(items)} itens, {len(appearances)} aparicoes")

    merged, added, updated = store.merge(existing, collected)
    stats = aggregate.build(list(merged.values()), config)

    if dry_run:
        print(f"[dry-run] +{added} novas, {updated} actualizadas, {len(merged)} no total")
        print(f"[dry-run] {len(quarantine)} itens em quarentena nesta corrida")
    else:
        store.save(merged)
        aggregate.save(stats)
        store.save_quarantine(quarantine)
        print(f"+{added} novas, {updated} actualizadas, {len(merged)} no total")
        print(f"{len(quarantine)} itens em quarentena nesta corrida")

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
