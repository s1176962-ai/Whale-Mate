"""Achievement predicates and per-account persistence."""

import tempfile
import unittest
from pathlib import Path

from learning_platform.achievements import BY_ID, AchievementStore
from learning_platform.storage import DataError


class AchievementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = AchievementStore(Path(self.temp.name) / "achievements.json")

    def test_one_shot_requires_single_damage_of_100(self):
        base = {
            "finished": True, "won": True, "max_hp": 100, "difficulty": "普通级",
            "player_hp": 100, "ai_hp": 0, "augment_rarity": None,
            "best_streak": 0, "max_single_damage": 99, "fastest_correct": None,
        }
        self.assertNotIn("one_shot", {b.id for b in self.store.evaluate(base)})
        self.store = AchievementStore(Path(self.temp.name) / "achievements.json")
        base["max_single_damage"] = 100
        self.assertIn("one_shot", {b.id for b in self.store.evaluate(base)})

    def test_demon_slayer_is_demon_tier(self):
        self.assertEqual(BY_ID["demon_slayer"].rarity, "demon")

    def test_demon_slayer_needs_hell_and_1000_hp_win(self):
        base = {
            "finished": True, "won": True, "max_hp": 1000, "difficulty": "地狱",
            "player_hp": 200, "ai_hp": 0, "augment_rarity": None,
            "best_streak": 0, "max_single_damage": 0, "fastest_correct": None,
        }
        unlocked = {b.id for b in self.store.evaluate(base)}
        self.assertIn("demon_slayer", unlocked)
        self.assertIn("comeback", unlocked)

    def test_multiple_achievements_unlock_at_once(self):
        base = {
            "finished": True, "won": True, "max_hp": 100, "difficulty": "普通级",
            "player_hp": 100, "ai_hp": 0, "augment_rarity": "prismatic",
            "best_streak": 5, "max_single_damage": 150, "fastest_correct": 4.0,
        }
        unlocked = {b.id for b in self.store.evaluate(base)}
        self.assertTrue(
            {"one_shot", "flawless", "streak5", "prismatic", "speed"}.issubset(unlocked)
        )

    def test_unlocks_are_persisted_and_not_repeated(self):
        base = {
            "finished": True, "won": True, "max_hp": 100, "difficulty": "普通级",
            "player_hp": 100, "ai_hp": 0, "augment_rarity": None,
            "best_streak": 5, "max_single_damage": 150, "fastest_correct": 4.0,
        }
        first = self.store.evaluate(base)
        self.assertTrue(first)
        second = self.store.evaluate(base)
        self.assertEqual(second, [])
        self.assertIn("one_shot", self.store.unlocked_ids())

    def test_lifetime_matches_count_towards_survivor(self):
        base = {
            "finished": True, "won": False, "max_hp": 100, "difficulty": "普通级",
            "player_hp": 0, "ai_hp": 50, "augment_rarity": None,
            "best_streak": 0, "max_single_damage": 0, "fastest_correct": None,
        }
        for _ in range(9):
            self.store.evaluate(base)
        self.assertNotIn("survivor", self.store.unlocked_ids())
        self.store.evaluate(base)
        self.assertIn("survivor", self.store.unlocked_ids())

    def test_path_for_binds_to_account_and_guest_separately(self):
        from types import SimpleNamespace
        from uuid import uuid4

        data_dir = Path(self.temp.name)
        store = AchievementStore(data_dir / "achievements.json")

        account_id = str(uuid4())
        user = {"id": account_id}
        app = SimpleNamespace(user=user, guest_progress_path=data_dir / "progress.json")
        self.assertEqual(
            store.path_for(app),
            data_dir / "profiles" / account_id / "achievements.json",
        )

        guest_app = SimpleNamespace(user=None, guest_progress_path=data_dir / "progress.json")
        self.assertEqual(store.path_for(guest_app), data_dir / "achievements.json")

    def test_corrupt_store_raises_data_error(self):
        path = Path(self.temp.name) / "bad.json"
        path.write_text("not json", encoding="utf-8")
        with self.assertRaises(DataError):
            AchievementStore(path).load()

    def test_all_badges_have_english_entries(self):
        catalog = Path(__file__).resolve().parents[1] / "learning_platform" / "locales" / "en.json"
        import json

        english = json.loads(catalog.read_text(encoding="utf-8"))
        for badge in BY_ID.values():
            self.assertIn(badge.name, english, badge.id)
            self.assertIn(badge.description, english, badge.id)


if __name__ == "__main__":
    unittest.main()
