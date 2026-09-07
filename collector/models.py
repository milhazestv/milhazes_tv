"""Modelo de dados e carregamento de configuracao."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "trackers.yml"
# Os dados vivem dentro do site publicado de proposito: quem contesta um
# numero descarrega o dataset completo do mesmo sitio onde viu o numero.
DATA_DIR = ROOT / "docs" / "data"


def slugify(value: str) -> str:
    """Normaliza para comparacao: sem acentos, minusculas, sem pontuacao."""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


@dataclass(frozen=True)
class Subject:
    id: str
    topic: str
    display_name: str
    role: str = ""
    match_any: tuple[str, ...] = ()

    def matches(self, text: str) -> bool:
        """Match por palavra inteira. Evita falsos positivos em substrings."""
        haystack = slugify(text)
        for term in self.match_any:
            if re.search(rf"\b{re.escape(slugify(term))}\b", haystack):
                return True
        return False


@dataclass(frozen=True)
class Topic:
    id: str
    name: str
    question: str = ""
    since: str = ""
    enabled: bool = True


@dataclass(frozen=True)
class Source:
    id: str
    type: str
    topic: str
    enabled: bool = True
    url: str = ""
    handle: str = ""
    channel: str = ""
    program: str = ""
    segment: str = ""
    roster: Any = "auto"
    attribution: str = "shared_equal"
    confidence: str = "medium"
    query_terms: tuple[str, ...] = ()


@dataclass
class Appearance:
    """Uma unidade de emissao atribuida a um subject.

    duration_s   -> duracao bruta do bloco emitido
    credited_s   -> duracao atribuida a este subject, ja com a regra de rateio
    """

    id: str
    block_id: str
    date: str
    topic: str
    subject: str
    channel: str
    program: str
    segment: str
    duration_s: int
    credited_s: float
    participants: int
    source: str
    confidence: str
    attribution: str
    title: str
    url: str
    first_seen: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Config:
    topics: dict[str, Topic] = field(default_factory=dict)
    subjects: dict[str, Subject] = field(default_factory=dict)
    sources: list[Source] = field(default_factory=list)

    def subjects_for_topic(self, topic_id: str) -> list[Subject]:
        return [s for s in self.subjects.values() if s.topic == topic_id]


def load_config(path: Path = CONFIG_PATH) -> Config:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    topics = {
        t["id"]: Topic(
            id=t["id"],
            name=t["name"],
            question=t.get("question", ""),
            since=t.get("since", ""),
            enabled=t.get("enabled", True),
        )
        for t in raw.get("topics", [])
    }

    subjects = {
        s["id"]: Subject(
            id=s["id"],
            topic=s["topic"],
            display_name=s["display_name"],
            role=s.get("role", ""),
            match_any=tuple((s.get("match") or {}).get("any", [])),
        )
        for s in raw.get("subjects", [])
    }

    sources = [
        Source(
            id=s["id"],
            type=s["type"],
            topic=s["topic"],
            enabled=s.get("enabled", True),
            url=s.get("url", ""),
            handle=s.get("handle", ""),
            channel=s.get("channel", ""),
            program=s.get("program", ""),
            segment=s.get("segment", ""),
            roster=s.get("roster", "auto"),
            attribution=s.get("attribution", "shared_equal"),
            confidence=s.get("confidence", "medium"),
            query_terms=tuple(s.get("query_terms", [])),
        )
        for s in raw.get("sources", [])
    ]

    return Config(topics=topics, subjects=subjects, sources=sources)


def stable_id(source_id: str, native_id: str) -> str:
    """Id deterministico: o mesmo item nunca entra duas vezes no dataset."""
    digest = hashlib.sha1(f"{source_id}::{native_id}".encode("utf-8")).hexdigest()
    return f"{source_id}:{digest[:12]}"


def today_iso() -> str:
    return date.today().isoformat()
