"""Extract only reader files from a checksummed offline release, without modifying it."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def prepare(archive, destination, hosts=None):
    archive, destination = Path(archive), Path(destination)
    data = archive.read_bytes()
    expected = Path(str(archive) + '.sha256').read_text().split()[0]
    if digest(data) != expected:
        raise ValueError('Archive checksum mismatch')
    if destination.exists():
        raise ValueError('Destination already exists; use a new immutable directory')
    prefix = 'principia-legacy/'
    reader = {'__init__.py', 'common.py', 'records.py', 'storage.py', 'catalog.py', 'retrieval.py', 'works.py'}
    licenses = {'LICENSE', 'DATA_LICENSE.md', 'THIRD_PARTY_NOTICES.md', 'GOVERNANCE.md'}
    selected = {}
    with zipfile.ZipFile(archive) as z:
        checksums = json.loads(z.read(prefix + 'CHECKSUMS.json'))
        for name, expected_file in checksums.items():
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError('Unsafe archive path')
            content = z.read(prefix + name)
            if digest(content) != expected_file:
                raise ValueError('File checksum mismatch: ' + name)
            if (name == 'build/atlas.sqlite' or name.startswith('web_dist/')
                    or name in licenses or name.startswith('manifests/releases/')
                    or (name.startswith('src/principia_legacy/') and path.name in reader)):
                selected[name] = content
    for name, content in selected.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    dbpath = destination / 'build/atlas.sqlite'
    with sqlite3.connect(dbpath.resolve().as_uri() + '?mode=ro', uri=True) as db:
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('Database integrity check failed')
        release = db.execute("SELECT value FROM metadata WHERE key='current_release'").fetchone()[0]
        public = [r[0] for r in db.execute('SELECT id FROM snapshots ORDER BY id')
                  if re.fullmatch(r'\d+\.\d+\.\d+-exploratory', r[0])]
        if release not in public:
            raise ValueError('Archive default is not a published snapshot')
    config = {'default_release': release, 'public_releases': public,
              'hosts': hosts or ['localhost', '127.0.0.1'],
              'upstream_archive_sha256': expected}
    (destination / 'hosting.json').write_text(json.dumps(config, indent=2) + '\n')
    receipt = {name: digest(content) for name, content in selected.items()}
    receipt['hosting.json'] = digest((destination / 'hosting.json').read_bytes())
    (destination / 'HOSTING_CHECKSUMS.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'bundle': str(destination), **config, 'verified_source_files': len(checksums), 'hosted_files': len(selected)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archive')
    parser.add_argument('destination')
    parser.add_argument('--host', action='append', help='Allowed HTTP Host; repeat for each public hostname')
    args = parser.parse_args()
    prepare(args.archive, args.destination, args.host)
