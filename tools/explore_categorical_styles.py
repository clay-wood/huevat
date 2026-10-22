"""Compare aesthetic-first categorical candidates without replacing H3 tables.

Run with huevat[design,research]. --check reaudits the saved float/u8 designs.
"""
import argparse
import hashlib
import importlib.metadata as md
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))

import numpy as np
from scipy.optimize import minimize
import huevat as hv
from huevat.design_h3 import _pair_data, validate_categorical, VERSION
from huevat.evaluation import _lab, _linear, condition_colors

# Independently chosen design targets, in semantic color order. These are
# preferences for this study, not newly named copies of a published palette.
ANCHORS = ("#4379a3", "#348b83", "#ae883b", "#bd6c60", "#9274a3", "#5599b4", "#9b586d", "#7e8750")
INDICES = {4: (0,1,2,3), 6: (0,1,2,3,4,5), 8: tuple(range(8))}
STYLES = {
    "balanced": {"chroma_scale": 1., "chroma_max": .155},
    "soft": {"chroma_scale": .78, "chroma_max": .125},
    "clear": {"chroma_scale": 1.18, "chroma_max": .18},
}
OUTPUT = ROOT / "research/categorical-aesthetics-v1"


def source_hashes():
    paths=(Path(__file__),ROOT/'src/huevat/design_h3.py',ROOT/'src/huevat/evaluation.py')
    return {str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in paths}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8", newline="\n")


def targets(n, style, background):
    lab = _lab(np.array([hv.from_hex(ANCHORS[i]) for i in INDICES[n]]))
    lab[:,1:] *= STYLES[style]["chroma_scale"]
    if background == "dark":
        lab[:,0] += .12
    return lab


def generate(n, style, background, starts=3, seed=14507):
    """Minimize anchor movement after satisfying fixed separation floors.

    Auxiliary z is a minimum-distance feasibility variable. Raising z after
    the required margin is reached is deliberately not the aesthetic objective.
    """
    target = targets(n,style,background)
    bg = hv.from_hex("#ffffff" if background=="light" else "#121212")
    Ybg = _linear(np.array([bg]))[0] @ np.array([.2126,.7152,.0722])
    rng = np.random.default_rng(seed+n)
    cmax = STYLES[style]['chroma_max']
    Llo,Lhi = (.43,.72) if background=='light' else (.57,.87)
    started=time.perf_counter();candidates=[];runs=[];failures=[]

    def constraints(x):
        rgb=x[:-1].reshape(n,3)
        d,dc,lab=_pair_data(rgb)
        Y=_linear(rgb)@np.array([.2126,.7152,.0722])
        lum=(Ybg+.05)/3-.05-Y if background=='light' else Y-(3*(Ybg+.05)-.05)
        C=np.linalg.norm(lab[:,1:],axis=1)
        movement=np.linalg.norm(lab-target,axis=1)
        return np.r_[(d-x[-1]).ravel(),(dc-4.15).ravel(),lum-.004,
                     lab[:,0]-Llo,Lhi-lab[:,0],C-.04,cmax-C,.065-movement]

    def objective(x):
        lab=_lab(x[:-1].reshape(n,3))
        return float(np.sum((lab-target)**2))

    for start in range(starts):
        lab=target.copy()
        if start:
            lab+=rng.normal(0,.018,lab.shape)
        rgb=np.array([hv.gamut_map(hv.oklab_to_oklch(row)) for row in lab])
        initial=np.r_[rgb.ravel(),.043]
        result=minimize(objective,initial,method="SLSQP",bounds=[(.002,.998)]*(3*n)+[(.043,.043)],
                        constraints={'type':'ineq','fun':constraints},options={'maxiter':200,'ftol':1e-10})
        violation=float(min(constraints(result.x)))
        runs.append({'start':start,'success':bool(result.success),'iterations':int(result.nit),
                     'minimum_constraint_residual':violation,'message':str(result.message)})
        recipe={'schema_version':1,'algorithm_version':VERSION,'family':'categorical','background':list(bg),'context':'data-marks',
                'rgb':result.x[:-1].reshape(n,3).tolist(),'preferences':[hv.to_hex(hv.gamut_map(hv.oklab_to_oklch(row))) for row in target],
                'identifier':f'aesthetic-study-{style}-{background}-{n}-v1'}
        report=validate_categorical(recipe)
        if violation>=-1e-7 and report['screen_pass']:
            candidates.append((objective(result.x),recipe,report))
        else:
            failures=[c for c in report['checks'] if not c['passed']]
    if not candidates:
        return {'outcome':'search-exhausted','infeasibility_proven':False,'runs':runs,'failed_checks':failures,
                'seconds':time.perf_counter()-started}
    error,recipe,report=min(candidates,key=lambda c:c[0])
    return {'outcome':'candidate','recipe':recipe,'report':report,'target_oklab':target.tolist(),
            'aesthetic_squared_error':error,'runs':runs,'seconds':time.perf_counter()-started,
            'visual_review':'pending','approved_default':False}


