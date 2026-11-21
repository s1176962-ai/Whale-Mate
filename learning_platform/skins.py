"""Swappable skins for the home, login and battle screens.

A *skin* is just a named set of replacement images. All skins are described by
``assets/skins/skin_registry.json``, which groups them into three scopes:

* ``home`` -- the idle mascot portrait (role ``mascot``)
* ``login`` -- the brand decoration (role ``decoration``)
* ``battle`` -- the seven opponent poses (roles in ``DEFAULT_STATES``)

Each scope declares its default skin and the roles a skin must provide. A skin
maps every role to an image path relative to ``assets/skins``. Adding a skin is
a data-only change: drop the images in a folder and add one registry entry --
no code changes required. Files missing from a skin fall back to the scope's
default skin, so partial packs are safe.

The legacy battle functions (``skin_for_difficulty``, ``portrait_path``, ...) are
kept intact for backwards compatibility; the generic API below is what the
settings UI uses. The module stays dependency-free (stdlib + pathlib) so both
the GUI and the tests can import it.
"""

import json
from functools import lru_cache
from pathlib import Path

from .storage import JsonStore

# Generic registry / preference locations (relative to the project root).
SKINS_DIR = "skins"
REGISTRY_FILE = "skin_registry.json"
PREFERENCES_FILE = "skins.json"
SCOPES = ("home", "login", "battle")
AUTO_SKIN = "auto"  # battle-only: follow the selected difficulty
# Battle opponent levels, mirroring battle.PROFILES keys. Kept here as a
# constant so this module stays dependency-free (battle must not be imported).
BATTLE_DIFFICULTIES = ("入门级", "普通级", "困难", "地狱")

DEFAULT_STATES = (
    "normal",
    "thinking",
    "correct",
    "wrong",
    "attack",
    "attacked",
    "die",
)


@lru_cache(maxsize=8)
def load_registry(project_root):
    """Return the parsed registry dict (cached per project root)."""
    path = Path(project_root) / "assets" / "battle" / "skins" / "skin_registry.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def available_skins(project_root, scope=None):
    """Ordered list of skin ids.

    With no ``scope`` this keeps the legacy behaviour: ids from the old battle
    registry. With a scope it delegates to the generic multi-scope registry.
    """
    if scope is not None:
        return list(scope_data(project_root, scope).get("skins", {}))
    reg = load_registry(project_root)
    return list(reg.get("skins", {}).keys())


def skin_for_difficulty(project_root, difficulty):
    """Pick the skin id for a difficulty value.

    The registry's ``hell_skin`` is used for the hell difficulty; every other
    difficulty uses ``default_skin``. Display labels are localised elsewhere.
    """
    data = scope_data(project_root, "battle")
    if data:
        if difficulty == "地狱" and "hell" in scope_skins(project_root, "battle"):
            return "hell"
        return default_skin(project_root, "battle")
    reg = load_registry(project_root)
    default = reg.get("default_skin", "default")
    hell = reg.get("hell_skin", "hell")
    if difficulty == "地狱" and hell in reg.get("skins", {}):
        return hell
    return default if default in reg.get("skins", {}) else "default"


def portrait_path(project_root, skin, state):
    """Resolve a state to an existing PNG path, or None.

    Resolution order:
      1. requested skin's file from the registry
      2. same state in the default skin (partial skin packs are tolerated)
      3. legacy flat assets (pre-skin-pack layout) for backwards compatibility
    """
    root = Path(project_root)
    if scope_data(root, "battle"):
        found = asset_path(root, "battle", skin, state)
        if found is not None:
            return found
    battle = root / "assets" / "battle"
    reg = load_registry(root)
    skins = reg.get("skins", {})
    default = reg.get("default_skin", "default")

    def from_skin(skin_id):
        entry = skins.get(skin_id, {})
        rel = entry.get("files", {}).get(state)
        if not rel:
            return None
        candidate = battle / "skins" / rel
        return candidate if candidate.exists() else None

    for sid in (skin, default):
        found = from_skin(sid)
        if found is not None:
            return found

    # Legacy fallbacks so older installs / partial packs never blank the art.
    if state in {"attack", "attacked", "die"}:
        legacy = battle / f"ai_assistant_{state}.png"
        if legacy.exists():
            return legacy
    if state in {"thinking", "correct", "wrong"}:
        legacy = battle / "expressions.png"
        if legacy.exists():
            return legacy
    return None


def is_sheet(project_root, skin, state):
    """All skin-pack portraits are standalone PNGs (never sprite sheets)."""
    return False


# ---------------------------------------------------------------------------
# Generic multi-scope skin registry (home / login / battle).
# ---------------------------------------------------------------------------
@lru_cache(maxsize=8)
def load_skin_registry(project_root):
    """Parse ``assets/skins/skin_registry.json`` (cached per project root)."""
    path = Path(project_root) / "assets" / SKINS_DIR / REGISTRY_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def scopes():
    """The user-switchable skin scopes, in display order."""
    return SCOPES


def scope_data(project_root, scope):
    """Return the registry section for a scope, or an empty dict."""
    section = load_skin_registry(project_root).get("scopes", {})
    return section.get(scope, {}) if isinstance(section, dict) else {}


