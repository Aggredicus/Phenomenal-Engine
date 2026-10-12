import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zlib

from phenomenal_engine.github_saves import encode_state, decode_state, GitHubSaveError
from phenomenal_engine.memory import new_memory, append_event, load_memory, verify_ledger
from phenomenal_engine.mod_loader import load_mod


class LedgerArchiveTests(unittest.TestCase):
    def setUp(self):
        self.memory = new_memory(load_mod('mods/mirror_delivery.json'), 'archive-fixture')
        for _ in range(18):
            append_event(self.memory, 'fixture_record', {'text': 'recorded history ' * 2500})

    def test_large_ledger_roundtrips_every_event_and_hash(self):
        before = copy.deepcopy(self.memory)
        raw = encode_state(self.memory)
        packed = json.loads(raw)
        self.assertIn('event_ledger_archive', packed)
        self.assertEqual(len(packed['event_ledger']), 1)
        revived = decode_state(raw)
        self.assertEqual(revived, before)
        self.assertEqual(self.memory, before)
        self.assertTrue(verify_ledger(revived))
        self.assertEqual(encode_state(revived), raw)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'campaign.json'
            path.write_bytes(raw)
            self.assertEqual(load_memory(path)['event_ledger'], before['event_ledger'])

    def test_archive_metadata_and_bounded_decompression_are_enforced(self):
        baseline = json.loads(encode_state(self.memory))
        for field, value in [('expanded_bytes', 10), ('expanded_bytes', 64_000_001),
                             ('event_count', 9999), ('sha256', '0' * 64), ('codec', 'other')]:
            candidate = copy.deepcopy(baseline)
            candidate['event_ledger_archive'][field] = value
            with self.assertRaises(GitHubSaveError):
                decode_state(json.dumps(candidate).encode())
        candidate = copy.deepcopy(baseline)
        candidate['event_ledger_archive']['data'] += '!!!'
        with self.assertRaises(GitHubSaveError):decode_state(json.dumps(candidate).encode())

    def test_archive_digest_does_not_replace_event_hash_verification(self):
        candidate = json.loads(encode_state(self.memory))
        archive = candidate['event_ledger_archive']
        events = json.loads(zlib.decompress(base64.b64decode(archive['data'])))
        events[0]['payload']['changed'] = True
        raw = json.dumps(events, separators=(',', ':'), ensure_ascii=False).encode()
        archive.update(data=base64.b64encode(zlib.compress(raw)).decode(),
                       expanded_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaisesRegex(GitHubSaveError, 'ledger'):
            decode_state(json.dumps(candidate).encode())

    def test_credentials_are_scanned_before_history_is_compressed(self):
        append_event(self.memory, 'fixture_record', {'text': 'ghp_' + 'A' * 30})
        append_event(self.memory, 'fixture_record', {'text': 'newest safe record'})
        with self.assertRaisesRegex(GitHubSaveError, 'credential'):encode_state(self.memory)


if __name__ == '__main__':unittest.main()
