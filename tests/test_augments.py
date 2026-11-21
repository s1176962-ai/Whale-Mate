"""Rules tests for the battle augment pool and its match-long effects."""

import random
import unittest

from learning_platform.augment_ui import (
    DEMON_BASE,
    DEMON_HIGHLIGHT,
    DEMON_STREAKS,
    edge_colors,
)
from learning_platform.augments import AUGMENTS, AugmentRuntime, draw_augments
from learning_platform.battle import grade, speed_bands


def card(augment_id):
    return next(item for item in AUGMENTS if item.id == augment_id)


class AugmentTests(unittest.TestCase):
    def test_late_correct_option_has_no_rewards_and_breaks_streak(self):
        for item in AUGMENTS:
            with self.subTest(augment=item.id):
                runtime = AugmentRuntime(item, 100)
                runtime.streak = 1
                score = runtime.player_score(True, 25.05, 20, limit=25)
                self.assertEqual(score.total, 0)
                if item.id == "streak_fervor":
                    self.assertEqual(runtime.streak, 0)
        # The boundary itself remains accepted, as in the base grading rule.
        runtime = AugmentRuntime(card("sharp_mind"), 100)
        self.assertGreater(runtime.player_score(True, 25, 100, limit=25).extra, 0)

    def test_draw_returns_one_card_per_tier(self):
        picks = draw_augments(random.Random(7))
        self.assertEqual(len(picks), 4)
        self.assertEqual(len({item.id for item in picks}), 4)
        self.assertEqual(
            {item.rarity for item in picks},
            {"silver", "gold", "prismatic", "demon"},
        )

    def test_all_cards_have_unique_ids_and_translatable_fields(self):
        self.assertEqual(len({item.id for item in AUGMENTS}), len(AUGMENTS))
        for item in AUGMENTS:
            self.assertTrue(item.name and item.description and item.rarity_label)

    def test_neutral_runtime_preserves_default_rules(self):
        runtime = AugmentRuntime(None, 100)
        self.assertEqual(runtime.round_seconds, 30)
        self.assertEqual(runtime.player_score(True, 3, 100).total, 150)
        self.assertIsNone(runtime.hidden_option_index(["A", "B", "C"], "B"))

    def test_time_sandglass_extends_limit(self):
        runtime = AugmentRuntime(card("time_sandglass"), 100)
        self.assertEqual(runtime.round_seconds, 38)
        self.assertEqual(grade(True, 35).total, 0)
        self.assertEqual(runtime.player_score(True, 35, 100, limit=38).total, 100)

    def test_sharp_mind_adds_extra_points(self):
        runtime = AugmentRuntime(card("sharp_mind"), 100)
        self.assertEqual(runtime.player_score(True, 3, 100).total, 180)
        self.assertEqual(runtime.player_score(False, 3, 100).total, 0)

    def test_thick_shell_blocks_only_first_loss(self):
        runtime = AugmentRuntime(card("thick_shell"), 500)
        weak, strong = grade(False, 31), grade(True, 3)
        first = runtime.damage(500, 500, weak, strong, False, True)
        self.assertEqual(first[:2], (500, 500))
        self.assertIn("厚壳", "".join(first[2]))
        second = runtime.damage(500, 500, weak, strong, False, True)
        self.assertEqual(second[:2], (350, 500))
        self.assertEqual(second[2], [])

    def test_thick_shell_ignores_loss_when_player_was_correct(self):
        # "免疫首次答错" must not be spent on a correct-but-slower answer.
        runtime = AugmentRuntime(card("thick_shell"), 500)
        player_hp, ai_hp, notes = runtime.damage(
            500, 500, grade(True, 12), grade(True, 3), True, True
        )
        self.assertLess(player_hp, 500)  # HP did drop (correct but slower)
        self.assertEqual(notes, [])  # shield untouched
        # A later real wrong answer is still blocked.
        next_hp, _, next_notes = runtime.damage(
            player_hp, 500, grade(False, 31), grade(True, 3), False, True
        )
        self.assertEqual(next_hp, player_hp)
        self.assertIn("厚壳", "".join(next_notes))

    def test_checkpoint_restore_rolls_back_streak(self):
        runtime = AugmentRuntime(card("streak_fervor"), 100)
        runtime.player_score(True, 3, 100)  # streak -> 1
        snap = runtime.checkpoint()
        runtime.player_score(True, 3, 100)  # streak -> 2 (would grant +20)
        runtime.restore(snap)  # voided round: back to streak 1
        # Next correct answer is treated as the 2nd, not the 3rd.
        self.assertEqual(runtime.player_score(True, 3, 100).total, 170)

    def test_knowledge_leech_adds_damage_on_correct_vs_wrong(self):
        runtime = AugmentRuntime(card("knowledge_leech"), 500)
        strong, weak = grade(True, 3), grade(False, 31)
        result = runtime.damage(500, 500, strong, weak, True, False)
        self.assertEqual(result[:2], (500, 335))

    def test_streak_fervor_rewards_and_resets(self):
        runtime = AugmentRuntime(card("streak_fervor"), 100)
        self.assertEqual(runtime.player_score(True, 3, 100).total, 150)
        self.assertEqual(runtime.player_score(True, 3, 100).total, 170)
        self.assertEqual(runtime.player_score(True, 3, 100).total, 190)
        self.assertEqual(runtime.player_score(False, 3, 100).total, 0)
        self.assertEqual(runtime.player_score(True, 3, 100).total, 150)

    def test_insight_blanks_only_wrong_options(self):
        runtime = AugmentRuntime(card("insight"), 100)
        for seed in range(20):
            hidden = runtime.hidden_option_index(["A", "B", "C"], "B", random.Random(seed))
            self.assertIn(hidden, (0, 2))

    def test_last_stand_only_when_low_hp(self):
        runtime = AugmentRuntime(card("last_stand"), 100)
        self.assertEqual(runtime.player_score(True, 3, 31).total, 150)
        self.assertEqual(runtime.player_score(True, 3, 30).total, 300)

    def test_demon_pact_halves_question_limit_and_triples_score(self):
        runtime = AugmentRuntime(card("demon_pact"), 100)
        self.assertEqual(runtime.limit_for(25), 12.5)
        self.assertEqual(runtime.limit_for(30), 15)
        self.assertEqual(runtime.limit_for(45), 22.5)
        easy_bands = speed_bands(25)
        self.assertEqual(grade(True, 13, limit=12.5, bands=easy_bands).total, 0)
        # 100 correct + 50 speed = 150 -> 450.
        score = runtime.player_score(True, 3, 100, limit=12.5, bands=easy_bands)
        self.assertEqual(score.total, 450)
        weak = grade(False, 31, limit=25, bands=easy_bands)
        # Damage still follows the (now tripled) score gap naturally.
        hit = runtime.damage(500, 500, score, weak, True, False)
        self.assertEqual(hit[:2], (500, 50))
        self.assertTrue(any("总得分 ×3" in note for note in hit[2]))
        self.assertEqual(runtime.damage(500, 500, weak, score, False, True)[:2], (50, 500))

    def test_double_edge_doubles_gain_and_backfires_on_wrong(self):
        runtime = AugmentRuntime(card("double_edge"), 100)
        self.assertEqual(runtime.player_score(True, 3, 100).total, 300)
        result = runtime.damage(500, 500, grade(False, 31), grade(True, 3), False, True)
        self.assertEqual(result[:2], (335, 500))

    def test_demon_border_runs_multiple_moving_streaks(self):
        count = 28

        def heads(phase):
            return [
                i for i, color in enumerate(edge_colors("demon", count, phase))
                if color == "#FFFFFF"
            ]

        for phase in (0, 1, 5):
            self.assertEqual(len(heads(phase)), DEMON_STREAKS)
        # Every streak advances together in the reverse (counter-clockwise) direction.
        first = heads(0)
        self.assertEqual(sorted(heads(1)), sorted((index - 1) % count for index in first))
        # Dark gaps survive; the border is not a solid zebra stripe.
        self.assertGreater(edge_colors("demon", count, 0).count(DEMON_BASE), 0)

    def test_demon_border_uses_multi_colour_tail(self):
        # Each streak is a white/blush/red/black/brown burning tail, not one hue.
        colors = edge_colors("demon", 28, 0)
        self.assertGreaterEqual(len(set(colors)), 8)  # 8 highlight hues + base
        for hue in DEMON_HIGHLIGHT:
            self.assertIn(hue, colors)

    def test_edge_colors_handles_empty_border(self):
        self.assertEqual(edge_colors("demon", 0, 0), [])


if __name__ == "__main__":
    unittest.main()