def scope_skins(project_root, scope):
    """Ordered list of skin ids for a scope (explicit generic-API name)."""
    return available_skins(project_root, scope)


def default_skin(project_root, scope):
    """Default skin id for a scope."""
    data = scope_data(project_root, scope)
    default = data.get("default", "default")
    skins = data.get("skins", {})
    return default if default in skins else (next(iter(skins), "default"))


def skin_display(project_root, scope, skin, language="zh"):
    """Localised display label for a skin, falling back to its id."""
    entry = scope_data(project_root, scope).get("skins", {}).get(skin, {})
    labels = entry.get("display", {}) if isinstance(entry, dict) else {}
    return labels.get(language) or labels.get("zh") or labels.get("en") or skin


def _skins_root(project_root):
    return Path(project_root) / "assets" / SKINS_DIR


def asset_path(project_root, scope, skin, role):
    """Resolve ``(scope, skin, role)`` to an existing image path, or None.

    Resolution: the requested skin's file for the role, then the scope default
    skin's file (partial packs are tolerated), then None.
    """
    data = scope_data(project_root, scope)
    skins = data.get("skins", {})
    root = _skins_root(project_root)

    def from_skin(skin_id):
        entry = skins.get(skin_id, {})
        rel = entry.get("files", {}).get(role) if isinstance(entry, dict) else None
        if not rel:
            return None
        candidate = (root / rel).resolve()
        return candidate if candidate.exists() else None

    found = from_skin(skin)
    if found is None:
        found = from_skin(default_skin(project_root, scope))
    return found


def resolve_battle_skin(project_root, difficulty, selected):
    """Resolve the effective battle skin from a user selection.

    ``selected == AUTO_SKIN`` (the default) keeps the historical behaviour of
    picking the skin by difficulty (hell difficulty -> hell pack). Any other
    valid skin id overrides the difficulty. Unknown ids fall back to the
    difficulty rule so a stale preference can never blank the portrait.
    """
    valid = (
        scope_skins(project_root, "battle")
        if scope_data(project_root, "battle") else available_skins(project_root)
    )
    if selected and selected != AUTO_SKIN and selected in valid:
        return selected
    return skin_for_difficulty(project_root, difficulty)


class SkinPreferences:
    """Persist each scope's selected skin in ``data/skins.json``.

    ``home`` and ``login`` store a single skin id. ``battle`` stores a mapping
    of difficulty -> skin id so every opponent level can be skinned
    independently (each value may be the pseudo-skin ``auto``). The legacy
    plain-string ``battle`` value is still read as "apply to every difficulty".
    A missing/corrupt file falls back to defaults without overwriting the bad
    file, matching the project's other preference stores.
    """

    def __init__(self, data_dir):
        self.store = JsonStore(Path(data_dir) / PREFERENCES_FILE, {})

    def load(self):
        try:
            raw = self.store.read()
        except Exception:
            return {}
        return raw if isinstance(raw, dict) else {}

    def _valid(self, project_root, scope):
        valid = list(scope_skins(project_root, scope))
        if scope == "battle":
            valid = [AUTO_SKIN] + valid
        return valid

    def selected(self, project_root, scope, difficulty=None):
        """Return the selected skin id for a scope (validated).

        For ``battle`` pass ``difficulty`` to get that level's skin. Without it,
        the whole per-difficulty mapping is returned for the settings UI. Every
        difficulty defaults to ``auto`` (follow difficulty) so the historical
        "hell -> hell pack" behaviour holds until the user picks a skin.
        """
        valid = self._valid(project_root, scope)
        raw = self.load().get(scope)
        if scope != "battle":
            return raw if raw in valid else default_skin(project_root, scope)

        if isinstance(raw, dict):
            if difficulty is not None:
                value = raw.get(difficulty)
                return value if value in valid else AUTO_SKIN
            # Whole mapping, normalised so missing/invalid keys read as auto.
            return {
                d: (raw[d] if raw.get(d) in valid else AUTO_SKIN)
                for d in BATTLE_DIFFICULTIES
            }
        if difficulty is not None:
            # Legacy plain string applies to every difficulty.
            return raw if raw in valid else AUTO_SKIN
        # No value (or a non-dict) -> every difficulty follows the rule.
        value = raw if raw in valid else AUTO_SKIN
        return {d: value for d in BATTLE_DIFFICULTIES}

    def select(self, scope, skin, difficulty=None):
        """Persist a selection. Battle without ``difficulty`` sets one level
        from the mapping; pass ``difficulty`` to target a specific level."""
        data = self.load()
        if scope != "battle":
            data[scope] = skin
        else:
            current = data.get(scope)
            mapping = dict(current) if isinstance(current, dict) else {}
            if difficulty is None:
                # Backward-compatible single-value set (used by old callers).
                data[scope] = skin
            else:
                mapping[difficulty] = skin
                data[scope] = mapping
        self.store.write(data)

    def reset(self, project_root, scope):
        """Restore a scope to its default skin."""
        if scope == "battle":
            data = self.load()
            data[scope] = AUTO_SKIN
            self.store.write(data)
        else:
            self.select(scope, default_skin(project_root, scope))
