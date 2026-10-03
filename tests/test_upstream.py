"""Offline upstream-monitor regressions; no network or credentials are used."""
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_upstream as upstream


CONFIG = {
    "allowed_origins": {
        "https://docs.example.test": ["/guide"],
        "https://github.com": ["/team/bot"],
        "https://raw.githubusercontent.com": ["/team/bot"],
        "https://registry.example.test": ["/"],
    },
    "additional_sources": [],
}
SOURCE = {
    "url": "https://docs.example.test/guide/api",
    "fetch_url": "https://docs.example.test/guide/api",
    "kind": "document",
    "skills": ["telegram-bot-alpha"],
    "skill_ledger_review_dates": {"telegram-bot-alpha": "2026-09-01"},
}
FIRST_CHECK = "2026-10-01T00:00:00Z"
SECOND_CHECK = "2026-10-02T00:00:00Z"
THIRD_CHECK = "2026-10-03T00:00:00Z"


def success(digest="a" * 64):
    return {"ok": True, "sha256": digest, "final_url": SOURCE["url"],
            "release_versions": [], "bytes": 100, "normalized_characters": 80, "seconds": 0.1}


def failure():
    return {"ok": False, "failure_kind": "timeout", "message": "Timed out",
            "transient": True, "seconds": 1.0}


class Response:
    def __init__(self, body, url=SOURCE["url"], content_type="text/plain", headers=None):
        self.stream = BytesIO(body)
        self.url = url
        self.headers = {"Content-Type": content_type, **(headers or {})}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read1(self, limit):
        return self.stream.read(limit)

    def geturl(self):
        return self.url


class URLSafetyTests(unittest.TestCase):
    def assert_untrusted(self, url):
        with self.assertRaises(upstream.CheckError) as caught:
            upstream.validate_url(url, CONFIG)
        self.assertEqual(caught.exception.kind, "untrusted_url")

    def test_canonicalization_deduplicates_fragments_and_preserves_query(self):
        self.assertEqual(
            upstream.validate_url("https://DOCS.EXAMPLE.TEST:443/guide/api?version=2#method", CONFIG),
            "https://docs.example.test/guide/api?version=2",
        )
        self.assertNotEqual(
            upstream.canonical_url("https://docs.example.test/guide?version=1"),
            upstream.canonical_url("https://docs.example.test/guide?version=2"),
        )

    def test_only_exact_origins_and_path_boundaries_are_allowed(self):
        for url in ("https://docs.example.test/guide", "https://docs.example.test/guide/", SOURCE["url"]):
            with self.subTest(url=url):
                self.assertEqual(upstream.validate_url(url, CONFIG), url)
        for url in (
            "http://docs.example.test/guide", "https://docs.example.test.evil.test/guide",
            "https://evil.test/guide", "https://docs.example.test/guides",
            "https://docs.example.test/other", "https://docs.example.test:8443/guide",
            "https://user:secret@docs.example.test/guide", "https://127.0.0.1/guide",
            "https://docs.example.test/guide\\outside", "https://docs.example.test/guide\n/api",
            "https://docs.example.test:invalid/guide",
        ):
            with self.subTest(url=url):
                self.assert_untrusted(url)

    def test_traversal_cannot_escape_a_path_allowlist(self):
        for url in (
            "https://github.com/team/bot/../outside",
            "https://github.com/team/bot/%2e%2e/outside",
            "https://github.com/team/bot/%2E%2E%2Foutside",
        ):
            with self.subTest(url=url):
                self.assert_untrusted(url)

    def test_redirects_recheck_origin_and_path(self):
        handler = upstream.GuardedRedirectHandler(CONFIG)
        request = Request(SOURCE["url"])
        allowed = "https://docs.example.test/guide/new"
        redirected = handler.redirect_request(request, None, 302, "Found", {}, allowed)
        self.assertEqual(redirected.full_url, allowed)
        for destination in ("https://evil.test/guide", "https://docs.example.test/private", "../../private"):
            with self.subTest(destination=destination):
                with self.assertRaises(upstream.CheckError) as caught:
                    handler.redirect_request(request, None, 302, "Found", {}, destination)
                self.assertEqual(caught.exception.kind, "untrusted_url")

    def test_fetch_validates_final_response_url_before_reading(self):
        response = Response(b"Authoritative content would otherwise pass.", url="https://evil.test/content")
        response.read1 = Mock(side_effect=AssertionError("Untrusted body must not be read"))
        with patch.object(upstream, "build_opener", return_value=Mock(open=Mock(return_value=response))):
            result = upstream.fetch_source(SOURCE, CONFIG, timeout=1, max_bytes=1024)
        self.assertFalse(result["ok"])
        self.assertEqual(result["failure_kind"], "untrusted_url")
        response.read1.assert_not_called()

    def test_fetch_rejects_disallowed_initial_url_without_opening(self):
        source = {**SOURCE, "fetch_url": "https://evil.test/content"}
        with patch.object(upstream, "build_opener") as opener:
            result = upstream.fetch_source(source, CONFIG, timeout=1, max_bytes=1024)
        self.assertEqual(result["failure_kind"], "untrusted_url")
        opener.assert_not_called()

    def test_size_limit_applies_without_a_content_length(self):
        response = Response(b"x" * 1025)
        with patch.object(upstream, "build_opener", return_value=Mock(open=Mock(return_value=response))):
            result = upstream.fetch_source(SOURCE, CONFIG, timeout=1, max_bytes=1024)
        self.assertEqual(result["failure_kind"], "oversize")
        self.assertNotIn("sha256", result)


