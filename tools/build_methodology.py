"""Gera docs/methodology.html a partir de METHODOLOGY.md.

    python -m tools.build_methodology            # escreve o HTML
    python -m tools.build_methodology --check    # so verifica se esta em dia

Existe porque as regras de trabalho exigem que o HTML seja regenerado
sempre que o Markdown muda, e uma regra que depende de alguem se lembrar
de a cumprir a mao acaba por ser quebrada. Ha um teste que corre o
--check, por isso um Markdown alterado sem regenerar o HTML parte a
suite antes de chegar a producao.

Converte o subconjunto de Markdown usado neste documento: titulos, texto,
listas numeradas, tabelas, blocos de codigo, negrito e codigo inline.
Nao e um conversor de Markdown geral, e nao deve passar a ser: menos
codigo, menos superficie para partir.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "METHODOLOGY.md"
TARGET = ROOT / "docs" / "methodology.html"

HEAD = """<!doctype html>
<html lang="pt-PT">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Metodologia | Milhazes TV</title>
<meta name="robots" content="index, follow">
<link rel="stylesheet" href="style.css">
<style>
  main { max-width: 44rem; }
  main h2 { border: 0; font-size: 1.15rem; margin-top: 2.25rem; }
  main h3 { font-size: 0.98rem; margin-top: 1.5rem; color: var(--ink); }
  main p { margin: 0 0 0.9rem; color: var(--ink-soft); }
  main ol, main ul { color: var(--ink-soft); padding-left: 1.2rem; }
  main li { margin-bottom: 0.5rem; }
  main code { font-family: var(--mono); background: var(--panel); padding: 0.1em 0.35em; }
  main pre { font-family: var(--mono); background: var(--panel); padding: 0.9rem 1rem; \
overflow-x: auto; font-size: 0.88rem; line-height: 1.6; }
  main table { margin: 1rem 0; width: 100%; border-collapse: collapse; }
  main th, main td { text-align: left; padding: 0.45rem 0.6rem; \
border-bottom: 1px solid var(--rule); font-size: 0.92rem; }
  main th { color: var(--ink); font-weight: 600; }
  main a { color: var(--ink); }
</style>
</head>
<body>

<header class="masthead">
  <p><a href="index.html">&larr; Milhazes TV</a></p>
  <h1>Metodologia</h1>
</header>

<main>
"""

TAIL = """</main>

</body>
</html>
"""


def inline(text: str) -> str:
    """Negrito, codigo inline e escape. O codigo inline e escapado primeiro
    para que o seu conteudo nunca seja interpretado como marcacao."""
    parts = re.split(r"(`[^`]+`)", text)
    out = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) > 1:
            out.append(f"<code>{html.escape(part[1:-1])}</code>")
            continue
        escaped = html.escape(part)
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
        out.append(escaped)
    return "".join(out)


def render(markdown: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    index = 0
    in_list = ""

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append(f"</{in_list}>")
            in_list = ""

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            close_list()
            index += 1
            continue

        if stripped.startswith("```"):
            close_list()
            index += 1
            block = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                block.append(html.escape(lines[index]))
                index += 1
            index += 1
            out.append("<pre>\n" + "\n".join(block) + "\n</pre>")
            continue

        if stripped.startswith("|"):
            close_list()
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append([c.strip() for c in lines[index].strip().strip("|").split("|")])
                index += 1
            header, body = rows[0], rows[2:]  # rows[1] e a linha de separacao
            out.append(
                "<table><thead><tr>"
                + "".join(f"<th>{inline(c)}</th>" for c in header)
                + "</tr></thead><tbody>"
            )
            for row in body:
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>")
            out.append("</tbody></table>")
            continue

        heading = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if heading:
            close_list()
            level = len(heading.group(1))
            if level > 1:  # o <h1> vem do cabecalho da pagina
                out.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
            index += 1
            continue

        item = re.match(r"^(\d+\.|-)\s+(.*)$", stripped)
        if item:
            tag = "ul" if item.group(1) == "-" else "ol"
            if in_list != tag:
                close_list()
                out.append(f"<{tag}>")
                in_list = tag
            out.append(f"<li>{inline(item.group(2))}</li>")
            index += 1
            continue

        close_list()
        out.append(f"<p>{inline(stripped)}</p>")
        index += 1

    close_list()
    return HEAD + "\n".join(out) + "\n" + TAIL


def build() -> str:
    return render(SOURCE.read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    generated = build()
    if "--check" in argv:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != generated:
            print(
                "docs/methodology.html esta desactualizado. "
                "Correr: python -m tools.build_methodology",
                file=sys.stderr,
            )
            return 1
        print("docs/methodology.html em dia")
        return 0
    TARGET.write_text(generated, encoding="utf-8")
    print(f"escrito {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
