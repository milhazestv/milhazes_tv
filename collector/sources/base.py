"""Contrato comum a todas as fontes.

Uma fonte devolve itens brutos. Nao sabe o que e um tema nem quem
sao os intervenientes. A atribuicao acontece toda em attribute.py,
para que a regra fique num unico sitio auditavel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class RawItem:
    native_id: str
    date: str  # YYYY-MM-DD
    duration_s: int
    title: str
    url: str
    description: str = ""
    channel: str = ""
    program: str = ""
    segment: str = ""
    extra: dict = field(default_factory=dict)


class SourcePlugin:
    """Interface das fontes. Implementar apenas `fetch`."""

    type: str = ""

    def __init__(self, source):
        self.source = source

    def fetch(self) -> Iterable[RawItem]:
        raise NotImplementedError


_REGISTRY: dict[str, type[SourcePlugin]] = {}


def register(cls: type[SourcePlugin]) -> type[SourcePlugin]:
    _REGISTRY[cls.type] = cls
    return cls


def get_plugin(source) -> SourcePlugin | None:
    cls = _REGISTRY.get(source.type)
    return cls(source) if cls else None


def known_types() -> list[str]:
    return sorted(_REGISTRY)
