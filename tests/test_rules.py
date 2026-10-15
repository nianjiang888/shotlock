"""规则自测。跑法：python -m unittest discover tests"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shotlock.engine import load, validate
from shotlock.rules import P0, P1, RULES, RULE_INDEX, count_speakable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOOD = os.path.join(ROOT, "examples", "good_deck.json")
BAD = os.path.join(ROOT, "examples", "bad_deck.json")


class TestExamples(unittest.TestCase):
    def test_good_deck_is_clean(self):
        report = validate(load(GOOD))
        self.assertFalse(report.blocked, f"合规样例不应被阻断：{[i.message for i in report.issues]}")
        self.assertEqual(report.counts[P1], 0, f"合规样例不应有严重项：{[i.message for i in report.issues]}")

    def test_bad_deck_fires_every_rule(self):
        """Gallery 的意义就是每条规则都得真能抓到东西，所以这条测试是硬门槛。"""
        report = validate(load(BAD))
        fired = {i.rule_id for i in report.issues}
        declared = {rid for rid, _, _ in RULES}
        self.assertEqual(declared - fired, set(), f"这些规则在坏样例里没被触发：{sorted(declared - fired)}")

    def test_bad_deck_blocks(self):
        report = validate(load(BAD))
        self.assertTrue(report.blocked)

    def test_rule_ids_are_unique_and_documented(self):
        ids = [rid for rid, _, _ in RULES]
        self.assertEqual(len(ids), len(set(ids)), "规则 ID 有重复")
        for rid in ids:
            self.assertIn(rid, RULE_INDEX)


class TestSpeechCount(unittest.TestCase):
    def test_chinese_counts_by_character(self):
        self.assertEqual(count_speakable("还没打烊吧"), 5)

    def test_latin_counts_by_word(self):
        self.assertEqual(count_speakable("OK fine"), 2)

    def test_mixed(self):
        self.assertEqual(count_speakable("来一杯 coffee"), 4)


class TestFiltering(unittest.TestCase):
    def test_only(self):
        report = validate(load(BAD), only=["SL003"])
        self.assertEqual({i.rule_id for i in report.issues}, {"SL003"})

    def test_skip(self):
        report = validate(load(BAD), skip=["SL001", "SL002"])
        self.assertNotIn("SL001", {i.rule_id for i in report.issues})
        self.assertNotIn("SL002", {i.rule_id for i in report.issues})


class TestAxisCrossing(unittest.TestCase):
    """越轴是这套规则里最反直觉的一条，单独测。"""

    def _script(self, prev_size: str, prev_dirs: dict, cur_dirs: dict):
        def chars(d):
            return [{"id": k, "screen_dir": v} for k, v in d.items()]

        return {
            "characters": [{"id": "c_a", "name": "A"}, {"id": "c_b", "name": "B"}],
            "scenes": [{"id": "s_01", "location": "x", "time_of_day": "夜", "lighting": "暗", "int_ext": "INT"}],
            "shots": [
                {"id": "sh_1", "scene_id": "s_01", "duration_sec": 3, "shot_size": prev_size,
                 "camera_move": "STATIC", "characters": chars(prev_dirs)},
                {"id": "sh_2", "scene_id": "s_01", "duration_sec": 3, "shot_size": "MEDIUM",
                 "camera_move": "STATIC", "characters": chars(cur_dirs)},
            ],
        }

    def test_flip_is_caught(self):
        from shotlock.schema import Script

        d = self._script("MEDIUM", {"c_a": "left", "c_b": "right"}, {"c_a": "right", "c_b": "left"})
        report = validate(Script.from_dict(d), only=["SL008"])
        self.assertEqual(len(report.issues), 1)

    def test_wide_resets_axis(self):
        from shotlock.schema import Script

        d = self._script("WIDE", {"c_a": "left", "c_b": "right"}, {"c_a": "right", "c_b": "left"})
        report = validate(Script.from_dict(d), only=["SL008"])
        self.assertEqual(len(report.issues), 0, "全景之后重设轴线，不该报越轴")

    def test_single_sided_flip_is_not_crossing(self):
        """只有一个人换边不构成越轴，轴线是两人连线决定的。"""
        from shotlock.schema import Script

        d = self._script("MEDIUM", {"c_a": "left", "c_b": "right"}, {"c_a": "right", "c_b": "right"})
        report = validate(Script.from_dict(d), only=["SL008"])
        self.assertEqual(len(report.issues), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
