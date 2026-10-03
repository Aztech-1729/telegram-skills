"""Approval never starts a different contributor's workflow or an obsolete commit."""
from copy import deepcopy
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import automation_github as publisher


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.run = {'id': 7, 'head_sha': 'a'*40, 'event': 'pull_request',
                    'head_repository': {'full_name': publisher.REPO},
                    'path': '.github/workflows/validate.yml', 'actor': {'login': 'github-actions[bot]'},
                    'pull_requests': [{'number': 3, 'head': {'ref': publisher.BRANCH}}],
                    'conclusion': 'action_required', 'html_url': 'https://github.com/example/run/7'}
        self.pr = {'head': {'sha': 'a'*40, 'ref': publisher.BRANCH}, 'user': {'login': 'github-actions[bot]'}, 'state': 'open'}
        self.calls = []
        self.enterContext(patch.object(publisher.time, 'sleep'))
        self.enterContext(patch('builtins.print'))
        self.enterContext(patch.object(publisher, 'api', side_effect=self.api))

    def api(self, path, method='GET'):
        self.calls.append((path, method))
        if '/actions/workflows/' in path:
            return {'workflow_runs': [self.run]}
        if '/pulls/3' in path:
            return self.pr
        if path.endswith('/approve') and method == 'POST':
            return None
        raise AssertionError(path)

    def test_only_exact_native_run_is_approved(self):
        publisher.start_validation(3, 'a'*40)
        self.assertIn((f'repos/{publisher.REPO}/actions/runs/7/approve', 'POST'), self.calls)

    def test_running_native_run_needs_no_approval(self):
        self.run['conclusion'] = None
        publisher.start_validation(3, 'a'*40)
        self.assertFalse(any(method == 'POST' for _, method in self.calls))

    def test_mismatching_run_cannot_be_approved(self):
        original = deepcopy(self.run)
        for key, value in [('head_sha', 'b'*40), ('event', 'workflow_dispatch'),
                           ('head_repository', {'full_name': 'other/repo'}),
                           ('actor', {'login': 'another-contributor'}),
                           ('path', '.github/workflows/other.yml'),
                           ('pull_requests', [{'number': 4, 'head': {'ref': publisher.BRANCH}}])]:
            with self.subTest(key=key):
                self.run = deepcopy(original)
                self.run[key] = value
                self.calls.clear()
                with self.assertRaisesRegex(RuntimeError, 'No native validation'):
                    publisher.start_validation(3, 'a'*40)
                self.assertFalse(any(method == 'POST' for _, method in self.calls))

    def test_pr_changed_between_creation_and_approval_fails_closed(self):
        for key, value in [('head', {'sha': 'b'*40, 'ref': publisher.BRANCH}),
                           ('user', {'login': 'maintainer'}), ('state', 'closed')]:
            with self.subTest(key=key):
                old = deepcopy(self.pr)
                self.pr[key] = value
                with self.assertRaisesRegex(RuntimeError, 'PR changed'):
                    publisher.start_validation(3, 'a'*40)
                self.pr = old
        self.assertFalse(any(method == 'POST' for _, method in self.calls))
