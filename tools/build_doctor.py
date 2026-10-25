"""Reproduce H4c numerical examples and render actual native figure previews."""
import argparse
import hashlib
import importlib.metadata as md
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'research/doctor-v1'
os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'.cache/matplotlib'))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from huevat import doctor
from huevat.gradients import _thaw


def write_json(path, data):
    path.write_text(json.dumps(data, separators=(',', ':'), sort_keys=True, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def digest(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n') if path.suffix != '.png' else path.read_bytes()).hexdigest()


def sources():
    files = list((ROOT/'src/huevat/doctor').glob('*.py')) + [Path(__file__), ROOT/'docs/METHODS_H4C.md']
    return {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in files}


def example(background='light', backend='matplotlib', mixed=False):
    bg, fg = ('#ffffff', '#29323b') if background == 'light' else ('#121212', '#e6e8eb')
    x = np.linspace(0, 10, 49)
    # Shared physical units and a deliberately ambiguous source palette.
    fields = {name: .65*np.sin(x/4+phase)+.035*x for name, phase in
              zip(('Reference', 'Shallow', 'Middle', 'Deep', 'Transient'), (0, .45, 1.1, 1.7, 2.35))}
    colors = dict(zip(fields, ('#4477aa', '#4c7fa9', '#638ca7', '#7c9aab', '#779fac')))
    if backend == 'plotly':
        import plotly.graph_objects as go
        fig = go.Figure()
        for name, y in fields.items():
            fig.add_trace(go.Scatter(x=x.tolist(), y=y.tolist(), mode='lines', name=name,
                                    line=dict(color=colors[name], width=2)))
        fig.update_layout(template='plotly_white' if background == 'light' else 'plotly_dark',
            paper_bgcolor=bg, plot_bgcolor=bg, width=1000, height=420,
            xaxis=dict(title='Distance (km)', range=[0, 10]),
            yaxis=dict(title='Displacement (mm)', range=[-.9, 1.3]),
            title='Five crossing series · explicit numeric scales')
        return fig
    if backend == 'ultraplot':
        import ultraplot as uplt
        fig, axs = uplt.subplots(ncols=2, figwidth=10, figheight=3.5, share=False)
        axes = [axs[0], axs[1]]
    else:
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))
        fig.subplots_adjust(left=.08, right=.97, bottom=.18, top=.84, wspace=.3)
    fig.set_facecolor(bg)
    for ai, ax in enumerate(axes):
        ax.set_facecolor(bg)
        names = list(fields) if ai == 0 else ['Deep', 'Reference', 'Transient', 'Middle']
        for name in names:
            ax.plot(x, fields[name]+(.035*np.sin(2*x) if ai else 0), color=colors[name], label=name,
                    linewidth=1.4)
        ax.set(xlim=(0, 10), ylim=(-.9, 1.3), xlabel='Distance (km)', ylabel='Displacement (mm)')
        ax.set_title('Full panel' if ai == 0 else 'Reordered · one category absent', fontsize=11, color=fg)
        ax.tick_params(colors=fg, labelsize=8)
        ax.xaxis.label.set_color(fg); ax.yaxis.label.set_color(fg)
        for spine in ax.spines.values(): spine.set_edgecolor(fg)
        ax.grid(alpha=.12)
        legend = ax.legend(fontsize=7, loc='upper left', ncols=2, facecolor=bg, labelcolor=fg,
                  edgecolor='#aaaaaa' if background == 'light' else '#555555')
        legend.get_frame().set_facecolor(bg); legend.get_frame().set_alpha(.92)
    if mixed:
        axes[0].fill_between(x, fields['Reference']-.09, fields['Reference']+.09,
                             color=colors['Reference'], alpha=.14, label='_uncertainty')
        im = axes[1].imshow(np.linspace(2., 5., 60).reshape(6, 10), extent=(0, 10, -.9, -.3),
                             origin='lower', cmap='Greys', alpha=.22, aspect='auto', vmin=2, vmax=5)
        cb = fig.colorbar(im, ax=axes[1], fraction=.045, pad=.025)
        cb.set_label('Velocity (km/s)', color=fg, fontsize=8); cb.ax.tick_params(colors=fg, labelsize=7)
    return fig


def compact(q):
    report = q.report
    return {'assignments': _thaw(q.assignments), 'color_screen_pass': report['color_screen_pass'],
            'unresolved_pairs': _thaw(report['unresolved_pairs']), 'redundant_pairs': _thaw(report['redundant_pairs']),
            'criteria': [{k: g[k] for k in ('name', 'condition', 'encoding', 'panel', 'measured', 'threshold', 'passed')}
                         for g in report['criteria']],
            'relationships': _thaw(report['relationships']), 'coverage': _thaw(report['coverage'])}


def case(background, backend='matplotlib', mixed=False):
    fig = example(background, backend, mixed)
    scene = doctor.inspect(fig)
    options = doctor.propose(scene)
    locks = {k: {'color': '#4379a3' if background == 'light' else '#76afd0'} for k in scene.categories}
    failing = doctor.propose(scene, locked=locks)[0]
    assert not failing.report['color_screen_pass'] and failing.report['redundant_pairs']
    summary = {'before': {'color_screen_pass': doctor.diagnose(scene)['color_screen_pass'],
                          'coverage': _thaw(scene.coverage)},
               'options': {q.name: compact(q) for q in options}, 'locked_failure': compact(failing)}
    return fig, options, failing, summary


def compare(a, b, path=''):
    if isinstance(a, dict):
        assert set(a) == set(b), path
        for k in a: compare(a[k], b[k], path+'/'+k)
    elif isinstance(a, list):
        assert len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b)): compare(x, y, path+'/'+str(i))
    elif isinstance(a, float): assert abs(a-b) <= 1e-8, (path, a, b)
    else: assert a == b, (path, a, b)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--check', action='store_true'); args = parser.parse_args()
    OUTPUT.mkdir(exist_ok=True)
    results, assets = {}, []
    for bg in ('light', 'dark'):
        for backend, mixed in (('matplotlib', False), ('matplotlib', True), ('ultraplot', False), ('plotly', False)):
            key = f'{backend}-{bg}'+('-mixed' if mixed else '')
            fig, options, failing, summary = case(bg, backend, mixed)
            results[key] = summary
            if args.check:
                # Validate actual native apply evidence, not just hypothetical reports.
                original = doctor.inspect(fig).fingerprint
                change = doctor.apply(fig, options[0])
                assert change.report['color_screen_pass'] == options[0].report['color_screen_pass']
                change.undo(); assert doctor.inspect(fig).fingerprint == original
            elif backend != 'plotly':
                variants = [('before', None, 'normal')] + [(q.name, q, 'normal') for q in options]
                if backend == 'matplotlib' and not mixed:
                    variants += [('separation-'+condition, options[1], condition) for condition in
                        ('protan-50','protan-80','protan-100','deutan-50','deutan-80','deutan-100','tritan-100','grayscale')]
                    variants += [('before-grayscale', None, 'grayscale'), ('locked-failure', failing, 'normal')]
                for label, proposal, condition in variants:
                    copy = doctor.preview(fig, proposal, condition=condition)
                    name = f'{key}-{label}.png'
                    copy.savefig(OUTPUT/name, dpi=160, facecolor=copy.get_facecolor())
                    assets.append(name); plt.close(copy)
                write_json(OUTPUT/f'{key}-proposal.json', json.loads(options[1].to_json()))
                assets.append(f'{key}-proposal.json')
            else:
                for label, proposal in (('before', None), ('separation', options[1])):
                    copy = doctor.preview(fig, proposal)
                    name = f'{key}-{label}.json'
                    (OUTPUT/name).write_text(copy.to_json()+'\n', encoding='utf-8', newline='\n')
                    assets.append(name)
            if backend != 'plotly': plt.close(fig)
    if args.check:
        manifest = json.loads((OUTPUT/'manifest.json').read_text())
        assert sources() == manifest['implementation_sha256_lf']
        compare(results, json.loads((OUTPUT/'results.json').read_text()))
        for name, sha in manifest['artifacts'].items(): assert digest(OUTPUT/name) == sha, name
        print('H4c: eight native cases, three tradeoffs, locked failures, guarded undo and artifact hashes reproduced')
        return
    write_json(OUTPUT/'results.json', results); assets.append('results.json')
    review = {'status': 'pending', 'visual_review': 'Human appearance/readability review pending',
              'simulation': 'Supported marks and backgrounds only; scalar maps/bands retained in mixed examples',
              'browser': 'Plotly native JSON checked; browser interaction not exercised'}
    write_json(OUTPUT/'review.json', review); assets.append('review.json')
    rows = []
    for bg in ('light', 'dark'):
        cards = ''.join(f'<figure><img loading="lazy" src="matplotlib-{bg}-{name}.png"><figcaption>{label}</figcaption></figure>'
            for name, label in (('before', 'Before · ambiguous colors'), ('closer', 'Closer · retain the original feel'),
                               ('separation', 'Separation · prioritize crossings'), ('simple', 'Simple · fewer extra encodings')))
        cvd = ''.join(f'<option value="{c}">{c}</option>' for c in
            ('normal','protan-50','protan-80','protan-100','deutan-50','deutan-80','deutan-100','tritan-100','grayscale'))
        rows.append(f'''<section><h2>{bg.title()} background</h2><div class="grid">{cards}</div>
        <h3>Review the actual figure under simulated conditions</h3><select data-bg="{bg}">{cvd}</select>
        <img class="simulation" id="{bg}" src="matplotlib-{bg}-separation.png">
        <details><summary>Locked identical colors: color screen still fails</summary><p>Distinct markers and dashes help track labels. The failed color-only result remains a failure.</p><img src="matplotlib-{bg}-locked-failure.png"></details>
        <details><summary>Mixed content: bands and colorbar preserved</summary><p>This is partial coverage: uncertainty bands, scalar maps and colorbars are retained and excluded from the mark-color screen.</p><img src="matplotlib-{bg}-mixed-separation.png"></details>
        <details><summary>Native UltraPlot preview</summary><img src="ultraplot-{bg}-separation.png"></details></section>''')
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Huevat · Figure doctor</title><style>
    *{box-sizing:border-box}body{margin:0;background:#f2f0eb;color:#29323b;font:16px/1.55 system-ui,sans-serif}
    main{max-width:1400px;margin:auto;padding:50px 28px}h1{font-size:44px;line-height:1.15;letter-spacing:-1.5px}
    h2{font-size:28px}p{max-width:900px}header{margin-bottom:36px}section{margin:30px 0 55px}
    .eyebrow{color:#397c78;font-weight:650;letter-spacing:2px;text-transform:uppercase;font-size:12px}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0;background:white;border-radius:10px;overflow:hidden}
    img{display:block;width:100%;height:auto}figcaption{padding:12px 18px;font-weight:550}.simulation{margin-top:14px;border-radius:10px}
    select{padding:9px 14px;background:white;border:1px solid #b8b9b4;border-radius:6px;font:inherit}
    details{margin-top:18px;background:#fff;border-radius:8px;padding:15px}summary{cursor:pointer;font-weight:600}
    code,pre{font:14px/1.6 ui-monospace,monospace}pre{background:#e7e7e1;padding:22px;border-radius:8px;overflow:auto}
    a{color:#246b7c}footer{font-size:13px;color:#5e6870}@media(max-width:850px){.grid{grid-template-columns:1fr}h1{font-size:34px}}
    </style><main><header><div class="eyebrow">Huevat · H4c</div><h1>Give a figure a clearer voice.</h1>
    <p>Inspect the existing plot. Compare three color, marker and dash choices. Preview on a copy. Apply only when you choose.</p>
    <p>Repeated labels keep their identity across panels, including when categories are reordered or absent. The selected Clearer palette remains the starting point.</p></header>
    <pre>from huevat import doctor
scene = doctor.inspect(fig)
closer, separation, simple = doctor.propose(scene)
copy = doctor.preview(fig, separation)
change = doctor.apply(fig, separation)  # explicit edit
change.undo()</pre>''' + ''.join(rows) + '''
    <section><h2>Use your own constraints</h2><pre>options = doctor.propose(scene, locked={"Reference": {"color": "#4379a3"}})
next_options = doctor.propose(next_scene, assignments=options[0].assignments)
saved = options[0].to_json()
restored = doctor.load_proposal(saved)</pre>
    <p>Retained assignments reserve absent categories. Hard locks remain exact, including when they cause a failed screen. Data, units, axis scales, physical limits and scalar color mappings are preserved.</p></section>
    <footer>Model screens are not human-readability certificates. Marker/dash differences are structural hints. Review at the intended figure size.
    <a href="results.json">Numerical results</a> · <a href="review.json">Review status</a> · <a href="../../docs/METHODS_H4C.md">Methods and supported coverage</a> ·
    <a href="plotly-light-separation.json">Native Plotly preview JSON</a>. No network required. Native Plotly rendering is tested through serialization; browser interaction remains unverified.</footer></main>
    <script>document.querySelectorAll('select').forEach(s=>s.onchange=()=>{let c=s.value;document.getElementById(s.dataset.bg).src='matplotlib-'+s.dataset.bg+'-separation'+(c==='normal'?'':'-'+c)+'.png'})</script></html>'''
    (OUTPUT/'index.html').write_text(html, encoding='utf-8', newline='\n'); assets.append('index.html')
    write_json(OUTPUT/'manifest.json', {'version':doctor.VERSION, 'protocol_commit':'6e3aa13',
        'implementation_sha256_lf':sources(), 'artifacts':{name:digest(OUTPUT/name) for name in sorted(assets)},
        'versions':{name:md.version(name) for name in ('matplotlib','plotly','ultraplot','colorspacious','numpy')}})
    print(f'Wrote H4c gallery: {len(assets)} assets; eight native cases and explicit locked failures')


if __name__ == '__main__': main()
