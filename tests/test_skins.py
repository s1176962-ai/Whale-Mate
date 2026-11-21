"""Tests for the multi-scope (home/login/battle) skin system."""

import json
import tempfile
import unittest
from pathlib import Path

from learning_platform import skins

ROOT = Path(__file__).resolve().parent.parent


class SkinRegistryTests(unittest.TestCase):
    def test_all_scopes_declared_with_defaults(self):
        self.assertEqual(set(skins.scopes()), {"home", "login", "battle"})
        for scope in skins.scopes():
            skins_data = skins.scope_skins(ROOT, scope)
            self.assertTrue(skins_data, f"{scope} has no skins")
            self.assertIn(skins.default_skin(ROOT, scope), skins_data)

    def test_every_role_resolves_for_every_skin(self):
        """No skin may leave a role blank; defaults cover partial packs."""
        for scope in skins.scopes():
            roles = skins.scope_data(ROOT, scope).get("roles", [])
            self.assertTrue(roles, f"{scope} declares no roles")
            for skin in skins.scope_skins(ROOT, scope):
                for role in roles:
                    path = skins.asset_path(ROOT, scope, skin, role)
                    self.assertIsNotNone(path, f"{scope}/{skin}/{role}")
                    self.assertTrue(path.exists(), f"{scope}/{skin}/{role}: {path}")

    def test_unknown_skin_falls_back_to_default(self):
        for scope in skins.scopes():
            for role in skins.scope_data(ROOT, scope).get("roles", []):
                chosen = skins.asset_path(ROOT, scope, "does-not-exist", role)
                fallback = skins.asset_path(
                    ROOT, scope, skins.default_skin(ROOT, scope), role
                )
                self.assertEqual(chosen, fallback)

    def test_display_labels_are_localised(self):
        self.assertEqual(skins.skin_display(ROOT, "battle", "hell", "zh"), "地狱")
        self.assertEqual(skins.skin_display(ROOT, "battle", "hell", "en"), "Hell")
        self.assertEqual(skins.skin_display(ROOT, "home", "ghost", "en"), "ghost")

    def test_legacy_battle_api_unchanged(self):
        self.assertEqual(skins.skin_for_difficulty(ROOT, "地狱"), "hell")
        self.assertEqual(skins.skin_for_difficulty(ROOT, "普通级"), "default")
        self.assertEqual(set(skins.available_skins(ROOT)), {"default", "hell"})


class SkinPreferenceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.prefs = skins.SkinPreferences(Path(temp.name))

    def test_battle_difficulties_match_profiles(self):
        from learning_platform.battle import PROFILES

        self.assertEqual(set(skins.BATTLE_DIFFICULTIES), set(PROFILES))

    def test_battle_defaults_to_auto_for_every_difficulty(self):
        for difficulty in skins.BATTLE_DIFFICULTIES:
            self.assertEqual(
                self.prefs.selected(ROOT, "battle", difficulty), skins.AUTO_SKIN
            )
        mapping = self.prefs.selected(ROOT, "battle")
        self.assertEqual(set(mapping), set(skins.BATTLE_DIFFICULTIES))
        self.assertTrue(all(v == skins.AUTO_SKIN for v in mapping.values()))

    def test_home_login_default_to_registry_default(self):
        self.assertEqual(self.prefs.selected(ROOT, "home"), "default")
        self.assertEqual(self.prefs.selected(ROOT, "login"), "default")

    def test_per_difficulty_selection_persists_independently(self):
        self.prefs.select("home", "default")
        self.prefs.select("battle", "hell", difficulty="地狱")
        self.prefs.select("battle", "default", difficulty="普通级")
        again = skins.SkinPreferences(Path(self.prefs.store.path.parent))
        self.assertEqual(again.selected(ROOT, "home"), "default")
        self.assertEqual(again.selected(ROOT, "battle", "地狱"), "hell")
        self.assertEqual(again.selected(ROOT, "battle", "普通级"), "default")
        self.assertEqual(again.selected(ROOT, "battle", "困难"), skins.AUTO_SKIN)

    def test_legacy_plain_battle_string_applies_to_all(self):
        self.prefs.select("battle", "hell")  # no difficulty -> legacy form
        for difficulty in skins.BATTLE_DIFFICULTIES:
            self.assertEqual(self.prefs.selected(ROOT, "battle", difficulty), "hell")

    def test_invalid_stored_value_falls_back(self):
        self.prefs.select("battle", "not-a-skin", difficulty="地狱")
        self.assertEqual(self.prefs.selected(ROOT, "battle", "地狱"), skins.AUTO_SKIN)

    def test_corrupt_file_does_not_raise(self):
        self.prefs.store.path.write_text("{bad json", encoding="utf-8")
        self.assertEqual(self.prefs.selected(ROOT, "home"), "default")


class BattleSkinResolutionTests(unittest.TestCase):
    def test_custom_battle_pack_uses_generic_registry_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "assets" / "skins"
            folder.mkdir(parents=True)
            custom = folder / "custom.png"
            default = folder / "default.png"
            custom.touch()
            default.touch()
            registry = {"scopes": {"battle": {
                "default": "default",
                "skins": {
                    "default": {"files": {"normal": "default.png", "wrong": "default.png"}},
                    "custom": {"files": {"normal": "custom.png"}},
                },
            }}}
            (folder / "skin_registry.json").write_text(json.dumps(registry), encoding="utf-8")
            prefs = skins.SkinPreferences(root / "data")
            prefs.select("battle", "custom", difficulty="普通级")
            chosen = prefs.selected(root, "battle", "普通级")
            effective = skins.resolve_battle_skin(root, "普通级", chosen)
            self.assertEqual(effective, "custom")
            # Windows CI may expose TEMP using an 8.3 alias (RUNNER~1),
            # while asset_path() resolves it to the long directory name.
            # Verify file identity for both the custom image and fallback.
            for state, expected in (("normal", custom), ("wrong", default)):
                with self.subTest(state=state):
                    actual = skins.portrait_path(root, effective, state)
                    self.assertTrue(actual is not None and actual.samefile(expected))
            self.assertEqual(skins.resolve_battle_skin(root, "地狱", "unknown"), "default")

    def test_legacy_registry_remains_usable_without_generic_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "assets" / "battle" / "skins"
            folder.mkdir(parents=True)
            portrait = folder / "normal.png"
            portrait.touch()
            (folder / "skin_registry.json").write_text(json.dumps({
                "default_skin": "legacy",
                "skins": {"legacy": {"files": {"normal": "normal.png"}}},
            }), encoding="utf-8")
            self.assertEqual(skins.resolve_battle_skin(root, "普通级", "legacy"), "legacy")
            self.assertEqual(skins.portrait_path(root, "legacy", "normal"), portrait)

    def test_auto_follows_difficulty(self):
        self.assertEqual(
            skins.resolve_battle_skin(ROOT, "地狱", skins.AUTO_SKIN), "hell"
        )
        self.assertEqual(
            skins.resolve_battle_skin(ROOT, "普通级", skins.AUTO_SKIN), "default"
        )

    def test_manual_choice_overrides_difficulty(self):
        self.assertEqual(skins.resolve_battle_skin(ROOT, "普通级", "hell"), "hell")
        self.assertEqual(skins.resolve_battle_skin(ROOT, "地狱", "default"), "default")

    def test_stale_choice_falls_back_to_difficulty(self):
        self.assertEqual(
            skins.resolve_battle_skin(ROOT, "地狱", "unknown"), "hell"
        )


if __name__ == "__main__":
    unittest.main()