def render(data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from build_baseline import style as axes_style
    labels={'original':'H3 original','balanced':'Balanced','soft':'Softer','clear':'Clearer'}
    for background in ('light','dark'):
        bg='#ffffff' if background=='light' else '#121212'
        fig,axes=plt.subplots(4,3,figsize=(11,7.7),layout='constrained')
        fg=axes_style(fig,axes,bg)
        for row,style in enumerate(('original','balanced','soft','clear')):
            for col,n in enumerate((4,6,8)):
                ax=axes[row,col]
                if style=='original':
                    rgb=np.array(hv.categorical(n,background=background).rgb)
                    passing=True
                else:
                    entry=data['candidates'][f'{style}/{background}/{n}']
                    passing=entry['outcome']=='candidate'
                    rgb=np.array([hv.from_hex(c) for c in entry['report']['hex']]) if passing else None
                if rgb is None:
                    ax.text(.5,.5,'No passing candidate found\nin this aesthetic envelope',ha='center',va='center',color=fg,fontsize=9)
                    ax.set_xticks([]);ax.set_yticks([])
                else:
                    for i,color in enumerate(rgb):
                        ax.add_patch(Rectangle((i/n,.79),1/n,.20,color=color,linewidth=0))
                    x=np.linspace(0,1,120)
                    for i,color in enumerate(rgb):
                        ax.plot(.04+.92*x,.17+.27*np.sin(2*np.pi*(x+.15*i))+.015*i,color=color,linewidth=1.5)
                        ax.scatter(.08+.84*i/(n-1),.68,s=30,color=color,edgecolors='none')
                    ax.set_xlim(0,1);ax.set_ylim(-.15,1.02);ax.set_xticks([]);ax.set_yticks([])
                ax.set_title(f'{labels[style]} | {n} colors'+(' | screens pass' if passing else ''),color=fg,fontsize=10)
                for spine in ax.spines.values():spine.set_visible(False)
        fig.suptitle(f'Categorical appearance study | {background} background',color=fg,fontsize=14)
        fig.supxlabel('Same H1 float/8-bit screening thresholds. New options preserve chosen color targets; human visual review pending.',color=fg,fontsize=9)
        fig.savefig(OUTPUT/f'comparison-{background}.png',dpi=200,facecolor=bg,metadata={'Software':'Huevat categorical aesthetics study'})
        plt.close(fig)
        # Show all simulated conditions for the six-color balanced candidate.
        entry=data['candidates'][f'balanced/{background}/6']
        if entry['outcome']=='candidate':
            q=np.array([hv.from_hex(c) for c in entry['report']['hex']])
            fig,axes=plt.subplots(8,1,figsize=(7.5,5.3),layout='constrained');fg=axes_style(fig,axes,bg)
            for ax,condition in zip(axes,data['conditions']):
                ax.imshow(condition_colors(q,condition)[0][None,:,:],aspect='auto',interpolation='nearest')
                ax.set_ylabel(condition,ha='right',va='center',rotation=0,color=fg,fontsize=8)
                ax.set_xticks([]);ax.set_yticks([])
            fig.suptitle(f'Balanced candidate | six colors | {background} | all CVD screens pass',color=fg,fontsize=11)
            fig.savefig(OUTPUT/f'balanced-six-cvd-{background}.png',dpi=200,facecolor=bg);plt.close(fig)
    cards=''.join(f'<h2>{bg.title()} background</h2><img src="comparison-{bg}.png" alt="Original versus three balanced aesthetic directions"><details><summary>Balanced six-color palette under all screened simulations</summary><img src="balanced-six-cvd-{bg}.png" alt="Eight viewing conditions"></details>' for bg in ('light','dark'))
    (OUTPUT/'index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><title>Huevat categorical appearance alternatives</title><style>body{font:16px/1.5 system-ui;max-width:1150px;margin:auto;padding:24px;background:#eee;color:#222}img{width:100%;height:auto}details{margin-bottom:24px}</style><h1>Categorical appearance alternatives</h1><p>Exploratory candidates; existing H0–H3 production tables are unchanged. These alternatives keep the H1 requirements and optimize closeness to blue, teal, ochre, coral and purple targets after satisfying separation. Soft and clear variants change chroma targets. Every displayed new palette passes float and 8-bit screens; unsuccessful searches are retained in the report. Human visual review is pending.</p><p><a href="results.json">Full recipes, reports and search results</a> · <a href="../../docs/CATEGORICAL_AESTHETICS.md">Methods and alternatives</a></p>'''+cards+'</html>',encoding='utf-8',newline='\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    path=OUTPUT/'results.json'
    if args.check:
        data=json.loads(path.read_text(encoding='utf-8'))
        assert data['source_sha256_lf']==source_hashes(),'Study implementation changed'
        assert set(data['candidates'])=={f'{s}/{b}/{n}' for s in STYLES for b in ('light','dark') for n in (4,6,8)}
        from build_ordered import compact_compare
        count=0
        for entry in data['candidates'].values():
            if entry['outcome']=='candidate':
                compact_compare(entry['report'],validate_categorical(entry['recipe']));count+=1
        manifest=json.loads((OUTPUT/'manifest.json').read_text(encoding='utf-8'))
        for name,digest in manifest['files'].items():
            assert hashlib.sha256((OUTPUT/name).read_bytes()).hexdigest()==digest,name
        print('Reproduced',count,'aesthetic candidates and verified gallery hashes')
        return
    OUTPUT.mkdir(parents=True,exist_ok=True)
    data={'version':'categorical-aesthetics-study-v1','profile_version':'h1-screening-v1',
          'source_sha256_lf':source_hashes(),'versions':{p:md.version(p) for p in ('numpy','scipy','colorspacious','matplotlib')},
          'seed':14507,'starts':3,'scope':'Exploratory designs; no prepared package tables replaced',
          'conditions':list(hv.load_profile()['conditions']),'objective':'satisfy separation floors, then minimize chosen anchor movement',
          'style_definitions':STYLES,'base_anchors':list(ANCHORS),'candidates':{}}
    for style in STYLES:
        for background in ('light','dark'):
            for n in (4,6,8):
                entry=generate(n,style,background)
                data['candidates'][f'{style}/{background}/{n}']=entry
                print(style,background,n,entry['outcome'],entry['seconds'],flush=True)
    write_json(path,data);render(data)
    write_json(OUTPUT/'manifest.json',{'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUTPUT.iterdir()) if p.is_file() and p.name!='manifest.json'}})


if __name__=='__main__':main()
