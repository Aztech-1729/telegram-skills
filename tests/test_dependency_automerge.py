"""Execute the trusted workflow's inline gates against mocked GitHub snapshots."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import yaml


REPO = 'Aztech-1729/telegram-skills'
SHA = 'a' * 40
WORKFLOW = yaml.safe_load((Path(__file__).resolve().parents[1] /
                          '.github/workflows/dependabot-automerge.yml').read_text(encoding='utf-8'))
STEPS = WORKFLOW['jobs']['enable']['steps']


class DependencyGateTests(unittest.TestCase):
    def setUp(self):
        self.pr = {'number': 7, 'head': {'sha': SHA, 'repo': {'full_name': REPO}},
                   'base': {'ref': 'main'}, 'user': {'login': 'dependabot[bot]'},
                   'state': 'open', 'draft': False, 'auto_merge': {'merge_method': 'squash'},
                   'changed_files': 1}
        self.protection = {'protected': True, 'protection': {
            'required_status_checks': {'contexts': ['validation']}}}
        self.files = [{'filename': 'requirements-dev.txt', 'status': 'modified'}]
        self.command = self.enterContext(patch.object(subprocess, 'run'))
        self.enterContext(patch.object(subprocess, 'check_output', side_effect=self.api))
        self.enterContext(patch.dict(os.environ, {
            'REPOSITORY': REPO, 'PR_NUMBER': '7', 'EXPECTED_SHA': SHA,
        }))

    def api(self, command):
        self.assertEqual(command[:2], ['gh', 'api'])
        path = command[2]
        if path == f'repos/{REPO}/pulls/7':
            return json.dumps(self.pr).encode()
        if path == f'repos/{REPO}/branches/main':
            return json.dumps(self.protection).encode()
        if f'repos/{REPO}/pulls/7/files?' in path:
            page = int(path.rsplit('=', 1)[1])
            return json.dumps(self.files[(page-1)*100:page*100]).encode()
        raise AssertionError(path)

    def run_step(self, index):
        exec(compile(STEPS[index]['run'], STEPS[index]['name'], 'exec'), {})

    def test_existing_auto_merge_is_revoked_before_metadata_or_file_checks(self):
        self.run_step(0)
        self.command.assert_called_once_with(['gh', 'pr', 'merge', '7', '--repo', REPO,
                                             '--disable-auto'], check=True)
        self.assertNotIn('if', STEPS[0])
        self.assertEqual(STEPS[1]['id'], 'metadata')
        eligibility = STEPS[2]['if']
        self.assertIn('version-update:semver-patch', eligibility)
        self.assertIn('version-update:semver-minor', eligibility)
        self.assertIn("maintainer-changes != 'true'", eligibility)
        self.assertNotIn('semver-major', eligibility)

    def test_draft_or_changed_base_still_revokes_before_metadata_is_skipped(self):
        for fields in [{'draft': True}, {'base': {'ref': 'other'}}]:
            with self.subTest(fields=fields):
                self.pr.update(fields)
                self.run_step(0)
                self.command.assert_called_with(['gh', 'pr', 'merge', '7', '--repo', REPO,
                                                '--disable-auto'], check=True)
        self.assertIn('!github.event.pull_request.draft', STEPS[1]['if'])
        self.assertIn('default_branch', STEPS[1]['if'])

    def test_stale_foreign_or_already_revoked_snapshot_is_not_revoked_again(self):
        original = deepcopy(self.pr)
        for fields in [{'head': {**original['head'], 'sha': 'b'*40}},
                       {'user': {'login': 'human'}}, {'state': 'closed'}, {'auto_merge': None}]:
            with self.subTest(fields=fields):
                self.pr = {**original, **fields}
                self.run_step(0)
        self.command.assert_not_called()

    def test_current_allowed_head_enables_only_protected_exact_head_auto_merge(self):
        self.run_step(2)
        self.command.assert_called_once_with(['gh', 'pr', 'merge', '7', '--repo', REPO,
                                             '--auto', '--squash', '--match-head-commit', SHA], check=True)

    def test_unprotected_missing_validation_or_explicit_nonstrict_branch_cannot_enable(self):
        for protection in [{'protected': False}, {'protected': True},
                           {'protected': True, 'protection': {'required_status_checks': {'contexts': ['lint']}}},
                           {'protected': True, 'protection': {'required_status_checks': {
                               'contexts': ['validation'], 'strict': False}}}]:
            with self.subTest(protection=protection):
                self.protection = protection
                self.run_step(0)
                self.command.reset_mock()
                with self.assertRaisesRegex(AssertionError, 'validation gate'):
                    self.run_step(2)
                self.command.assert_not_called()

    def test_unauthorized_file_operations_paths_or_incomplete_diff_remain_revoked(self):
        for file in [{'filename': 'README.md', 'status': 'modified'},
                     {'filename': 'requirements-dev.txt', 'status': 'removed'},
                     {'filename': 'requirements-dev.txt', 'status': 'renamed'},
                     {'filename': '.github/workflows/validate.yml', 'status': 'added',
                      'patch': '+ uses: actions/checkout@' + SHA},
                     {'filename': '.github/workflows/validate.yml', 'status': 'modified',
                      'patch': '+ run: echo change'},
                     {'filename': '.github/workflows/validate.yml', 'status': 'modified',
                      'patch': '+ uses: actions/checkout@v6'},
                     {'filename': '.github/workflows/validate.yml', 'status': 'modified'}]:
            with self.subTest(file=file):
                self.files = [file]
                self.run_step(0)
                self.command.reset_mock()
                with self.assertRaises(AssertionError):
                    self.run_step(2)
                self.command.assert_not_called()
        self.files = [{'filename': 'requirements-dev.txt', 'status': 'modified'}]
        self.pr['changed_files'] = 2
        with self.assertRaises(AssertionError):
            self.run_step(2)
        self.command.assert_not_called()

    def test_actions_patch_only_accepts_immutable_action_reference_lines(self):
        self.files = [{'filename': '.github/workflows/validate.yml', 'status': 'modified',
                       'patch': '- uses: actions/checkout@' + SHA + '\n+ uses: actions/checkout@' + 'b'*40}]
        self.run_step(2)
        self.command.assert_called_once()


if __name__ == '__main__':
    unittest.main()
