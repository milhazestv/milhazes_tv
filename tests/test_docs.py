"""A Metodologia publicada tem de corresponder ao Markdown.

O `METHODOLOGY.md` e o documento que defende os numeros; o
`docs/methodology.html` e o que o publico le. Se divergirem, o site passa
a publicar uma metodologia que ja nao e a do projeto, e isso nao parte
nada, apenas mente em silencio. Por isso a correspondencia e verificada
pela suite, e nao pela memoria de quem faz a alteracao.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.build_methodology import SOURCE, TARGET, build  # noqa: E402

DASHES = ("\u2014", "\u2013")
VERSIONED_TEXT = [
    ROOT / "METHODOLOGY.md",
    ROOT / "README.md",
    ROOT / "config" / "trackers.yml",
    ROOT / "docs" / "index.html",
    ROOT / "docs" / "app.js",
    ROOT / "docs" / "style.css",
    ROOT / "docs" / "methodology.html",
]


class TestMethodologyHtmlEstaEmDia(unittest.TestCase):
    def test_html_corresponde_ao_markdown(self):
        self.assertEqual(
            TARGET.read_text(encoding="utf-8"),
            build(),
            "docs/methodology.html desactualizado. "
            "Correr: python -m tools.build_methodology",
        )

    def test_o_markdown_existe_e_nao_esta_vazio(self):
        self.assertTrue(SOURCE.read_text(encoding="utf-8").strip())


class TestConvencoesDeTexto(unittest.TestCase):
    """Sem travessoes nos textos versionados: e uma preferencia declarada
    do projeto e, sem verificacao, volta sempre."""

    def test_sem_travessoes(self):
        for path in VERSIONED_TEXT:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                for dash in DASHES:
                    found = [
                        f"{path.name}:{n}"
                        for n, line in enumerate(text.splitlines(), 1)
                        if dash in line
                    ]
                    self.assertEqual(found, [], f"travessao {dash!r} em {found}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
