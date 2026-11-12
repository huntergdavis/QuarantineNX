#!/usr/bin/env python3
"""Check that preparation refuses overwrites and edits are transactional."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parent.parent
upstream = root / 'work/upstream'
files = [
    'runtime/disc.h', 'runtime/rt_config.c', 'runtime/rt_core.c',
    'runtime/rt_disc.c', 'runtime/rt_launcher.c', 'runtime/rt_sys.c',
    'runtime/rt_cd.c', 'runtime/rt_snd.c', 'runtime/sys.h',
]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

# The second invocation must fail without changing an existing checkout.
protected = upstream / 'runtime/rt_sys.c'
before = digest(protected)
result = subprocess.run([str(root / 'prepare.sh')], cwd=root, capture_output=True, text=True)
assert result.returncode != 0 and 'Refusing to replace existing' in result.stderr
assert digest(protected) == before

# Start with exact original inputs, corrupt the last, and verify no partial writes.
scratch = root / 'build'
scratch.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='transform-guard-', dir=scratch) as temp:
    target = Path(temp)
    for name in files:
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(subprocess.check_output(['git', '-C', str(upstream), 'show', 'HEAD:' + name]))
    (target / files[-1]).write_bytes((target / files[-1]).read_bytes() + b'\ncorrupt\n')
    before = {name: digest(target / name) for name in files}
    result = subprocess.run([sys.executable, str(root / 'tools/apply_switch.py'), str(target)], capture_output=True, text=True)
    assert result.returncode != 0 and 'unexpected input' in result.stderr
    assert {name: digest(target / name) for name in files} == before
print('Preparation overwrite and transactional input guards passed')
