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
                   'base': {'ref': 'main'}, 'mergeable_state': 'behind', 'state': 'open',
                   'draft': False, 'changed_files': 1}
        self.files = [{'filename': 'requirements-dev.txt', 'status': 'modified'}]
        self.calls = []
        self.changed = False
        self.enterContext(patch.object(maintenance.time, 'sleep'))
        self.protection = self.enterContext(patch.object(maintenance, 'protected'))
        self.validation = self.enterContext(patch.object(maintenance, 'start_validation'))
        self.command = self.enterContext(patch.object(maintenance.subprocess, 'run'))
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
        if '/pulls/3/files?' in path:
            page = int(path.rsplit('=', 1)[1])
            return deepcopy(self.files[(page-1)*100:page*100])
        raise AssertionError(path)

    def test_eligible_behind_dependency_update_uses_exact_head_and_native_tests(self):
        maintenance.maintain_updates(self.path)
        self.protection.assert_called_once_with()
        self.assertIn((f'repos/{maintenance.REPO}/pulls/3/update-branch', 'PUT',
                       {'expected_head_sha': 'a'*40}), self.calls)
        self.validation.assert_called_once_with(3, 'b'*40, 'dependabot/pip/update', 'dependabot[bot]')
        self.command.assert_not_called()

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

    def test_retained_auto_merge_is_revoked_when_current_diff_is_no_longer_allowed(self):
        for state in ['clean', 'behind']:
            for file in [{'filename': 'README.md', 'status': 'modified'},
                         {'filename': 'requirements-dev.txt', 'status': 'removed'},
                         {'filename': 'requirements-dev.txt', 'status': 'renamed'}]:
                with self.subTest(state=state, file=file):
                    self.pr['mergeable_state'] = state
                    self.files = [file]
                    self.calls.clear()
                    maintenance.maintain_updates(self.path)
                    self.command.assert_called_with(['gh', 'pr', 'merge', '3', '--repo', maintenance.REPO,
                                                     '--disable-auto'], check=True)
                    self.assertFalse(any(method == 'PUT' for _, method, _ in self.calls))
        self.validation.assert_not_called()

    def test_current_draft_is_revoked_and_revoked_closed_or_changed_author_pr_is_skipped(self):
        original = deepcopy(self.pr)
        self.pr['draft'] = True
        maintenance.maintain_updates(self.path)
        self.command.assert_called_once()
        self.command.reset_mock()
        for fields in [{'auto_merge': None}, {'state': 'closed'}, {'user': {'login': 'human'}}]:
            with self.subTest(fields=fields):
                self.pr = {**original, **fields}
                maintenance.maintain_updates(self.path)
        self.command.assert_not_called()
        self.validation.assert_not_called()

    def test_missing_diff_files_prevent_branch_update(self):
        self.pr['changed_files'] = 2
        maintenance.maintain_updates(self.path)
        self.command.assert_called_once()
        self.validation.assert_not_called()
        self.assertFalse(any(method == 'PUT' for _, method, _ in self.calls))

    def test_bad_file_on_second_page_revokes_auto_merge(self):
        self.files = [{'filename': f'.github/workflows/job-{i}.yml', 'status': 'modified',
                       'patch': '- uses: actions/checkout@' + 'a'*40 + '\n+ uses: actions/checkout@' + 'b'*40}
                      for i in range(100)] + [{'filename': 'README.md', 'status': 'modified'}]
        self.pr['changed_files'] = len(self.files)
        maintenance.maintain_updates(self.path)
        self.assertIn((f'repos/{maintenance.REPO}/pulls/3/files?per_page=100&page=2', 'GET', None), self.calls)
        self.command.assert_called_once()
        self.validation.assert_not_called()

    def test_actions_diff_only_accepts_immutable_action_reference_changes(self):
        original = deepcopy(self.pr)
        for change in ['+ uses: actions/checkout@v6', '+ run: echo change', '+ permissions: write-all', '']:
            with self.subTest(change=change):
                self.pr = deepcopy(original)
                self.files = [{'filename': '.github/workflows/validate.yml', 'status': 'modified',
                               'patch': '- uses: actions/checkout@' + 'a'*40 + '\n' + change}]
                # A missing patch is independently rejected too.
                if not change:
                    self.files[0]['patch'] = ''
                maintenance.maintain_updates(self.path)
                self.command.assert_called()
        self.validation.assert_not_called()
        self.command.reset_mock()
        self.files[0]['patch'] = '- uses: actions/checkout@' + 'a'*40 + '\n+ uses: actions/checkout@' + 'b'*40
        maintenance.maintain_updates(self.path)
        self.command.assert_not_called()
        self.validation.assert_called_once()

    def test_generated_pr_is_limited_to_generated_evidence(self):
        self.pr['user']['login'] = 'github-actions[bot]'
        self.pr['head']['ref'] = maintenance.BRANCH
        for file in [{'filename': 'requirements-dev.txt', 'status': 'modified'},
                     {'filename': '.github/workflows/validate.yml', 'status': 'modified',
                      'patch': '+ uses: actions/checkout@' + 'b'*40}]:
            with self.subTest(file=file):
                self.files = [file]
                maintenance.maintain_updates(self.path)
                self.command.assert_called()
        self.validation.assert_not_called()
        self.command.reset_mock()
        self.files = [{'filename': 'automation/upstream-state.json', 'status': 'modified'}]
        maintenance.maintain_updates(self.path)
        self.command.assert_not_called()
        self.validation.assert_called_once_with(3, 'b'*40, maintenance.BRANCH, 'github-actions[bot]')

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
