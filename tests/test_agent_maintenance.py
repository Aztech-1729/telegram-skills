"""Offline regressions for source review and protected exact-commit AI merges."""
import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import agent_maintenance as agent

HEAD, BASE = "a" * 40, "b" * 40
HASH = "c" * 64
NOW = datetime(2026, 10, 3, 16, tzinfo=timezone.utc)
STAMP = NOW.isoformat().replace("+00:00", "Z")
URL = "https://core.telegram.org/bots/api"
OTHER = "https://core.telegram.org/bots/features"


def pr(number=8):
    return {"number": number, "state": "open", "draft": False, "auto_merge": None,
            "user": {"login": "Aztech-1729"}, "body": agent.MARKER,
            "head": {"sha": HEAD, "ref": agent.AGENT_BRANCH + "test", "repo": {"full_name": agent.REPO}},
            "base": {"sha": BASE, "ref": "main", "repo": {"full_name": agent.REPO}},
            "mergeable": True, "mergeable_state": "clean", "html_url": "https://github.com/" + agent.REPO + "/pull/8"}


class PluginFixture:
    """Git's actual blob shape, with immutable byte-derived identifiers."""
    def __init__(self):
        resource = "telegram-bot-alpha/references/guide.md"
        self.files = [{"filename": resource, "status": "modified", "sha": HEAD}]
        self.base_tree = {"truncated": False, "tree": [
            {"path": resource, "type": "blob", "mode": "100644", "sha": BASE}]}
        self.head_tree = {"truncated": False, "tree": [
            {"path": resource, "type": "blob", "mode": "100644", "sha": HEAD}]}
        self.blobs = {}
        self.documents = {
            name: {"name": "telegram", "version": "1.0.0", "skills": ["./telegram-bot-alpha"],
                   "author": {"name": "Aztech"}, "interface": {"displayName": "Telegram Skills"}}
            for name in agent.PLUGIN_MANIFESTS}
        for name, document in self.documents.items():
            self.store(name, document, base=True)
            self.store(name, {**document, "version": "1.0.1"})

    def store(self, name, document=None, *, base=False, raw=None):
        raw = raw if raw is not None else json.dumps(document).encode()
        sha = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
        self.blobs[sha] = {"sha": sha, "encoding": "base64", "size": len(raw),
                           "content": base64.encodebytes(raw).decode("ascii")}
        tree = self.base_tree if base else self.head_tree
        tree["tree"] = [entry for entry in tree["tree"] if entry["path"] != name]
        tree["tree"].append({"path": name, "type": "blob", "mode": "100644", "sha": sha})
        if not base:
            self.files = [entry for entry in self.files if entry["filename"] != name]
            self.files.append({"filename": name, "status": "modified", "sha": sha})
        return sha

    def respond(self, path, **kwargs):
        if path == agent.PREFIX + f"/git/trees/{BASE}?recursive=1":
            return self.base_tree
        if path.startswith(agent.PREFIX + "/git/blobs/"):
            return self.blobs[path.rsplit("/", 1)[1]]
        raise AssertionError("Unexpected Git blob request: " + path)


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.api = self.enterContext(patch.object(agent, "api", side_effect=AssertionError("Unexpected GitHub call")))
        self.command = self.enterContext(patch.object(agent.subprocess, "run"))
        self.directory = self.enterContext(TemporaryDirectory())
        self.root = Path(self.directory)
        (self.root / "telegram-bot-alpha").mkdir()
        (self.root / "telegram-bot-alpha/SKILL.md").write_text("Alpha", encoding="utf-8")


