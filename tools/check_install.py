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
hv.simulate((1, 0, 0), 'deutan', severity=53.1)
assert len(hv.references()) == 13
assert hv.to_hex(hv.reference('okabe-ito').colors(8)[0]) == '#000000'
assert hv.load_profile('filled-fields', 'dark')['background'] == '#121212'
gradient = hv.diverging(background='dark')
assert gradient.report.screen_pass
assert len(gradient.discrete(7)) == 7
assert hv.load_recipe(gradient.to_json()).at(.25) == gradient.at(.25)
palette = hv.categorical(8, background='dark')
assert len(palette) == 8 and palette.report.screen_pass
assert palette.report['style'] == 'clearer'
assert hv.load_recipe(palette.to_json()).colors == palette.colors
assert hv.categorical(6, style='max-separation').report.screen_pass
for factory in (hv.multihue, hv.spectral):
    gradient = factory(background='dark')
    assert gradient.report.screen_pass
    assert hv.load_recipe(gradient.to_json()).at(.25) == gradient.at(.25)
    assert gradient.reversed().at(.25) == gradient.at(.75)
import huevat.adapters.matplotlib
import huevat.adapters.plotly
import huevat.adapters.ultraplot
from huevat import doctor
assert doctor.__all__
assert len(hv.gradient_names()) == 12
assert hv.__version__ == md.version('huevat') == '0.1.0'
assert len(hv.design_ids()) == 76
assert len(hv.design_ids(role='default')) == 30
for identifier in hv.design_ids():
    design = hv.get_design(identifier)
    loaded = hv.load_export(hv.export(design)).design
    if isinstance(design, hv.Gradient):
        assert loaded.at(.37) == design.at(.37)
    else:
        assert loaded.colors == design.colors
assert hv.load_export(hv.export(hv.diverging(), n=7)).design.colors == hv.diverging().discrete(7).colors
assert hv.nearby_counts(hv.diverging(), 8)[:2] == (7, 9)
assert hv.export(hv.categorical(4), format='csv').text.startswith('index,label,position,hex,r,g,b')
assert hv.gradient_info('highland')['orientation'] == 'elevation-lightens'
for name in hv.gradient_names():
    for background in ('light', 'dark'):
        gradient = hv.gradient(name, background=background)
        assert gradient.report.screen_pass
        assert hv.load_recipe(gradient.to_recipe()).at(.3) == gradient.at(.3)
        assert hv.known_counts(gradient)
try:
    hv.optimized_discrete(hv.sequential(), 10000)
except hv.ConstraintConflictError:
    pass
else:
    raise AssertionError('Expected a dependency-free fixed-path count bound')
for forbidden in ('numpy', 'scipy', 'matplotlib', 'plotly', 'ultraplot', 'PIL', 'playwright', 'sketchplot', 'colorspacious', 'colorcet'):
    assert forbidden not in sys.modules, forbidden
    try:
        md.distribution('pillow' if forbidden == 'PIL' else forbidden)
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
        assert set(metadata.get_all("Provides-Extra", [])) == {"design", "research", "matplotlib", "plotly", "ultraplot"}
        for filename in ("__init__.py", "space.py", "vision.py"):
            assert f"huevat/{filename}" in names
        for filename in ("library.py", "exports.py", "_prepared.py"):
            assert f"huevat/{filename}" in names
        for filename in ("matplotlib.py", "plotly.py", "ultraplot.py"):
            assert f"huevat/adapters/{filename}" in names
        for filename in ("__init__.py", "_backends.py", "_audit.py", "_search.py"):
            assert f"huevat/doctor/{filename}" in names
        for filename in ("references-v1.json", "profiles-v1.json", "machado-v1.json", "manifest-v1.json", "ordered-v1.json", "families-v1.json", "categorical-v2.json", "collection-v1.json", "release-v1.json"):
            assert f"huevat/data/{filename}" in names
        for license_name in ("LICENSE", "sketchplot-MIT.txt", "colorspacious-MIT.txt"):
            assert any(n.endswith('/' + license_name) for n in names), license_name
        assert not any(any(part in n.lower() for part in
                           ('renderer', 'playwright', '.venv', 'sketchplot/')) or n.endswith('.js') for n in names)
    with tarfile.open(sdist) as archive:
        names = archive.getnames()
        allowed_tests={'test_space.py','test_core.py','test_release.py','test_doctor.py'}
        assert all(Path(n).name in allowed_tests for n in names if '/tests/' in n and n.endswith('.py'))
        assert not any('/research/' in n or '/artifacts/' in n for n in names)
        assert not any(n.endswith(('/MIGRATION.md', '/MAINTENANCE.md', '/TECHNICAL_STATUS.md',
                                   '/PROJECT_REVIEW.md', '/NEXT_STEPS.md', '/profile_runtime.py'))
                       for n in names)
        for required in ("pyproject.toml", "uv.lock", "project_plan.md", "docs/extraction.json",
                         "tools/check_install.py", "tests/test_space.py", "examples/quickstart.py",
                         "docs/QUICKSTART.md", "examples/README.md", "examples/gallery.py",
                         "docs/images/palettes.png", "docs/images/gradients.png"):
            assert any(n.endswith('/' + required) for n in names), required
    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit("uv is required to verify both installation workflows")
    records = {}
    with tempfile.TemporaryDirectory(prefix="huevat-install-") as temporary:
        work = Path(temporary)
        pip_env, uv_env = work / "pip-env", work / "uv-env"
        # uv preserves the managed interpreter's library paths on all platforms.
        # Install with development pip into this otherwise empty environment.
        run([uv, "venv", "--offline", "--python", sys.executable, pip_env], work)
        run([sys.executable, "-m", "pip", "--python", python_at(pip_env),
             "install", "--no-index", "--no-deps", wheel], work)
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
