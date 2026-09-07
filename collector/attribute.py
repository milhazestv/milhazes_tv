"""Atribuicao: de item bruto para aparicao contabilizada.

Toda a decisao editorial do projecto esta neste ficheiro. E de proposito.
Quem quiser contestar os numeros tem um unico sitio para ler, e o
ficheiro e curto.

Duas regras:

1. Quem conta. Se a fonte tem elenco fixo (`roster`), o elenco conta
   sempre. Se e `auto`, os intervenientes sao detectados por match no
   titulo e na descricao. Item sem interveniente detectado e descartado.

2. Quanto conta. Um bloco de 20 minutos com dois intervenientes vale
   10 minutos a cada (`shared_equal`) ou 20 a cada (`each_full`). O
   dataset guarda `duration_s` e `credited_s` em separado, por isso as
   duas leituras sao sempre reconstruiveis sem nova recolha.
"""

from __future__ import annotations

from .models import Appearance, Config, Source, stable_id, today_iso
from .sources.base import RawItem


def resolve_subjects(item: RawItem, source: Source, config: Config) -> list[str]:
    if source.roster != "auto":
        return [s for s in source.roster if s in config.subjects]

    haystack = f"{item.title} {item.description}"
    return [
        subject.id
        for subject in config.subjects_for_topic(source.topic)
        if subject.matches(haystack)
    ]


def credit(duration_s: int, participants: int, attribution: str) -> float:
    if participants <= 0:
        return 0.0
    if attribution == "each_full":
        return float(duration_s)
    return round(duration_s / participants, 2)


def build(item: RawItem, source: Source, config: Config) -> list[Appearance]:
    subjects = resolve_subjects(item, source, config)
    if not subjects:
        return []

    credited = credit(item.duration_s, len(subjects), source.attribution)
    block_id = stable_id(source.id, item.native_id)
    stamp = today_iso()

    return [
        Appearance(
            id=stable_id(source.id, f"{item.native_id}::{subject_id}"),
            block_id=block_id,
            date=item.date,
            topic=source.topic,
            subject=subject_id,
            channel=item.channel or source.channel,
            program=item.program or source.program,
            segment=item.segment or source.segment,
            duration_s=item.duration_s,
            credited_s=credited,
            participants=len(subjects),
            source=source.id,
            confidence=source.confidence,
            attribution=source.attribution,
            title=item.title,
            url=item.url,
            first_seen=stamp,
        )
        for subject_id in subjects
    ]
