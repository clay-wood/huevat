"""Install a built wheel in an isolated environment for each optional extra."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MINIMUM = {
    "design": ["numpy==1.24.0", "scipy==1.10.0", "colorspacious==1.1.2"],
    "research": ["numpy==1.24.0", "scipy==1.10.0", "matplotlib==3.8.0", "colorspacious==1.1.2", "colorcet==3.2.1"],
    "matplotlib": ["matplotlib==3.9.0"],
    "plotly": ["plotly==6.0.0"],
    "ultraplot": ["ultraplot==2.7.0"],
}
SMOKE = r'''
import importlib.metadata as md
import importlib.util
import json
import sys
import huevat as hv
extra = sys.argv[1]
assert 'site-packages' in hv.__file__, hv.__file__
assert hv.__version__ == md.version('huevat')
g = hv.diverging()
p = g.discrete()
assert len(p) == 9 and p.colors[4] == hv.to_hex(g.at(.5))
assert len(hv.gradient_names()) == 18
assert len(hv.design_ids(role='collection')) == 36
assert hv.load_export(hv.export(g, n=9)).design.colors == p.colors
allowed = {
 'design': {'numpy','scipy','colorspacious'},
 'research': {'numpy','scipy','colorspacious','matplotlib','colorcet'},
 'matplotlib': {'numpy','matplotlib'},
 'plotly': {'plotly'},
 'ultraplot': {'numpy','matplotlib','ultraplot'},
}[extra]
for module in {'numpy','scipy','colorspacious','matplotlib','colorcet','plotly','ultraplot'} - allowed:
 assert importlib.util.find_spec(module) is None, ('unrequested dependency', module)
if extra == 'design':
 selected = hv.optimized_discrete(g, 8, max_seconds=30)
 assert len(selected) == 8 and selected.report.screen_pass
elif extra == 'research':
 from huevat.evaluation import evaluate
 from huevat.design import validate_gradient
 result = evaluate([g.at(i/64) for i in range(65)], 'diverging')
 assert len(result['conditions']) == 8
 assert validate_gradient(g)['screen_pass']
elif extra in ('matplotlib','ultraplot'):
 import matplotlib
 matplotlib.use('Agg')
 if extra == 'matplotlib':
  import matplotlib.pyplot as plt
  from huevat.adapters import matplotlib as adapter
  fig, ax = plt.subplots()
  kwargs = {}
 else:
  import ultraplot as plt
  from huevat.adapters import ultraplot as adapter
  fig, ax = plt.subplots()
  kwargs = {'discrete': False}
 cmap = adapter.colormap(g)
 norm = adapter.normalizer(-2, 8, center=0)
 assert norm(0) == .5
 image = ax.pcolormesh([[-2, 0], [1, 8]], cmap=cmap, norm=norm, **kwargs)
 fig.canvas.draw()
 assert adapter.colormap(p).N == 9
 import matplotlib.pyplot as mplplt
 mplplt.close(fig)
elif extra == 'plotly':
 import plotly.graph_objects as go
 from huevat.adapters import plotly as adapter
 axis = adapter.coloraxis(g, -2, 8, center=0)
 fig = go.Figure(go.Heatmap(z=[[-2, 0], [1, 8]], coloraxis='coloraxis'))
 fig.update_layout(coloraxis=axis)
 assert json.loads(fig.to_json())['layout']['coloraxis']['cmin'] == -2
print(json.dumps({'extra': extra, 'version': hv.__version__, 'python': sys.version.split()[0]}))
'''


def run(command, cwd, env):
    result = subprocess.run([str(v) for v in command], cwd=cwd, env=env,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(f"Command failed: {command}\n{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extra', choices=tuple(MINIMUM), action='append')
    parser.add_argument('--minimum', action='store_true', help='Requires Python 3.10 for the declared minimum versions')
    parser.add_argument('--dist-dir', type=Path, default=ROOT/'dist')
    args = parser.parse_args()
    if args.minimum and sys.version_info[:2] != (3, 10):
        parser.error('--minimum must run on Python 3.10')
    wheels = list(args.dist_dir.glob('*.whl'))
    if len(wheels) != 1:
        parser.error('Expected exactly one wheel in --dist-dir')
    records = []
    with tempfile.TemporaryDirectory(prefix='huevat-extras-') as temporary:
        work = Path(temporary)
        env = {**os.environ, 'MPLBACKEND': 'Agg', 'MPLCONFIGDIR': str(work/'mpl'),
               'XDG_CACHE_HOME': str(work/'cache')}
        for extra in args.extra or MINIMUM:
            prefix = work/extra
            python = prefix/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            run(['uv', 'venv', '--offline', '--python', sys.executable, prefix], work, env)
            requirement = f'{wheels[0].resolve()}[{extra}]'
            constraints = MINIMUM[extra] if args.minimum else []
            run(['uv', 'pip', 'install', '--python', python, requirement, *constraints], work, env)
            run(['uv', 'pip', 'check', '--python', python], work, env)
            result = json.loads(run([python, '-I', '-c', SMOKE, extra], work, env))
            result['minimum_dependencies'] = args.minimum
            records.append(result)
            print(json.dumps(result), flush=True)
    output = ROOT/'artifacts'/('extras-minimum-check.json' if args.minimum else 'extras-check.json')
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(records, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
