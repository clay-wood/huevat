import json
import subprocess
import sys

import huevat


def test_import_without_optional_packages():
    script = """
import importlib.abc
import sys
class BlockOptional(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'numpy', 'scipy', 'matplotlib', 'PIL', 'playwright', 'sketchplot', 'colorcet', 'colorspacious'}:
            raise AssertionError('Unexpected optional import: ' + fullname)
sys.meta_path.insert(0, BlockOptional())
import huevat
assert huevat.to_hex(huevat.gamut_map((.5, .2, 30))).startswith('#')
assert len(huevat.references()) == 13
assert len(huevat.reference('okabe-ito').colors(8)) == 8
huevat.simulate((1, 0, 0), 'deutan', severity=50)
huevat.load_profile('filled-fields', 'dark')
g = huevat.sequential(background='dark')
assert g.report.screen_pass
assert len(g.discrete(7)) == 7
assert g.reversed().at(.25) == g.at(.75)
assert huevat.load_recipe(g.to_json()).at(.25) == g.at(.25)
assert huevat.diverging().report.screen_pass
for n in range(2, 60):
    try:
        g.discrete(n)
    except huevat.QualityError:
        pass
"""
    subprocess.run([sys.executable, "-I", "-c", script], check=True)


def test_version_and_stdlib_json_output():
    assert huevat.__version__ == "0.1.0.dev0"
    rgb = huevat.from_hex("#0072b2")
    assert tuple(json.loads(json.dumps(rgb))) == rgb
