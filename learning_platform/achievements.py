"""Hextech battle achievements.

Achievements are pure data plus a predicate over a battle snapshot. The store
is a plain JSON document next to the user's (or guest's) progress file, so it
survives restarts and follows account switching without extra plumbing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .storage import JsonStore


@dataclass(frozen=True)
class Achievement:
    id: str
    name: str  # Chinese source string; pass through app.tr() in the UI.
    description: str
    icon: str
    rarity: str  # silver / gold / prismatic / demon
    check: Callable[[dict], bool] = field(compare=False, repr=False)

    def unlocked(self, context):
        try:
            return bool(self.check(context))
        except (KeyError, TypeError, ValueError):
            return False


def _one_shot(c):
    return c.get("max_single_damage", 0) >= 100


def _demon_slayer(c):
    return (
        c.get("won")
        and c.get("max_hp") == 1000
        and c.get("difficulty") == "地狱"
    )


def _flawless(c):
    return c.get("finished") and c.get("player_hp") == c.get("max_hp")


def _streak5(c):
    return c.get("best_streak", 0) >= 5


def _comeback(c):
    return c.get("won") and c.get("player_hp") <= c.get("max_hp", 1) * 0.3


def _prismatic(c):
    return c.get("won") and c.get("augment_rarity") == "prismatic"


def _speed(c):
    return c.get("fastest_correct", 999) <= 5


def _survivor(c):
    return c.get("total_matches", 0) >= 10


# Wall order: highest tier first (Demon -> Prismatic -> Gold -> Silver).
ACHIEVEMENTS = (
    Achievement("demon_slayer", "大魔王猎手", "击败 1000 血的地狱难度大肥鱼。", "♛", "demon", _demon_slayer),
    Achievement("one_shot", "一击必杀", "单次对大肥鱼造成至少 100 点伤害。", "⚡", "prismatic", _one_shot),
    Achievement("flawless", "毫发无伤", "满血通关一整场对战。", "✦", "gold", _flawless),
    Achievement("streak5", "连战连捷", "连续答对 5 题。", "✧", "gold", _streak5),
    Achievement("comeback", "绝地反击", "血量不高于 30% 时逆转获胜。", "✹", "gold", _comeback),
    Achievement("prismatic", "棱彩大师", "带着棱彩强化赢得对战。", "◆", "gold", _prismatic),
    Achievement("speed", "速战速决", "5 秒内答对一道题。", "➤", "silver", _speed),
    Achievement("survivor", "百战之姿", "累计完成 10 场对战。", "✪", "silver", _survivor),
)

BY_ID = {item.id: item for item in ACHIEVEMENTS}


class AchievementStore:
    """Tracks unlocked badges and lifetime stats in one JSON document."""

    DEFAULT = {
        "unlocked": {},
        "stats": {
            "matches": 0,
            "wins": 0,
            "best_streak": 0,
            "max_single_damage": 0,
            "fastest_correct": None,
        },
    }

    def __init__(self, path):
        self.store = JsonStore(Path(path), self.DEFAULT)

    @staticmethod
    def path_for(app):
        data_dir = app.guest_progress_path.parent
        if app.user:
            try:
                from uuid import UUID

                account_id = str(UUID(app.user["id"]))
                return data_dir / "profiles" / account_id / "achievements.json"
            except (ValueError, KeyError, TypeError):
                pass
        return data_dir / "achievements.json"

    def load(self):
        data = self.store.read()
        if not isinstance(data, dict):
            raise ValueError("成就存档格式无效")
        unlocked = data.get("unlocked", {})
        stats = data.get("stats", {})
        if not isinstance(unlocked, dict) or not isinstance(stats, dict):
            raise ValueError("成就存档格式无效")
        merged = dict(self.DEFAULT)
        merged["unlocked"] = {
            key: value for key, value in unlocked.items() if key in BY_ID
        }
        merged["stats"] = {**self.DEFAULT["stats"], **stats}
        return merged

    def save(self, data):
        self.store.write(data)

    def evaluate(self, context):
        """Merge a battle snapshot into lifetime stats and unlock new badges.

        Returns the list of newly unlocked achievements. The caller is expected
        to call :meth:`save` once per battle to avoid repeated disk writes.
        """
        data = self.load()
        stats = data["stats"]
        stats["matches"] = int(stats.get("matches", 0)) + (1 if context.get("finished") else 0)
        stats["wins"] = int(stats.get("wins", 0)) + (1 if context.get("won") else 0)
        stats["best_streak"] = max(int(stats.get("best_streak", 0)), int(context.get("best_streak", 0)))
        stats["max_single_damage"] = max(
            int(stats.get("max_single_damage", 0)), int(context.get("max_single_damage", 0))
        )
        fastest = context.get("fastest_correct")
        # The battle layer already validates the answer against that round's
        # real clock (difficulty 25/30/45s plus timing augments). A fixed 30s
        # cap here would discard legitimate fast answers on harder questions,
        # so only reject non-positive values. The speed badge itself is an
        # absolute <=5s threshold and is unaffected.
        if fastest is not None and 0 < fastest:
            old = stats.get("fastest_correct")
            stats["fastest_correct"] = fastest if old is None else min(float(old), float(fastest))

        full = dict(context)
        full.update(stats)
        full["total_matches"] = stats["matches"]
        full["max_single_damage"] = stats["max_single_damage"]
        full["best_streak"] = stats["best_streak"]
        fastest = stats.get("fastest_correct")
        full["fastest_correct"] = fastest if fastest is not None else 999

        new = []
        for badge in ACHIEVEMENTS:
            if badge.id not in data["unlocked"] and badge.unlocked(full):
                data["unlocked"][badge.id] = 1
                new.append(badge)
        self.save(data)
        return new

    def unlocked_ids(self):
        return set(self.load()["unlocked"])

    def reset(self):
        """Clear all unlocked badges and lifetime stats for this account.

        Used by the Settings > reset action (e.g. for a fresh demo). Writes a
        brand-new default document so the class-level ``DEFAULT`` is never
        mutated. Returns the number of badges that were cleared.
        """
        data = self.load()
        cleared = len(data.get("unlocked", {}))
        fresh = {
            "unlocked": {},
            "stats": dict(self.DEFAULT["stats"]),
        }
        self.save(fresh)
        return cleared
