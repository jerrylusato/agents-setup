import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from agents_setup_cli.resolve import resolve, validate_request


class ResolveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.archive = self.root / 'skills.tar.gz'
        self.request = {'schema_version': 1, 'source': {
            'repository': 'iPFSoftwares/skills', 'version': 'v1.0.0', 'archive_sha256': '0' * 64,
        }, 'skills': ['backend/review/example']}
        self.entry = {'name': 'example', 'department': 'backend', 'group': 'review',
                      'path': 'skills/backend/review/example/SKILL.md'}
        self.files = {
            'catalog.json': json.dumps([self.entry]),
            self.entry['path']: '---\nname: example\ndepartment: backend\ngroup: review\n---\nReview instructions.\n',
            'skills/backend/review/example/references/case.md': 'Evidence example.\n',
        }

    def build(self, special=None):
        with tarfile.open(self.archive, 'w:gz') as bundle:
            for name, content in self.files.items():
                data = content.encode()
                item = tarfile.TarInfo('ipf-skills-v1.0.0/' + name)
                item.size = len(data)
                bundle.addfile(item, io.BytesIO(data))
            if special:
                bundle.addfile(special)
        self.request['source']['archive_sha256'] = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        path = self.root / 'request.json'
        path.write_text(json.dumps(self.request))
        return path

    def test_resolves_exact_packages_and_resources_without_user_state(self):
        manifest = self.build()
        output = self.root / 'output'
        with patch('agents_setup_cli.skills.install_skill', side_effect=AssertionError('user install called')):
            result = resolve(manifest, output, self.archive)
        self.assertTrue((output / 'skills/backend/review/example/references/case.md').is_file())
        self.assertEqual(result, json.loads((output / 'resolved.json').read_text()))
        self.assertEqual(len(result['skills'][0]['sha256']), 64)
        self.assertEqual(sorted(p.name for p in output.iterdir()), ['resolved.json', 'skills'])

    def test_checksum_failure_leaves_no_destination(self):
        manifest = self.build()
        self.archive.write_bytes(self.archive.read_bytes() + b'tampered')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            resolve(manifest, self.root / 'output', self.archive)
        self.assertFalse((self.root / 'output').exists())

    def test_existing_destination_is_not_replaced(self):
        manifest = self.build()
        output = self.root / 'output'
        output.mkdir()
        (output / 'keep').write_text('owned by somebody else')
        with self.assertRaisesRegex(ValueError, 'must not already exist'):
            resolve(manifest, output, self.archive)
        self.assertEqual((output / 'keep').read_text(), 'owned by somebody else')

    def test_mutable_sources_and_escaping_ids_are_rejected(self):
        for field, value in (('version', 'latest'), ('version', 'main'), ('archive_sha256', 'missing')):
            with self.subTest(field=field, value=value):
                request = json.loads(json.dumps(self.request))
                request['source'][field] = value
                with self.assertRaises(ValueError):
                    validate_request(request)
        self.request['skills'] = ['../escape']
        with self.assertRaises(ValueError):
            validate_request(self.request)

    def test_missing_skill_or_dependency_is_rejected(self):
        self.entry['dependencies'] = ['backend/review/missing']
        self.files['catalog.json'] = json.dumps([self.entry])
        manifest = self.build()
        with self.assertRaisesRegex(ValueError, 'Unselected skill dependency'):
            resolve(manifest, self.root / 'output', self.archive)
        self.assertFalse((self.root / 'output').exists())

    def test_catalog_cannot_rename_or_redirect_skill(self):
        self.files[self.entry['path']] = self.files[self.entry['path']].replace('name: example', 'name: other')
        manifest = self.build()
        with self.assertRaisesRegex(ValueError, 'metadata differs'):
            resolve(manifest, self.root / 'output', self.archive)

    def test_links_special_files_and_traversal_are_rejected(self):
        for kind, name in ((tarfile.SYMTYPE, 'ipf-skills-v1.0.0/link'),
                           (tarfile.FIFOTYPE, 'ipf-skills-v1.0.0/fifo'),
                           (tarfile.REGTYPE, '../escaped')):
            with self.subTest(kind=kind):
                special = tarfile.TarInfo(name)
                special.type = kind
                special.linkname = '/etc/passwd' if kind == tarfile.SYMTYPE else ''
                manifest = self.build(special)
                with self.assertRaises((ValueError, SystemExit)):
                    resolve(manifest, self.root / 'output', self.archive)
                self.assertFalse((self.root / 'output').exists())
                self.assertFalse((self.root / 'escaped').exists())

    def test_duplicate_json_keys_are_rejected(self):
        manifest = self.root / 'request.json'
        manifest.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            resolve(manifest, self.root / 'output', self.archive)
