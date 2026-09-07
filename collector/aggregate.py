"""Agregacao para consumo do site.

Distincao que o resto do projecto depende de acertar:

- **Tempo de emissao** (nivel do tema, do dia, do mes, do programa) e
  tempo de relogio. Um bloco de 20 minutos com dois intervenientes sao
  20 minutos de emissao, nunca 40. Por isso os totais de tema somam
  blocos distintos, nao linhas atribuidas.

- **Tempo por interveniente** admite as duas leituras, rateada e
  integral, porque ai a pergunta e outra: quanto daquele bloco pertence
  a cada um.

Misturar as duas coisas seria a forma mais rapida de o projecto perder
credibilidade, por isso ficam em campos separados.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .models import Config, DATA_DIR

STATS = DATA_DIR / "stats.json"


def _blocks() -> dict:
    return {}


def _airtime(bucket: dict) -> dict:
    return {"airtime_s": sum(bucket.values()), "blocks": len(bucket)}


def _empty_subject() -> dict:
    return {"shared_equal": 0.0, "each_full": 0.0, "blocks": set()}


def _round_subject(bucket: dict) -> dict:
    return {
        "shared_equal": round(bucket["shared_equal"]),
        "each_full": round(bucket["each_full"]),
        "blocks": len(bucket["blocks"]),
    }


def _key(row: dict) -> str:
    return row.get("block_id") or row["id"]


def build(rows: list[dict], config: Config) -> dict:
    by_topic: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_topic[row["topic"]].append(row)

    topics = []
    for topic in config.topics.values():
        if not topic.enabled:
            continue

        topic_rows = by_topic.get(topic.id, [])

        total: dict = _blocks()
        per_day: dict = defaultdict(_blocks)
        per_month: dict = defaultdict(_blocks)
        per_program: dict = defaultdict(_blocks)
        per_subject: dict = defaultdict(_empty_subject)

        # Repartições por dia — o que permite ao site somar qualquer
        # período (semana, mês, ano, desde sempre) sem nova agregação.
        subject_by_day: dict = defaultdict(lambda: defaultdict(_empty_subject))
        program_by_day: dict = defaultdict(lambda: defaultdict(_blocks))

        for row in topic_rows:
            key = _key(row)
            date = row["date"]
            duration = row["duration_s"]
            program = row["program"] or row["channel"]

            total[key] = duration
            per_day[date][key] = duration
            per_month[date[:7]][key] = duration
            per_program[program][key] = duration
            program_by_day[date][program][key] = duration

            bucket = per_subject[row["subject"]]
            bucket["shared_equal"] += row["credited_s"]
            bucket["each_full"] += duration
            bucket["blocks"].add(key)

            day_bucket = subject_by_day[date][row["subject"]]
            day_bucket["shared_equal"] += row["credited_s"]
            day_bucket["each_full"] += duration
            day_bucket["blocks"].add(key)

        dates = sorted(per_day)

        topics.append(
            {
                "id": topic.id,
                "name": topic.name,
                "question": topic.question,
                "since": topic.since,
                "first_record": dates[0] if dates else None,
                "last_record": dates[-1] if dates else None,
                "totals": _airtime(total),
                "subjects": [
                    {
                        "id": subject.id,
                        "name": subject.display_name,
                        "role": subject.role,
                        "totals": _round_subject(
                            per_subject.get(subject.id, _empty_subject())
                        ),
                    }
                    for subject in config.subjects_for_topic(topic.id)
                ],
                "by_month": [
                    {"month": month, **_airtime(per_month[month])}
                    for month in sorted(per_month)
                ],
                "by_day": [{"date": day, **_airtime(per_day[day])} for day in dates],
                "by_program": sorted(
                    (
                        {"program": program, **_airtime(bucket)}
                        for program, bucket in per_program.items()
                    ),
                    key=lambda entry: entry["airtime_s"],
                    reverse=True,
                ),
                "subject_by_day": [
                    {
                        "date": day,
                        "subjects": {
                            sid: _round_subject(bucket)
                            for sid, bucket in subject_by_day[day].items()
                        },
                    }
                    for day in dates
                ],
                "program_by_day": [
                    {
                        "date": day,
                        "programs": {
                            program: _airtime(bucket)
                            for program, bucket in program_by_day[day].items()
                        },
                    }
                    for day in dates
                ],
                "sources": sorted({row["source"] for row in topic_rows}),
            }
        )

    return {
        "schema": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "default_attribution": "shared_equal",
        "topics": topics,
    }


def save(stats: dict, path: Path = STATS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(stats, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
