"""Build/recheck prepared H2 designs, discrete evidence and offline review panels."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR",str(ROOT/".cache/matplotlib"))

import numpy as np
from huevat import from_hex, to_hex
from huevat._data import load_data
from huevat._discrete import screen_discrete
from huevat.design import generate, make_recipe, validate_gradient
from huevat.gradients import Gradient, QualityReport, fingerprint, _arc_bound


def implementation_hashes():
    return {name:hashlib.sha256((ROOT/'src/huevat'/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            for name in ('gradients.py','design.py','_certify.py','_discrete.py')}


def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding="utf-8",newline="\n")


def compact_compare(old,new,path="root"):
    if isinstance(old,dict):
        if set(old)!=set(new):
            raise ValueError("Different report keys at "+path)
        for key in old:
            compact_compare(old[key],new[key],path+"/"+key)
    elif isinstance(old,(list,tuple)):
        if len(old)!=len(new):
            raise ValueError("Different array lengths at "+path)
        for i,(a,b) in enumerate(zip(old,new)):
            compact_compare(a,b,path+f"/{i}")
    elif isinstance(old,(int,float)) and not isinstance(old,bool):
        import math
        if not math.isclose(old,new,rel_tol=1e-8,abs_tol=1e-8):
            raise ValueError(f"Different measurement at {path}: {old} != {new}")
    elif old!=new:
        raise ValueError("Different report value at "+path)


def records(gradient):
    result={}
    for context in ("filled-fields","data-marks"):
        minimum=.04 if context=='filled-fields' else .08
        import math
        limit=math.floor((_arc_bound(gradient._recipe['segments'])+1e-12)/minimum)+1
        for n in range(2,limit+1):
            rgb=tuple(gradient.at(i/(n-1)) for i in range(n))
            result[f"{context}/{n}"]=screen_discrete(rgb,gradient.at(.5),gradient.family,gradient.background,context)
    return result


def render(data,output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from huevat.evaluation import condition_colors,gray_rgb,_lab
    from build_baseline import fields, style
    output.mkdir(parents=True,exist_ok=True)
    cards=[]
    def save(fig,path):
        fig.savefig(path,dpi=300,facecolor=fig.get_facecolor(),metadata={'Software':'Huevat H2 ordered-v1'})
        plt.close(fig)
    for key,entry in data["designs"].items():
        family,background=key.split('/')
        gradient=Gradient(entry["recipe"],QualityReport(entry["report"]),entry["discrete"],entry["reversed"])
        rgb=np.array([gradient.at(i/256) for i in range(257)])
        def sample_field(field,condition):
            colors=np.array([gradient.at(float(t)) for t in field.ravel()])
            colors=np.rint(colors*255)/255
            colors=gray_rgb(colors) if condition=='grayscale' else condition_colors(colors,condition)[0]
            return np.rint(colors.reshape(field.shape+(3,))*255).astype(np.uint8)
        fig,axes=plt.subplots(4,3,figsize=(8,7.2),layout="constrained")
        bg=to_hex(gradient.background)
        fg=style(fig,axes,bg)
        for row,condition in enumerate(("normal","protan-100","deutan-100","tritan-100")):
            transformed=condition_colors(np.rint(rgb*255)/255,condition)[0]
            axes[row,0].imshow(np.rint(transformed[None,:,:]*255).astype(np.uint8),aspect="auto",interpolation="nearest")
            axes[row,0].set_title(condition,fontsize=8,color=fg)
            axes[row,0].set_xticks([]);axes[row,0].set_yticks([])
        ripple,feature=fields(family)
        for ax,field,condition,title in ((axes[0,1],ripple,"normal","Known oscillating ramp"),
                                         (axes[0,2],ripple,"grayscale","Luminance grayscale"),
                                         (axes[1,1],feature,"normal","Signed / known feature field"),
                                         (axes[1,2],feature,"deutan-100","Same field: deutan-100")):
            ax.imshow(sample_field(field,condition),aspect="auto",interpolation="nearest")
            ax.set_title(title,fontsize=8,color=fg);ax.set_xticks([]);ax.set_yticks([])
        for ax,n in ((axes[2,1],5),(axes[2,2],7)):
            try:
                palette=gradient.discrete(n)
                ax.imshow(np.array(palette.rgb)[None,:,:],aspect="auto",interpolation="nearest")
                title=f"{n} bins: PASS"
            except ValueError as error:
                ax.text(.5,.5,f"{n} bins rejected\n"+str(error)[:90],ha="center",va="center",wrap=True,fontsize=7,color=fg)
                title=f"{n} bins: FAIL"
            ax.set_title(title,fontsize=8,color=fg);ax.set_xticks([]);ax.set_yticks([])
        labs=_lab(rgb)
        axes[3,1].plot(np.linspace(0,1,257),labs[:,0],linewidth=1)
        axes[3,1].set_title("Oklab lightness",fontsize=8,color=fg)
        axes[3,2].plot(np.linspace(0,1,256),np.linalg.norm(np.diff(labs,axis=0),axis=1),linewidth=.8)
        axes[3,2].set_title("Oklab step, floating path",fontsize=8,color=fg)
        fig.suptitle(f"H2 experimental {family} | {background} | float/u8 screens PASS",color=fg,fontsize=11)
        filename=key.replace('/','-')+'.png'
        save(fig,output/filename)
        diagnostic=plt.figure(figsize=(7.2,7.4),layout='constrained')
        grid=diagnostic.add_gridspec(9,2,width_ratios=[1,1.7])
        ramps=[diagnostic.add_subplot(grid[i,0]) for i in range(9)]
        traces=[diagnostic.add_subplot(grid[0:4,1]),diagnostic.add_subplot(grid[4:9,1])]
        style(diagnostic,ramps+traces,bg)
        from huevat import load_profile
        conditions=load_profile()['conditions']+['grayscale']
        for ax,condition in zip(ramps,conditions):
            source=np.rint(rgb*255)/255
            shown=gray_rgb(source) if condition=='grayscale' else condition_colors(source,condition)[0]
            ax.imshow(np.rint(shown[None,:,:]*255).astype(np.uint8),aspect='auto',interpolation='nearest')
            ax.set_title(condition,fontsize=7,color=fg);ax.set_xticks([]);ax.set_yticks([])
        quantized=np.rint(rgb*255)/255
        for values,label,linestyle in ((rgb,'float','-'),(quantized,'8-bit',':')):
            lab=_lab(values)
            traces[0].plot(np.linspace(0,1,257),lab[:,0],linestyle,label=label,linewidth=1)
            traces[1].plot(np.linspace(0,1,256),np.linalg.norm(np.diff(lab,axis=0),axis=1),linestyle,label=label,linewidth=.8)
        traces[0].set_title('Normal lightness: float and quantized',fontsize=8,color=fg)
        traces[1].set_title('Normal Oklab step: float and quantized',fontsize=8,color=fg)
        for ax in traces:
            ax.legend(fontsize=7,facecolor=bg,labelcolor=fg)
            ax.set_xlabel('Parameter t',fontsize=7)
        diagnostic.suptitle(f'H2 {family} | {background} | all screened viewing conditions',fontsize=10,color=fg)
        diagnostic_name=key.replace('/','-')+'-screening.png'
        save(diagnostic,output/diagnostic_name)
        passed=[int(k.split('/')[1]) for k,r in entry['discrete'].items() if k.startswith('filled-fields/') and r['screen_pass']]
        cards.append(f'<section><h2>{family} / {background}</h2><p>Passing cached filled-field counts: {passed}. Every count below the curve-length bound is audited; larger counts are rejected with that bound. No accepted H4 default is claimed.</p><img src="{filename}" alt="{family} on {background} background"><details><summary>All CVD severities, grayscale and export diagnostics</summary><img src="{diagnostic_name}" alt="All screened conditions for {family} on {background}"></details></section>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Huevat H2 ordered gradients</title><style>body{font:16px/1.5 system-ui;max-width:1000px;margin:auto;padding:24px;background:#eee;color:#222}section{padding:20px;margin:24px 0;background:white}img{width:100%;height:auto}</style><h1>H2 ordered-gradient review</h1><p>Four experimental prepared paths pass the unchanged H1 profiles in both floating point and 8-bit export. Complete-segment gamut/C1/order certificates supplement a 4,097-point CVD ordering audit. These are numerical screens; perceptual review remains pending.</p><p><a href="results.json">Numerical results and measured generation budgets</a> · <a href="../../docs/METHODS_H2.md">Methods and limitations</a></p>'''+''.join(cards)+'</html>'
    page=page.replace('</h1>','</h1><p><a href="../baseline-v1/index.html">H1 published-reference comparison gallery</a></p>',1)
    (output/'index.html').write_text(page,encoding='utf-8',newline='\n')
    write_json(output/'review.json',{'status':'pending','panels':[{'file':p.name,'status':'pending','notes':''} for p in sorted(output.glob('*.png'))]})
    write_json(output/'manifest.json',{'implementation_sha256_lf':implementation_hashes(),
                                     'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file() and p.name!='manifest.json'}})


def benchmark():
    script="""
