"""Testes da pipeline. Correm offline, sem rede."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collector import aggregate, attribute  # noqa: E402
from collector.models import Config, Source, Subject, Topic, slugify  # noqa: E402
from collector.sources.podcast_rss import PodcastRssSource, parse_duration  # noqa: E402
from collector.sources.youtube import parse_iso_duration  # noqa: E402

FIXTURE = (ROOT / "tests" / "fixtures" / "podcast_sample.xml").read_text(encoding="utf-8")


def make_config() -> Config:
    return Config(
        topics={"t": Topic(id="t", name="Tema", since="2022-01-01")},
        subjects={
            "a": Subject(id="a", topic="t", display_name="Pessoa A", match_any=("alfa",)),
            "b": Subject(id="b", topic="t", display_name="Pessoa B", match_any=("beta",)),
        },
        sources=[],
    )


def make_source(**kwargs) -> Source:
    defaults = dict(
        id="src",
        type="podcast_rss",
        topic="t",
        url="https://example.invalid/feed.rss",
        channel="Canal",
        program="Programa",
        segment="Rubrica",
        roster=["a", "b"],
        attribution="shared_equal",
        confidence="high",
    )
    defaults.update(kwargs)
    return Source(**defaults)


class TestDurations(unittest.TestCase):
    def test_mm_ss(self):
        self.assertEqual(parse_duration("18:49"), 1129)

    def test_hh_mm_ss(self):
        self.assertEqual(parse_duration("1:02:30"), 3750)

    def test_plain_seconds(self):
        self.assertEqual(parse_duration("1520"), 1520)

    def test_garbage_is_zero(self):
        self.assertEqual(parse_duration("cerca de 20 minutos"), 0)
        self.assertEqual(parse_duration(None), 0)

    def test_iso8601(self):
        self.assertEqual(parse_iso_duration("PT21M43S"), 1303)
        self.assertEqual(parse_iso_duration("PT1H2M30S"), 3750)
        self.assertEqual(parse_iso_duration("lixo"), 0)


class TestRssParsing(unittest.TestCase):
    def fetch(self):
        with mock.patch("collector.sources.podcast_rss.get_text", return_value=FIXTURE):
            return list(PodcastRssSource(make_source()).fetch())

    def test_discards_items_without_duration(self):
        items = self.fetch()
        self.assertEqual(len(items), 3)
        self.assertNotIn("fixture-0004", [i.native_id for i in items])

    def test_dates_and_durations(self):
        items = self.fetch()
        self.assertEqual(items[0].date, "2026-09-02")
        self.assertEqual(items[0].duration_s, 1129)

    def test_html_is_stripped(self):
        self.assertNotIn("<p>", self.fetch()[0].description)


class TestAttribution(unittest.TestCase):
    def build(self, source):
        with mock.patch("collector.sources.podcast_rss.get_text", return_value=FIXTURE):
            items = list(PodcastRssSource(source).fetch())
        out = []
        for item in items:
            out.extend(attribute.build(item, source, make_config()))
        return out

    def test_shared_equal_splits_between_two(self):
        rows = self.build(make_source())
        first = [r for r in rows if r.date == "2026-09-02"]
        self.assertEqual(len(first), 2)
        self.assertEqual(first[0].duration_s, 1129)
        self.assertAlmostEqual(first[0].credited_s, 564.5)

    def test_each_full_credits_whole_block(self):
        rows = self.build(make_source(attribution="each_full"))
        first = [r for r in rows if r.date == "2026-09-02"]
        self.assertAlmostEqual(first[0].credited_s, 1129.0)

    def test_auto_roster_matches_on_text(self):
        source = make_source(roster="auto")
        config = make_config()
        from collector.sources.base import RawItem

        item = RawItem(
            native_id="x",
            date="2026-09-02",
            duration_s=600,
            title="Comentario de Alfa sobre o tema",
            url="https://example.invalid/x",
            description="",
        )
        rows = attribute.build(item, source, config)
        self.assertEqual([r.subject for r in rows], ["a"])
        self.assertEqual(rows[0].credited_s, 600.0)

    def test_item_without_any_subject_is_dropped(self):
        from collector.sources.base import RawItem

        item = RawItem(
            native_id="x",
            date="2026-09-02",
            duration_s=600,
            title="Assunto sem intervenientes conhecidos",
            url="",
        )
        self.assertEqual(attribute.build(item, make_source(roster="auto"), make_config()), [])

    def test_ids_are_stable_across_runs(self):
        self.assertEqual(
            [r.id for r in self.build(make_source())],
            [r.id for r in self.build(make_source())],
        )


class TestMatching(unittest.TestCase):
    def test_accent_and_case_insensitive(self):
        subject = Subject(id="s", topic="t", display_name="X", match_any=("Milhazes",))
        self.assertTrue(subject.matches("JOSE MILHAZES analisa"))
        self.assertTrue(subject.matches("josé milhazes"))

    def test_no_substring_false_positives(self):
        subject = Subject(id="s", topic="t", display_name="X", match_any=("globo",))
        self.assertFalse(subject.matches("globosat"))

    def test_slugify(self):
        self.assertEqual(slugify("Leste/Oeste, de Nuno Rogeiro"), "leste oeste de nuno rogeiro")


class TestAggregate(unittest.TestCase):
    def _stats(self):
        source = make_source()
        config = make_config()
        with mock.patch("collector.sources.podcast_rss.get_text", return_value=FIXTURE):
            items = list(PodcastRssSource(source).fetch())
        rows = []
        for item in items:
            rows.extend(r.to_dict() for r in attribute.build(item, source, config))

        return aggregate.build(rows, config)["topics"][0]

    def test_topic_total_is_clock_time_not_person_time(self):
        # 1129 + 1520 + 3750 = 6399 s emitidos. Dois intervenientes nao
        # transformam isto em 12798 s de emissao.
        topic = self._stats()
        self.assertEqual(topic["totals"]["airtime_s"], 6399)
        self.assertEqual(topic["totals"]["blocks"], 3)
        self.assertNotIn("each_full", topic["totals"])

    def test_subject_totals_carry_both_readings(self):
        subject = self._stats()["subjects"][0]
        self.assertEqual(subject["totals"]["shared_equal"], 3200)
        self.assertEqual(subject["totals"]["each_full"], 6399)
        self.assertEqual(subject["totals"]["blocks"], 3)

    def test_period_and_buckets(self):
        topic = self._stats()
        self.assertEqual(topic["first_record"], "2026-09-02")
        self.assertEqual(len(topic["by_month"]), 1)
        self.assertEqual(topic["by_month"][0]["airtime_s"], 6399)
        self.assertEqual(topic["by_program"][0]["program"], "Programa")

    def test_subject_by_day_lets_client_sum_any_period(self):
        topic = self._stats()
        by_date = {d["date"]: d["subjects"] for d in topic["subject_by_day"]}
        self.assertIn("2026-09-02", by_date)
        first_day = by_date["2026-09-02"]
        self.assertIn("a", first_day)
        self.assertIn("b", first_day)
        self.assertEqual(first_day["a"]["shared_equal"], 564)
        self.assertEqual(first_day["a"]["blocks"], 1)
        # cada dia é arredondado à parte, por isso somar os dias pode
        # divergir do total all-time em ±1s por dia com dados — é o
        # mesmo comportamento descrito na Metodologia, não um erro.
        total_a = sum(d["subjects"].get("a", {}).get("shared_equal", 0)
                      for d in topic["subject_by_day"])
        self.assertAlmostEqual(
            total_a, topic["subjects"][0]["totals"]["shared_equal"], delta=3
        )

    def test_program_by_day_is_clock_time_not_summed_across_subjects(self):
        topic = self._stats()
        by_date = {d["date"]: d["programs"] for d in topic["program_by_day"]}
        first_day = by_date["2026-09-02"]
        # o bloco de 2026-09-02 tem os dois intervenientes (a e b) mas
        # é um único bloco de "Programa" — airtime não duplica.
        self.assertEqual(first_day["Programa"]["airtime_s"], 1129)
        self.assertEqual(first_day["Programa"]["blocks"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
