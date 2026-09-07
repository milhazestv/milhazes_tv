"""Testes da classificação por segmento, da exigência de prova de emissão,
do corte de data e da deduplicação entre fontes. Correm offline."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collector import attribute  # noqa: E402
from collector.main import dedupe_native  # noqa: E402
from collector.models import Config, SegmentRule, Source, Subject, Topic  # noqa: E402
from collector.sources.base import RawItem  # noqa: E402
from collector.sources.podcast_rss import PodcastRssSource  # noqa: E402

FIXTURE = (ROOT / "tests" / "fixtures" / "rogeiro_show_sample.xml").read_text(encoding="utf-8")

ROGEIRO_SEGMENTS = (
    SegmentRule(match_any=("Jogos de Poder",), program="Jogos de Poder", channel="SIC"),
    SegmentRule(
        match_any=("Nuno Rogeiro Convida",), program="Nuno Rogeiro Convida", channel="SIC"
    ),
    SegmentRule(match_any=(), program="Leste/Oeste", channel="SIC Notícias"),
)


def make_config(since: str = "2022-02-24") -> Config:
    return Config(
        topics={"guerra": Topic(id="guerra", name="Guerra", since=since)},
        subjects={
            "rogeiro": Subject(id="rogeiro", topic="guerra", display_name="Nuno Rogeiro",
                                match_any=("rogeiro",)),
        },
        sources=[],
    )


def make_rogeiro_source(**kwargs) -> Source:
    defaults = dict(
        id="omny-rogeiro-show",
        type="podcast_rss",
        topic="guerra",
        url="https://example.invalid/feed.rss",
        channel="SIC Notícias",
        program="Leste/Oeste",
        roster=["rogeiro"],
        attribution="shared_equal",
        confidence="high",
        require_broadcast_evidence=True,
        segments=ROGEIRO_SEGMENTS,
    )
    defaults.update(kwargs)
    return Source(**defaults)


class TestSegmentClassification(unittest.TestCase):
    def fetch(self):
        with mock.patch("collector.sources.podcast_rss.get_text", return_value=FIXTURE):
            return list(PodcastRssSource(make_rogeiro_source()).fetch())

    def by_native_id(self, native_id):
        return next(i for i in self.fetch() if i.native_id == native_id)

    def test_jogos_de_poder_classified_correctly(self):
        item = self.by_native_id("rogeiro-jdp-0001")
        program, channel = attribute.classify_segment(item, make_rogeiro_source())
        self.assertEqual(program, "Jogos de Poder")
        self.assertEqual(channel, "SIC")

    def test_convida_classified_correctly(self):
        item = self.by_native_id("rogeiro-convida-0001")
        program, channel = attribute.classify_segment(item, make_rogeiro_source())
        self.assertEqual(program, "Nuno Rogeiro Convida")

    def test_fallback_is_leste_oeste(self):
        item = self.by_native_id("rogeiro-leste-oeste-0001")
        program, channel = attribute.classify_segment(item, make_rogeiro_source())
        self.assertEqual(program, "Leste/Oeste")
        self.assertEqual(channel, "SIC Notícias")

    def test_only_one_playlist_source_needed_no_double_counting(self):
        # As sub-playlists (jogos-de-poder, nuno-rogeiro-convida) NÃO são
        # configuradas como fontes à parte — só existe uma fonte para todo
        # o feed. Isto é a própria proteção estrutural contra duplicação.
        source = make_rogeiro_source()
        config = make_config()
        rows = []
        for item in self.fetch():
            rows.extend(attribute.build(item, source, config))
        block_ids = [r.block_id for r in rows]
        self.assertEqual(len(block_ids), len(set(block_ids)))


class TestBroadcastEvidence(unittest.TestCase):
    def test_accepts_emitido(self):
        item = RawItem("x", "2026-09-02", 600, "t", "u", description="emitido na SIC a 2 de setembro")
        self.assertTrue(attribute.BROADCAST_EVIDENCE.search(item.description))

    def test_accepts_exibido(self):
        item = RawItem("x", "2026-09-02", 600, "t", "u", description="foi exibido na SIC")
        self.assertTrue(attribute.BROADCAST_EVIDENCE.search(item.description))

    def test_rejects_missing_evidence(self):
        source = make_rogeiro_source()
        config = make_config()
        item = RawItem("x", "2026-09-02", 600, "t", "u",
                        description="uma sinopse qualquer sem confirmação")
        quarantine = []
        rows = attribute.build(item, source, config, quarantine)
        self.assertEqual(rows, [])
        self.assertEqual(quarantine[0]["reason"], "sem_evidencia_emissao")

    def test_accepts_when_evidence_present(self):
        source = make_rogeiro_source()
        config = make_config()
        item = RawItem("x", "2026-09-02", 600, "Rogeiro fala", "u",
                        description="emitido na SIC Notícias a 2 de setembro")
        rows = attribute.build(item, source, config)
        self.assertEqual(len(rows), 1)

    def test_flag_off_skips_the_check(self):
        source = make_rogeiro_source(require_broadcast_evidence=False)
        config = make_config()
        item = RawItem("x", "2026-09-02", 600, "Rogeiro fala", "u", description="sem prova nenhuma")
        rows = attribute.build(item, source, config)
        self.assertEqual(len(rows), 1)


class TestSinceCutoff(unittest.TestCase):
    def test_before_since_is_quarantined(self):
        source = make_rogeiro_source()
        config = make_config(since="2022-02-24")
        item = RawItem("x", "2022-01-03", 600, "t", "u",
                        description="emitido na SIC Notícias a 3 de janeiro de 2022")
        quarantine = []
        rows = attribute.build(item, source, config, quarantine)
        self.assertEqual(rows, [])
        self.assertEqual(quarantine[0]["reason"], "anterior_ao_inicio")

    def test_on_since_date_is_accepted(self):
        source = make_rogeiro_source()
        config = make_config(since="2022-02-24")
        item = RawItem("x", "2022-02-24", 600, "Rogeiro", "u",
                        description="emitido na SIC Notícias a 24 de fevereiro de 2022")
        rows = attribute.build(item, source, config)
        self.assertEqual(len(rows), 1)

    def test_full_fixture_drops_the_pre_war_item(self):
        source = make_rogeiro_source()
        config = make_config(since="2022-02-24")
        with mock.patch("collector.sources.podcast_rss.get_text", return_value=FIXTURE):
            items = list(PodcastRssSource(source).fetch())
        quarantine = []
        rows = []
        for item in items:
            rows.extend(attribute.build(item, source, config, quarantine))
        native_ids_kept = {r.title for r in rows}
        self.assertNotIn("Episódio anterior ao início do tema", native_ids_kept)
        reasons = {q["reason"] for q in quarantine}
        self.assertIn("anterior_ao_inicio", reasons)
        self.assertIn("sem_evidencia_emissao", reasons)


class TestCrossSourceDedup(unittest.TestCase):
    def test_second_source_with_same_native_id_is_quarantined(self):
        item_a = RawItem("dup-1", "2026-09-02", 600, "t", "u")
        item_b = RawItem("dup-1", "2026-09-02", 600, "t", "u")
        seen: dict[str, str] = {}

        accepted_a, dup_a = dedupe_native([item_a], "fonte-a", seen)
        accepted_b, dup_b = dedupe_native([item_b], "fonte-b", seen)

        self.assertEqual(len(accepted_a), 1)
        self.assertEqual(len(accepted_b), 0)
        self.assertEqual(len(dup_b), 1)
        self.assertIn("fonte-a", dup_b[0]["reason"])

    def test_same_source_twice_is_not_flagged_as_cross_source(self):
        item = RawItem("dup-2", "2026-09-02", 600, "t", "u")
        seen: dict[str, str] = {}
        dedupe_native([item], "fonte-a", seen)
        accepted, dup = dedupe_native([item], "fonte-a", seen)
        # mesma fonte outra vez -> nao e "entre fontes", mas tambem nao
        # deve reintroduzir o item (o proprio dict seen ja o marca)
        self.assertEqual(dup, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