class NormalizationTests(unittest.TestCase):
    def normalize(self, text):
        return upstream.normalized_content(text.encode("utf-8"), "text/html; charset=utf-8")

    def test_navigation_changes_do_not_change_article_content(self):
        def page(menu):
            return f"""<html><head><title>{menu}</title><style>{menu}</style></head>
              <body><header>{menu}</header><nav>{menu}</nav><main><article>
              <h1>Send a message</h1><p>Use <code>sendMessage</code> with a chat identifier.</p>
              <div class="sidebar">{menu}</div><div id="toc">{menu}</div>
              <div aria-hidden="true">{menu}</div><script>{menu}</script>
              </article></main><footer>{menu}</footer></body></html>"""
        self.assertEqual(self.normalize(page("Navigation version one")), self.normalize(page("Changed links and counters")))
        self.assertEqual(self.normalize(page("Noise")), "Send a message Use sendMessage with a chat identifier.")

    def test_text_tables_and_code_survive_normalization(self):
        page = """<main><h1>Method parameters</h1><p>Pass a <strong>chat_id</strong>.</p>
          <ul><li>Required integer</li></ul><table><tr><th>Field</th><td>text</td></tr></table>
          <pre>sendMessage(chat_id=42, text=&quot;Hello&quot;)</pre><br><p>Returns a Message.</p></main>"""
        normalized = self.normalize(page)
        for text in ("Method parameters", "chat_id", "Required integer", "Field text",
                     'sendMessage(chat_id=42, text="Hello")', "Returns a Message."):
            self.assertIn(text, normalized)
        self.assertNotEqual(normalized, self.normalize(page.replace("Required integer", "Optional string")))

    def test_whitespace_and_plain_text_are_stable(self):
        self.assertEqual(
            upstream.normalized_content(b"  sendMessage\n\t requires a chat_id and text.  ", "text/plain"),
            "sendMessage requires a chat_id and text.",
        )

    def test_telegram_content_container_excludes_surrounding_page_text(self):
        self.assertEqual(
            self.normalize('<html><div>Site announcements change daily</div><div class="wide dev_page_content"><h1>Bot API</h1><p>Send messages with sendMessage.</p></div></html>'),
            "Bot API Send messages with sendMessage.",
        )

    def test_empty_content_and_challenges_are_failures(self):
        for text, kind in (("<html><nav>Only navigation</nav></html>", "empty_content"),
                           ("<html><main>Verify you are human before reading documentation.</main></html>", "challenge_page")):
            with self.subTest(kind=kind):
                with self.assertRaises(upstream.CheckError) as caught:
                    self.normalize(text)
                self.assertEqual(caught.exception.kind, kind)
                self.assertEqual(caught.exception.transient, kind == "challenge_page")


