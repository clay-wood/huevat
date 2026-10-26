"""Freeze/reproduce the v0.1 registry, compact exports and offline release page."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'research/release-v1'
RESOURCE = ROOT/'src/huevat/data/release-v1.json'

import huevat as hv
from huevat._data import load_data
from huevat.gradients import fingerprint


def write_json(path, data):
    path.write_text(json.dumps(data, separators=(',', ':'), sort_keys=True, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def digest(path): return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def registry():
    designs = {}
    def entry(recipe, background, factory, role, *, is_reversed=False, **kwargs):
        identifier = recipe['identifier']
        view = dict(recipe)
        if recipe['family'] != 'categorical': view['reversed'] = is_reversed
        designs[identifier] = {'identifier':identifier, 'family':recipe['family'], 'background':background,
            'count':len(recipe['rgb']) if recipe['family']=='categorical' else None,
            'factory':factory, 'role':role, 'recipe_sha256':fingerprint(recipe),
            'reversed':is_reversed, 'view_sha256':fingerprint(view),
            'human_discrimination_validated':False, 'numerical_profile':'h1-screening-v1', **kwargs}
    for key, value in load_data('ordered-v1.json')['designs'].items():
        family, bg = key.split('/')
        entry(value['recipe'], bg, family, 'default', is_reversed=value['reversed'], review='current defaults retained by v0.1 release policy')
    families = load_data('families-v1.json')
    for key, value in {**families['categorical'], **families['ordered']}.items():
        recipe = value['recipe']; family = recipe['family']; bg = key.split('/')[1] if family!='categorical' else key.split('/')[0]
        if family == 'categorical':
            entry(recipe, bg, 'categorical', 'legacy', style='max-separation', review='original H3 style; retained compatibility')
        else: entry(recipe, bg, family, 'default', is_reversed=value['reversed'], review='current defaults retained by v0.1 release policy')
    for key, value in load_data('categorical-v2.json')['designs'].items():
        bg, n = key.split('/')
        entry(value['recipe'], bg, 'categorical', 'default', style='clearer',
              review='user-selected Clearer direction; comparison counts 4/6/8; expanded counts numerically screened')
    for name, value in load_data('collection-v1.json')['candidates'].items():
        for bg, variant in value['variants'].items():
            entry(variant['recipe'], bg, 'gradient', 'experimental', is_reversed=variant['reversed'], name=name, review='appearance review pending; no default adoption')
    for identifier, variant in load_data('collection-v1.json').get('archived',{}).items():
        name,bg=identifier.removeprefix('h4b-').rsplit('-v',1)[0].rsplit('-',1)
        entry(variant['recipe'],bg,'gradient','legacy',is_reversed=variant['reversed'],name=name,
              review='superseded collection route; exact recipe retained')
    return {'version':'h4-release-v1', 'package_version':'0.1.0',
        'policy':'keep current defaults including Clearer; named routes remain experimental',
        'review_scope':'release inclusion is not a human-readability certificate; frozen reports unchanged',
        'designs':dict(sorted(designs.items()))}


def freeze_registry():
    write_json(RESOURCE, registry())
    path = ROOT/'src/huevat/data/manifest-v1.json'
    data = json.loads(path.read_text()); data['sha256_lf'][RESOURCE.name] = digest(RESOURCE)
    write_json(path, data)


def cases():
    result = {}
    for identifier in hv.design_ids():
        design = hv.get_design(identifier)
        assert design is hv.get_design(identifier)
        out = hv.export(design)
        loaded = hv.load_export(out).design
        if isinstance(design, hv.Gradient):
            assert all(loaded.at(t) == design.at(t) for t in (0, .125, .5, .875, 1))
            assert hv.load_export(hv.export(design.reversed())).design.at(.25) == design.at(.75)
        else: assert loaded.colors == design.colors
        info = hv.design_info(identifier)
        result[identifier] = {'role':info['role'], 'recipe_sha256':info['recipe_sha256'],
            'export_sha256':out.sha256, 'compact_bytes':len(out.text.encode()),
            'full_evidence_bytes':len(design.to_json().encode()),
            'screen_pass':loaded.report.screen_pass}
    return result


def sources():
    names = ('src/huevat/library.py','src/huevat/exports.py','src/huevat/__init__.py','src/huevat/_prepared.py',
             'tools/build_release.py','docs/METHODS_H4D.md')
    return {n:digest(ROOT/n) for n in names}


def compare(expected, actual, path=''):
    if isinstance(expected, dict):
        assert set(expected)==set(actual),path
        for key in expected:compare(expected[key],actual[key],path+'/'+key)
    elif isinstance(expected, list):
        assert len(expected)==len(actual),path
        for i,(a,b) in enumerate(zip(expected,actual)):compare(a,b,path+'/'+str(i))
    elif isinstance(expected,float):assert abs(expected-actual)<=1e-8,(path,expected,actual)
    else:assert expected==actual,(path,expected,actual)


def render(results):
    import html
    OUTPUT.mkdir(exist_ok=True)
    assets = []
    p = hv.categorical(6); g = hv.diverging()
    for name, source, kwargs in [('clearer',p,{'labels':['Control','A','B','C','D','E']}),
                                 ('signed',g,{}), ('signed-seven',g,{'n':7})]:
        for fmt in ('json','csv','hex','css'):
            if name == 'signed' and fmt in ('csv','hex'): continue
            if fmt == 'css' and name == 'signed': continue
            output = hv.export(source, format=fmt, **kwargs)
            filename = name+'.'+('txt' if fmt=='hex' else fmt)
            output.write(OUTPUT/filename); assets.append(filename)
    routes = []
    css_evidence = {}
    for factory in (hv.sequential,hv.diverging,hv.multihue,hv.spectral):
        for bg in ('light','dark'):
            source = factory(background=bg); output = hv.export(source, format='css')
            key = source.family+'-'+bg
            output.write(OUTPUT/(key+'.css')); assets.append(key+'.css')
            css_evidence[key] = output.report.to_dict()
            routes.append(f'<div class="route {bg}"><b>{source.family} · {bg}</b><div class="ramp" style="background:{html.escape(output.text.strip(), quote=True)}"></div></div>')
    write_json(OUTPUT/'exports.json', {'designs':results, 'css':css_evidence}); assets.append('exports.json')
    pcss = hv.export(p, format='css').text.strip()
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Huevat · Colors for scientific figures</title><style>
    *{box-sizing:border-box}body{margin:0;background:#f2f0eb;color:#29323b;font:16px/1.6 system-ui,sans-serif}
    main{max-width:1120px;margin:auto;padding:50px 30px}h1{font-size:48px;line-height:1.1;letter-spacing:-1.8px}
    h2{margin-top:44px;font-size:27px}a{color:#236f7a}p{max-width:850px}.kicker{color:#367d76;letter-spacing:2px;font-size:12px;font-weight:700;text-transform:uppercase}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.card{background:white;border-radius:10px;padding:22px}
    .route{padding:16px;background:white;border-radius:8px}.route.dark{background:#121212;color:#eee}.ramp{height:40px;border-radius:4px;margin:12px 0}
    pre{font:14px/1.6 ui-monospace,monospace;background:#e6e7e2;padding:22px;border-radius:8px;overflow:auto}
    img{width:100%;height:auto;display:block;border-radius:8px}small{color:#59646a}.swatch{height:64px;border-radius:8px}
    @media(max-width:750px){.grid{grid-template-columns:1fr}h1{font-size:36px}}
    </style><main><div class="kicker">Huevat</div><h1>Colors for scientific figures.</h1>
    <p>Palettes and gradients for Matplotlib, Plotly and UltraPlot, with a figure doctor for coordinated colors, markers and dashes.</p>
    <div class="swatch" style="background:''' + html.escape(pcss, quote=True) + '''"></div>
    <p><b>Clearer is the default categorical palette.</b> Choose light or dark variants to suit your figure. The eighteen additional named gradients are experimental alternatives.</p>
    <pre>import huevat as hv
palette = hv.categorical(6)
gradient = hv.diverging()
hv.export(palette, labels=["Control", "A", "B", "C", "D", "E"]).write("palette.json")
restored = hv.load_export(open("palette.json", encoding="utf-8").read()).design</pre>
    <div class="grid"><div class="card"><b>Make a plot</b><p>Pick a palette, choose your plotting library and follow a short example.</p><a href="../../docs/QUICKSTART.md">Quick start</a> · <a href="../../examples/README.md">Plotting examples</a></div>
    <div class="card"><b>Improve an existing figure</b><p>Compare colors, markers and dashes on a copy, then apply the option you prefer.</p><a href="../../docs/FIGURE_DOCTOR.md">Figure doctor guide</a></div></div>
    <h2>Current gradient defaults</h2><div class="grid">''' + ''.join(routes) + '''</div>
    <h2>More gradients</h2><img src="../../docs/images/gradients.png" alt="The eighteen experimental gradients on light and dark backgrounds">
    <p>Additional choices for general plots, seismic data, terrain, depth and atmospheric fields.</p>
    <h2>Save and reuse</h2><p>JSON saves a design and its labels for reuse. CSV and hex give you color lists; CSS gradients are also available.</p>
    <p><a href="clearer.json">Six labeled Clearer colors</a> · <a href="signed.json">Exact signed gradient</a> · <a href="signed-seven.csv">Seven-color CSV</a> · <a href="signed-seven.json">Seven-color recipe</a> · <a href="sequential-light.css">Continuous CSS</a></p>
    <p><a href="../../README.md">Palette gallery</a> · <a href="../../docs/API.md">API guide</a> · <a href="../../docs/RELEASE_NOTES.md">Release notes</a></p>
    <small>Review your figures at their intended size.</small></main></html>'''
    (OUTPUT/'index.html').write_text(page, encoding='utf-8', newline='\n'); assets.append('index.html')
    write_json(OUTPUT/'manifest.json', {'version':'h4-release-v1','implementation_sha256_lf':sources(),
        'registry_sha256_lf':digest(RESOURCE),'artifacts':{name:digest(OUTPUT/name) for name in sorted(assets)}})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--registry',action='store_true');parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if args.registry:
        freeze_registry();print('Froze v0.1 registry and added its resource hash');return
    assert registry() == load_data('release-v1.json')
    result = cases()
    if args.check:
        manifest=json.loads((OUTPUT/'manifest.json').read_text())
        assert manifest['implementation_sha256_lf']==sources()
        assert manifest['registry_sha256_lf']==digest(RESOURCE)
        assert json.loads((OUTPUT/'exports.json').read_text())['designs']==result
        for name, expected in manifest['artifacts'].items(): assert digest(OUTPUT/name)==expected,name
        # Re-audit the actual CSS stop strings and preserved source hashes.
        evidence=json.loads((OUTPUT/'exports.json').read_text())['css']
        for factory in (hv.sequential,hv.diverging,hv.multihue,hv.spectral):
            for bg in ('light','dark'):
                source=factory(background=bg);output=hv.export(source,format='css')
                retained=(OUTPUT/(source.family+'-'+bg+'.css')).read_text()
                def stops(text):
                    return [[*(float(v) for v in rgb.split(',')),float(t)]
                            for rgb,t in re.findall(r'rgb\(([^)]+)\) ([0-9.]+)%',text)]
                compare(stops(retained),stops(output.text))
                compare(evidence[source.family+'-'+bg],output.report.to_dict())
        print(f'H4d: {len(result)} IDs, old recipes, compact exchange and all eight default CSS audits reproduced')
    else:
        render(result);print(f'Built private v0.1 release overview and {len(result)} identity/roundtrip records')


if __name__=='__main__': main()