class MergeTests(OfflineTests):
    def setUp(self):
        super().setUp()
        self.pull = pr()
        self.files = [{"filename": "README.md", "status": "modified", "sha": HEAD}]
        self.protection = {"enforce_admins": {"enabled": True}, "required_status_checks": {
            "strict": True, "checks": [{"context": "validation", "app_id": agent.ACTION_APP}]}}
        self.tree = {"truncated": False, "tree": [{"path": self.files[0]["filename"], "type": "blob", "mode": "100644"}]}
        self.run = {"id": 55, "event": "pull_request", "path": ".github/workflows/validate.yml",
                    "head_sha": HEAD, "head_branch": self.pull["head"]["ref"],
                    "head_repository": {"full_name": agent.REPO}, "pull_requests": [{"number": 8}],
                    "status": "completed", "conclusion": "success"}
        self.check = {"name": "validation", "app": {"id": agent.ACTION_APP}, "head_sha": HEAD,
                      "status": "completed", "conclusion": "success",
                      "details_url": f"https://github.com/{agent.REPO}/actions/runs/55/job/100"}
        self.review = {"schema_version": 1, "repository": agent.REPO, "pull_request": 8,
                       "head_sha": HEAD, "base_sha": BASE, "files_sha256": agent.files_digest(self.files),
                       "reviewer": "independent-reviewer", "reviewed_at": STAMP, "approved": True, "findings": []}
        self.command.return_value.returncode = 0
        self.plugin_fixture = None
        self.api.side_effect = self.respond

    def respond(self, path, method="GET", data=None, missing=False):
        self.assertEqual(method, "GET")
        if path == agent.PREFIX + "/pulls/8":
            result = deepcopy(self.pull)
            if self.command.called:
                result.update({"merged": True, "merge_commit_sha": "d" * 40})
            return result
        if path == agent.PREFIX + "/git/ref/heads/main":
            return {"object": {"sha": BASE}}
        if path == agent.PREFIX + "/branches/main/protection":
            return self.protection
        if path.startswith(agent.PREFIX + "/pulls/8/files?"):
            return self.files
        if path == agent.PREFIX + f"/git/trees/{HEAD}?recursive=1":
            return self.tree
        if self.plugin_fixture and ("/git/blobs/" in path or f"/git/trees/{BASE}?" in path):
            return self.plugin_fixture.respond(path)
        if path.startswith(agent.PREFIX + "/actions/workflows/validate.yml/runs?"):
            return {"workflow_runs": [self.run]}
        if path.startswith(agent.PREFIX + f"/commits/{HEAD}/check-runs?"):
            return {"check_runs": [self.check]}
        raise AssertionError("Unexpected GitHub request: " + path)

    def attempt(self):
        return agent.merge(8, HEAD, BASE, self.review, self.root, NOW)

    def refused(self):
        with self.assertRaises((ValueError, TypeError)):
            self.attempt()
        self.command.assert_not_called()

    def test_success_merges_immediately_and_binds_head(self):
        result = self.attempt()
        self.assertTrue(result["merged"])
        command = self.command.call_args.args[0]
        self.assertEqual(command[-2:], ["--match-head-commit", HEAD])
        self.assertNotIn("--auto", command)
        self.assertNotIn("--admin", command)

    def test_missing_or_weakened_protection_refused(self):
        for protection in ({}, {"enforce_admins": {"enabled": False}, "required_status_checks": self.protection["required_status_checks"]},
                           {"enforce_admins": {"enabled": True}, "required_status_checks": {"strict": False}},
                           {"enforce_admins": {"enabled": True}, "required_status_checks": {"strict": True, "checks": [{"context": "validation", "app_id": 1}]}}):
            self.protection = protection
            self.refused()

    def test_changed_head_base_or_repository_refused(self):
        original = deepcopy(self.pull)
        for keys, value in ((["head", "sha"], "f" * 40), (["base", "sha"], "e" * 40),
                            (["head", "repo", "full_name"], "other/repo"), (["base", "ref"], "other")):
            self.pull = deepcopy(original)
            item = self.pull
            for key in keys[:-1]:
                item = item[key]
            item[keys[-1]] = value
            self.refused()

    def test_changed_main_ref_refused(self):
        original = self.respond
        self.api.side_effect = lambda path, **kw: {"object": {"sha": "f" * 40}} if path.endswith("/git/ref/heads/main") else original(path, **kw)
        self.refused()

    def test_draft_wrong_author_missing_marker_or_reserved_branch_refused(self):
        original = deepcopy(self.pull)
        for mutation in (lambda p: p.update(draft=True), lambda p: p["user"].update(login="stranger"),
                         lambda p: p.update(body=""), lambda p: p["head"].update(ref="human-work")):
            self.pull = deepcopy(original)
            mutation(self.pull)
            self.refused()

    def test_retained_auto_merge_refused(self):
        self.pull["auto_merge"] = {"enabled_by": {"login": "Aztech-1729"}}
        self.refused()

    def test_foundation_deletion_or_rename_refused(self):
        for filename, status in ((".github/workflows/validate.yml", "modified"),
                                 ("scripts/agent_maintenance.py", "modified"),
                                 ("automation/sources.json", "modified"),
                                 ("docs/AGENT_MAINTENANCE.md", "modified"),
                                 (".agents/plugins/marketplace.json", "modified"),
                                 (".claude-plugin/marketplace.json", "modified"),
                                 ("assets/plugin-icon.svg", "modified"),
                                 ("telegram-bot-alpha/old.py", "removed"),
                                 ("telegram-bot-alpha/new.py", "renamed")):
            self.files = [{"filename": filename, "status": status, "sha": HEAD}]
            self.refused()

    def test_non_regular_or_incomplete_tree_refused(self):
        for mode in ("120000", "160000", "100755"):
            self.tree["tree"][0]["mode"] = mode
            self.refused()
        self.tree["tree"][0]["mode"] = "100644"
        self.tree["truncated"] = True
        self.refused()

    def test_rejected_stale_or_forged_review_refused(self):
        original = deepcopy(self.review)
        for key, value in (("approved", False), ("findings", ["Fix required"]), ("reviewer", ""),
                           ("head_sha", "f" * 40), ("base_sha", "e" * 40), ("files_sha256", "d" * 64),
                           ("reviewed_at", (NOW - timedelta(hours=49)).isoformat()),
                           ("reviewed_at", (NOW + timedelta(minutes=6)).isoformat())):
            self.review = {**original, key: value}
            self.refused()

    def test_changed_file_list_invalidates_review(self):
        self.files[0]["sha"] = "d" * 40
        self.refused()

    def test_wrong_or_failed_native_run_refused(self):
        original = deepcopy(self.run)
        for key, value in (("event", "workflow_dispatch"), ("conclusion", "failure"), ("status", "in_progress"),
                           ("head_sha", "f" * 40), ("head_branch", "other"), ("head_repository", {"full_name": "other/repo"}),
                           ("pull_requests", []), ("path", ".github/workflows/other.yml")):
            self.run = {**original, key: value}
            self.refused()

    def test_newer_run_prevents_reusing_old_pass(self):
        original = self.respond
        self.api.side_effect = lambda path, **kw: {"workflow_runs": [self.run, {**self.run, "id": 56, "status": "in_progress", "conclusion": None}]} if "/actions/workflows/validate.yml/runs?" in path else original(path, **kw)
        self.refused()

    def test_wrong_missing_or_failed_check_refused(self):
        original = deepcopy(self.check)
        for key, value in (("app", {"id": 1}), ("head_sha", "f" * 40), ("conclusion", "failure"),
                           ("details_url", f"https://github.com/{agent.REPO}/actions/runs/99/job/100")):
            self.check = {**original, key: value}
            self.refused()

    def test_base_changes_before_merge_refused(self):
        original = self.respond
        reads = 0
        def respond(path, **kw):
            nonlocal reads
            if path.endswith("/git/ref/heads/main"):
                reads += 1
                if reads == 2:
                    return {"object": {"sha": "f" * 40}}
            return original(path, **kw)
        self.api.side_effect = respond
        self.refused()

    def test_behind_or_conflicted_pr_refused(self):
        for state in ("behind", "dirty", "blocked", "unknown"):
            self.pull["mergeable_state"] = state
            self.refused()

    def test_merge_failure_never_retries_with_bypass(self):
        self.command.return_value.returncode = 1
        with self.assertRaises(RuntimeError):
            self.attempt()
        self.assertEqual(self.command.call_count, 1)

    def test_template_is_not_an_approval(self):
        result = agent.review_template(8, HEAD, BASE)
        self.assertFalse(result["approved"])
        self.assertEqual(result["files_sha256"], agent.files_digest(self.files))
        self.command.assert_not_called()

    def release_fixture(self):
        self.plugin_fixture = PluginFixture()
        self.files = self.plugin_fixture.files
        self.tree = self.plugin_fixture.head_tree
        self.review["files_sha256"] = agent.files_digest(self.files)

    def test_paired_plugin_patch_release_uses_normal_exact_merge(self):
        self.release_fixture()
        self.assertTrue(self.attempt()["merged"])
        self.assertEqual(self.command.call_args.args[0][-2:], ["--match-head-commit", HEAD])

    def test_actual_skill_change_without_plugin_release_refused(self):
        self.release_fixture()
        self.files = self.files[:1]
        self.review["files_sha256"] = agent.files_digest(self.files)
        self.refused()

    def test_plugin_release_still_requires_same_review_and_native_ci(self):
        self.release_fixture()
        self.review["files_sha256"] = "d" * 64
        self.refused()
        self.review["files_sha256"] = agent.files_digest(self.files)
        self.run["conclusion"] = "failure"
        self.refused()

    def test_root_npm_manifests_retain_independent_review_and_native_ci(self):
        for name in ("package.json", "package-lock.json"):
            self.files = [{"filename": name, "status": "modified", "sha": HEAD}]
            self.tree = {"truncated": False, "tree": [{"path": name, "type": "blob", "mode": "100644"}]}
            self.review["files_sha256"] = "d" * 64
            self.refused()
            self.review["files_sha256"] = agent.files_digest(self.files)
            self.run["conclusion"] = "failure"
            self.refused()
            self.run["conclusion"] = "success"
            self.assertTrue(self.attempt()["merged"])
            self.command.reset_mock()

    def test_path_policy_blocks_escape_and_foundation(self):
        for name in ("../README.md", "/README.md", "telegram-bot-alpha/../x.py", "telegram-bot-alpha\\x.py",
                     "telegram-bot-alpha/.github/x.yml", "telegram-bot-alpha/.env", "new-skill/SKILL.md",
                     "tests/test_agent_maintenance.py", "tests/test_dependency_automerge.py", "tests/test_online.py", "docs/AUTOMATION.md",
                     ".codex-plugin/plugin.json", ".claude-plugin/plugin.json", ".agents/plugins/marketplace.json",
                     ".claude-plugin/marketplace.json"):
            self.assertFalse(agent.allowed_file(name, {"telegram-bot-alpha"}), name)
        for name in ("README.md", "requirements-dev.txt", "package.json", "package-lock.json",
                     "telegram-bot-alpha/.env.example", "telegram-bot-alpha/assets/bot.py"):
            self.assertTrue(agent.allowed_file(name, {"telegram-bot-alpha"}), name)


