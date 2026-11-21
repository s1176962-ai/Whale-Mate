"""Hextech-style battle augments: a curated pool and match-long effects.

Cards are data; their effects are applied through :class:`AugmentRuntime` so
the UI never has to branch on raw card ids. ``AugmentRuntime(None, hp)`` is a
neutral runtime used when the player skips the pick (existing callers/tests).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .battle import ROUND_SECONDS, BattleScore, apply_damage, grade

RARITY_LABELS = {
    "silver": "白银",
    "gold": "黄金",
    "prismatic": "棱彩",
    "demon": "魔王",
}
# Highest tier, above prismatic. Rendered with a black / white / red strobe.
RARITY_ORDER = ("silver", "gold", "prismatic", "demon")


@dataclass(frozen=True)
class Augment:
    id: str
    name: str  # Chinese source string; pass through app.tr() in the UI.
    description: str  # Chinese source string; pass through app.tr() in the UI.
    rarity: str
    weight: float

    @property
    def rarity_label(self):
        return RARITY_LABELS[self.rarity]


AUGMENTS = (
    Augment(
        "sharp_mind",
        "锋锐思维",
        "答对时额外获得 30 分。",
        "silver",
        5,
    ),
    Augment(
        "thick_shell",
        "厚壳",
        "本局首次答错时免疫一次扣血。",
        "silver",
        5,
    ),
    Augment(
        "time_sandglass",
        "时间沙漏",
        "每回合答题时间增加 8 秒。",
        "gold",
        3,
    ),
    Augment(
        "knowledge_leech",
        "知识掠夺",
        "你答对且大肥鱼答错时，额外扣除它 15 点血量。",
        "gold",
        3,
    ),
    Augment(
        "streak_fervor",
        "连胜狂热",
        "连续答对：第 2 题额外 +20 分，第 3 题起额外 +40 分；答错后重新计数。",
        "gold",
        3,
    ),
    Augment(
        "insight",
        "洞察之眼",
        "每回合随机排除一个错误选项。",
        "prismatic",
        1.5,
    ),
    Augment(
        "last_stand",
        "绝境反冲",
        "当你的血量不高于初始血量的 30% 时，答对得分翻倍。",
        "prismatic",
        1.5,
    ),
    Augment(
        "double_edge",
        "双刃剑",
        "答对得分翻倍，但答错时自己额外失去 15 点血量。",
        "prismatic",
        1.5,
    ),
    Augment(
        "demon_pact",
        "魔王契约",
        "你的答题时间缩短为该题时限的一半，但本题总得分 ×3。",
        "demon",
        1,
    ),
)

DRAW_COUNT = 4


def draw_augments(rng=None, count=DRAW_COUNT):
    """Offer one card per tier, then shuffle them into the draft hand.

    Guaranteeing one card from each tier (silver / gold / prismatic / demon)
    makes every rarity -- including the top demon tier -- visible each match,
    the way the Arena augment draft does.
    """
    rng = rng or random.Random()
    picked = []
    for tier in RARITY_ORDER:
        pool = [item for item in AUGMENTS if item.rarity == tier]
        if pool:
            picked.append(rng.choice(pool))
    rng.shuffle(picked)
    return tuple(picked[:count])


class AugmentRuntime:
    """Mutable per-match state for one selected card (or no card)."""

    def __init__(self, augment, max_hp):
        self.augment = augment
        self.max_hp = max_hp
        self.streak = 0
        self.shield_used = False

    @property
    def id(self):
        return self.augment.id if self.augment is not None else None

    @property
    def name(self):
        return self.augment.name if self.augment is not None else ""

    @property
    def description(self):
        return self.augment.description if self.augment is not None else ""

    @property
    def round_seconds(self):
        """Legacy default window; battle rounds use ``limit_for`` instead."""
        return self.limit_for(ROUND_SECONDS)

    def checkpoint(self):
        """Snapshot mutable match state (streak / shield) for a voided round."""
        return self.streak, self.shield_used

    def restore(self, snapshot):
        """Roll back to a pre-answer snapshot when a round is voided."""
        self.streak, self.shield_used = snapshot

    def limit_for(self, base_seconds):
        """Apply this card's timing rule to a question's base clock."""
        if self.id == "demon_pact":
            return base_seconds / 2
        if self.id == "time_sandglass":
            return base_seconds + 8
        return base_seconds

    def hidden_option_index(self, options, answer, rng=None):
        """Return the index of a wrong option to blank out, if this card does it."""
        if self.id != "insight":
            return None
        rng = rng or random.Random()
        wrong = [index for index, option in enumerate(options) if option != answer]
        return rng.choice(wrong) if wrong else None

    def player_score(self, correct, elapsed, player_hp, limit=None, bands=None):
        """Grade the player's answer, then layer the augment's scoring rules."""
        base = grade(correct, elapsed, limit=limit, bands=bands)
        # Only an answer accepted within the clock window earns augment
        # rewards or advances the streak, even if the clicked option is right.
        correct = bool(base.correct)
        extra = base.extra
        card = self.id
        if correct and card == "sharp_mind":
            extra += 30
        if card == "streak_fervor":
            self.streak = self.streak + 1 if correct else 0
            if correct and self.streak == 2:
                extra += 20
            elif correct and self.streak >= 3:
                extra += 40
        score = BattleScore(base.correct, base.time, extra)
        low_hp = player_hp <= self.max_hp * 0.3
        if correct and ((card == "last_stand" and low_hp) or card == "double_edge"):
            score = BattleScore(score.correct * 2, score.time * 2, score.extra * 2)
        if card == "demon_pact":
            # 100 correct + 50 speed -> 450; damage follows the score gap.
            score = BattleScore(score.correct * 3, score.time * 3, score.extra * 3)
        return score

    def damage(self, player_hp, ai_hp, player_score, ai_score, player_correct, ai_correct):
        """Apply normal damage plus the card's defensive/offensive twist."""
        notes = []
        card = self.id
        next_player, next_ai = apply_damage(
            player_hp, ai_hp, player_score.total, ai_score.total
        )
        if card == "demon_pact":
            notes.append("魔王契约：本题总得分 ×3。")
        if (
            card == "thick_shell"
            and not player_correct
            and next_player < player_hp
            and not self.shield_used
        ):
            next_player = player_hp
            self.shield_used = True
            notes.append("厚壳抵挡了本次伤害。")
        if card == "knowledge_leech" and player_correct and not ai_correct:
            next_ai = max(0, next_ai - 15)
            notes.append("知识掠夺额外扣除大肥鱼 15 点血量。")
        if card == "double_edge" and not player_correct:
            next_player = max(0, next_player - 15)
            notes.append("双刃剑反噬：你额外失去 15 点血量。")
        return next_player, next_ai, notes
