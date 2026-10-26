"""Verify index hashes and install the uploaded base wheel in a clean environment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from check_install import SMOKE

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True, choices=('testpypi', 'pypi'))
    parser.add_argument('--version', required=True)
    parser.add_argument('--dist-dir', type=Path, default=ROOT/'dist')
    args = parser.parse_args()
    host = 'test.pypi.org' if args.repository == 'testpypi' else 'pypi.org'
    endpoint = f'https://{host}/pypi/huevat/{args.version}/json'
    for attempt in range(8):
        try:
            with urllib.request.urlopen(endpoint, timeout=20) as response:
                release = json.load(response)
            break
        except urllib.error.HTTPError as error:
            if error.code != 404 or attempt == 7:
                raise
            time.sleep(min(2**attempt, 8))
    remote = {item['filename']: item['digests']['sha256'] for item in release['urls']}
    distributions = [*args.dist_dir.glob('*.whl'), *args.dist_dir.glob('*.tar.gz')]
    assert len(distributions) == 2, 'Expected one wheel and one source archive'
    for path in distributions:
        assert remote.get(path.name) == hashlib.sha256(path.read_bytes()).hexdigest(), path.name
    with tempfile.TemporaryDirectory(prefix='huevat-index-') as temporary:
        work = Path(temporary)
        prefix = work/'env'
        python = prefix/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        subprocess.run(['uv','venv','--offline','--python',sys.executable,str(prefix)],check=True)
        subprocess.run(['uv','pip','install','--python',str(python),
                        '--default-index',f'https://{host}/simple/', '--no-deps',
                        '--only-binary',':all:',f'huevat=={args.version}'],cwd=work,check=True)
        subprocess.run([str(python),'-I','-c',SMOKE],cwd=work,check=True)
    print(json.dumps({'repository':args.repository,'version':args.version,
                      'verified_files':sorted(path.name for path in distributions),
                      'installation':'passed','sha256':'matched exact built artifacts'}))


if __name__ == '__main__':
    main()