class ReleaseFeedTests(unittest.TestCase):
    def normalized(self, value, kind):
        return upstream.normalized_content(json.dumps(value).encode("utf-8"), "application/json", kind)

    def versions(self, value, kind):
        return upstream.release_versions(json.dumps(value).encode("utf-8"), kind)

    def test_github_list_filters_unstable_releases_and_ignores_metadata(self):
        releases = [
            {"tag_name": "v4-draft", "draft": True}, {"tag_name": "v3-rc", "prerelease": True},
            {"tag_name": "v2", "name": "Two", "body": "Adds polling", "download_count": 10, "published_at": "yesterday"},
            {"tag_name": "v1", "name": "One", "body": "Initial release"},
        ]
        changed_metadata = deepcopy(releases)
        changed_metadata[2].update(download_count=500, published_at="today", html_url="https://example.test/new")
        self.assertEqual(self.normalized(releases, "github-release"), self.normalized(changed_metadata, "github-release"))
        self.assertEqual(self.versions(releases, "github-release"), ["v2", "v1"])
        changed_metadata[2]["body"] = "Polling now requires a timeout"
        self.assertNotEqual(self.normalized(releases, "github-release"), self.normalized(changed_metadata, "github-release"))

    def test_github_single_release_and_history_limit(self):
        release = {"tag_name": "v2", "name": "Two", "body": "Release notes"}
        self.assertEqual(self.versions(release, "github-release"), ["v2"])
        releases = [{**release, "tag_name": f"v{number}"} for number in range(8, 0, -1)]
        self.assertEqual(self.versions(releases, "github-release"), ["v8", "v7", "v6", "v5", "v4"])

    def test_github_prereleases_require_an_explicit_channel_and_still_exclude_drafts(self):
        releases = [{"tag_name": "v3-draft", "draft": True},
                    {"tag_name": "v2-rc1", "prerelease": True},
                    {"tag_name": "v1", "prerelease": False}]
        self.assertEqual(self.versions(releases, "github-release"), ["v1"])
        self.assertEqual(self.versions(releases, "github-prerelease"), ["v2-rc1", "v1"])
        summary = json.loads(self.normalized(releases, "github-prerelease"))
        self.assertTrue(summary[0]["prerelease"])
        self.assertFalse(summary[1]["prerelease"])

    def test_all_registry_shapes_preserve_versions_and_relevant_dependencies(self):
        fixtures = [
            ("pypi-release", {"info": {"name": "bot", "version": "2.0", "requires_python": ">=3.10", "requires_dist": ["httpx>=0.27"]}, "downloads": 1}, ["2.0"], "httpx>=0.27"),
            ("npm-release", {"name": "bot", "version": "3.0", "engines": {"node": ">=20"}, "dependencies": {"debug": "^4"}, "dist": {"shasum": "ignored"}}, ["3.0"], "debug"),
            ("nuget-versions", {"versions": ["1.0.0", "2.0.0-beta", "2.0.0"]}, ["2.0.0", "1.0.0"], "1.0.0"),
            ("packagist-release", {"packages": {"team/bot": [{"name": "team/bot", "version": "dev-main"}, {"name": "team/bot", "version": "v3.0.0-RC1"}, {"name": "team/bot", "version": "v2.0.0", "require": {"php": ">=8.2"}}]}}, ["v2.0.0"], "php"),
            ("crates-release", {"crate": {"id": "bot", "max_stable_version": "2.0.0", "newest_version": "3.0.0-beta", "downloads": 100}}, ["2.0.0"], "2.0.0"),
        ]
        for kind, value, versions, retained in fixtures:
            with self.subTest(kind=kind):
                self.assertEqual(self.versions(value, kind), versions)
                self.assertIn(retained, self.normalized(value, kind))

    def test_registry_download_metadata_is_ignored_but_version_changes_are_not(self):
        pairs = [
            ("pypi-release", {"info": {"name": "bot", "version": "1.0"}, "urls": [{"upload_time": "yesterday"}]}, "info", "version"),
            ("npm-release", {"name": "bot", "version": "1.0", "dist": {"shasum": "first"}}, None, "version"),
            ("crates-release", {"crate": {"id": "bot", "max_stable_version": "1.0", "newest_version": "1.0", "downloads": 10}}, "crate", "max_stable_version"),
        ]
        for kind, original, inner_key, version_key in pairs:
            with self.subTest(kind=kind):
                changed = deepcopy(original)
                changed["downloads"] = 999
                changed["urls"] = [{"upload_time": "today"}]
                changed["dist"] = {"shasum": "second"}
                if inner_key:
                    changed[inner_key]["downloads"] = 999
                self.assertEqual(self.normalized(original, kind), self.normalized(changed, kind))
                (changed[inner_key] if inner_key else changed)[version_key] = "2.0"
                self.assertNotEqual(self.normalized(original, kind), self.normalized(changed, kind))

    def test_malformed_or_empty_release_feeds_are_not_accepted_as_baselines(self):
        fixtures = [
            ("github-release", None), ("github-release", ["not a release"]),
            ("github-release", {"message": "API rate limit exceeded"}),
            ("github-release", [{"tag_name": "v2", "prerelease": True}]),
            ("pypi-release", {"info": {}}), ("npm-release", {}),
            ("nuget-versions", {"versions": ["2.0.0-beta"]}),
            ("packagist-release", {"packages": {}}),
            ("crates-release", {"crate": {}}),
        ]
        for kind, value in fixtures:
            with self.subTest(kind=kind, value=value):
                with self.assertRaises(upstream.CheckError) as caught:
                    self.normalized(value, kind)
                self.assertEqual(caught.exception.kind, "invalid_payload")


