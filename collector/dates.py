"""Data de emissao declarada na sinopse.

O `pubDate` de um feed de podcast e a data em que o episodio foi
publicado, nao a data em que o bloco foi para o ar. As duas divergem, e a
divergencia e visivel nos dados: rubricas que vao ao ar em dias fixos
aparecem espalhadas por toda a semana quando se usa a data de publicacao.

Quando a propria sinopse declara a data de emissao ("emitido na SIC a 7
de setembro"), essa e a data correcta e e a que vale. Quando nao declara,
fica a data de publicacao, registada como tal no campo `date_source` para
que a diferenca seja auditavel sem voltar a fonte.

Regra de prudencia: a data extraida so e aceite se cair numa janela
plausivel face a publicacao, ou seja, no mesmo dia ou ate 45 dias antes.
Uma emissao nunca e anterior a publicacao do podcast por muito tempo, e
nunca e posterior. Fora dessa janela, a leitura e considerada duvidosa e
usa-se a data de publicacao. Melhor uma data conservadora do que uma data
inventada por um regex.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

# "emitido na SIC a 7 de setembro", "exibido no Jornal da Noite de 1 de
# setembro de 2025". Ate 80 caracteres entre a prova de emissao e a data,
# sem atravessar o fim da frase, para nao apanhar uma data de outro
# assunto mais a frente na sinopse.
DECLARED = re.compile(
    r"(?:emitid|exibid)[oa]\b[^.;!?]{0,80}?\b(\d{1,2})\s+de\s+([a-z]+)"
    r"(?:\s+de\s+(\d{4}))?",
    re.IGNORECASE,
)

MAX_LAG_DAYS = 45


def _strip_accents(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    return "".join(c for c in value if not unicodedata.combining(c))


def _plausible(candidate: date, published: date) -> bool:
    lag = (published - candidate).days
    return 0 <= lag <= MAX_LAG_DAYS


def declared_broadcast_date(text: str, published_iso: str) -> str | None:
    """Devolve a data de emissao declarada no texto, em ISO, ou None.

    `published_iso` e a data de publicacao do episodio e serve de ancora:
    e dela que sai o ano quando a sinopse nao o diz, e e contra ela que se
    verifica a plausibilidade.
    """
    if not published_iso:
        return None
    try:
        published = date.fromisoformat(published_iso)
    except ValueError:
        return None

    match = DECLARED.search(_strip_accents(text))
    if not match:
        return None

    day = int(match.group(1))
    month = MONTHS.get(match.group(2).lower())
    if not month:
        return None

    years = [int(match.group(3))] if match.group(3) else [published.year, published.year - 1]
    for year in years:
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        if _plausible(candidate, published):
            return candidate.isoformat()
    return None


def resolve_date(text: str, published_iso: str) -> tuple[str, str]:
    """(data a usar, origem da data). Origem: "sinopse" ou "publicacao"."""
    declared = declared_broadcast_date(text, published_iso)
    if declared:
        return declared, "sinopse"
    return published_iso, "publicacao"


__all__ = ["declared_broadcast_date", "resolve_date", "MAX_LAG_DAYS"]