class PluginReleaseTests(OfflineTests):
    def setUp(self):
        super().setUp()
        self.fixture = PluginFixture()
        self.api.side_effect = self.fixture.respond
        self.name = sorted(agent.PLUGIN_MANIFESTS)[0]

    def attempt(self):
        return agent.plugin_release(self.fixture.files, {"telegram-bot-alpha"}, BASE,
                                    self.fixture.head_tree)

    def refused(self):
        with self.assertRaises(ValueError):
            self.attempt()
        self.command.assert_not_called()

    def test_actual_decoded_blobs_allow_only_paired_patch(self):
        self.assertIsNone(self.attempt())
        paths = [call.args[0] for call in self.api.call_args_list]
        self.assertEqual(paths[0], agent.PREFIX + f"/git/trees/{BASE}?recursive=1")
        self.assertEqual(len([path for path in paths if "/git/blobs/" in path]), 4)
        self.assertTrue(all("/git/" in path for path in paths))
        self.command.assert_not_called()

    def test_actual_skill_update_requires_release_even_when_manifests_omitted(self):
        self.fixture.files = self.fixture.files[:1]
        self.refused()
        self.assertEqual(len(self.api.call_args_list), 1)

    def test_generated_status_without_content_change_needs_no_release(self):
        self.fixture.files = [{**self.fixture.files[0], "filename": "telegram-bot-alpha/references/upstream-status.md"}]
        self.attempt()
        self.api.assert_not_called()

    def test_mode_only_skill_change_needs_no_release(self):
        self.fixture.files = self.fixture.files[:1]
        self.fixture.base_tree["tree"][0]["sha"] = HEAD
        self.attempt()
        self.assertEqual(len(self.api.call_args_list), 1)

    def test_single_or_new_manifest_refused(self):
        original = deepcopy(self.fixture.files)
        self.fixture.files = [file for file in original if file["filename"] != self.name]
        self.refused()
        self.fixture.files = original
        self.fixture.files[-1]["status"] = "added"
        self.refused()

    def test_all_non_version_fields_are_immutable(self):
        document = deepcopy(self.fixture.documents[self.name])
        for change in ({"name": "another"}, {"skills": ["./other"]}, {"permissions": ["network"]},
                       {"author": {"name": "other"}}, {"interface": {"displayName": "Changed"}},
                       {"mcpServers": {"remote": {"url": "https://example.invalid"}}}):
            self.fixture.store(self.name, {**document, **change, "version": "1.0.1"})
            self.refused()

    def test_nested_json_type_changes_are_not_equal(self):
        document = deepcopy(self.fixture.documents[self.name])
        self.fixture.store(self.name, {**document, "enabled": True}, base=True)
        self.fixture.store(self.name, {**document, "enabled": 1, "version": "1.0.1"})
        self.refused()

    def test_version_must_increment_exactly_one_patch_and_match_both(self):
        for version in ("1.0.0", "0.9.9", "1.0.2", "1.1.0", "2.0.0", "1.0.1-beta", "01.0.1", 101, None):
            for name, document in self.fixture.documents.items():
                self.fixture.store(name, {**document, "version": version})
            self.refused()
        for name, document in self.fixture.documents.items():
            self.fixture.store(name, {**document, "version": "1.0.1"})
        self.fixture.store(self.name, {**self.fixture.documents[self.name], "version": "1.0.2"})
        self.refused()

    def test_unequal_or_invalid_base_versions_refused(self):
        document = self.fixture.documents[self.name]
        for version in ("1.0.1", "v1.0.0", None):
            self.fixture.store(self.name, {**document, "version": version}, base=True)
            self.refused()

    def test_canonical_json_allows_only_order_and_whitespace_variations(self):
        document = {**self.fixture.documents[self.name], "version": "1.0.1"}
        raw = json.dumps(dict(reversed(list(document.items()))), indent=4).encode() + b"\n"
        self.fixture.store(self.name, raw=raw)
        self.attempt()

    def test_malformed_duplicate_and_non_json_manifest_refused(self):
        for raw in (b"{broken", b"[]", b"null", b'\xff',
                    b'{"version":"1.0.1","version":"1.0.1"}',
                    b'{"version":"1.0.1","nested":{"key":1,"key":1}}',
                    b'{"version":"1.0.1","number":NaN}',
                    b'{"version":"1.0.1","number":Infinity}'):
            self.fixture.store(self.name, raw=raw)
            self.refused()

    def test_invalid_blob_encoding_digest_size_or_bytes_refused(self):
        sha = next(entry["sha"] for entry in self.fixture.head_tree["tree"] if entry["path"] == self.name)
        original = deepcopy(self.fixture.blobs[sha])
        for change in ({"encoding": "utf-8"}, {"sha": "f" * 40}, {"size": -1}, {"size": True},
                       {"size": original["size"] + 1}, {"size": agent.MAX_MANIFEST_BYTES + 1},
                       {"content": "%%%"}, {"content": base64.b64encode(b"{}").decode()},
                       {"content": "a" * (agent.MAX_MANIFEST_BYTES * 2 + 1)}):
            self.fixture.blobs[sha] = {**original, **change}
            self.refused()

    def test_file_digest_must_match_exact_head_blob(self):
        next(file for file in self.fixture.files if file["filename"] == self.name)["sha"] = "f" * 40
        self.refused()

    def test_skill_content_digest_drift_cannot_bypass_required_release(self):
        self.fixture.files = self.fixture.files[:1]
        for value in (None, "f" * 40):
            self.fixture.files[0]["sha"] = value
            self.refused()

    def test_base_or_head_missing_nonregular_or_truncated_tree_refused(self):
        for tree in (self.fixture.base_tree, self.fixture.head_tree):
            tree["truncated"] = True
            self.refused()
            tree["truncated"] = False
            entry = next(entry for entry in tree["tree"] if entry["path"] == self.name)
            for mode in ("120000", "100755", "160000"):
                entry["mode"] = mode
                self.refused()
            entry["mode"] = "100644"
            tree["tree"].remove(entry)
            self.refused()
            tree["tree"].append(entry)

    def test_release_requires_changed_skill_bytes_beyond_generated_status(self):
        resource = deepcopy(self.fixture.files[0])
        self.fixture.files = self.fixture.files[1:]
        self.refused()
        self.fixture.files.insert(0, {**resource, "filename": "package.json"})
        self.refused()
        self.fixture.files[0] = resource
        self.fixture.base_tree["tree"][0]["sha"] = HEAD
        self.refused()
        self.fixture.base_tree["tree"][0]["sha"] = BASE
        self.fixture.files[0]["filename"] = "telegram-bot-alpha/references/upstream-status.md"
        self.fixture.head_tree["tree"][0]["path"] = self.fixture.files[0]["filename"]
        self.refused()


