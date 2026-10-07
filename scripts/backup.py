"""Consistent SQLite snapshot plus its immutable referenced files and signing key.

Usage: python scripts/backup.py --destination /private/backups/new-directory
The destination must be new and must be kept private; it contains user data.
"""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--destination', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    data = Path(os.environ.get('AI_PN2_DATA_DIR', root.parent / 'ai-pn2-data')).resolve()
    destination = Path(args.destination).resolve()
    if destination == root or root in destination.parents or destination == data or data in destination.parents:
        raise SystemExit('Backup must be outside the Git checkout and active data directory.')
    os.umask(0o077)
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    original = sqlite3.connect((data / 'db.sqlite3').as_uri() + '?mode=ro', uri=True)
    snapshot = sqlite3.connect(destination / 'db.sqlite3')
    try:
        original.backup(snapshot)
        names = [r[0] for r in snapshot.execute('SELECT storage_name FROM projects_drawing')]
        directories = [r[0] for r in snapshot.execute("SELECT artifact_dir FROM projects_job WHERE status='succeeded' AND artifact_dir != ''")]
        (destination / 'files').mkdir(mode=0o700)
        file_root = (data / 'files').resolve()
        for name in names + directories:
            source = (file_root / name).resolve()
            if file_root not in source.parents:
                raise RuntimeError('Invalid stored file path')
            target = destination / 'files' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
        key = data / 'django-secret-key'
        if key.exists():
            shutil.copy2(key, destination / 'django-secret-key')
        elif not os.environ.get('AI_PN2_SECRET_KEY'):
            raise RuntimeError('No signing key available')
    finally:
        original.close(); snapshot.close()
    manifest = {}
    for path in sorted(destination.rglob('*')):
        if path.is_file():
            checksum = hashlib.sha256()
            with path.open('rb') as file:
                for chunk in iter(lambda: file.read(65536), b''):
                    checksum.update(chunk)
            manifest[str(path.relative_to(destination))] = checksum.hexdigest()
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(f'Backup completed: {destination}. Keep private and copy to separate durable storage.')


if __name__ == '__main__':
    main()
