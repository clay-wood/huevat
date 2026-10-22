"""Build/recheck H3 count-specific designs and the complete offline gallery."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR",str(ROOT/".cache/matplotlib"))

import numpy as np
from huevat import from_hex, to_hex
from huevat._data import load_data
from huevat.design_h3 import (generate_categorical, generate_ordered, validate_categorical,
                              validate_ordered, make_ordered_recipe)
from huevat.families import HueGradient, MULTIHUE_COLORS, SPECTRAL_COLORS, proxy_recipe
from huevat.gradients import Gradient, QualityReport, fingerprint
from build_ordered import compact_compare, records, write_json


def implementation_hashes():
    return {name:hashlib.sha256((ROOT/'src/huevat'/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            for name in ('families.py','design_h3.py')}


def discrete_records(gradient):
    return records(Gradient(proxy_recipe(gradient._recipe),QualityReport({}),{}))


def render(data, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from huevat.evaluation import condition_colors,gray_rgb,_lab
    import build_baseline
    from build_baseline import style, fields
    output.mkdir(parents=True,exist_ok=True)
    cards=[]

    def save(fig,path):
        fig.savefig(path,dpi=300,facecolor=fig.get_facecolor(),metadata={'Software':'Huevat H3 families-v1'})
        plt.close(fig)
    # Reuse the frozen matched line/mark geometries, with an explicit H3 title.
    build_baseline.save=save
    for background in ('light','dark'):
        bg='#ffffff' if background=='light' else '#121212'
        fig,axes=plt.subplots(11,1,figsize=(8,5.5),layout='constrained')
        fg=style(fig,axes,bg)
        for ax,n in zip(axes,range(2,13)):
            entry=data['categorical'][f'{background}/{n}']
            rgb=np.array(entry['recipe']['rgb']);rgb=np.rint(rgb*255)/255
            ax.imshow(rgb[None,:,:],aspect='auto',interpolation='nearest')
            ax.set_ylabel(str(n),rotation=0,color=fg);ax.set_xticks([]);ax.set_yticks([])
        fig.suptitle(f'H3 experimental categorical | {background} | each count jointly optimized',color=fg,fontsize=11)
        name=f'categorical-{background}-counts.png';save(fig,output/name)
        cards.append(f'<section><h2>Categorical / {background}: counts 2–12</h2><p>Every row is a separate optimization and passes float/8-bit data-mark screens. Changing count can change every color.</p><img src="{name}" alt="Independent count-specific palettes on {background}"></section>')
        for n in (4,6,8):
            entry=data['categorical'][f'{background}/{n}']
            class Ref:
                label=f'H3 experimental categorical, independent n={n}'
                def colors(self,count):
                    assert count==n
                    return tuple(map(tuple,entry['recipe']['rgb']))
            name=f'categorical-{background}-{n}.png'
            build_baseline.categorical_panel(Ref(),n,background,output/name)
            cards.append(f'<section><h3>Categorical / {background} / {n}</h3><img src="{name}" alt="Matched thin lines and small marks, all CVD conditions and grayscale"></section>')
            fig,axes=plt.subplots(2,4,figsize=(8,4.4),layout='constrained');fg=style(fig,axes,bg)
            for ax,(condition,m) in zip(axes.ravel(),entry['report']['measurements']['u8']['conditions'].items()):
                matrix=np.array(m['oklab']['distance_matrix'])
                image=ax.imshow(matrix,vmin=0,vmax=.5,cmap='cividis')
                ax.set_title(f"{condition}: min {m['oklab']['minimum_pair']:.3f}",fontsize=7,color=fg)
                ax.set_xticks(range(n));ax.set_yticks(range(n))
            fig.suptitle(f'H3 Oklab pair distances | n={n} | {background} | 8-bit export',color=fg,fontsize=10)
            fig.colorbar(image,ax=list(axes.ravel()),shrink=.65)
            name=f'categorical-{background}-{n}-distances.png';save(fig,output/name)
            cards.append(f'<details><summary>All pair-distance matrices, n={n} / {background}</summary><img src="{name}" alt="Eight Oklab distance matrices"></details>')
    for key,entry in data['ordered'].items():
        family,background=key.split('/')
        gradient=HueGradient(entry['recipe'],QualityReport(entry['report']),entry['discrete'],entry['reversed'])
        bg=to_hex(gradient.background)
        rgb=np.array([gradient.at(i/256) for i in range(257)]);q=np.rint(rgb*255)/255
        fig=plt.figure(figsize=(8,8.5),layout='constrained');grid=fig.add_gridspec(9,3,width_ratios=[1,1.5,1.5])
        ramps=[fig.add_subplot(grid[i,0]) for i in range(9)]
        panels=[fig.add_subplot(grid[0:3,1]),fig.add_subplot(grid[0:3,2]),fig.add_subplot(grid[3:6,1]),fig.add_subplot(grid[3:6,2])]
        legends=[fig.add_subplot(grid[i,1]) for i in (6,7,8)]
        trace=fig.add_subplot(grid[6:9,2]);fg=style(fig,ramps+panels+legends+[trace],bg)
        for ax,condition in zip(ramps,(*data['conditions'],'grayscale')):
            shown=gray_rgb(q) if condition=='grayscale' else condition_colors(q,condition)[0]
            ax.imshow(shown[None,:,:],aspect='auto',interpolation='nearest')
            ax.set_title(condition,fontsize=7,color=fg);ax.set_xticks([]);ax.set_yticks([])
        ripple,feature=fields('sequential' if family=='multihue' else 'spectral')
        for ax,field,condition,title in zip(panels,(ripple,ripple,feature,feature),('normal','grayscale','normal','deutan-100'),
                                          ('Known oscillating ramp','Luminance grayscale','Signed field: zero at center' if family=='spectral' else 'Known spatial features','Same field: deutan-100')):
            pixels=np.array([gradient.at(float(t)) for t in field.ravel()]);pixels=np.rint(pixels*255)/255
            pixels=gray_rgb(pixels) if condition=='grayscale' else condition_colors(pixels,condition)[0]
            ax.imshow(pixels.reshape(field.shape+(3,)),aspect='auto',interpolation='nearest')
            ax.set_title(title,fontsize=7,color=fg);ax.set_xticks([]);ax.set_yticks([])
        for ax,n in zip(legends,(5,7,9)):
            result=entry['discrete'][f'filled-fields/{n}']
            if result['screen_pass']:
                colors=gradient.discrete(n).rgb
                ax.imshow(np.array(colors)[None,:,:],aspect='auto',interpolation='nearest')
            else:
                ax.text(.5,.5,'Rejected; see criteria in numerical results',ha='center',va='center',color=fg,fontsize=6)
            ax.set_title(f'{n} bins: '+('PASS' if result['screen_pass'] else 'FAIL'),fontsize=7,color=fg);ax.set_xticks([]);ax.set_yticks([])
        for condition,linestyle in (('normal','-'),('protan-100','--'),('deutan-100',':'),('tritan-100','-.')):
            trace.plot(np.linspace(0,1,257),_lab(condition_colors(q,condition)[0])[:,0],linestyle,label=condition,linewidth=.8)
        trace.legend(fontsize=5,facecolor=bg,labelcolor=fg);trace.set_title('8-bit Oklab lightness',fontsize=7,color=fg)
        fig.suptitle(f'H3 experimental {family} | {background} | float/u8 screens PASS',color=fg,fontsize=10)
        fig.supxlabel('Cubic-path sampling; independent bin validation; human review pending',color=fg,fontsize=7)
        name=key.replace('/','-')+'.png';save(fig,output/name)
        passed=[int(k.split('/')[1]) for k,v in entry['discrete'].items() if k.startswith('filled-fields/') and v['screen_pass']]
        cards.append(f'<section><h2>{family} / {background}</h2><p>Passing cached field counts: {passed}. Failed selections are retained. Multi-hue route checks supplement the unchanged H1 order, feature, center and arm criteria.</p><img src="{name}" alt="{family} ramps, CVD, grayscale, fields and discrete legends"></section>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Huevat H3 family review</title><style>body{font:16px/1.5 system-ui;max-width:1050px;margin:auto;padding:24px;background:#eee;color:#222}section,details{background:white;padding:20px;margin:20px 0}img{width:100%;height:auto}</style><h1>H3 categorical and multi-hue review</h1><p>Experimental numerical designs; human perceptual review is pending. No approved H4 default is claimed. All H1 thresholds remain frozen.</p><p><a href="../baseline-v1/index.html">H1 attributed reference comparisons</a> · <a href="../ordered-v1/index.html">H2 single-hue/diverging</a> · <a href="../../docs/METHODS_H3.md">H3 methods and limits</a> · <a href="results.json">Results and measured budgets</a> · <a href="../../src/huevat/data/families-v1.json">Full float/8-bit reports and recipes</a></p>'''+''.join(cards)+'</html>'
    (output/'index.html').write_text(page,encoding='utf-8',newline='\n')
    write_json(output/'review.json',{'status':'pending','panels':[{'file':p.name,'status':'pending','notes':''} for p in sorted(output.glob('*.png'))]})
    write_json(output/'manifest.json',{'implementation_sha256_lf':implementation_hashes(),
        'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file() and p.name!='manifest.json'}})


def benchmark():
    script="""