class AcknowledgeTests(OfflineTests):
    def setUp(self):
        super().setUp()
        (self.root / "automation").mkdir()
        (self.root / "docs").mkdir()
        self.state_path = self.root / "automation/upstream-state.json"
        entry = {"sha256": HASH, "kind": "html", "skills": ["telegram-bot-alpha"], "last_checked_at": STAMP,
                 "first_observed_at": "2026-10-01T00:00:00Z", "last_changed_at": STAMP,
                 "pending_change_since": STAMP, "reviewed_sha256": "d" * 64}
        self.state = {"schema_version": 1, "last_run_at": STAMP, "sources": {URL: deepcopy(entry), OTHER: deepcopy(entry)}}
        self.state_path.write_text(json.dumps(self.state), encoding="utf-8")
        (self.root / "automation/sources.json").write_text('{"schema_version":1}', encoding="utf-8")
        self.enterContext(patch.object(agent.upstream, "load_sources", return_value=[{"url": URL}, {"url": OTHER}]))
        self.fetcher = self.enterContext(patch.object(agent.upstream, "fetch_source", autospec=True,
                                                     return_value={"ok": True, "sha256": HASH}))
        self.review = {"schema_version": 1, "reviewer": "codex", "sources": [
            {"url": URL, "sha256": HASH, "decision": "cosmetic", "notes": "Inspected official diff; no API behavior change."}]}

    def attempt(self):
        return agent.acknowledge(self.review, self.root, current_time=NOW)

    def test_refetch_acknowledges_only_selected_source_preserves_fetch_date(self):
        result = self.attempt()
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(result["acknowledged"], 1)
        self.assertNotIn("pending_change_since", state["sources"][URL])
        self.assertEqual(state["sources"][OTHER], self.state["sources"][OTHER])
        self.assertEqual(state["sources"][URL]["reviewed_sha256"], HASH)
        self.assertEqual(state["last_run_at"], STAMP)
        self.assertEqual(state["sources"][URL]["last_checked_at"], STAMP)
        self.assertIn("2 changed this run", (self.root / "docs/UPSTREAM_STATUS.md").read_text(encoding="utf-8"))
        self.api.assert_not_called()
        self.command.assert_not_called()

    def test_changed_or_unavailable_refetch_leaves_every_file_unchanged(self):
        original = self.state_path.read_bytes()
        for outcome in ({"ok": False}, {"ok": True, "sha256": "e" * 64}):
            self.fetcher.return_value = outcome
            with self.assertRaises(ValueError):
                self.attempt()
            self.assertEqual(self.state_path.read_bytes(), original)
            self.assertFalse((self.root / "docs/UPSTREAM_STATUS.md").exists())

    def test_second_review_failure_does_not_clear_first(self):
        self.review["sources"].append({**self.review["sources"][0], "url": OTHER})
        original = self.state_path.read_bytes()
        self.fetcher.side_effect = [{"ok": True, "sha256": HASH}, {"ok": False}]
        with self.assertRaises(ValueError):
            self.attempt()
        self.assertEqual(self.state_path.read_bytes(), original)

    def test_unknown_duplicate_or_empty_review_refused(self):
        original = deepcopy(self.review)
        for rows in ([], [original["sources"][0]] * 2, [{**original["sources"][0], "url": "https://attacker.invalid"}],
                     [{**original["sources"][0], "notes": ""}], [{**original["sources"][0], "decision": "approved"}]):
            self.review = {**original, "sources": rows}
            with self.assertRaises(ValueError):
                self.attempt()
            self.assertIn("pending_change_since", json.loads(self.state_path.read_text())["sources"][URL])

    def test_stale_record_or_recorded_failure_refused_before_refetch(self):
        for change in ({"sha256": "e" * 64}, {"last_failure": {"failure_kind": "timeout"}}):
            state = deepcopy(self.state)
            state["sources"][URL].update(change)
            self.state_path.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaises(ValueError):
                self.attempt()
        self.fetcher.assert_not_called()


