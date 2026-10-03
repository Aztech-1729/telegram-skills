"""Offline publishing and notification regressions; GitHub and git are mocked."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import automation_github as automation


PREFIX = f"repos/{automation.REPO}"
MAIN = "1" * 40
REPORT = {
    "counts": {"total": 2, "unavailable": 0, "pending_review": 0},
    "sources": [{"ok": True, "url": "https://example.test/api"}],
    "pending_review_sources": [],
}


def blob_sha(content):
    raw = content.replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class OfflineTests(unittest.TestCase):
    def setUp(self):
        # Every test fails closed if a new code path unexpectedly calls GitHub.
        self.api = self.enterContext(patch.object(
            automation, "api", side_effect=AssertionError("Unexpected GitHub API request")))
        self.command = self.enterContext(patch.object(automation.subprocess, "run"))
        self.git_head = self.enterContext(patch.object(
            automation.subprocess, "check_output", return_value=MAIN + "\n"))
        self.enterContext(patch("builtins.print"))


class PublishTests(OfflineTests):
    def setUp(self):
        super().setUp()
        self.directory = self.enterContext(TemporaryDirectory())
        self.root = Path(self.directory).resolve()
        self.enterContext(patch.object(automation, "ROOT", self.root))
        self.enterContext(patch.dict(os.environ, {
            "GITHUB_EVENT_NAME": "schedule", "GITHUB_REF": "refs/heads/main",
        }))
        self.contents = {
            "automation/upstream-state.json": '{"sources": {}}\n',
            "docs/UPSTREAM_STATUS.md": "# Source observations\n",
            "telegram-bot-alpha/references/upstream-status.md": "Observed alpha\n",
            "telegram-bot-beta/references/upstream-status.md": "Observed beta\n",
        }
        self.editorial = {
            "README.md": "Repository documentation\n",
            "telegram-bot-alpha/SKILL.md": "Editorial skill instructions\n",
            "telegram-bot-alpha/references/sources.md": "Reviewed 2026-09-01\n",
            "automation/sources.json": '{"allowed_origins": {}}\n',
            "unrelated/references/upstream-status.md": "Not a skill status\n",
        }
        for name, content in {**self.contents, **self.editorial}.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.report_path = self.root / "report.json"
        self.report_path.write_text(json.dumps(REPORT), encoding="utf-8")
        # The function's default root is bound on import; exercise the real
        # selector against our temporary repository when publish calls it.
        selector = automation.generated_paths
        self.paths = self.enterContext(patch.object(
            automation, "generated_paths", side_effect=lambda: selector(self.root)))
        self.source_alert = self.enterContext(patch.object(automation, "source_alert"))
        self.validation = self.enterContext(patch.object(automation, "start_validation"))
        self.protection = {"protected": True, "protection": {
            "required_status_checks": {"contexts": ["validation"], "strict": True}}}
        self.tree = {"truncated": False, "tree": []}
        self.pulls = []
        self.ref = None
        self.prior = {"message": automation.COMMIT}
        self.main_reads = [MAIN, MAIN]
        self.branch_reads = []
        self.api.side_effect = self.respond

    def respond(self, path, method="GET", data=None, missing=False):
        if method == "GET":
            if path == PREFIX + "/branches/main":
                return self.protection
            if path == PREFIX + "/git/ref/heads/main":
                return {"object": {"sha": self.main_reads.pop(0)}}
            if path == PREFIX + f"/git/commits/{MAIN}":
                return {"tree": {"sha": "base-tree"}}
            if path == PREFIX + "/git/trees/base-tree?recursive=1":
                return self.tree
            if path == PREFIX + f"/pulls?state=open&base=main&head=Aztech-1729:{automation.BRANCH}":
                return self.pulls
            if path == PREFIX + f"/git/ref/heads/{automation.BRANCH}":
                return self.branch_reads.pop(0) if self.branch_reads else self.ref
            if path == PREFIX + "/git/commits/old-automation-head":
                return self.prior
        if method == "POST":
            if path == PREFIX + "/git/trees":
                return {"sha": "new-tree"}
            if path == PREFIX + "/git/commits":
                return {"sha": "new-commit"}
            if path == PREFIX + "/pulls":
                return {"number": 42, "html_url": "https://example.test/pull/42"}
            if path in {PREFIX + "/git/refs", PREFIX + "/actions/workflows/validate.yml/dispatches"}:
                return None
        raise AssertionError(f"Unexpected GitHub API request: {method} {path}")

    def mutations(self):
        return [item for item in self.api.call_args_list
                if (item.args[1] if len(item.args) > 1 else item.kwargs.get("method", "GET")) != "GET"]

    def test_publish_requires_validation_branch_protection(self):
        for protection in (
            {"protected": False}, {"protected": True},
            {"protected": True, "protection": {"required_status_checks": {"contexts": ["lint"]}}},
            {"protected": True, "protection": {"required_status_checks": {"contexts": ["validation"], "strict": False}}},
        ):
            with self.subTest(protection=protection):
                self.protection = protection
                with self.assertRaisesRegex(RuntimeError, "validation protection"):
                    automation.publish(self.report_path)
                self.git_head.assert_not_called()
                self.assertEqual(self.mutations(), [])
        self.source_alert.assert_not_called()

    def test_publish_accepts_public_branch_response_without_admin_only_strict_field(self):
        del self.protection["protection"]["required_status_checks"]["strict"]
        automation.publish(self.report_path)
        self.validation.assert_called_once_with(42, "new-commit")

    def test_publish_rejects_non_default_branch_and_untrusted_events(self):
        for event, ref in (("pull_request", "refs/heads/main"), ("push", "refs/heads/main"),
                           ("workflow_dispatch", "refs/heads/feature"), ("schedule", "refs/tags/v1")):
            with self.subTest(event=event, ref=ref), patch.dict(os.environ, {
                "GITHUB_EVENT_NAME": event, "GITHUB_REF": ref,
            }):
                with self.assertRaisesRegex(RuntimeError, "default branch"):
                    automation.publish(self.report_path)
        self.api.assert_not_called()
        self.git_head.assert_not_called()

    def test_publish_rejects_checkout_that_no_longer_matches_main(self):
        self.git_head.return_value = "stale-main\n"
        with self.assertRaisesRegex(RuntimeError, "Main advanced during the scan"):
            automation.publish(self.report_path)
        self.assertEqual(self.mutations(), [])
        self.paths.assert_not_called()

    def test_truncated_tree_cannot_be_used_as_a_publication_baseline(self):
        self.tree["truncated"] = True
        with self.assertRaisesRegex(RuntimeError, "tree was truncated"):
            automation.publish(self.report_path)
        self.assertEqual(self.mutations(), [])

    def test_publish_only_writes_generated_paths_and_starts_native_validation(self):
        with patch.dict(os.environ, {"GITHUB_EVENT_NAME": "workflow_dispatch"}):
            automation.publish(self.report_path)
        tree_call = next(item for item in self.mutations() if item.args[0] == PREFIX + "/git/trees")
        tree_data = tree_call.args[2]
        self.assertEqual(tree_data["base_tree"], "base-tree")
        changes = tree_data["tree"]
        self.assertEqual({item["path"] for item in changes}, set(self.contents))
        self.assertTrue(set(self.editorial).isdisjoint(item["path"] for item in changes))
        for item in changes:
            self.assertEqual(item["content"], self.contents[item["path"]])
            self.assertEqual((item["mode"], item["type"]), ("100644", "blob"))
        for name, content in self.editorial.items():
            self.assertEqual((self.root / name).read_text(encoding="utf-8"), content)
        self.api.assert_any_call(PREFIX + "/git/commits", "POST", {
            "message": automation.COMMIT, "tree": "new-tree", "parents": [MAIN]})
        self.command.assert_called_once_with([
            "gh", "pr", "merge", "42", "--repo", automation.REPO, "--auto", "--squash",
            "--match-head-commit", "new-commit"], check=True)
        self.validation.assert_called_once_with(42, "new-commit")
        self.source_alert.assert_called_once_with(REPORT)

    def test_unchanged_blobs_still_refresh_alerts_without_a_commit_or_pr(self):
        self.tree["tree"] = [{"path": name, "sha": blob_sha(content), "type": "blob"}
                             for name, content in self.contents.items()]
        automation.publish(self.report_path)
        self.assertEqual(self.mutations(), [])
        self.command.assert_not_called()
        self.source_alert.assert_called_once_with(REPORT)

    def test_escaping_generated_path_is_rejected_before_reading(self):
        self.paths.side_effect = lambda: ["../outside-status.md"]
        with self.assertRaisesRegex(RuntimeError, "escaped the repository"):
            automation.publish(self.report_path)
        self.assertEqual(self.mutations(), [])

    def test_symlink_generated_path_is_rejected(self):
        # Mock the filesystem flag because Windows symlink creation can require
        # privileges; real path resolution is covered by the traversal case.
        with patch.object(Path, "is_symlink", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "escaped the repository"):
                automation.publish(self.report_path)
        self.assertEqual(self.mutations(), [])

    def test_reserved_branch_cannot_replace_another_authors_pr(self):
        self.pulls = [{"number": 5, "user": {"login": "maintainer"}}]
        with self.assertRaisesRegex(RuntimeError, "belongs to another author"):
            automation.publish(self.report_path)
        self.assertEqual(self.mutations(), [])

    def test_reserved_branch_cannot_replace_a_non_automation_commit(self):
        self.ref = {"object": {"sha": "old-automation-head"}}
        self.prior = {"message": "Human-authored work"}
        with self.assertRaisesRegex(RuntimeError, "non-automation branch"):
            automation.publish(self.report_path)
        self.assertEqual(self.mutations(), [])

    def test_main_advancing_after_commit_creation_prevents_ref_or_pr_changes(self):
        self.main_reads = [MAIN, "2" * 40]
        with self.assertRaisesRegex(RuntimeError, "Main advanced; generated results"):
            automation.publish(self.report_path)
        self.assertEqual([item.args[0] for item in self.mutations()],
                         [PREFIX + "/git/trees", PREFIX + "/git/commits"])
        self.command.assert_not_called()

    def test_concurrent_automation_branch_change_prevents_force_update(self):
        self.ref = {"object": {"sha": "old-automation-head"}}
        self.branch_reads = [self.ref, {"object": {"sha": "concurrent-change"}}]
        with self.assertRaisesRegex(RuntimeError, "branch changed concurrently"):
            automation.publish(self.report_path)
        self.assertEqual([item.args[0] for item in self.mutations()],
                         [PREFIX + "/git/trees", PREFIX + "/git/commits"])
        self.command.assert_not_called()


class IssueTests(OfflineTests):
    def setUp(self):
        super().setUp()
        self.marker = "<!-- telegram-skills-automation:source-drift -->"
        self.list_path = PREFIX + "/issues?state=open&creator=github-actions%5Bbot%5D&per_page=100&page=1"
        self.details = "Source changed: https://example.test/api"

    def test_unchanged_findings_hash_does_not_update_issue(self):
        digest = hashlib.sha256(self.details.encode()).hexdigest()
        self.api.side_effect = [[{"number": 7, "body": self.marker + f"\n<!-- findings:{digest} -->\nOld presentation"}]]
        automation.issue("source-drift", "Updated title", self.details)
        self.api.assert_called_once_with(self.list_path)

    def test_changed_findings_update_only_the_exact_marker_issue(self):
        self.api.side_effect = [[
            {"number": 1, "body": "A human issue without the automation marker"},
            {"number": 2, "body": "<!-- telegram-skills-automation:source-drift-other -->"},
            {"number": 3, "body": self.marker, "pull_request": {}},
            {"number": 7, "body": self.marker + "\nOld findings"},
        ], None]
        automation.issue("source-drift", "New findings", self.details)
        self.assertEqual(self.api.call_count, 2)
        update = self.api.call_args
        self.assertEqual(update.args[:2], (PREFIX + "/issues/7", "PATCH"))
        self.assertEqual(update.args[2]["title"], "New findings")
        self.assertIn(self.marker, update.args[2]["body"])
        self.assertIn(hashlib.sha256(self.details.encode()).hexdigest(), update.args[2]["body"])
        self.assertTrue(update.args[2]["body"].endswith(self.details))

    def test_resolved_findings_close_all_matching_issues_only(self):
        self.api.side_effect = [[
            {"number": 1, "body": "Unrelated issue"},
            {"number": 2, "body": self.marker, "pull_request": {}},
            {"number": 7, "body": self.marker}, {"number": 8, "body": self.marker},
        ], None, None]
        automation.issue("source-drift", "", "")
        self.assertEqual(self.api.call_args_list, [call(self.list_path),
            call(PREFIX + "/issues/7", "PATCH", {"state": "closed", "state_reason": "completed"}),
            call(PREFIX + "/issues/8", "PATCH", {"state": "closed", "state_reason": "completed"})])

    def test_new_findings_create_one_marked_issue(self):
        self.api.side_effect = [[], None]
        automation.issue("source-drift", "New findings", self.details)
        self.assertEqual(self.api.call_count, 2)
        self.assertEqual(self.api.call_args.args[:2], (PREFIX + "/issues", "POST"))
        self.assertEqual(self.api.call_args.args[2]["title"], "New findings")
        self.assertTrue(self.api.call_args.args[2]["body"].startswith(self.marker + "\n<!-- findings:"))

    def test_issue_lookup_pages_before_creating_a_duplicate(self):
        self.api.side_effect = [
            [{"number": number, "body": None} for number in range(100)],
            [{"number": 101, "body": self.marker + "\nOld findings"}], None,
        ]
        automation.issue("source-drift", "New findings", self.details)
        self.assertEqual(self.api.call_args_list[1], call(self.list_path[:-1] + "2"))
        self.assertEqual(self.api.call_args.args[:2], (PREFIX + "/issues/101", "PATCH"))


class AlertTests(OfflineTests):
    def setUp(self):
        super().setUp()
        directory = self.enterContext(TemporaryDirectory())
        self.path = Path(directory) / "event.json"
        self.issue = self.enterContext(patch.object(automation, "issue"))
        self.run = {"repository": {"full_name": automation.REPO}, "head_branch": "main",
                    "name": "Validate skill pack", "workflow_id": 123, "id": 456,
                    "run_number": 10, "html_url": "https://example.test/runs/456", "conclusion": "failure"}
        self.api.side_effect = None
        self.api.return_value = {"workflow_runs": [{"id": 456}]}

    def alert(self, run=None):
        self.path.write_text(json.dumps({"workflow_run": run or self.run}), encoding="utf-8")
        automation.alert(self.path)

    def test_other_repositories_branches_and_workflows_are_ignored(self):
        for field, value in (("repository", {"full_name": "fork/telegram-skills"}),
                             ("head_branch", "feature"), ("name", "Unrelated workflow")):
            with self.subTest(field=field):
                self.alert({**self.run, field: value})
        self.api.assert_not_called()
        self.issue.assert_not_called()

    def test_superseded_run_cannot_open_or_close_an_issue(self):
        self.api.return_value = {"workflow_runs": [{"id": 457}]}
        for conclusion in ("failure", "success"):
            with self.subTest(conclusion=conclusion):
                self.alert({**self.run, "conclusion": conclusion})
        self.issue.assert_not_called()

    def test_cancelled_and_skipped_runs_leave_alerts_unchanged(self):
        for conclusion in ("cancelled", "skipped"):
            with self.subTest(conclusion=conclusion):
                self.alert({**self.run, "conclusion": conclusion})
        self.issue.assert_not_called()

    def test_current_failure_creates_workflow_specific_alert_with_run_link(self):
        for name in ("Validate skill pack", "Refresh upstream evidence"):
            with self.subTest(name=name):
                self.alert({**self.run, "name": name})
                key, title, details = self.issue.call_args.args
                self.assertEqual(key, "workflow-123")
                self.assertEqual(title, "Automation failed: " + name)
                self.assertIn(self.run["html_url"], details)
                self.assertIn("finished with failure", details)
        self.api.assert_called_with(PREFIX + "/actions/workflows/123/runs?branch=main&status=completed&per_page=1")

    def test_current_success_resolves_only_its_workflow_alert(self):
        self.alert({**self.run, "conclusion": "success"})
        self.issue.assert_called_once_with("workflow-123", "", "")


class SourceAlertTests(OfflineTests):
    def test_source_findings_are_stable_when_report_order_changes(self):
        report = deepcopy(REPORT)
        report["sources"] = [{"ok": False, "url": "https://example.test/z", "failure_kind": "timeout"},
                             {"ok": False, "url": "https://example.test/a", "failure_kind": "http_error"}]
        report["pending_review_sources"] = ["https://example.test/b", "https://example.test/a"]
        with patch.object(automation, "issue") as issue:
            automation.source_alert(report)
            first = issue.call_args
            report["sources"].reverse()
            report["pending_review_sources"].reverse()
            automation.source_alert(report)
            self.assertEqual(issue.call_args, first)
            self.assertIn("Unavailable: https://example.test/z (timeout)", first.args[2])
            self.assertIn("Source changed; review affected guides: https://example.test/a", first.args[2])


if __name__ == "__main__":
    unittest.main()