class ObservationStateTests(unittest.TestCase):
    def baseline(self):
        return upstream.reconcile(SOURCE, success(), None, FIRST_CHECK)[0]

    def test_first_observation_does_not_claim_editorial_review(self):
        entry, row = upstream.reconcile(SOURCE, success(), None, FIRST_CHECK)
        self.assertEqual(row["status"], "baseline")
        self.assertEqual(entry["baseline_sha256"], success()["sha256"])
        self.assertEqual(entry["first_observed_at"], FIRST_CHECK)
        self.assertIsNone(entry["reviewed_sha256"])
        self.assertIsNone(entry["editorial_reviewed_at"])
        self.assertEqual(entry["skill_ledger_review_dates"], SOURCE["skill_ledger_review_dates"])
        self.assertFalse(row["pending_review"])

    def test_failure_preserves_last_successful_evidence_and_review_state(self):
        previous = {**self.baseline(), "reviewed_sha256": "a" * 64, "editorial_reviewed_at": FIRST_CHECK,
                    "pending_change_since": FIRST_CHECK, "release_versions": ["1.0"]}
        original = deepcopy(previous)
        entry, row = upstream.reconcile(SOURCE, failure(), previous, SECOND_CHECK)
        self.assertEqual(row["status"], "unavailable")
        for key in ("sha256", "baseline_sha256", "last_checked_at", "first_observed_at", "final_url",
                    "reviewed_sha256", "editorial_reviewed_at", "pending_change_since", "release_versions"):
            self.assertEqual(entry[key], previous[key], key)
        self.assertEqual(entry["last_attempt_at"], SECOND_CHECK)
        self.assertEqual(entry["last_failure"]["failure_kind"], "timeout")
        self.assertEqual(previous, original, "Reconciliation must not mutate prior state")

    def test_initial_failure_does_not_establish_a_baseline(self):
        entry, row = upstream.reconcile(SOURCE, failure(), None, FIRST_CHECK)
        self.assertEqual(row["status"], "unavailable")
        for key in ("sha256", "baseline_sha256", "last_checked_at", "first_observed_at"):
            self.assertNotIn(key, entry)

    def test_pending_change_survives_unchanged_fetch_and_additional_changes(self):
        baseline = self.baseline()
        changed, row = upstream.reconcile(SOURCE, success("b" * 64), baseline, SECOND_CHECK)
        self.assertEqual(row["status"], "changed")
        self.assertEqual(row["previous_sha256"], "a" * 64)
        self.assertEqual(changed["pending_change_since"], SECOND_CHECK)
        unchanged, row = upstream.reconcile(SOURCE, success("b" * 64), changed, THIRD_CHECK)
        self.assertEqual(row["status"], "unchanged")
        self.assertTrue(row["pending_review"])
        self.assertEqual(unchanged["pending_change_since"], SECOND_CHECK)
        changed_again, row = upstream.reconcile(SOURCE, success("c" * 64), unchanged, THIRD_CHECK)
        self.assertEqual(changed_again["pending_change_since"], SECOND_CHECK)
        self.assertEqual(changed_again["last_changed_at"], THIRD_CHECK)
        self.assertEqual(changed_again["baseline_sha256"], baseline["baseline_sha256"])
        self.assertIsNone(changed_again["reviewed_sha256"])

    def test_recovery_clears_failure_without_erasing_pending_review(self):
        changed, _ = upstream.reconcile(SOURCE, success("b" * 64), self.baseline(), SECOND_CHECK)
        unavailable, _ = upstream.reconcile(SOURCE, failure(), changed, THIRD_CHECK)
        recovered, row = upstream.reconcile(SOURCE, success("b" * 64), unavailable, THIRD_CHECK)
        self.assertNotIn("last_failure", recovered)
        self.assertTrue(row["pending_review"])
        self.assertEqual(recovered["pending_change_since"], SECOND_CHECK)

    def test_run_report_keeps_pending_failures_visible(self):
        changed, _ = upstream.reconcile(SOURCE, success("b" * 64), self.baseline(), SECOND_CHECK)
        new_source = {**SOURCE, "url": "https://docs.example.test/guide/new", "fetch_url": "https://docs.example.test/guide/new"}
        state, report = upstream.run_checks(
            [SOURCE, new_source], CONFIG, {"sources": {SOURCE["url"]: changed}}, THIRD_CHECK,
            lambda source: failure() if source["url"] == SOURCE["url"] else success(), workers=2,
        )
        self.assertEqual(report["counts"], {"baseline": 1, "changed": 0, "unchanged": 0,
                                         "unavailable": 1, "total": 2, "pending_review": 1, "transient_failures": 1})
        self.assertEqual(report["failed_sources"], [SOURCE["url"]])
        self.assertEqual(report["pending_review_sources"], [SOURCE["url"]])
        self.assertEqual(state["sources"][SOURCE["url"]]["sha256"], "b" * 64)
        markdown = upstream.markdown_report(report, state)
        self.assertIn(SECOND_CHECK, markdown)
        self.assertIn("timeout", markdown)
        self.assertIn("alpha", markdown)


