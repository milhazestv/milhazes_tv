"""Atribuicao: de item bruto para aparicao contabilizada.

Toda a decisao editorial do projeto esta neste ficheiro. E de proposito.
Quem quiser contestar os numeros tem um unico sitio para ler.

Um item pode ser rejeitado por quatro razoes, cada uma registada na
quarentena em vez de desaparecer em silencio:

1. `anterior_ao_inicio`      antes da data de inicio do tema.
2. `sem_evidencia_emissao`   a fonte exige prova de que foi para o ar
                             (require_broadcast_evidence) e a sinopse nao
                             a contem.
3. `sem_interveniente`       nenhum subject do tema foi identificado.
4. `duplicado_entre_fontes`  o mesmo clipe ja entrou por outra fonte
                             nesta mesma corrida (ver main.py).

Quatro decisoes de conteudo, sempre as mesmas:

1. Que data conta. A data de emissao declarada pelo emissor na sinopse,
   quando existe e e plausivel; caso contrario, a data de publicacao do
   episodio. A origem fica gravada em cada registo (ver dates.py).
2. Quem conta. O elenco da regra de segmento, se a regra o declarar; senao
   o elenco fixo da fonte (`roster`); com `roster: auto`, os intervenientes
   sao detetados por texto no titulo e na sinopse.
3. Quanto conta. `shared_equal` reparte o bloco pelos intervenientes;
   `each_full` atribui o bloco inteiro a cada um. O dataset guarda a
   duracao e o numero de intervenientes, por isso as duas leituras sao
   sempre reconstruiveis sem nova recolha.
4. O que serve de prova. O excerto do texto que comprova a emissao fica
   guardado no proprio registo, para que a decisao possa ser auditada sem
   voltar a fonte.

Uma fonte com varias rubricas no mesmo feed (por exemplo, um feed que
mistura Leste/Oeste, Jogos de Poder e Nuno Rogeiro Convida) usa `segments`
para classificar cada item no programa certo, e com o elenco certo, antes
de tudo o resto. Ver `matched_rule`.
"""

from __future__ import annotations

import re

from .dates import resolve_date
from .models import Appearance, Config, SegmentRule, Source, stable_id, today_iso
from .sources.base import RawItem

BROADCAST_EVIDENCE = re.compile(r"emitid[oa]|exibid[oa]", re.IGNORECASE)
EVIDENCE_MARGIN = 70


def matched_rule(item: RawItem, source: Source) -> SegmentRule | None:
    """Primeira regra de segmento que corresponde ao item, ou None quando a
    fonte nao tem regras ou nenhuma corresponde."""
    text = f"{item.title} {item.description}"
    for rule in source.segments:
        if rule.matches(text, item.duration_s):
            return rule
    return None


def classify_segment(item: RawItem, source: Source) -> tuple[str, str]:
    """(programa, canal) para este item."""
    rule = matched_rule(item, source)
    if rule is not None:
        return rule.program or source.program, rule.channel or source.channel
    return item.program or source.program, item.channel or source.channel


def resolve_subjects(
    item: RawItem, source: Source, config: Config, rule: SegmentRule | None = None
) -> list[str]:
    """Quem conta neste bloco.

    O elenco da regra de segmento tem precedencia sobre o da fonte: e o
    unico sitio onde se sabe que aquele episodio concreto pertence a outra
    rubrica, com outro elenco.
    """
    if rule is not None and rule.roster:
        return [s for s in rule.roster if s in config.subjects]

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


def evidence_excerpt(text: str) -> str:
    """Excerto em torno da prova de emissao, para o registo poder ser
    auditado sem voltar a fonte. Vazio quando nao ha prova."""
    match = BROADCAST_EVIDENCE.search(text)
    if not match:
        return ""
    start = max(0, match.start() - EVIDENCE_MARGIN)
    end = min(len(text), match.end() + EVIDENCE_MARGIN)
    return " ".join(text[start:end].split())


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
            # O excerto da sinopse fica registado com a rejeicao: sem ele,
            # discutir se uma regra esta demasiado rigida obriga a ir buscar
            # o episodio a fonte, um a um.
            "excerpt": " ".join(item.description.split())[:280],
        }
    )


def build(
    item: RawItem,
    source: Source,
    config: Config,
    quarantine: list | None = None,
) -> list[Appearance]:
    topic = config.topics.get(source.topic)
    text = f"{item.title} {item.description}"

    aired_on, date_source = resolve_date(text, item.date)

    if topic and topic.since and aired_on < topic.since:
        _quarantine(quarantine, item, source, "anterior_ao_inicio")
        return []

    evidence = evidence_excerpt(text)
    if source.require_broadcast_evidence and not evidence:
        _quarantine(quarantine, item, source, "sem_evidencia_emissao")
        return []

    rule = matched_rule(item, source)
    subjects = resolve_subjects(item, source, config, rule)
    if not subjects:
        _quarantine(quarantine, item, source, "sem_interveniente")
        return []

    if rule is not None:
        program = rule.program or source.program
        channel = rule.channel or source.channel
    else:
        program = item.program or source.program
        channel = item.channel or source.channel

    credited = credit(item.duration_s, len(subjects), source.attribution)
    block_id = stable_id(source.id, item.native_id)
    stamp = today_iso()

    return [
        Appearance(
            id=stable_id(source.id, f"{item.native_id}::{subject_id}"),
            block_id=block_id,
            date=aired_on,
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
            date_source=date_source,
            published_at=item.date,
            evidence=evidence,
            first_seen=stamp,
        )
        for subject_id in subjects
    ]
