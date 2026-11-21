"""Real Tk widgets with isolated progress; no user interaction required."""

import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

from learning_platform.gui import Application
from learning_platform.repositories import (
    LearningPlanRepository,
    PersonalQuestionRepository,
    ProgressRepository,
)
from tests import fresh_tk_root


class GuiTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = fresh_tk_root()
        except tk.TclError as exc:
            self.skipTest(f"Tk display unavailable: {exc}")
        self.root.withdraw()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.app = Application(self.root, progress_path=Path(temp.name) / "progress.json")
        self.app.enter_guest()
        user = self.app.auth.register("GuiTester", "Password1", "Password1")
        self.app.user = user
        self.app.progress = ProgressRepository(self.app.auth.progress_path(user))
        self.app.personal_bank = PersonalQuestionRepository(
            self.app.auth.personal_questions_path(user)
        )
        self.app.learning_plan = LearningPlanRepository(self.app.auth.learning_plan_path(user))
        self.app.home()
        self.root.update()

    def test_settings_scroll_tracks_wrapped_content(self):
        self.root.deiconify()
        self.root.geometry("1000x700")
        self.app.settings()
        self.root.update()
        app = self.app
        self.assertEqual(int(app.canvas.itemcget(app.window, "height")), 0)
        self.assertFalse(any(
            isinstance(w, ttk.LabelFrame) and w.cget("text") == app.tr("皮肤")
            for w in app.body.winfo_children()
        ))
        app.body.event_generate("<MouseWheel>", delta=-120)
        self.root.update()
        self.assertGreater(app.canvas.yview()[0], 0)
        # Resize causes descriptions to wrap again after the initial layout.
        self.root.geometry("760x600")
        self.root.update()
        app.canvas.yview_moveto(1)
        self.root.update()
        self.assertGreaterEqual(float(app.canvas.cget("scrollregion").split()[3]),
                                app.body.winfo_reqheight())
        last = app.body.winfo_children()[-1]
        self.assertLessEqual(last.winfo_y() + last.winfo_height(),
                             app.canvas.canvasy(app.canvas.winfo_height()))
        self.assertAlmostEqual(app.canvas.yview()[1], 1)

    def test_settings_small_wheel_deltas_and_control_hover_scroll_page(self):
        self.root.deiconify()
        self.root.geometry("1000x700")
        self.app.settings()
        self.root.update()
        app = self.app
        before = app.canvas.yview()[0]
        for _ in range(12):
            app.body.event_generate("<MouseWheel>", delta=-10)
        self.root.update()
        self.assertGreater(app.canvas.yview()[0], before)
        combo = ttk.Combobox(app.body, values=("one", "two"), state="readonly")
        combo.current(0)
        combo.pack()
        self.root.update()
        app.canvas.yview_moveto(0)
        app.display["wheel_controls"] = False
        combo.event_generate("<MouseWheel>", delta=-120)
        self.root.update()
        self.assertGreater(app.canvas.yview()[0], 0)
        self.assertEqual(combo.current(), 0)

    def test_home_shirt_opens_separate_skin_page(self):
        self.app.home()
        self.app.skin_button.invoke()
        self.root.update()
        self.assertEqual(self.app.chrome_title.cget("text"), self.app.tr("皮肤"))
        self.assertEqual(len(self.app._skin_controls["battle"]), 4)
        self.app._apply_battle_skin("普通级", "hell")
        self.assertEqual(self.app.skin_prefs.selected(
            self.app.project_root, "battle", "普通级"), "hell")
        self.assertEqual(self.app.skin_prefs.selected(
            self.app.project_root, "battle", "困难"), "auto")
        self.app.home()
        self.assertTrue(self.app.skin_button.winfo_exists())

    def test_cancel_motion_removes_all_overlapping_overlays(self):
        from learning_platform.motion import Motion

        self.root.deiconify()
        self.root.update()
        motion = Motion(self.root)
        motion.fade_in(self.app.canvas, duration=10000)
        first = motion._overlay
        motion.fade_overlay(self.app.canvas, duration=10000)
        second = motion._overlay
        self.assertIsNot(first, second)
        self.assertTrue(first.winfo_exists())
        self.assertTrue(second.winfo_exists())
        motion.cancel()
        self.assertFalse(first.winfo_exists())
        self.assertFalse(second.winfo_exists())
        self.assertFalse(motion._jobs)
        self.assertFalse(motion._overlays)
        motion.cancel()  # Cleanup remains safe when invoked twice.

    def test_overlay_completion_preserves_other_animation(self):
        from learning_platform.motion import Motion

        motion = Motion(self.root)
        with patch.object(motion, "active", return_value=True):
            motion.fade_in(self.app.canvas, duration=10000)
            first = motion._overlay
            motion.fade_in(self.app.canvas, duration=10000)
            second = motion._overlay
        motion._drop_overlay(first)
        self.assertTrue(second.winfo_exists())
        motion.cancel()
        self.assertFalse(second.winfo_exists())

    def test_animated_settings_and_notebook_update_scroll_without_resize(self):
        self.root.deiconify()
        self.root.geometry("1000x700")
        self.app.home()
        self.root.update()
        self.app.motion.enabled = True
        data = self.app.progress.load()
        for q in self.app.questions[:5]:
            data["wrong"][q.id] = {
                "count": 1, "last_answer": q.options[0],
                "last_seen": "2026-11-21T10:00:00+08:00",
            }
        data["history"] = [{
            "id": f"scroll-{index}", "date": "2026-11-21T10:00:00+08:00",
            "subject": "English", "mode": "quiz", "total": 2,
            "correct": 1, "incorrect": 1, "accuracy": 50.0,
            "score": 1, "max_score": 2,
        } for index in range(8)]
        self.app.progress.save(data)
        # Keep the window size unchanged throughout, as in real navigation.
        for page in (self.app.settings, self.app.notebook, self.app.history, self.app.settings):
            with self.subTest(page=page.__name__):
                page()
                self.root.update()
                app = self.app
                self.assertGreater(app.body.winfo_reqheight(), app.canvas.winfo_height())
                self.assertEqual(int(app.canvas.itemcget(app.window, "height")), 0)
                self.assertTrue(app.scrollbar.winfo_ismapped())
                app.body.event_generate("<MouseWheel>", delta=-120)
                self.root.update()
                self.assertGreater(app.canvas.yview()[0], 0)
                app.canvas.yview_moveto(1)
                self.root.update()
                self.assertGreaterEqual(app.canvas.canvasy(app.canvas.winfo_height()),
                                        app.body.winfo_reqheight())
        self.app.home()
        self.root.update()
        self.assertGreaterEqual(self.app.body.winfo_height(), self.app.canvas.winfo_height())

    def test_guest_cannot_open_notebook_or_history(self):
        self.app.enter_guest()
        with patch("learning_platform.gui.messagebox.showinfo") as info:
            self.app.notebook()
            self.app.history()
        self.assertEqual(info.call_count, 2)
        self.assertNotIn("notebook", self.app._nav_buttons)
        self.assertNotIn("history", self.app._nav_buttons)

    def test_late_valid_battle_decision_is_void_without_damage(self):
        from learning_platform.battle import OpponentDecision

        self.app.battle_page()
        battle = self.app.battle
        battle.start()
        q = battle.questions[0]
        battle.answer(q.answer)
        decision = OpponentDecision(q.id, q.answer, 10, "A valid answer", "api")
        # Use the round's actual deadline so the "late" assertion holds for
        # every difficulty (hard questions have a 45s window, not 30s).
        battle.receive_decision(decision, None, battle.ai_limit + 0.01)
        self.assertIsNone(battle.decision)
        self.assertIsNone(battle.planned)
        battle.finish_round()
        self.assertEqual((battle.player_hp, battle.ai_hp), (battle.max_hp, battle.max_hp))
        self.assertEqual(battle.records, [])
        self.assertEqual(battle.next.cget("text"), "▶")
        self.root.after_cancel(battle.timer_id)

    def test_voided_round_rolls_back_augment_state(self):
        """A late/errored decision must restore the pre-answer augment snapshot."""
        from learning_platform.battle import OpponentDecision

        self.app.battle_page()
        battle = self.app.battle
        battle.start()
        q = battle.questions[0]
        battle.answer(q.answer)  # saves a snapshot before player_score()
        self.assertTrue(hasattr(battle, "_augment_snapshot"))

        # Force the void path with a late decision, then spy on restore().
        decision = OpponentDecision(q.id, q.answer, 10, "late", "api")
        battle.receive_decision(decision, None, battle.ai_limit + 0.01)
        with patch.object(battle.augment, "restore") as restore:
            battle.finish_round()
        restore.assert_called_once_with(battle._augment_snapshot)
        self.assertEqual((battle.player_hp, battle.ai_hp), (battle.max_hp, battle.max_hp))
        self.root.after_cancel(battle.timer_id)

    def test_battle_round_renders_question_portrait_and_options(self):
        self.app.battle_page()
        battle = self.app.battle
        battle.start()
        self.root.update()
        self.assertTrue(battle.active)
        self.assertEqual(len(battle.buttons), len(battle.questions[0].options))
        self.assertTrue(battle.portrait.cget("image"))
        battle.show_decision_stage(1)
        text = battle.thinking_status.get("1.0", "end-1c")
        self.assertIn("2 / 3", text)
        self.assertNotIn("1 / 3", text)
        self.assertNotIn("Decision saved", text)
        battle.answer(battle.questions[0].answer)
        self.assertEqual(battle.player.correct, 100)
        battle.active = False
        battle.generation += 1
        self.root.after_cancel(battle.timer_id)

    def test_battle_api_failure_does_not_damage_or_score(self):
        from learning_platform.battle import grade

        self.app.battle_page()
        battle = self.app.battle
        battle.start()
        battle.answer(battle.questions[0].answer)
        battle.ai = grade(False, 31)
        battle.decision_error = "Invalid JSON response"
        battle.finish_round()
        self.assertEqual((battle.player_hp, battle.ai_hp), (battle.max_hp, battle.max_hp))
        self.assertEqual(battle.records, [])
        self.assertEqual(battle.next.cget("text"), "▶")
        self.assertIn("Invalid JSON response", battle.thinking_status.get("1.0", "end-1c"))
        battle.generation += 1
        self.root.after_cancel(battle.timer_id)

    def test_battle_augment_selection_starts_match_with_card(self):
        self.root.deiconify()
        self.root.geometry("1000x800")
        self.root.update()
        self.app.battle_page()
        battle = self.app.battle
        battle.choose_augment()
        self.root.update()
        self.assertTrue(all(card.find_all() for card in battle.augment_cards))
        self.assertEqual(len(battle.augment_choices), 3)
        self.assertEqual(len(battle.augment_cards), 3)
        self.assertEqual(len({card.augment.id for card in battle.augment_cards}), 3)
        self.app.motion.cancel()
        chosen = battle.augment_choices[0]
        battle._confirm_augment(chosen)
        self.root.update()
        self.assertIs(battle.selected_augment, chosen)
        self.assertIs(battle.augment.augment, chosen)
        badge = battle.augment_badge
        self.assertTrue(badge.winfo_exists())
        self.assertTrue(badge.find_all())
        badge_text = [
            str(badge.itemcget(item, "text"))
            for item in badge.find_all()
            if badge.type(item) == "text"
        ]
        self.assertTrue(any(self.app.tr(chosen.name) in text for text in badge_text))
        self.assertIn(self.app.tr(chosen.rarity_label), badge_text)
        self.app.motion.cancel()
        battle.generation += 1
        self.root.after_cancel(battle.timer_id)

    def test_demon_pact_does_not_void_slower_opponent_answer(self):
        from learning_platform.augments import AUGMENTS
        from learning_platform.battle import OpponentDecision

        demon = next(card for card in AUGMENTS if card.id == "demon_pact")
        from learning_platform.battle import question_seconds

        self.app.battle_page()
        battle = self.app.battle
        battle.start(demon)
        self.root.update()
        q = battle.questions[0]
        self.assertEqual(battle.player_limit, question_seconds(q.difficulty) / 2)
        self.assertEqual(battle.ai_limit, question_seconds(q.difficulty))
        self.assertGreater(battle.ai_limit, battle.player_limit)

        decision = OpponentDecision(q.id, q.answer, 12, "A valid answer", "api")
        battle.receive_decision(decision, None, 12, battle.ai_limit)
        battle._score_opponent(q)
        self.assertEqual(battle.ai.correct, 100)
        self.assertGreater(battle.ai.time, 0)

        battle.answer(q.answer, limit=battle.player_limit)
        battle.finish_round()
        self.app.motion.cancel()
        self.assertLess(battle.ai_hp, battle.max_hp)
        self.assertEqual(battle.player_hp, battle.max_hp)
        self.assertEqual(str(battle.ai_status.cget("foreground")), "#22C55E")
        self.assertIn(
            self.app.tr("魔王契约：本题总得分 ×3。"),
            battle.result.get("1.0", "end-1c"),
        )
        battle.generation += 1
        self.root.after_cancel(battle.timer_id)
        battle._cancel_pending()

    def test_battle_round_uses_question_difficulty_clock(self):
        from learning_platform.battle import question_seconds

        self.app.battle_page()
        battle = self.app.battle
        battle.start()
        self.root.update()
        q = battle.questions[0]
        expected = question_seconds(q.difficulty)
        self.assertEqual(battle.question_limit, expected)
        self.assertEqual(battle.player_limit, expected)
        self.assertEqual(battle.ai_limit, expected)
        self.assertEqual(battle.ai_grade_limit, expected)
        battle._cancel_pending()

    def test_demon_damage_float_with_motion_enabled(self):
        """The ×3 float must not crash finish_round when motion is active.

        battle_fx imports the raw ``tokens`` module, where colours live only in
        ``palette()``; using ``T.BG`` there raised AttributeError and aborted the
        whole round (no result text, no auto-advance). Activation requires a
        viewable window, which is why earlier motion-off tests never hit it.
        """
        from learning_platform.augments import AUGMENTS
        from learning_platform.battle import grade

        demon = next(card for card in AUGMENTS if card.id == "demon_pact")
        self.app.battle_page()
        battle = self.app.battle
        battle.start(demon)
        self.root.update()

        battle.answer(battle.questions[0].answer)
        battle.ai = grade(False, 31)  # player lands a hit -> ai_damage > 0
        # Force the motion branch (a real session has a viewable window, the
        # shared test root does not). tween() calls frame(0) synchronously, so
        # a broken colour token raises right here instead of in an after().
        with patch.object(self.app.motion, "active", return_value=True):
            battle.finish_round()  # would raise AttributeError before the fix
        self.root.update()

        # finish_round ran to completion rather than aborting mid-damage stage.
        self.assertLess(battle.ai_hp, battle.max_hp)
        self.assertIn(
            self.app.tr("魔王契约：本题总得分 ×3。"),
            battle.result.get("1.0", "end-1c"),
        )
        # The floating ×3 label was actually painted on the enemy bar.
        ai_floats = [
            battle.ai_bar.itemcget(i, "text")
            for i in battle.ai_bar.find_all()
            if battle.ai_bar.type(i) == "text"
            and battle.ai_bar.itemcget(i, "text") == "×3"
        ]
        self.assertGreaterEqual(len(ai_floats), 1)

        self.app.motion.cancel()
        battle.generation += 1
        self.root.after_cancel(battle.timer_id)
        battle._cancel_pending()

    def test_infinite_match_can_settle_between_rounds_without_awarding_victory(self):
        from learning_platform.battle import grade

        self.app.battle_page()
        battle = self.app.battle
        battle.count.set(battle.COUNT_INFINITE)
        battle.initial_hp.set("1000")
        battle.start()
        self.assertTrue(battle.end_button.instate(["disabled"]))
        self.assertEqual(battle.playback_status.cget("text"), self.app.tr("答题中，揭晓后可暂停"))
        battle.end_match()
        self.assertFalse(battle._results_shown)
        battle.answer(battle.questions[0].answer)
        self.assertEqual(battle.playback_status.cget("text"),
                         self.app.tr("等待对手作答，揭晓后可暂停"))
        battle.ai = grade(True, 3)
        battle.planned = battle.questions[0].answer
        battle.finish_round()
        self.assertTrue(battle.end_button.instate(["!disabled"]))
        self.assertIsNotNone(battle._auto_after)
        battle.end_button.invoke()
        self.assertTrue(battle._results_shown)
        self.assertIsNone(battle._auto_after)
        self.assertEqual(len(battle.records), 1)
        data = battle.achievement_store.load()
        self.assertEqual(data["stats"]["matches"], 0)
        self.assertEqual(data["stats"]["wins"], 0)
        self.assertNotIn("flawless", data["unlocked"])
        with patch.object(battle.achievement_store, "evaluate") as evaluate:
            battle.end_match()
            battle.advance()
            evaluate.assert_not_called()
        self.root.after_cancel(battle.timer_id)

    def test_wrong_answer_infinite_match_can_end_while_paused(self):
        from learning_platform.battle import grade

        self.app.battle_page()
        battle = self.app.battle
        battle.count.set(battle.COUNT_INFINITE)
        battle.initial_hp.set("1000")
        battle.start()
        battle.answer(None, timed_out=True)
        battle.ai = grade(True, 3)
        battle.planned = battle.questions[0].answer
        battle.finish_round()
        self.assertTrue(battle.paused)
        self.assertEqual(battle.playback_status.cget("text"),
                         self.app.tr("答错已暂停，查看解析后按空格继续"))
        battle.end_match()
        self.assertTrue(battle._results_shown)
        self.assertIsNone(battle._auto_after)
        self.root.after_cancel(battle.timer_id)

    def test_infinite_knockout_uses_natural_result_even_when_end_is_clicked(self):
        from learning_platform.battle import grade

        self.app.battle_page()
        battle = self.app.battle
        battle.count.set(battle.COUNT_INFINITE)
        battle.start()
        battle.answer(battle.questions[0].answer)
        battle.ai = grade(False, 31)
        battle.finish_round()
        self.assertEqual(battle.ai_hp, 0)
        battle.end_match()
        data = battle.achievement_store.load()
        self.assertEqual(data["stats"]["matches"], 1)
        self.assertEqual(data["stats"]["wins"], 1)
        self.root.after_cancel(battle.timer_id)

    def test_demo_draft_guarantees_demon_without_changing_profile_pity(self):
        self.app.battle_page()
        battle = self.app.battle
        store = battle._augment_draft_store()
        store.store.write({"misses": 2})
        battle.demo_choice.set(True)
        battle.choose_augment()
        self.assertEqual(len(battle.augment_choices), 3)
        self.assertTrue(any(c.rarity == "demon" for c in battle.augment_choices))
        self.assertEqual(store.misses(), 2)
        account_path = store.store.path
        self.app.user = None
        self.assertNotEqual(battle._augment_draft_store().store.path, account_path)
        self.assertEqual(battle._augment_draft_store().misses(), 0)
        battle.setup()
        self.assertFalse(battle.demo_choice.get())

    def test_battle_review_pause_and_space(self):
        from learning_platform.battle import grade

        self.root.deiconify()
        self.root.geometry("1200x850")
        self.app.battle_page()
        battle = self.app.battle
        battle.start()
        self.root.update()
        battle.toggle_pause()
        self.assertTrue(battle.active)
        self.assertFalse(battle.paused)
        self.assertIsNone(battle._auto_after)
        self.assertTrue(battle.next.instate(["disabled"]))
        battle.answer(battle.questions[0].answer)
        battle.ai = grade(True, 12)
        battle.planned = battle.questions[0].answer
        battle.finish_round()
        self.assertFalse(battle.paused)
        self.assertIsNotNone(battle._auto_after)
        # Focus on the control to verify native Space does not toggle twice.
        battle.next.focus_force()
        self.root.update()
        battle.next.event_generate("<KeyPress-space>")
        self.root.update()
        self.assertTrue(battle.paused)
        self.assertIsNone(battle._auto_after)
        self.assertEqual(battle.next.cget("text"), "▶")
        self.assertEqual(battle.playback_status.cget("text"), self.app.tr("已暂停，按空格继续"))
        remaining = battle._advance_remaining
        battle.next.event_generate("<KeyPress-space>")
        self.root.update()
        self.assertFalse(battle.paused)
        self.assertEqual(battle._advance_remaining, remaining)
        self.assertIsNotNone(battle._auto_after)
        battle._cancel_pending()
        self.root.after_cancel(battle.timer_id)

    def test_battle_wrong_answer_pauses_including_final_round(self):
        from learning_platform.battle import grade

        self.app.battle_page()
        battle = self.app.battle
        battle.start()
        battle.index = len(battle.questions) - 1
        battle.answer(None, timed_out=True)
        battle.ai = grade(True, 12)
        battle.planned = battle.questions[battle.index].answer
        battle.finish_round()
        self.assertTrue(battle.paused)
        self.assertIsNone(battle._auto_after)
        self.assertTrue(battle.next.instate(["!disabled"]))
        self.assertIn(battle.questions[battle.index].explanation,
                      battle.thinking_status.get("1.0", "end-1c"))
        battle.toggle_pause()
        self.assertIsNotNone(battle._auto_after)
        battle._cancel_pending()
        self.root.after_cancel(battle.timer_id)

    def test_battle_health_bars_and_damage_poses(self):
        self.app.battle_page()
        battle = self.app.battle
        battle.start()
        self.root.update()
        self.assertTrue(battle.player_bar.winfo_exists())
        self.assertTrue(battle.ai_bar.winfo_exists())
        self.assertEqual(battle.player_bar.value, battle.max_hp)

        battle.answer(battle.questions[0].answer)
        battle.ai = __import__(
            "learning_platform.battle", fromlist=["grade"]
        ).grade(False, 31)
        battle.planned = "wrong option"
        battle.finish_round()
        self.app.motion.cancel()
        self.assertLess(battle.ai_bar.value, battle.max_hp)
        self.assertTrue(battle.ai_bar.winfo_exists())

        # Segmented score cards: four framed values with total = sum of parts.
        self.assertTrue(battle.player_score.winfo_exists())
        self.assertTrue(battle.ai_score.winfo_exists())
        self.assertEqual(battle.player_score._segment_values(), (100, 50, 0, 150))
        ptexts = [
            str(battle.player_score.itemcget(i, "text"))
            for i in battle.player_score.find_all()
            if battle.player_score.type(i) == "text"
        ]
        self.assertIn("+", ptexts)
        self.assertIn("=", ptexts)
        self.assertIn("150", ptexts)
        self.assertIn(self.app.tr("正确"), ptexts)
        self.assertIn(self.app.tr("总分"), ptexts)
        # The centre dialog keeps the answer/explanation and drops the
        # now-redundant score arithmetic.
        result = battle.result.get("1.0", "end-1c")
        self.assertIn(self.app.tr("正确答案"), result)
        self.assertNotIn(" = 150", result)
        battle.generation += 1
        self.root.after_cancel(battle.timer_id)
        battle._cancel_pending()

    def test_battle_health_bars_share_column_and_clear_names(self):
        from tkinter import font as tkfont

        from learning_platform import tokens as T

        self.app.battle_page()
        battle = self.app.battle
        battle.start()
        self.root.update()
        name_font = tkfont.Font(font=T.TYPE_BODY)
        longest = max(
            name_font.measure(battle.player_name),
            name_font.measure(battle.opponent_name),
        )
        self.assertEqual(battle.player_bar.label_width, battle.ai_bar.label_width)
        self.assertGreaterEqual(battle.player_bar.label_width, longest)
        self.assertEqual(battle.player_bar.winfo_width(), battle.ai_bar.winfo_width())
        self.assertEqual(battle.player_bar.bar_geometry, battle.ai_bar.bar_geometry)
        self.assertFalse(battle.player_bar.mirrored)
        self.assertTrue(battle.ai_bar.mirrored)
        if battle.player_bar.value_x is not None:
            self.assertEqual(
                battle.player_bar.value_x + battle.ai_bar.value_x,
                battle.player_bar.winfo_width(),
            )
        # The two combatants sit side by side in one row (reference layout).
        self.assertEqual(battle.player_bar.grid_info()["row"], 0)
        self.assertEqual(battle.ai_bar.grid_info()["row"], 0)
        self.assertNotEqual(
            battle.player_bar.grid_info()["column"],
            battle.ai_bar.grid_info()["column"],
        )
        self.assertEqual(battle.player_bar.winfo_y(), battle.ai_bar.winfo_y())
        battle.generation += 1
        self.root.after_cancel(battle.timer_id)
        battle._cancel_pending()

    def test_battle_header_fixed_and_clock_in_dock(self):
        """Augment + bars sit in a fixed header; clock sits in the dock centre.

        The health bars and augment banner must not scroll with the question,
        and the round counter/timer must be in the bottom centre column rather
        than above the question.
        """
        from learning_platform.augments import AUGMENTS

        self.app.battle_page()
        battle = self.app.battle
        augment = next(card for card in AUGMENTS if card.rarity == "prismatic")
        battle.start(augment)
        self.root.update()

        header = self.app.battle_header
        # Fixed header is packed into outer, not the scrolling canvas body.
        self.assertTrue(header.winfo_exists())
        self.assertIsNot(header.master, self.app.body)
        self.assertIs(header.master, self.app.outer)
        # Bars and augment banner are children of that fixed header.
        self.assertIs(battle.player_bar.master.master, header)
        self.assertIs(battle.ai_bar.master.master, header)
        self.assertIs(battle.augment_badge.master, header)
        # Clock lives in the bottom dock's centre column, above the data row,
        # between the two symmetric score cards (clock -> panel -> dock).
        self.assertIs(battle.clock.master.master, self.app.action_dock)
        self.assertEqual(battle.clock.grid_info()["row"], 0)
        self.assertEqual(battle.clock.grid_info()["column"], 1)
        self.assertIn("/", battle.clock.cget("text"))
        self.assertIn("s", battle.clock.cget("text"))
        # Battle-data output is on its own row below the clock, not sharing a
        # horizontal band with the score cards (that crowding hid the content).
        self.assertEqual(battle.result.master.master.grid_info()["row"], 3)
        # Score cards share one uniform column definition => mirror symmetry.
        self.assertEqual(battle.player_score.grid_info()["column"], 0)
        self.assertEqual(battle.ai_score.grid_info()["column"], 2)
        self.assertEqual(battle.player_score.master, battle.ai_score.master)
        # Two-line HUD keeps the names separate from the health track.
        self.assertLess(battle.player_bar.winfo_reqheight(), 64)
        self.assertLess(battle.player_score.winfo_reqheight(), 60)

        battle.generation += 1
        self.root.after_cancel(battle.timer_id)
        battle._cancel_pending()

    def test_battle_cards_share_health_bar_inset_and_result_is_centred(self):
        """Question cards line up with the fixed bars; centre text is centred.

        The canvas window must use SPACE_4 AND measure against `outer`, while
        the body frame's own padding stays 0. With a visible scrollbar the
        canvas is ~10px narrower than `outer`, so measuring against the canvas
        shrank the cards; a second SPACE_4 on the body frame shrank them again.
        Separately, tk.Text ignores the built-in "all" tag for justify, so
        centring needs a named tag covering the whole document.
        """
        from learning_platform import tokens as T
        from learning_platform.gui import AssistantReply

        self.root.deiconify()
        self.root.geometry("1400x1000")
        self.root.update()
        self.app.battle_page()
        battle = self.app.battle
        battle.start()
        self.root.update()

        # The single inset matches the fixed header/dock; the body frame adds
        # none, and the width is measured against `outer` (scrollbar-proof).
        self.assertEqual(self.app._body_side_pad, T.px(T.SPACE_4))
        self.assertTrue(self.app._body_match_outer)
        body_pad_left, _ = self.app.body.cget("padding")
        self.assertEqual(body_pad_left, 0)

        # Geometry invariant: the body window's real canvas bbox starts at
        # SPACE_4 and spans exactly the header's inner width. Root coordinates
        # are unreliable here (withdrawn test root, and canvas-embedded widgets
        # omit the window item's own offset), so compare widths in local space.
        self.root.update_idletasks()
        self.root.update()
        bx0, _, bx1, _ = self.app.canvas.bbox(self.app.window)
        header_w = self.app.battle_header.winfo_width()
        self.assertEqual(bx0, T.px(T.SPACE_4))
        self.assertEqual(bx1 - bx0, header_w - 2 * T.px(T.SPACE_4))

        # Health bars and question cards must use the SAME symmetric column
        # structure: equal widths and mirror padx on the two columns. Any
        # asymmetry (e.g. cards with padx=(0,12)/(0,0)) shifted the middle
        # gutter and made the right column wider than the left — the ragged
        # edges the reference layout forbids.
        pcard, acard = battle.player_status.master, battle.ai_status.master
        self.assertEqual(pcard.winfo_width(), acard.winfo_width())
        self.assertEqual(battle.player_bar.winfo_width(), battle.ai_bar.winfo_width())
        self.assertEqual(pcard.winfo_width(), battle.player_bar.winfo_width())
        battle.player_bar.set_value(50, animate=False)
        battle.ai_bar.set_value(50, animate=False)
        left = battle.player_bar.fill_geometry
        right = battle.ai_bar.fill_geometry
        width = battle.player_bar.winfo_width()
        self.assertAlmostEqual(left[0], width - right[2])
        self.assertAlmostEqual(left[2], width - right[0])
        battle.player_bar.set_value(0, animate=False)
        self.assertEqual(battle.player_bar.fill_geometry[0], battle.player_bar.fill_geometry[2])
        self.assertTrue(battle.ai_score.mirrored)
        self.assertFalse(battle.player_score.mirrored)

        left_c = pcard.grid_info()["column"]
        right_c = acard.grid_info()["column"]
        self.assertEqual((left_c, right_c), (0, 1))
        # Symmetric padx: left card's right gap == right card's left gap.
        lp = pcard.grid_info()["padx"]
        rp = acard.grid_info()["padx"]
        self.assertEqual(lp[0], 0)  # left card hugs the outer left edge
        self.assertEqual(rp[1], 0)  # right card hugs the outer right edge
        self.assertEqual(lp[1], rp[0])  # equal middle gutter on both sides

        # Centring uses a named tag spanning the full text, not the "all" tag.
        self.assertIsInstance(battle.result, AssistantReply)
        self.assertEqual(battle.result._justify, "center")
        self.assertIn("aligned", battle.result.tag_names())
        self.assertNotIn("all", battle.result.tag_names())
        battle.result.configure(text="alpha\nbeta")
        ranges = battle.result.tag_ranges("aligned")
        # Tk keeps one implicit trailing newline; the tag must cover it too
        # (stopping at end-1c left the last line left-aligned).
        self.assertEqual((str(ranges[0]), str(ranges[-1])), ("1.0", "3.0"))

        battle.generation += 1
        self.root.after_cancel(battle.timer_id)
        battle._cancel_pending()

    def test_battle_damage_pose_images_exist(self):
        root = self.app.project_root
        for state in ("attacked", "die", "attack"):
            path = root / "assets" / "battle" / f"ai_assistant_{state}.png"
            self.assertTrue(path.exists(), str(path))

        self.app.battle_page()
        battle = self.app.battle
        battle.start()
        battle.show_expression("attacked")
        self.assertTrue(battle.portrait.cget("image"))
        battle.generation += 1
        self.root.after_cancel(battle.timer_id)
        battle._cancel_pending()

    def test_skin_packs_have_all_states(self):
        """Every skin pack provides the full 7-state set as standalone PNGs."""
        root = self.app.project_root
        skins = (
            (root / "assets" / "battle" / "skins" / "default", "default"),
            (root / "assets" / "battle" / "skins" / "hell", "hell"),
        )
        states = ("normal", "thinking", "correct", "wrong", "attack", "attacked", "die")
        for skin_dir, name in skins:
            self.assertTrue(skin_dir.is_dir(), name)
            for state in states:
                path = skin_dir / f"{state}.png"
                self.assertTrue(path.exists(), f"{name}/{state}.png")
                from PIL import Image

                with Image.open(path) as im:
                    self.assertEqual(im.mode, "RGBA", f"{name}/{state}.png")
        registry = root / "assets" / "battle" / "skins" / "skin_registry.json"
        self.assertTrue(registry.exists())

    def test_hell_difficulty_uses_hell_skin_pack(self):
        """地狱难度 uses the hell skin pack (7 poses); others use default."""
        self.app.battle_page()
        battle = self.app.battle
        battle.start()

        # Normal difficulty -> default skin pack, all standalone PNGs.
        battle.difficulty = "普通级"
        self.assertFalse(battle._hell_art)
        self.assertEqual(battle._skin_id, "default")
        for state in ("thinking", "correct", "wrong", "attack"):
            path, sheet = battle._portrait_source(state)
            self.assertEqual(path.parent.name, "default", state)
            self.assertFalse(sheet, state)

        # Hell difficulty -> hell skin for every one of the seven poses.
        battle.difficulty = "地狱"
        self.assertTrue(battle._hell_art)
        self.assertEqual(battle._skin_id, "hell")
        for state in ("normal", "thinking", "correct", "wrong", "attack", "attacked", "die"):
            path, sheet = battle._portrait_source(state)
            self.assertEqual(path.parent.name, "hell", state)
            self.assertEqual(path.name, f"{state}.png", state)
            self.assertFalse(sheet, state)

        battle.show_expression("normal")
        self.assertTrue(battle.portrait.cget("image"))
        battle.generation += 1
        self.root.after_cancel(battle.timer_id)
        battle._cancel_pending()

    def test_skin_store_difficulty_and_fallback(self):
        """Skin registry maps difficulties to skins and never returns a missing path."""
        from learning_platform import skins as skin_store

        root = self.app.project_root
        self.assertEqual(
            skin_store.skin_for_difficulty(root, "地狱"), "hell"
        )
        self.assertEqual(
            skin_store.skin_for_difficulty(root, "普通级"), "default"
        )
        for skin in skin_store.available_skins(root):
            for state in skin_store.DEFAULT_STATES:
                path = skin_store.portrait_path(root, skin, state)
                self.assertIsNotNone(path, f"{skin}/{state}")
                self.assertTrue(path.exists(), f"{skin}/{state}: {path}")
            # Unknown states resolve to None (shown as text fallback) or a file.
            self.assertFalse(skin_store.is_sheet(root, skin, "thinking"))

    def test_achievement_page_renders_badges(self):
        self.app.achievements_page()
        self.root.update()
        from learning_platform.achievements import ACHIEVEMENTS

        canvases = [
            child
            for child in self.app.body.winfo_children()
            for child in child.winfo_children()
            if child.winfo_class() == "Canvas"
        ]
        self.assertGreaterEqual(len(canvases), len(ACHIEVEMENTS))

    def test_achievements_sorted_demon_to_silver(self):
        from learning_platform.achievements import ACHIEVEMENTS

        rank = {"demon": 0, "prismatic": 1, "gold": 2, "silver": 3}
        tiers = [rank[badge.rarity] for badge in ACHIEVEMENTS]
        self.assertEqual(tiers, sorted(tiers))

    def test_locked_badge_shows_tier_border_and_label(self):
        from learning_platform.achievement_ui import AchievementCard
        from learning_platform.achievements import BY_ID

        self.root.deiconify()
        self.root.geometry("1000x800")
        card = AchievementCard(
            self.app.body, BY_ID["demon_slayer"], False, self.app.tr,
            motion=self.app.motion,
        )
        card.pack()
        self.root.update()
        self.assertTrue(card.find_all())
        texts = [
            str(card.itemcget(item, "text"))
            for item in card.find_all() if card.type(item) == "text"
        ]
        self.assertTrue(any("魔王" in t or "Demon" in t for t in texts), texts)
        # The unlock condition must stay visible even while locked (it is
        # wrapped to two lines, so match on a distinctive leading fragment).
        condition = self.app.tr(BY_ID["demon_slayer"].description)
        self.assertTrue(
            any(condition[:8] in t for t in texts), texts
        )
        # Border is built from many line segments (card-style), not one flat
        # round_rect outline.
        self.assertGreater(
            len([i for i in card.find_all() if card.type(i) == "line"]), 8
        )
        self.app.motion.cancel()
        # An unlocked prismatic badge gets the same multi-colour segmented edge.
        prism = AchievementCard(
            self.app.body, BY_ID["one_shot"], True, self.app.tr,
            motion=self.app.motion,
        )
        prism.pack()
        self.root.update()
        plines = [i for i in prism.find_all() if prism.type(i) == "line"]
        self.assertGreater(len(plines), 8)
        self.assertGreater(
            len({str(prism.itemcget(i, "fill")) for i in plines}), 1
        )
        self.app.motion.cancel()

    def test_achievement_entry_is_in_battle_setup_not_sidebar(self):
        self.app.battle_page()

        def walk(widget):
            found = []
            try:
                found.append(str(widget.cget("text")))
            except (tk.TclError, AttributeError):
                pass
            for child in widget.winfo_children():
                found.extend(walk(child))
            return found

        texts = walk(self.app.body)
        self.assertIn(self.app.tr("成就徽章"), texts)
        self.assertNotIn("achievements", getattr(self.app, "_nav_buttons", {}))

    def test_guest_achievement_page_shows_signup_prompt(self):
        self.app.enter_guest()
        self.app.achievements_page()
        self.root.update()
        texts = []
        for widget in self.app.body.winfo_children():
            try:
                texts.append(str(widget.cget("text")))
            except tk.TclError:
                pass
        joined = " ".join(texts).lower()
        self.assertTrue("account" in joined or "账号" in joined, joined)
        self.assertFalse("unlocked" in joined or "已解锁" in joined, joined)

    def test_notebook_overflow_shows_scrollbar(self):
        self.root.deiconify()
        self.root.geometry("960x640")
        data = self.app.progress.load()
        for q in self.app.questions[:5]:
            data["wrong"][q.id] = {
                "count": 1,
                "last_answer": q.options[0],
                "last_seen": "2026-11-13T10:00:00+08:00",
            }
        self.app.progress.save(data)
        self.app.notebook()
        self.root.update()
        self.assertTrue(self.app.scrollbar.winfo_ismapped())
        self.app.canvas.yview_moveto(1)
        self.root.update()
        self.assertGreater(self.app.canvas.yview()[0], 0)

    def test_text_only_question_and_feedback_keep_assistant_geometry(self):
        from dataclasses import replace

        self.root.deiconify()
        self.root.geometry("1080x800")
        self.app.motion.enabled = False
        question = replace(self.app.questions[0], question_image=None, option_images=None)
        self.app.start_quiz([question])
        self.root.update()
        self.assertEqual(self.app.images, [])
        panel = self.app.quiz_ai_panel
        before = (panel.winfo_rooty(), panel.winfo_height())
        self.app.answer.set(question.answer)
        with patch.object(self.app.ai_assistant, "ask") as request:
            self.app.submit()
            request.assert_not_called()
        self.assertNotIn("Keep going", self.app.feedback.cget("text"))
        self.root.update()
        self.assertEqual((panel.winfo_rooty(), panel.winfo_height()), before)

    def test_wrong_feedback_is_local_and_selected_option_has_short_label(self):
        self.app.motion.enabled = False
        question = self.app.questions[0]
        self.app.start_quiz([question])
        chosen = next(option for option in question.options if option != question.answer)
        self.app.answer.set(chosen)
        with patch.object(self.app.ai_assistant, "ask") as request:
            self.app.submit()
            request.assert_not_called()
        self.assertEqual(self.app.option_status[chosen].cget("text"), self.app.tr("你的选择"))
        feedback = self.app.feedback.cget("text")
        self.assertNotIn(self.app.tr("再想一想"), feedback)
        self.assertIn(question.answer, feedback)
        self.assertIn(question.explanation, feedback)
        self.assertTrue(feedback.startswith(self.app.tr("回答错误，已记入错题本。")))

    def test_numeric_controls_accept_direct_editing(self):
        self.app.configure()
        timer = self.app.timer_box
        timer.entry.delete(0, "end")
        timer.entry.insert(0, "120")
        self.assertEqual(self.app.timer_seconds.get(), "120")
        timer._commit_entry()
        self.assertEqual(timer.get(), "120")
        count = self.app.count_box
        count.entry.delete(0, "end")
        count.entry.insert(0, "12")
        self.assertEqual(self.app.count.get(), "12")
        count.entry.insert("end", "abc")
        self.assertEqual(count.get(), "12")
        count._commit_entry()
        self.app.start_configured()
        self.assertEqual(len(self.app.engine.questions), 12)

    def test_subject_cards_and_primary_action_positions(self):
        self.app.home()
        self.assertTrue(self.app.home_ai_button.winfo_exists())
        self.app.configure()
        self.assertEqual(self.app.chrome.pack_slaves()[0], self.app.chrome_back)
        self.assertEqual(self.app.chrome_back.winfo_manager(), "pack")
        self.assertEqual(
            {name for _, name in self.app._subject_cards}, {q.subject for q in self.app.questions}
        )
        self.app._select_subject("Science")
        self.assertEqual(self.app.subject.get(), "Science")
        self.assertEqual(self.app.start_button.pack_info()["side"], "left")
        self.app.start_quiz(self.app.questions[:2])
        self.assertTrue(self.app.quiz_ai_button.winfo_exists())
        self.assertEqual(self.app.submit_button.pack_info()["side"], "left")
        self.assertFalse(
            any(isinstance(w, ttk.Progressbar) for w in self.app.body.winfo_children())
        )
        self.app.answer.set(self.app.engine.current.answer)
        self.app.submit_button.invoke()
        self.assertEqual(self.app.next_button.pack_info()["side"], "left")

    def test_home_ai_card_uses_primary_tints_and_idle_portrait(self):
        from learning_platform import ui_tokens as T

        self.app.home()
        self.root.update_idletasks()
        self.assertEqual(self.app.home_ai_input.cget("bg"), T.AI_INPUT_BG)
        self.assertEqual(self.app.home_ai_reply.cget("bg"), T.AI_REPLY_BG)
        previous = T.theme_name()
        try:
            for theme in ("light", "dark"):
                T.set_theme(theme)
                self.assertNotEqual(T.AI_INPUT_BG, T.HOVER)
                self.assertNotEqual(T.AI_REPLY_BG, T.HOVER)
                self.assertNotEqual(T.AI_REPLY_BG, T.SURFACE)
        finally:
            T.set_theme(previous)
        self.assertEqual(self.app._home_ai_idle.winfo_manager(), "pack")
        self.assertEqual(self.app._home_ai_answer.winfo_manager(), "")
        self.assertIsNotNone(self.app._home_mascot_base())
        self.assertGreaterEqual(int(self.app._home_mascot.cget("width")), T.px(64))
        self.app.home_ai_reply.configure(text="Hint text")
        self.assertEqual(self.app._home_ai_idle.winfo_manager(), "")
        self.assertEqual(self.app._home_ai_answer.winfo_manager(), "pack")
        self.app.home_ai_reply.configure(text="")
        self.assertEqual(self.app._home_ai_idle.winfo_manager(), "pack")

    def test_count_changes_update_start_label_immediately(self):
        self.app.configure()
        self.app.count.set("2")
        self.assertIn("2", self.app.start_button.cget("text"))
        self.app.count_box.set("1")
        self.assertIn("1", self.app.start_button.cget("text"))
        self.app.start_button.invoke()
        self.assertEqual(len(self.app.engine.questions), 1)

    def test_daily_practice_starts_directly_from_saved_filters(self):
        self.app.learning_plan.set_settings("public", "English", "easy", 3)
        self.app.start_daily_practice()
        self.assertEqual(len(self.app.engine.questions), 3)
        self.assertEqual(self.app._practice_bank_kind, "public")
        self.assertEqual(self.app._last_filters["subject"], "English")
        self.assertEqual(self.app._last_filters["difficulty"], "easy")

    def test_wheel_control_setting_and_persistence(self):
        from types import SimpleNamespace

        self.app.configure()
        box = self.app.topic_box
        box.current(0)
        event = SimpleNamespace(widget=box, delta=-120)
        self.assertEqual(self.app._control_wheel(event), "break")
        self.assertEqual(box.current(), 0)
        self.app.display["wheel_controls"] = True
        self.app._control_wheel(event)
        self.assertEqual(box.current(), 1)
        self.app.settings()
        self.app.wheel_choice.set(True)
        self.app.save_display()
        self.assertTrue(self.app.display_store.load()["wheel_controls"])

    def test_quiz_actions_remain_visible_when_content_scrolls(self):
        self.root.deiconify()
        self.root.geometry("960x640")
        self.app.start_quiz(self.app.questions[:2])
        self.root.update()
        self.assertEqual(self.app.submit_button.master, self.app.action_dock)
        self.assertTrue(self.app.submit_button.winfo_ismapped())
        position = self.app.action_dock.winfo_rooty()
        header = self.app.quiz_progress_header
        header_position = header.winfo_rooty()
        self.assertIs(header.master, self.app.outer)
        self.assertFalse(any(isinstance(w, tk.Canvas) for w in self.app.body.winfo_children()))
        self.app.canvas.yview_moveto(1)
        self.root.update()
        self.assertEqual(self.app.action_dock.winfo_rooty(), position)
        self.assertEqual(header.winfo_rooty(), header_position)
        self.assertTrue(header.winfo_ismapped())
        q = self.app.engine.current
        self.assertEqual(self.app.option_buttons[0].cget("text"), q.options[0])
        self.app.answer.set(q.answer)
        self.app.submit_button.invoke()
        self.root.update()
        self.assertFalse(self.app.submit_button.winfo_ismapped())
        self.assertTrue(self.app.next_button.winfo_ismapped())
        self.app.next_button.invoke()
        self.assertEqual(self.app.engine.index, 1)

    def test_full_quiz_review_and_history_flow(self):
        self.app.configure()
        self.app.subject.set("Mathematics")
        self.app.refresh_filters()
        self.app.topic.set("Geometry")
        self.app.refresh_difficulties()
        self.app.count.set("2")
        self.app.start_configured()
        self.assertEqual(len(self.app.engine.questions), 2)
        self.assertTrue(self.app.images)
        question = self.app.engine.current
        self.app.answer.set(next(x for x in question.options if x != question.answer))
        self.app.submit_button.invoke()
        self.assertTrue(self.app.submit_button.instate(["disabled"]))
        self.assertTrue(all(button.instate(["disabled"]) for button in self.app.option_buttons))
        self.app.submit_button.invoke()
        self.assertEqual(len(self.app.engine.answers), 1)
        self.app.next_button.invoke()
        self.app.answer.set(self.app.engine.current.answer)
        self.app.submit_button.invoke()
        self.app.next_button.invoke()
        self.assertIsNone(self.app.engine)
        self.app.notebook()
        self.app.start_quiz([question], review=True)
        self.app.answer.set(question.answer)
        self.app.submit_button.invoke()
        self.app.next_button.invoke()
        self.assertEqual(self.app.progress.load()["wrong"], {})
        self.app.history()
        self.assertEqual(len(self.app.progress.load()["history"]), 2)
        self.root.update()

    def test_question_art_fills_the_question_column(self):
        from learning_platform.gui import art_factor

        # Source art is 3x the design grid, so a 720px box needs one halving.
        self.assertEqual(art_factor(1440, 810, 720, 420), 2)
        self.assertEqual(art_factor(480, 270, 720, 420), 1)
        self.root.deiconify()
        self.root.geometry("1200x800")
        self.app.start_quiz(self.app.questions[:1])
        self.root.update()
        column = self.app.question_shell.winfo_width()
        photos = []

        def walk(widget):
            for child in widget.winfo_children():
                photo = getattr(child, "_fit_photo", None)
                if photo is not None:
                    photos.append(photo)
                walk(child)

        walk(self.app.question_shell)
        self.assertTrue(photos)
        self.assertGreaterEqual(photos[0].width(), column * 0.55)
        self.assertLessEqual(photos[0].width(), column)
        # Regression guard: the old fixed 480x220 cap shrank art to half size.
        self.assertGreater(photos[0].width(), 240)

    def test_missing_and_invalid_images_fall_back(self):
        self.app.show_image("assets/missing.png")
        self.app.show_image("data/questions/english.json")
        self.app.show_image("../outside.png")
        labels = [
            w.cget("text") for w in self.app.body.winfo_children() if isinstance(w, ttk.Label)
        ]
        # Assertion stays valid in either locale: derive the lead-in from the catalog.
        marker = self.app.tr("图片无法显示：{0}\n{1}", "", "").splitlines()[0]
        marker = marker.replace("：", ":").split(":")[0]
        self.assertEqual(sum(marker in str(text) for text in labels), 3)

    def test_missing_question_in_notebook(self):
        q = self.app.questions[0]
        self.app.start_quiz([q])
        self.app.answer.set(next(x for x in q.options if x != q.answer))
        self.app.submit()
        del self.app.by_id[q.id]
        self.app.notebook()
        self.assertIn(q.id, self.app.progress.load()["wrong"])

    def test_invalid_input_and_empty_notebook(self):
        self.app.notebook()
        self.app.history()
        self.app.configure()
        self.app.count.set("abc")
        with patch("learning_platform.gui.messagebox.showerror") as error:
            self.app.start_configured()
            error.assert_called_once()
        self.app.start_quiz([self.app.questions[0]])
        with patch("learning_platform.gui.messagebox.showerror") as error:
            self.app.submit()
            error.assert_called_once()
        self.assertFalse(self.app.engine.submitted)

    def test_empty_bank_and_corrupt_progress(self):
        self.app.questions = []
        self.app.configure()
        self.app.progress.store.path.parent.mkdir(parents=True, exist_ok=True)
        self.app.progress.store.path.write_text("{bad", encoding="utf-8")
        self.app.home()
        with patch("learning_platform.gui.messagebox.showerror"):
            self.app.history()
            self.app.notebook()
        with patch("learning_platform.gui.messagebox.showerror") as error:
            self.app.start_quiz([self.app.questions[0]])
            error.assert_called_once()

    def test_login_password_toggle_error_and_narrow_layout(self):
        self.app.logout()
        self.app.login_page()
        self.assertEqual(self.app.password_entries[0].cget("show"), "•")
        self.app.password_toggle.invoke()
        self.assertEqual(self.app.password_entries[0].cget("show"), "")
        self.app.password_toggle.invoke()
        self.assertEqual(self.app.password_entries[0].cget("show"), "•")
        self.app.login_button.invoke()
        self.assertIn(self.app.tr("请输入用户名"), self.app.login_error.cget("text"))
        self.app.login_page(True)
        self.assertIn(self.app.tr("注册并进入"), self.app.login_button.cget("text"))
        self.root.geometry("700x620")
        self.root.update()
        self.app._layout_login()
        self.root.geometry("1100x720")
        self.root.update()
        self.app._layout_login()
        self.app.enter_guest()
        self.assertTrue(self.app.signed_in)

    def test_interactive_controls_without_face_still_activate(self):
        """Regression: controls lacking _face() must not crash on press/release.

        Segmented / Stepper / Dropdown / Toggle inherit Interactive but do not
        define ``_face()``. If ``_face_current()`` calls it unconditionally,
        the press/release handlers raise before ``_activate()`` runs and every
        such control becomes silently unclickable (the Configure-quiz bug).
        """
        from learning_platform import modern

        calls = []
        seg = modern.Segmented(self.root, values=["a", "b", "c"], on_change=calls.append)
        seg.pack()
        self.root.update_idletasks()
        # A control without _face() must report no blend face, not raise.
        self.assertIsNone(seg._face_current())
        # Simulate the press/release sequence the real pointer generates.
        seg._st_press(type("E", (), {"x": 0})())
        seg._st_release(None)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], "a")

        # Every Interactive subclass either defines _face() or is safe.
        for cls in (modern.Segmented, modern.Stepper, modern.Dropdown, modern.Toggle):
            self.assertFalse(
                hasattr(cls, "_face"),
                f"{cls.__name__} unexpectedly defines _face; test needs updating",
            )
        seg.destroy()

    def test_battle_infinite_mode_reshuffles_instead_of_ending(self):
        """With count=∞ the deck reshuffles until HP hits zero."""
        self.app.battle_page()
        battle = self.app.battle
        battle.count.set("∞")
        battle.subject.set("All")
        battle.topic.set(self.app.tr("全部"))
        battle.start()
        self.assertTrue(battle.infinite)
        deck_size = len(battle.questions)
        self.assertGreater(deck_size, 0)
        # Exhaust the deck with both sides still alive.
        battle.index = deck_size - 1
        battle.player_hp = battle.ai_hp = battle.max_hp
        battle.advance()
        self.assertFalse(getattr(battle, "_result_shown", False))
        self.assertEqual(battle.index, 0)
        self.assertEqual(len(battle.questions), deck_size)
        battle._cancel_pending()

    def test_battle_setup_has_bank_subject_topic_count_controls(self):
        """Battle setup exposes bank -> subject -> topic -> count in order."""
        self.app.battle_page()
        battle = self.app.battle
        for attr in (
            "bank_picker", "subject_box", "topic_box", "count_picker",
        ):
            widget = getattr(battle, attr, None)
            self.assertIsNotNone(widget, attr)
            self.assertTrue(widget.winfo_exists(), attr)
        self.assertIn("public", battle.bank_picker._values)
        self.assertIn("∞", battle.count_picker._values)
        self.assertIn(self.app.tr("全部"), list(battle.topic_box._values))
        # Default count is finite and the hint describes the match count.
        self.assertEqual(battle.count.get(), "5")

    def test_battle_setup_filters_share_one_row_and_actions_stay_in_card(self):
        """Filters use equal grid columns; Start is inside the visible card."""
        self.app.battle_page()
        battle = self.app.battle
        columns = []
        for widget in (
            battle.bank_picker, battle.subject_box,
            battle.topic_box, battle.count_picker,
        ):
            info = widget.master.grid_info()
            self.assertEqual(int(info["row"]), 0)
            columns.append(int(info["column"]))
        self.assertEqual(columns, [0, 1, 2, 3])

        # The primary action must not be packed onto the scroller body after an
        # expanding card (that made it invisible in a normal-height window).
        self.assertTrue(hasattr(battle, "start_button"))
        node = battle.start_button
        ancestors = []
        while node is not None:
            ancestors.append(node)
            node = node.master
        self.assertIn(self.app.battle.setup_card, ancestors)
        self.assertEqual(battle.start_button.cget("text"), self.app.tr("开始对战"))

    def test_achievement_store_reset_clears_everything(self):
        from learning_platform.achievements import AchievementStore

        tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        path = Path(tmp) / "achievements.json"
        store = AchievementStore(path)
        store.evaluate({"finished": True, "won": True, "total_matches": 1})
        self.assertGreater(len(store.unlocked_ids()), 0)
        cleared = store.reset()
        self.assertGreater(cleared, 0)
        self.assertEqual(store.unlocked_ids(), set())
        data = store.load()
        self.assertEqual(data["stats"]["matches"], 0)
        self.assertEqual(data["stats"]["wins"], 0)

    def test_settings_has_reset_achievements_action(self):
        from unittest.mock import patch

        self.app.settings()
        self.root.update()
        # The reset button exists and asks for confirmation before clearing.
        with patch("learning_platform.gui.messagebox.askyesno", return_value=False), \
             patch("learning_platform.gui.messagebox.showinfo") as info:
            self.app._reset_achievements()
            info.assert_not_called()
        with patch("learning_platform.gui.messagebox.askyesno", return_value=True), \
             patch("learning_platform.gui.messagebox.showinfo") as info:
            self.app._reset_achievements()
            self.assertTrue(info.called)



if __name__ == "__main__":
    unittest.main()