import json,sys,time
t=time.perf_counter();import huevat as hv
import_time=time.perf_counter()-t
t=time.perf_counter();p=hv.categorical(8);g=hv.spectral();s=hv.multihue()
lookup_time=time.perf_counter()-t
t=time.perf_counter();[g.at(i/4095) for i in range(4096)]
print(json.dumps({'core_import_seconds':import_time,'three_cold_lookups_seconds':lookup_time,'4096_samples_seconds':time.perf_counter()-t,'optional_modules_loaded':[n for n in ('numpy','scipy','colorspacious','matplotlib','playwright') if n in sys.modules]}))
"""
    result=json.loads(subprocess.check_output([sys.executable,'-I','-c',script],text=True))
    script="import tracemalloc;tracemalloc.start();import huevat as hv;p=hv.categorical(8);g=hv.spectral();print(tracemalloc.get_traced_memory()[1])"
    result['peak_traced_python_bytes_separate_run']=int(subprocess.check_output([sys.executable,'-I','-c',script],text=True))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    output=ROOT/'research/families-v1'
    if args.check:
        data=load_data('families-v1.json')
        if data['implementation_sha256_lf']!=implementation_hashes():
            raise SystemExit('H3 implementation differs from recorded source hashes')
        for key,entry in data['categorical'].items():
            compact_compare({k:v for k,v in entry['report'].items() if k!='search'},validate_categorical(entry['recipe']))
        print('Reproduced 22 independent categorical float/u8 reports',flush=True)
        for key,entry in data['ordered'].items():
            g=HueGradient(entry['recipe'],QualityReport({}),{})
            compact_compare({k:v for k,v in entry['report'].items() if k not in ('search','construction_parameters')},validate_ordered(g))
            rebuilt=make_ordered_recipe(g.family,entry['report']['construction_parameters'],entry['recipe']['preferences'],g.background,entry['recipe']['context'],entry['recipe']['identifier'])
            compact_compare(entry['recipe'],rebuilt);compact_compare(entry['discrete'],discrete_records(g))
            print('Reproduced',key,'continuous and count-specific evidence',flush=True)
        manifest=json.loads((output/'manifest.json').read_text(encoding='utf-8'))
        for name,digest in manifest['files'].items():
            if hashlib.sha256((output/name).read_bytes()).hexdigest()!=digest:raise SystemExit('H3 artifact hash mismatch: '+name)
        return
    data={'version':'h3-experimental-families-v1','profile_version':'h1-screening-v1','conditions':['normal','protan-50','protan-80','protan-100','deutan-50','deutan-80','deutan-100','tritan-100'],
          'implementation_sha256_lf':implementation_hashes(),'categorical':{},'ordered':{}}
    timings={}
    for background in ('light','dark'):
        for n in range(2,13):
            p=generate_categorical(n,background=background,starts=2,max_seconds=120)
            recipe=p.to_recipe()['recipe'];recipe['identifier']=f'h3-experimental-categorical-{background}-{n}-v1'
            report=validate_categorical(recipe);report['search']=p.report.to_dict()['search']
            key=f'{background}/{n}';data['categorical'][key]={'recipe':recipe,'report':report}
            timings['categorical/'+key]=report['search']['elapsed_seconds']
            print('categorical',key,'PASS',flush=True)
    for family,colors in (('multihue',MULTIHUE_COLORS),('spectral',SPECTRAL_COLORS)):
        for background in ('light','dark'):
            g=generate_ordered(family,colors,background=background,starts=2,max_seconds=120)
            recipe=g.to_recipe()['recipe'];reverse=recipe.pop('reversed');recipe['identifier']=f'h3-experimental-{family}-{background}-v1'
            source=HueGradient(recipe,QualityReport({}),{});report=validate_ordered(source)
            for name in ('search','construction_parameters'):report[name]=g._report.to_dict()[name]
            key=f'{family}/{background}';data['ordered'][key]={'recipe':recipe,'report':report,'reversed':reverse,'discrete':discrete_records(source)}
            timings[key]=report['search']['elapsed_seconds'];print(key,'PASS',flush=True)
    path=ROOT/'src/huevat/data/families-v1.json';write_json(path,data)
    manifest_path=ROOT/'src/huevat/data/manifest-v1.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['sha256_lf'][path.name]=hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest();write_json(manifest_path,manifest)
    output.mkdir(parents=True,exist_ok=True)
    write_json(output/'results.json',{'version':data['version'],'profile_version':data['profile_version'],'visual_review':'pending','approved_defaults':[],
        'generation_seconds_by_family_count':timings,'benchmark':benchmark(),
        'categorical':{k:{'hex':v['report']['hex'],'screen_pass':v['report']['screen_pass']} for k,v in data['categorical'].items()},
        'ordered':{k:{'screen_pass':v['report']['screen_pass'],'hue_routes':v['report']['hue_routes'],
                      'discrete':{n:{'screen_pass':r['screen_pass'],'failures':[c for c in r['checks'] if not c['passed']]} for n,r in v['discrete'].items()}} for k,v in data['ordered'].items()}})
    render(data,output)


if __name__=='__main__':main()
