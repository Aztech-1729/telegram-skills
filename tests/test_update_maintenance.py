"""Protected update branches are refreshed without executing their contents."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import automation_github as maintenance


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.path = Path(directory) / 'event.json'
        self.run = {'repository': {'full_name': maintenance.REPO},
                    'name': 'Validate skill pack', 'conclusion': 'success'}
        self.path.write_text(json.dumps({'workflow_run': self.run}))
        self.item = {'number': 3, 'auto_merge': {'merge_method': 'squash'},
                     'user': {'login': 'dependabot[bot]'}}
        self.pr = {**self.item, 'head': {'sha': 'a'*40, 'ref': 'dependabot/pip/update',
                                      'repo': {'full_name': maintenance.REPO}},
                   'base': {'ref': 'main'}, 'mergeable_state': 'behind', 'state': 'open'}
        self.calls = []
        self.changed = False
        self.enterContext(patch.object(maintenance.time, 'sleep'))
        self.protection = self.enterContext(patch.object(maintenance, 'protected'))
        self.validation = self.enterContext(patch.object(maintenance, 'start_validation'))
        self.enterContext(patch.object(maintenance, 'api', side_effect=self.api))

    def api(self, path, method='GET', data=None):
        self.calls.append((path, method, data))
        if path.endswith('/pulls?state=open&base=main&per_page=100'):
            return [self.item]
        if path.endswith('/pulls/3/update-branch'):
            self.changed = True
            return {'message': 'Updating pull request branch'}
        if path.endswith('/pulls/3'):
            value = deepcopy(self.pr)
            if self.changed:
                value['head']['sha'] = 'b'*40
            return value
        raise AssertionError(path)

    def test_eligible_behind_dependency_update_uses_exact_head_and_native_tests(self):
        maintenance.maintain_updates(self.path)
        self.protection.assert_called_once_with()
        self.assertIn((f'repos/{maintenance.REPO}/pulls/3/update-branch', 'PUT',
                       {'expected_head_sha': 'a'*40}), self.calls)
        self.validation.assert_called_once_with(3, 'b'*40, 'dependabot/pip/update', 'dependabot[bot]')

    def test_non_success_other_repository_or_other_workflow_does_nothing(self):
        for key, value in [('conclusion', 'failure'), ('repository', {'full_name': 'other/repo'}),
                           ('name', 'Other workflow')]:
            with self.subTest(key=key):
                run = {**self.run, key: value}
                self.path.write_text(json.dumps({'workflow_run': run}))
                maintenance.maintain_updates(self.path)
        self.protection.assert_not_called()
        self.assertEqual(self.calls, [])

    def test_unapproved_and_human_updates_are_not_touched(self):
        for item in [{**self.item, 'auto_merge': None}, {**self.item, 'user': {'login': 'human'}}]:
            self.item = item
            self.calls.clear()
            maintenance.maintain_updates(self.path)
            self.assertFalse(any(method == 'PUT' for _, method, _ in self.calls))
        self.validation.assert_not_called()

    def test_other_head_repository_base_branch_and_current_branches_are_not_touched(self):
        original = deepcopy(self.pr)
        for value in [{**original, 'head': {**original['head'], 'repo': {'full_name': 'other/repo'}}},
                      {**original, 'base': {'ref': 'other'}},
                      {**original, 'mergeable_state': 'clean'},
                      {**original, 'user': {'login': 'github-actions[bot]'}}]:
            self.pr = value
            self.calls.clear()
            maintenance.maintain_updates(self.path)
            self.assertFalse(any(method == 'PUT' for _, method, _ in self.calls))
        self.validation.assert_not_called()