class SourceHarvestTests(unittest.TestCase):
    def write_ledger(self, root, skill, text):
        path = root / skill / "references" / "sources.md"
        path.parent.mkdir(parents=True)
        path.write_text(text, encoding="utf-8")

    def test_harvest_deduplicates_fragments_and_maps_all_affected_skills(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_ledger(root, "telegram-bot-alpha", "Reviewed 2026-09-01\n[API](https://docs.example.test/guide/api#one)\nhttps://docs.example.test/guide/api#two\nhttps://docs.example.test/guide/api?version=2")
            self.write_ledger(root, "telegram-bot-beta", "Reviewed 2026-09-02\nhttps://docs.example.test/guide/api#three\n[Source](https://github.com/team/bot/blob/main/README.md#usage)")
            sources = upstream.load_sources(root, CONFIG)
        by_url = {source["url"]: source for source in sources}
        self.assertEqual(len(by_url), 3)
        shared = by_url[SOURCE["url"]]
        self.assertEqual(shared["skills"], ["telegram-bot-alpha", "telegram-bot-beta"])
        self.assertEqual(shared["skill_ledger_review_dates"], {"telegram-bot-alpha": "2026-09-01", "telegram-bot-beta": "2026-09-02"})
        self.assertEqual(by_url["https://github.com/team/bot/blob/main/README.md"]["fetch_url"], "https://raw.githubusercontent.com/team/bot/main/README.md")
        self.assertEqual(by_url[SOURCE["url"] + "?version=2"]["skills"], ["telegram-bot-alpha"])

    def test_additional_feed_merges_skill_coverage_and_preserves_ledger_review_dates(self):
        config = deepcopy(CONFIG)
        config["additional_sources"] = [{"url": SOURCE["url"] + "#feed", "kind": "npm-release", "skills": ["telegram-bot-beta", "telegram-bot-alpha"], "label": "Current release"}]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_ledger(root, "telegram-bot-alpha", "Reviewed 2026-09-01\n" + SOURCE["url"])
            sources = upstream.load_sources(root, config)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["kind"], "npm-release")
        self.assertEqual(sources[0]["skills"], ["telegram-bot-alpha", "telegram-bot-beta"])
        self.assertEqual(sources[0]["skill_ledger_review_dates"], SOURCE["skill_ledger_review_dates"])
        self.assertEqual(sources[0]["label"], "Current release")

    def test_harvest_fails_closed_on_untrusted_sources_or_missing_ledgers(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "No skill source ledgers"):
                upstream.load_sources(root, CONFIG)
            self.write_ledger(root, "telegram-bot-alpha", "https://evil.test/instructions")
            with self.assertRaises(upstream.CheckError) as caught:
                upstream.load_sources(root, CONFIG)
            self.assertEqual(caught.exception.kind, "untrusted_url")

    def test_raw_github_destination_needs_its_own_allowlist_entry(self):
        config = deepcopy(CONFIG)
        del config["allowed_origins"]["https://raw.githubusercontent.com"]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_ledger(root, "telegram-bot-alpha", "https://github.com/team/bot/blob/main/README.md")
            with self.assertRaises(upstream.CheckError) as caught:
                upstream.load_sources(root, config)
            self.assertEqual(caught.exception.kind, "untrusted_url")

    def test_fetch_override_preserves_source_identity_and_is_independently_validated(self):
        config = deepcopy(CONFIG)
        raw_url = "https://raw.githubusercontent.com/team/bot/main/docs/api.md"
        config["fetch_overrides"] = {SOURCE["url"]: raw_url}
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_ledger(root, "telegram-bot-alpha", "Reviewed 2026-09-01\n" + SOURCE["url"])
            sources = upstream.load_sources(root, config)
            self.assertEqual(sources[0]["url"], SOURCE["url"])
            self.assertEqual(sources[0]["fetch_url"], raw_url)
            self.assertEqual(sources[0]["skills"], SOURCE["skills"])
            self.assertEqual(sources[0]["skill_ledger_review_dates"], SOURCE["skill_ledger_review_dates"])
            config["fetch_overrides"][SOURCE["url"]] = "https://evil.test/docs/api.md"
            with self.assertRaises(upstream.CheckError) as caught:
                upstream.load_sources(root, config)
            self.assertEqual(caught.exception.kind, "untrusted_url")


if __name__ == "__main__":
    unittest.main()
