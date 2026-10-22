"""Build/recheck the selected H3 Clearer categorical revision."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache/matplotlib'))

import numpy as np
from huevat._data import load_data
from huevat.categorical import VERSION
from huevat.design_categorical import generate,validate_categorical
from build_ordered import compact_compare,write_json

OUTPUT = ROOT/'research/categorical-v2'


def implementation_hashes():
    return {name:hashlib.sha256((ROOT/'src/huevat'/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            for name in ('categorical.py','design_categorical.py')}


def render(data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import build_baseline
    cards=[]

    def save(fig,path):
        fig.savefig(path,dpi=300,facecolor=fig.get_facecolor(),metadata={'Software':'Huevat Clearer categorical v2'})
        plt.close(fig)
    build_baseline.save=save
    for background in ('light','dark'):
        bg='#ffffff' if background=='light' else '#121212'
        fig,axes=plt.subplots(11,1,figsize=(8,5.5),layout='constrained');fg=build_baseline.style(fig,axes,bg)
        for ax,n in zip(axes,range(2,13)):
            entry=data['designs'][f'{background}/{n}']
            colors=np.array(entry['recipe']['rgb']);colors=np.rint(colors*255)/255
            ax.imshow(colors[None,:,:],aspect='auto',interpolation='nearest')
            ax.set_ylabel(str(n),rotation=0,color=fg);ax.set_xticks([]);ax.set_yticks([])
        fig.suptitle(f'H3 Clearer categorical | {background} | every count jointly optimized',color=fg,fontsize=10)
        name=f'clearer-{background}-counts.png';save(fig,OUTPUT/name)
        cards.append(f'<section><h2>{background.title()} / counts 2–12</h2><p>Every count passes the original float/8-bit screens and the Clearer aesthetic envelope. Additional separation is traded for preserving the selected appearance.</p><img src="{name}" alt="All Clearer prepared counts on {background}"></section>')
        for n in (4,6,8,12):
            entry=data['designs'][f'{background}/{n}']
            class Ref:
                label=f'H3 Clearer categorical, n={n}'
                def colors(self,count):
                    assert count==n
                    return entry['recipe']['rgb']
            name=f'clearer-{background}-{n}.png'
            build_baseline.categorical_panel(Ref(),n,background,OUTPUT/name)
            cards.append(f'<details><summary>{n} colors / {background}: CVD, grayscale, thin lines and small marks</summary><img src="{name}" alt="Clearer matched-geometry audit"></details>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Huevat H3 Clearer revision</title><style>body{font:16px/1.5 system-ui;max-width:1050px;margin:auto;padding:24px;background:#eee;color:#222}section,details{background:white;padding:20px;margin:20px 0}img{width:100%;height:auto}</style><h1>H3: selected Clearer categorical design</h1><p>The user selected Clearer after comparing the original, Balanced, Softer and Clearer alternatives. It is now the default categorical construction. The original numerical thresholds remain unchanged. The direction is selected; expanded counts and H4 human validation remain separate.</p><p><a href="../categorical-aesthetics-v1/index.html">Appearance selection study</a> · <a href="../families-v1/index.html">Original H3 baseline and unchanged multi-hue/Spectral paths</a> · <a href="../ordered-v1/index.html">H2</a> · <a href="../../docs/METHODS_CATEGORICAL_V2.md">Methods and migration</a> · <a href="../../src/huevat/data/categorical-v2.json">Full recipes/reports</a></p>'''+''.join(cards)+'</html>'
    (OUTPUT/'index.html').write_text(page,encoding='utf-8',newline='\n')
    write_json(OUTPUT/'review.json',{'style':'clearer','direction':'selected by user','reviewed_counts':[4,6,8],
                                   'expanded_count_review':'pending','approved_H4_default':False,
                                   'panels':[{'file':p.name,'layout':'checked','perceptual_review':'pending'} for p in sorted(OUTPUT.glob('*.png'))]})
    write_json(OUTPUT/'manifest.json',{'implementation_sha256_lf':implementation_hashes(),
        'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUTPUT.iterdir()) if p.is_file() and p.name!='manifest.json'}})


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if args.check:
        data=load_data('categorical-v2.json')
        assert data['implementation_sha256_lf']==implementation_hashes(),'Clearer implementation differs from its source hashes'
        assert set(data['designs'])=={f'{b}/{n}' for b in ('light','dark') for n in range(2,13)}
        for entry in data['designs'].values():
            compact_compare({k:v for k,v in entry['report'].items() if k!='search'},validate_categorical(entry['recipe']))
        manifest=json.loads((OUTPUT/'manifest.json').read_text(encoding='utf-8'))
        for name,digest in manifest['files'].items():
            assert hashlib.sha256((OUTPUT/name).read_bytes()).hexdigest()==digest,name
        print('Reproduced 22 Clearer float/u8 reports and verified source/gallery hashes')
        return
    data={'version':VERSION,'style':'clearer','profile_version':'h1-screening-v1',
          'implementation_sha256_lf':implementation_hashes(),'designs':{}}
    for background in ('light','dark'):
        for n in range(2,13):
            p=generate(n,background=background,starts=3,max_seconds=120)
            recipe=p.to_recipe()['recipe'];recipe['identifier']=f'h3-clearer-{background}-{n}-v2'
            report=validate_categorical(recipe);report['search']=p.report.to_dict()['search']
            data['designs'][f'{background}/{n}']={'recipe':recipe,'report':report}
            print(background,n,'PASS',round(report['search']['elapsed_seconds'],3),'s',flush=True)
    path=ROOT/'src/huevat/data/categorical-v2.json';write_json(path,data)
    manifest_path=ROOT/'src/huevat/data/manifest-v1.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['sha256_lf'][path.name]=hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest();write_json(manifest_path,manifest)
    OUTPUT.mkdir(parents=True,exist_ok=True);render(data)


if __name__=='__main__':main()
