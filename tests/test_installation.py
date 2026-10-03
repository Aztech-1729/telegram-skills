"""Installed skills retain resources and routes inside their project."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_installation import verify_install


class InstalledFilesTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.source = self.root / "source"
        self.project = self.root / "project"
        self.target = self.project / ".agents/skills"
        self.contents = {
            "telegram-bot-alpha/SKILL.md": "# Alpha\n[Guide](references/guide.md)\n[Beta](../telegram-bot-beta/SKILL.md)\n",
            "telegram-bot-alpha/references/guide.md": "# Guide\n[Starter](../assets/starter.py)\n",
            "telegram-bot-alpha/assets/starter.py": "print('Example')\n",
            "telegram-bot-beta/SKILL.md": "# Beta\n",
        }
        self.files = {}
        for name, content in self.contents.items():
            for folder in (self.source, self.target):
                path = folder / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            self.files[name] = self.source / name

    def test_complete_resources_and_sibling_routes_pass(self):
        verify_install(self.files, self.target, self.project)

    def test_git_text_line_ending_normalization_is_accepted(self):
        name = "telegram-bot-alpha/SKILL.md"
        self.files[name].write_bytes(self.contents[name].replace("\n", "\r\n").encode())
        (self.target / name).write_bytes(self.contents[name].encode())
        verify_install(self.files, self.target, self.project)

    def test_missing_resource_is_rejected(self):
        (self.target / "telegram-bot-alpha/assets/starter.py").unlink()
        with self.assertRaisesRegex(ValueError, "Missing installed resource"):
            verify_install(self.files, self.target, self.project)

    def test_modified_resource_is_rejected(self):
        (self.target / "telegram-bot-alpha/assets/starter.py").write_text("Changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Installed resource differs"):
            verify_install(self.files, self.target, self.project)

    def test_shared_repo_doc_is_unavailable_after_skill_only_install(self):
        name = "telegram-bot-alpha/references/guide.md"
        content = "[Validation](../../docs/VALIDATION.md)"
        self.files[name].write_text(content, encoding="utf-8")
        (self.target / name).write_text(content, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unavailable installed local route"):
            verify_install(self.files, self.target, self.project)

    def test_existing_route_outside_project_is_rejected(self):
        outside = self.root / "outside.md"
        outside.write_text("Outside", encoding="utf-8")
        name = "telegram-bot-alpha/SKILL.md"
        content = "[Outside](../../../../outside.md)"
        self.files[name].write_text(content, encoding="utf-8")
        (self.target / name).write_text(content, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unavailable installed local route"):
            verify_install(self.files, self.target, self.project)

    def test_claude_links_into_project_canonical_tree_are_valid(self):
        linked = self.project / ".claude/skills"
        linked.mkdir(parents=True)
        try:
            for name in ("telegram-bot-alpha", "telegram-bot-beta"):
                (linked / name).symlink_to(self.target / name, target_is_directory=True)
        except OSError:
            self.skipTest("Creating directory symlinks is unavailable on this host")
        verify_install(self.files, linked, self.project)

    def test_symlink_resource_outside_project_is_rejected_before_reading(self):
        outside = self.root / "outside.py"
        outside.write_text("Outside", encoding="utf-8")
        installed = self.target / "telegram-bot-alpha/assets/starter.py"
        installed.unlink()
        try:
            installed.symlink_to(outside)
        except OSError:
            self.skipTest("Creating symlinks is unavailable on this host")
        with self.assertRaisesRegex(ValueError, "Installed resource escapes the test project"):
            verify_install(self.files, self.target, self.project)


if __name__ == "__main__":
    unittest.main()
