"""Check wheel/sdist contents and clean, offline pip and uv base installs.

Run after `uv build`. This script never contacts a package index.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
from email.parser import BytesParser

ROOT = Path(__file__).resolve().parents[1]
SMOKE = """
import importlib.metadata as md
import json
import sys
import huevat as hv
assert hv.to_hex(hv.from_hex('#0072b2')) == '#0072b2'
assert hv.in_gamut(hv.gamut_map((.65, .4, 30)), tolerance=0)
assert abs(hv.contrast((0, 0, 0), (1, 1, 1)) - 21) < 1e-10
hv.simulate((1, 0, 0), 'protan')
for forbidden in ('numpy', 'scipy', 'matplotlib', 'PIL', 'playwright', 'sketchplot'):
    assert forbidden not in sys.modules, forbidden
    try:
        md.distribution(forbidden)
    except md.PackageNotFoundError:
        pass
    else:
        raise AssertionError('Unexpected installed dependency: ' + forbidden)
assert 'site-packages' in hv.__file__, hv.__file__
print(json.dumps({'version': hv.__version__, 'python': sys.version.split()[0]}))
"""


def run(args, cwd):
    result = subprocess.run([str(arg) for arg in args], cwd=cwd, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(f"Command failed: {args}\n{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def python_at(env):
    return env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def main():
    wheels = sorted((ROOT / "dist").glob("*.whl"))
    sdists = sorted((ROOT / "dist").glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit("Expected exactly one wheel and one sdist in dist/. Run uv build first.")
    wheel, sdist = wheels[0], sdists[0]
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        metadata = BytesParser().parsebytes(archive.read(next(n for n in names if n.endswith('.dist-info/METADATA'))))
        requirements = metadata.get_all("Requires-Dist", [])
        assert all("extra ==" in requirement for requirement in requirements), requirements
        assert set(metadata.get_all("Provides-Extra", [])) == {"design"}
        for filename in ("__init__.py", "space.py", "vision.py"):
            assert f"huevat/{filename}" in names
        for license_name in ("LICENSE", "sketchplot-MIT.txt", "colorspacious-MIT.txt"):
            assert any(n.endswith('/' + license_name) for n in names), license_name
        assert not any(any(part in n.lower() for part in
                           ('renderer', 'playwright', '.js', '.venv', 'sketchplot/')) for n in names)
    with tarfile.open(sdist) as archive:
        names = archive.getnames()
        for required in ("pyproject.toml", "uv.lock", "project_plan.md", "docs/extraction.json",
                         "tools/check_install.py", "tests/test_space.py"):
            assert any(n.endswith('/' + required) for n in names), required
    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit("uv is required to verify both installation workflows")
    records = {}
    with tempfile.TemporaryDirectory(prefix="huevat-install-") as temporary:
        work = Path(temporary)
        pip_env, uv_env = work / "pip-env", work / "uv-env"
        venv.EnvBuilder(with_pip=True).create(pip_env)
        run([python_at(pip_env), "-m", "pip", "install", "--no-index", "--no-deps", wheel], work)
        records["pip"] = json.loads(run([python_at(pip_env), "-I", "-c", SMOKE], work))
        run([uv, "venv", "--offline", "--python", sys.executable, uv_env], work)
        run([uv, "pip", "install", "--offline", "--no-deps", "--python", python_at(uv_env), wheel], work)
        records["uv"] = json.loads(run([python_at(uv_env), "-I", "-c", SMOKE], work))
    record = {
        "wheel": wheel.name, "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "sdist": sdist.name, "sdist_sha256": hashlib.sha256(sdist.read_bytes()).hexdigest(),
        "base_dependencies": [], "offline_clean_installs": records,
    }
    output = ROOT / "artifacts/install-check.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