import json,sys,time
t=time.perf_counter()
import huevat as hv
import_seconds=time.perf_counter()-t
t=time.perf_counter(); g=hv.sequential(); lookup_seconds=time.perf_counter()-t
t=time.perf_counter(); [g.at(i/4095) for i in range(4096)]; sample_seconds=time.perf_counter()-t
print(json.dumps({'core_import_seconds':import_seconds,'cold_prepared_lookup_seconds':lookup_seconds,'4096_samples_seconds':sample_seconds,'optional_modules_loaded':[n for n in ('numpy','scipy','colorspacious','matplotlib','playwright') if n in sys.modules]}))
"""
    result=json.loads(subprocess.check_output([sys.executable,'-I','-c',script],text=True))
    memory_script="import tracemalloc; tracemalloc.start(); import huevat as hv; g=hv.sequential(); [g.at(i/4095) for i in range(4096)]; print(tracemalloc.get_traced_memory()[1])"
    result['peak_traced_python_bytes_separate_run']=int(subprocess.check_output([sys.executable,'-I','-c',memory_script],text=True))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    output=ROOT/'research/ordered-v1'
    if args.check:
        data=load_data('ordered-v1.json')
        if data['implementation_sha256_lf']!=implementation_hashes():
            raise SystemExit('H2 implementation differs from its recorded source hashes')
        for key,entry in data['designs'].items():
            source=Gradient(entry['recipe'],QualityReport(entry['report']),{})
            refreshed=validate_gradient(source)
            expected={k:v for k,v in entry['report'].items() if k not in ('search','construction_parameters','gamut_fallback')}
            compact_compare(expected,refreshed)
            rebuilt=make_recipe(source.family,entry['report']['construction_parameters'],tuple(entry['recipe']['preferences']),source.background,entry['recipe']['context'],entry['recipe']['identifier'])
            compact_compare(entry['recipe'],rebuilt)
            compact_compare(entry['discrete'],records(source))
            print('Reproduced',key,'continuous and discrete evidence',flush=True)
        manifest=json.loads((output/'manifest.json').read_text(encoding='utf-8'))
        for name,digest in manifest['files'].items():
            if hashlib.sha256((output/name).read_bytes()).hexdigest()!=digest:
                raise SystemExit('H2 review artifact hash mismatch: '+name)
        return
    data={'version':'h2-experimental-ordered-v1','profile_version':'h1-screening-v1','implementation_sha256_lf':implementation_hashes(),'designs':{}}
    timings={}
    for family in ('sequential','diverging'):
        preferences=('#0072b2',) if family=='sequential' else ('#0072b2','#d55e00')
        for background in ('light','dark'):
            started=time.perf_counter()
            generated=generate(family,preferences,background=background,starts=2,max_seconds=60.)
            source_recipe=generated.to_recipe()['recipe']
            reverse=source_recipe.pop('reversed')
            source_recipe['identifier']=f'h2-experimental-{family}-{background}-v1'
            source=Gradient(source_recipe,QualityReport({}),{})
            report=validate_gradient(source)
            original=generated._report.to_dict()
            for name in ('search','construction_parameters','gamut_fallback'):
                report[name]=original[name]
            if not report['screen_pass']:
                raise SystemExit('Prepared path failed '+family+'/'+background)
            discrete=records(source)
            key=f'{family}/{background}'
            data['designs'][key]={'recipe':source_recipe,'report':report,'reversed':reverse,'discrete':discrete}
            timings[key]=time.perf_counter()-started
            print(key,'PASS; passing field counts',[int(k.split('/')[1]) for k,r in discrete.items() if k.startswith('filled-fields/') and r['screen_pass']],flush=True)
    data_path=ROOT/'src/huevat/data/ordered-v1.json'
    write_json(data_path,data)
    manifest_path=ROOT/'src/huevat/data/manifest-v1.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['sha256_lf']['ordered-v1.json']=hashlib.sha256(data_path.read_bytes()).hexdigest()
    write_json(manifest_path,manifest)
    write_json(output/'results.json',{'generation_seconds_including_discrete_audits':timings,'core_benchmark':benchmark(),'discrete_audit_count':sum(len(entry['discrete']) for entry in data['designs'].values()),'designs':{key:{'screen_pass':entry['report']['screen_pass'],'search':entry['report']['search'],'certificate':entry['report']['certificate']} for key,entry in data['designs'].items()},'visual_review':'pending'})
    render(data,output)


if __name__=='__main__':
    main()
