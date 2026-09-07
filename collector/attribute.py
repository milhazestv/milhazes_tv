"""Atribuição: de item bruto para aparição contabilizada.

Toda a decisão editorial do projeto está neste ficheiro. É de propósito.
Quem quiser contestar os números tem um único sítio para ler.

Um item pode ser rejeitado por quatro razões, cada uma registada na
quarentena (ver quarantine, abaixo) em vez de desaparecer em silêncio:

1. `anterior_ao_inicio`      — antes da data de início do tema.
2. `sem_evidencia_emissao`   — a fonte exige prova de que foi para o ar
                                 (require_broadcast_evidence) e a sinopse
                                 não a contém.
3. `sem_interveniente`       — nenhum subject do tema foi identificado.
4. `duplicado_entre_fontes`  — o mesmo clipe já entrou por outra fonte
                                 nesta mesma corrida (ver main.py).

Duas regras de conteúdo, sempre as mesmas:

1. Quem conta. Elenco fixo (`roster`) conta sempre; `roster: auto` deteta
   por texto no título e na sinopse.
2. Quanto conta. `shared_equal` reparte o bloco pelos intervenientes;
   `each_full` atribui o bloco inteiro a cada um. O dataset guarda as duas
   leituras, sempre reconstruíveis sem nova recolha.

Uma fonte com várias rubricas no mesmo feed (ex.: um podcast que mistura
Leste/Oeste, Jogos de Poder e Nuno Rogeiro Convida) usa `segments` para
classificar cada item no programa certo antes de tudo o resto — ver
`classify_segment`.
"""

from __future__ import annotations

import re

from .models import Appearance, Config, Source, stable_id, today_iso
from .sources.base import RawItem

BROADCAST_EVIDENCE = re.compile(r"emitid[oa]|exibid[oa]", re.IGNORECASE)


def classify_segment(item: RawItem, source: Source) -> tuple[str, str]:
    """Devolve (programa, canal) usando as regras de segmento da fonte.
    Sem regras que correspondam — ou sem regras nenhumas — usa o
    programa/canal por omissão da própria fonte."""
    text = f"{item.title} {item.description}"
    for rule in source.segments:
        if rule.matches(text, item.duration_s):
            return rule.program or source.program, rule.channel or source.channel
    return item.program or source.program, item.channel or source.channel


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


def _quarantine(quarantine, item: RawItem, source: Source, reason: str) -> None:
    if quarantine is None:
        return
    quarantine.append(
        {
            "source": source.id,
            "native_id": item.native_id,
            "date": item.date,
            "title": item.title,
            "url": item.url,
            "reason": reason,
        }
    )


def build(
    item: RawItem,
    source: Source,
    config: Config,
    quarantine: list | None = None,
) -> list[Appearance]:
    topic = config.topics.get(source.topic)

    if topic and topic.since and item.date < topic.since:
        _quarantine(quarantine, item, source, "anterior_ao_inicio")
        return []

    if source.require_broadcast_evidence and not BROADCAST_EVIDENCE.search(
        f"{item.title} {item.description}"
    ):
        _quarantine(quarantine, item, source, "sem_evidencia_emissao")
        return []

    subjects = resolve_subjects(item, source, config)
    if not subjects:
        _quarantine(quarantine, item, source, "sem_interveniente")
        return []

    program, channel = classify_segment(item, source)
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
            channel=channel,
            program=program,
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