class PlanTests(OfflineTests):
    def setUp(self):
        super().setUp()
        (self.root / "automation").mkdir()
        self.state = {"last_run_at": STAMP, "sources": {}}
        self.workflow_state, self.conclusion, self.completed_at = "active", "success", STAMP
        self.pulls = []
        self.api.side_effect = self.respond

    def respond(self, path, **kwargs):
        if path == agent.PREFIX:
            return {"full_name": agent.REPO, "default_branch": "main"}
        if path.endswith("/git/ref/heads/main"):
            return {"object": {"sha": BASE}}
        if "/pulls?" in path:
            return self.pulls
        if "/actions/workflows/" in path:
            if "/runs?" in path:
                return {"workflow_runs": [{"status": "completed", "updated_at": self.completed_at,
                                          "conclusion": self.conclusion, "head_repository": {"full_name": agent.REPO},
                                          "html_url": "https://github.com/" + agent.REPO + "/actions/runs/55"}]}
            return {"state": self.workflow_state}
        raise AssertionError(path)

    def attempt(self):
        (self.root / "automation/upstream-state.json").write_text(json.dumps(self.state), encoding="utf-8")
        return agent.plan(self.root, NOW)

    def test_healthy_empty_plan_is_quiet_without_mutations(self):
        self.assertFalse(self.attempt()["needs_attention"])
        self.command.assert_not_called()

    def test_stale_failed_or_disabled_workflow_is_actionable(self):
        self.conclusion = "failure"
        self.assertTrue(self.attempt()["needs_attention"])
        self.conclusion = "success"
        self.completed_at = (NOW - timedelta(days=9)).isoformat()
        self.assertTrue(self.attempt()["needs_attention"])
        self.completed_at = STAMP
        self.workflow_state = "disabled_inactivity"
        self.assertTrue(self.attempt()["needs_attention"])

    def test_stale_observations_are_actionable(self):
        self.state["last_run_at"] = (NOW - timedelta(days=3)).isoformat()
        self.assertTrue(self.attempt()["observations_stale"])

    def test_pending_and_unavailable_sources_are_not_lost(self):
        self.state["sources"] = {URL: {"sha256": HASH, "skills": ["telegram-bot-alpha"], "pending_change_since": STAMP},
                                 OTHER: {"sha256": HASH, "skills": [], "last_failure": {"failure_kind": "timeout"}}}
        result = self.attempt()
        self.assertTrue(result["needs_attention"])
        self.assertEqual(len(result["sources"]), 2)

    def test_bot_and_reserved_agent_prs_only(self):
        bot = pr(9)
        bot["user"]["login"] = "dependabot[bot]"
        bot["body"] = ""
        bot["head"]["ref"] = "dependabot/pip/root"
        human = pr(10)
        human["head"]["ref"] = "human-work"
        self.pulls = [pr(), bot, human]
        result = self.attempt()
        self.assertEqual([p["number"] for p in result["pull_requests"]], [8, 9])


if __name__ == "__main__":
    unittest.main()
