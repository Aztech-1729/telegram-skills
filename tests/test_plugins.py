"""Native manifests cannot lose skills, escape paths or change package identity."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_plugins as plugins


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.manifests = {name: json.loads((plugins.ROOT / name).read_text(encoding="utf-8")) for name in (
            *plugins.MANIFESTS, ".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json")}
        # Keep fixture versions stable when the published pack advances.
        for name in plugins.MANIFESTS:
            self.manifests[name]["version"] = "1.0.0"
        for name in self.manifests[plugins.MANIFESTS[0]]["skills"]:
            folder = self.root / name[2:]
            folder.mkdir()
            (folder / "SKILL.md").write_text("# Test skill\n", encoding="utf-8")
        (self.root / "assets").mkdir()
        (self.root / "assets/plugin-icon.svg").write_text(
            (plugins.ROOT / "assets/plugin-icon.svg").read_text(encoding="utf-8"), encoding="utf-8")
        self.write()

    def write(self):
        for name, manifest in self.manifests.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(manifest), encoding="utf-8")

    def rejected(self):
        self.write()
        with self.assertRaises(ValueError):
            plugins.validate(self.root)

    def test_all_skills_share_one_canonical_package_identity(self):
        result = plugins.validate(self.root)
        self.assertEqual(result, {"plugin": "telegram@aztech", "version": "1.0.0", "skills": len(self.manifests[plugins.MANIFESTS[0]]["skills"])})

    def test_missing_duplicate_reordered_or_untracked_skill_is_rejected(self):
        original = self.manifests[plugins.MANIFESTS[0]]["skills"]
        for paths in (original[:-1], original + [original[0]], list(reversed(original)), original + ["./outside"]):
            for name in plugins.MANIFESTS:
                self.manifests[name]["skills"] = paths
            self.rejected()

    def test_manifest_drift_is_rejected(self):
        for field, value in (("name", "other"), ("version", "2.0.0"), ("repository", "https://example.invalid")):
            original = deepcopy(self.manifests)
            self.manifests[plugins.MANIFESTS[1]][field] = value
            self.rejected()
            self.manifests = original

    def test_paths_cannot_escape_or_use_unprefixed_or_windows_paths(self):
        for name in ("../README.md", "./../README.md", "telegram-bot-test", "./telegram-bot-test\\file", "/absolute"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                plugins.contained_path(self.root, name)

    def test_symlink_components_are_refused(self):
        with patch.object(Path, "is_symlink", return_value=True), self.assertRaises(ValueError):
            plugins.validate(self.root)

    def test_portable_root_manifest_cannot_silently_hide_canonical_skills(self):
        (self.root / "plugin.json").write_text('{}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "override"):
            plugins.validate(self.root)

    def test_marketplace_source_must_include_sibling_references(self):
        for name, source in ((".agents/plugins/marketplace.json", {"source": "local", "path": "./telegram-bot-aiogram"}),
                             (".claude-plugin/marketplace.json", "./telegram-bot-aiogram")):
            original = deepcopy(self.manifests)
            self.manifests[name]["plugins"][0]["source"] = source
            self.rejected()
            self.manifests = original

    def test_no_automatic_hooks_service_wiring_or_marketplace_component_override(self):
        self.manifests[plugins.MANIFESTS[0]]["hooks"] = "./hooks.json"
        self.manifests[plugins.MANIFESTS[1]]["hooks"] = "./hooks.json"
        self.rejected()
        del self.manifests[plugins.MANIFESTS[0]]["hooks"]
        del self.manifests[plugins.MANIFESTS[1]]["hooks"]
        self.manifests[".claude-plugin/marketplace.json"]["plugins"][0]["skills"] = ["./alternate"]
        self.rejected()

    def test_invalid_or_missing_listing_icon_is_refused(self):
        icon = self.root / "assets/plugin-icon.svg"
        icon.write_text('<svg viewBox="0 0 20 40"/>', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "square"):
            plugins.validate(self.root)
        icon.unlink()
        with self.assertRaises(ValueError):
            plugins.validate(self.root)

    def test_duplicate_json_keys_are_refused(self):
        path = self.root / plugins.MANIFESTS[0]
        path.write_text('{"name":"telegram","name":"other"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            plugins.validate(self.root)


if __name__ == "__main__":
    unittest.main()
