"""Entirely synthetic inputs; no catalog acquisition or imported fixtures."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'scripts' / 'stage_snapshot.py'
spec = importlib.util.spec_from_file_location('stage_snapshot', MODULE)
stager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stager)


def sample():
    return {
        'format': 'public-chatgpt-directory-export', 'version': 1,
        'source_type': 'official_public_chatgpt_directory',
        'issued_at': '2026-10-18T12:00:00Z',
        'terms_ref': 'synthetic:terms', 'verification_proof_ref': 'synthetic:review',
        'records': [
            {'id': 'plugin_synthetic_a', 'name': ' Synthetic Alpha ',
             'description': ' Synthetic description ', 'verified_public': True,
             'source_url': 'https://chatgpt.com/plugins/plugin_synthetic_a'},
            {'id': 'plugin_synthetic_b', 'name': 'Synthetic Beta',
             'verified_public': True,
             'source_url': 'https://chatgpt.com/plugins/plugin_synthetic_b'}]}


class SnapshotTests(unittest.TestCase):
    def test_valid_and_stable(self):
        first = sample()
        result = stager.validate(first)
        self.assertEqual({item['id']: item['name'] for item in result['entries']}['plugin_synthetic_a'], 'Synthetic Alpha')
        self.assertEqual(result['counts'], {'entries': 2, 'with_description': 1})
        self.assertFalse(result['publication_authorized'])
        self.assertTrue(all(e['claimed_public'] is True and 'verified_public' not in e for e in result['entries']))
        self.assertEqual(result['source']['verification_status'], 'unverified_claims')
        first['records'].reverse()
        self.assertEqual(stager.canonical(result), stager.canonical(stager.validate(first)))
        payload = {k: v for k, v in result.items() if k != 'sha256'}
        self.assertEqual(result['sha256'], hashlib.sha256(stager.canonical(payload)).hexdigest())

    def test_reject_invalid_entire_input(self):
        cases = []
        for key, value in [('source_type', 'account_visible_private'),
                           ('source_type', 'codex_app_list'), ('source_type', 'mcptop'),
                           ('source_type', 'third_party_scrape'), ('terms_ref', ''),
                           ('verification_proof_ref', ''), ('version', True),
                           ('issued_at', '2026-02-30T00:00:00Z'), ('auth_token', 'secret')]:
            item = sample(); item[key] = value; cases.append(item)
        for key, value in [('id', '../bad'), ('id', 'plugin-with-hyphen'), ('verified_public', False),
                           ('verified_public', 1), ('name', 'bad\nname'),
                           ('description', '\u202eevil'), ('name', 'x' * 201),
                           ('name', 'bad\u2028line'), ('name', 'bad\u2029line'),
                           ('cookie', 'secret'), ('source_url', 'https://evil.test/apps/plugin_synthetic_b'),
                           ('source_url', 'https://chatgpt.com/plugins/plugin-other'),
                           ('source_url', 'https://chatgpt.com/apps/plugin_synthetic_b'),
                           ('source_url', 'https://chatgpt.com/plugins/plugin_synthetic_b/'),
                           ('source_url', 'http://chatgpt.com/plugins/plugin_synthetic_b'),
                           ('source_url', 'https://CHATGPT.com/plugins/plugin_synthetic_b'),
                           ('source_url', 'https://chatgpt.com/plugins/plugin_synthetic_b#part'),
                           ('source_url', 'https://chatgpt.com/plugins/plugin_synthetic_b?token=x')]:
            item = sample(); item['records'][1][key] = value; cases.append(item)
        item = sample(); item['records'].append(copy.deepcopy(item['records'][0])); cases.append(item)
        item = sample(); del item['terms_ref']; cases.append(item)
        item = sample(); item['records'] *= stager.MAX_RECORDS; cases.append(item)
        for item in cases:
            with self.subTest(item=item), self.assertRaises(ValueError):
                stager.validate(item)

    def test_id_bounds_and_unicode_exclusions(self):
        for identifier in ('a' * 6, 'a' * 120, 'test_~id'):
            item = sample()
            item['records'][0]['id'] = identifier
            item['records'][0]['source_url'] = 'https://chatgpt.com/plugins/' + identifier
            self.assertEqual(stager.validate(item)['counts']['entries'], 2)
        for identifier in ('a' * 5, 'a' * 121, '١' * 6, 'bad-hyphen'):
            item = sample()
            item['records'][0]['id'] = identifier
            item['records'][0]['source_url'] = 'https://chatgpt.com/plugins/' + identifier
            with self.assertRaises(ValueError):
                stager.validate(item)

    def test_fifo_input_rejected_without_blocking(self):
        import os
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'input.fifo'
            os.mkfifo(path)
            with self.assertRaisesRegex(ValueError, 'regular file'):
                stager.stage(path, Path(td) / 'stage.json')

    def test_zero_records(self):
        item = sample(); item['records'] = []
        self.assertEqual(stager.validate(item)['counts'], {'entries': 0, 'with_description': 0})

    def test_atomic_staging_and_preservation(self):
        with tempfile.TemporaryDirectory() as td:
            source, output = Path(td) / 'input.json', Path(td) / 'stage.json'
            source.write_text(json.dumps(sample()))
            stager.stage(source, output)
            original = output.read_bytes()
            self.assertEqual(original, stager.canonical(json.loads(original)))
            stager.stage(source, output)
            self.assertEqual(output.read_bytes(), original)
            for operation in ('replace', 'fsync'):
                with patch.object(stager.os, operation, side_effect=OSError('write failure')):
                    with self.assertRaises(OSError):
                        stager.stage(source, output)
                self.assertEqual(output.read_bytes(), original)
            self.assertEqual(sorted(p.name for p in Path(td).iterdir()), ['input.json', 'stage.json'])
            for raw in ['{"format":1,"format":2}', '{', json.dumps({'auth': 'secret'}),
                        ' ' * (stager.MAX_BYTES + 1)]:
                source.write_text(raw)
                with self.assertRaises(ValueError):
                    stager.stage(source, output)
                self.assertEqual(output.read_bytes(), original)
            source.write_text(json.dumps(sample()))
            with self.assertRaises(ValueError):
                stager.stage(source, source)

    def test_cli_reports_counts_only_and_fails_safely(self):
        with tempfile.TemporaryDirectory() as td:
            source, output = Path(td) / 'in.json', Path(td) / 'out.json'
            source.write_text(json.dumps(sample()))
            result = subprocess.run([sys.executable, str(MODULE), '--input', str(source),
                                     '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['counts']['entries'], 2)
            source.write_text('{"auth_token":"do-not-echo"}')
            result = subprocess.run([sys.executable, str(MODULE), '--input', str(source),
                                     '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('do-not-echo', result.stderr)
