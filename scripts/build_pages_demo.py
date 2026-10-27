"""Build a static Pages artifact from shared UI and allowlisted Python sources."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'backend/src/kairos'
PYODIDE_VERSION = '0.28.3'
CDN = f'https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/'
CORE_FILES = [
    '__init__.py', 'contracts.py', 'i18n.py', 'tools.py', 'workflow.py',
    'models/__init__.py', 'models/event.py', 'models/actions.py',
    'models/guidance.py', 'models/session.py', 'locales/messages.json',
    'demo/__init__.py', 'demo/provider.py', 'demo/scenarios.py', 'demo/runtime.py',
]


def build(output: Path, cache: Path):
    if output.resolve() == ROOT or ROOT in output.resolve().parents and output.resolve() == SOURCE:
        raise ValueError('Output must be a dedicated build directory')
    output.mkdir(parents=True, exist_ok=True)
    # Only explicitly selected assets are publishable; no env files, real adapters, SQL or logs.
    static = output / 'static'
    if static.exists():
        shutil.rmtree(static)
    static.mkdir()
    html = (SOURCE / 'static/index.html').read_text()
    html = re.sub(r'<!-- LIVE:[A-Z]+ -->.*?<!-- /LIVE:[A-Z]+ -->', '', html, flags=re.S)
    html = html.replace('data-mode="live"', 'data-mode="demo"')
    html = html.replace('>Ambiente locale<', '>Demo simulata<')
    (output / 'index.html').write_text(html)
    (output / '.nojekyll').touch()
    for name in ('playground.css', 'playground.js', 'kairos-logo.png'):
        shutil.copy2(SOURCE / 'static' / name, static / name)
    for name in ('ui', 'demo'):
        shutil.copytree(SOURCE / 'static' / name, static / name)
    # Diagnostics and real HTTP transport are not part of the public artifact.
    (static / 'ui/diagnostics.js').unlink(missing_ok=True)
    (static / 'playground-config.json').write_text(json.dumps({'mode': 'demo'}))
    python = static / 'demo/python'
    for name in CORE_FILES:
        target = python / 'kairos' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE / name, target)
    (python / 'manifest.json').write_text(json.dumps({'files': [f'kairos/{name}' for name in CORE_FILES]}))
    cache.mkdir(parents=True, exist_ok=True)
    vendor = static / 'demo/vendor/pyodide'
    vendor.mkdir(parents=True)

    def download(name, expected=None):
        file = cache / name
        if not file.exists() or (expected and sha256(file.read_bytes()).hexdigest() != expected):
            with urlopen(CDN + name, timeout=120) as response:
                content = response.read()
            if expected and sha256(content).hexdigest() != expected:
                raise ValueError(f'Package integrity check failed: {name}')
            file.write_bytes(content)
        shutil.copy2(file, vendor / name)
        return file

    lock = json.loads(download('pyodide-lock.json').read_text())
    for name in ('pyodide.mjs', 'pyodide.asm.js', 'pyodide.asm.wasm', 'python_stdlib.zip'):
        download(name)
    included = set()

    def package(name):
        name = re.sub(r'[-_.]+', '-', name).lower()
        if name in included:
            return
        included.add(name)
        item = lock['packages'][name]
        for dependency in item['depends']:
            package(dependency)
        download(item['file_name'], item['sha256'])

    package('pydantic')
    package('tzdata')
    print(f'Built {output}: shared Python workflow + {len(included)} runtime packages; no live API credentials.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/pages')
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/pyodide' / PYODIDE_VERSION)
    args = parser.parse_args()
    build(args.output, args.cache)
