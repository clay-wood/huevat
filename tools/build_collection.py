"""Construct/revalidate H4b candidates and build their offline application gallery."""
import argparse
import hashlib
import gzip
import importlib.metadata as md
import json
import math
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'research/collection-v1'
RESOURCE=ROOT/'src/huevat/data/collection-v1.json'
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache/matplotlib'))

import numpy as np
import huevat as hv
from huevat._collection_specs import SPECS, VERSION, specification
from huevat._collection_design import generate, make_recipe
from huevat.gradients import Gradient, QualityReport, fingerprint
from huevat._discrete import screen_discrete
from huevat.design import validate_gradient
from huevat.evaluation import evaluate, condition_colors, gray_rgb
from verify import compare as compact_compare
from collection_fields import seismic,structure,terrain,atmosphere


def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,separators=(',',':'),sort_keys=True,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def digest(path):return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def implementation_hashes():
    return {n:digest(ROOT/'src/huevat'/n) for n in ('catalog.py','_collection_specs.py','_collection_design.py')}


def audit(name,recipe):
    report=validate_gradient(Gradient(recipe,QualityReport({}),{}))
    version=int(recipe['identifier'].rsplit('-v',1)[1])
    report.update(collection_construction_version=specification(name,version).get('construction_version',VERSION),collection_name=name,family=recipe['family'])
    return report


def discrete_records(g):
    return {f'{context}/{n}':screen_discrete(tuple(g.at(i/(n-1)) for i in range(n)),g.at(.5),g.family,g.background,context)
            for context in ('filled-fields','data-marks') for n in (2,3,5,7,8,9,11)}


def construct(refresh=None):
    data=json.loads(RESOURCE.read_text()) if RESOURCE.exists() else {'version':'h4b-collection-v1','construction_version':VERSION,'profile_version':'h1-screening-v1',
        'implementation_sha256_lf':implementation_hashes(),'protocol_commit':'5c101d3',
        'approved_defaults':[],'visual_review':'pending','candidates':{},'failures':{}}
    for name,spec in SPECS.items():
        if refresh and name not in refresh:continue
        metadata={k:spec[k] for k in ('label','route','family','domains','orientation')}
        metadata.update(name=name,version=1,status='supported',approved_default=False,
                        recipe_format='h2-ordered-v1',construction_version=VERSION,
                        context='filled-fields',normalization='chosen explicitly from physical data; no implied bin boundaries')
        entry={'metadata':metadata,'variants':{}}
        metadata['version']=spec.get('version',1)
        metadata['construction_version']=spec.get('construction_version',VERSION)
        previous=data['candidates'].get(name,{})
        for bg in ('light','dark'):
            data['failures'].pop(name+'/'+bg,None)
            try:
                g=generate(name,bg,max_seconds=120)
                entry['variants'][bg]={'recipe':dict(g.to_recipe()['recipe']),'report':g._report.to_dict(),
                                        'discrete':discrete_records(Gradient(g._recipe,g._report,{})),
                                        'reversed':g._reverse}
                entry['variants'][bg]['recipe'].pop('reversed')
                old=previous.get('variants',{}).get(bg)
                if old and old['recipe']['identifier']!=entry['variants'][bg]['recipe']['identifier']:
                    data.setdefault('archived',{})[old['recipe']['identifier']]=old
                print(name,bg,'PASS',g.report['search']['candidates_tested'],flush=True)
            except hv.SearchExhaustedError as error:
                data['failures'][name+'/'+bg]=error.report.to_dict()
                print(name,bg,'SEARCH EXHAUSTED',flush=True)
        metadata['available_backgrounds']=list(entry['variants'])
        data['candidates'][name]=entry
    OUTPUT.mkdir(parents=True,exist_ok=True)
    archive=OUTPUT/'construction.json.gz'
    searches=json.loads(gzip.decompress(archive.read_bytes())) if archive.exists() else {}
    for identifier,v in data.get('archived',{}).items():
        search=v['report']['search']
        old_key=identifier.removeprefix('h4b-').rsplit('-v',1)[0].rsplit('-',1)
        if identifier not in searches:
            searches[identifier]=searches['/'.join(old_key)].copy()
        search['rejection_evidence']='research/collection-v1/construction.json.gz#'+identifier
    for name,entry in data['candidates'].items():
        for bg,v in entry['variants'].items():
            search=v['report']['search']
            search['algorithm_version']=SPECS[name].get('construction_version',VERSION)
            if 'rejected' in search:
                searches[name+'/'+bg]=search.copy()
                search['rejected_count']=len(search.pop('rejected'))
                search['rejection_evidence']='research/collection-v1/construction.json.gz#'+name+'/'+bg
    searches['failed_searches']=data['failures']
    archive.write_bytes(gzip.compress(json.dumps(searches,sort_keys=True,allow_nan=False).encode('utf-8'),mtime=0))
    data['implementation_sha256_lf']=implementation_hashes()
    data['construction_versions']=sorted({entry['metadata']['construction_version'] for entry in data['candidates'].values()})
    write_json(RESOURCE,data)
    manifest=ROOT/'src/huevat/data/manifest-v1.json'
    m=json.loads(manifest.read_text());m['sha256_lf']['collection-v1.json']=digest(RESOURCE);write_json(manifest,m)
    return data


def control_arrays():
    x=np.linspace(0,1,257)
    from matplotlib import colormaps
    rainbow=np.asarray(colormaps['jet'](x))[:,:3]
    plateau=x.copy();plateau[(x>.35)&(x<.65)]=.5
    plateau=np.repeat(plateau[:,None],3,axis=1)
    good=hv.diverging();wrong_center=np.array([good.at(float(t**2)) for t in x])
    return [('hue-rainbow',rainbow,'sequential'),('gray-plateau',plateau,'sequential'),('misplaced-neutral',wrong_center,'diverging')]


def controls():
    result={}
    for name,rgb,family in control_arrays():
        r=evaluate(rgb,family,encoding='u8')
        result[name]={'screen_pass':r['screen_pass'],'failed_criteria':[c for c in r['criteria'] if not c['passed']]}
        assert not r['screen_pass'],name
    return result


def style(fig,axes,bg):
    color='#ffffff' if bg=='light' else '#121212';fg='#26323b' if bg=='light' else '#e4e7eb'
    fig.patch.set_facecolor(color)
    for ax in np.asarray(axes,dtype=object).ravel():
        ax.set_facecolor(color);ax.tick_params(colors=fg,labelsize=7)
        ax.title.set_color(fg);ax.xaxis.label.set_color(fg);ax.yaxis.label.set_color(fg)
        for spine in ax.spines.values():spine.set_edgecolor('#83909b')
    return fg


def save(fig,name):
    import matplotlib.pyplot as plt
    fig.savefig(OUTPUT/name,dpi=200,facecolor=fig.get_facecolor(),metadata={'Software':'Huevat H4b collection v1'})
    plt.close(fig)


def shown(rgb,condition):
    shape=rgb.shape;values=np.rint(np.clip(rgb.reshape(-1,3),0,1)*255)/255
    transformed=gray_rgb(values) if condition=='grayscale' else condition_colors(values,condition)[0]
    return np.rint(np.clip(transformed,0,1)*255).astype(np.uint8).reshape(shape)


def map_values(g,values,lo,hi,center=None,log=False):
    from matplotlib.colors import ListedColormap, Normalize, TwoSlopeNorm, LogNorm
    # Dense native lookup; the H4a tests separately measure adapter approximation.
    cmap=ListedColormap([g.at(i/4096) for i in range(4097)])
    norm=LogNorm(lo,hi) if log else Normalize(lo,hi) if center is None else TwoSlopeNorm(center,vmin=lo,vmax=hi)
    cmap=cmap.with_extremes(bad='#8c8c8c')
    rgb=cmap(norm(np.ma.masked_invalid(values)))[:,:,:3]
    if log:rgb[np.isfinite(values)&(values<=0)]=[.90,.84,.70]
    return rgb,cmap,norm


def field_for(name):
    if name=='bathymetry':
        f=terrain();z=f['data'];return np.where(z<=0,-z,np.nan),0,4000,None,'Water depth (m)',(0,80,0,60),False
    if name=='highland':
        f=terrain();z=f['data'];return np.where(z>=0,z,np.nan),0,3000,None,'Elevation above sea level (m)',(0,80,0,60),False
    if SPECS[name]['family']=='diverging':
        f=seismic();return f['data'],-1,1,0,'Signed amplitude (a.u.)',(0,12,2.4,0),False
    if name=='lagoon':
        f=atmosphere();return f['moisture'],0,18,None,'Moisture (g/kg)',(0,1000,0,700),False
    if name=='aerosol':
        f=atmosphere();return f['concentration'],.01,100,None,'Concentration (a.u.; log10)',(0,1000,0,700),True
    f=structure();return f['data'],2,5,None,'Velocity (km/s)',(0,12,5,0),False


def overview(bg):
    import matplotlib.pyplot as plt
    names=hv.gradient_names();fig,axes=plt.subplots(len(names),1,figsize=(9,.6*len(names)+.8),layout='constrained')
    fg=style(fig,axes,bg)
    for ax,name in zip(axes,names):
        g=hv.gradient(name,background=bg)
        rgb=np.array([g.at(i/512) for i in range(513)])
        ax.imshow(shown(rgb[None,:,:],'normal'),aspect='auto',interpolation='nearest')
        ax.set_ylabel(name,rotation=0,ha='right',va='center',color=fg,fontsize=9)
        # The neutral is part of the sampled colors; an overlaid reference
        # line looks like a defect in the palette, especially in the overview.
        ax.set_xticks([]);ax.set_yticks([])
    fig.suptitle(f'{len(names)} named gradients · {bg} background · supported collection',color=fg,fontsize=12)
    save(fig,f'overview-{bg}.png')


def diagnostics(name,bg):
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    g=hv.gradient(name,background=bg);values,lo,hi,center,label,extent,log=field_for(name)
    rgb,cmap,norm=map_values(g,values,lo,hi,center,log)
    conditions=hv.load_profile()['conditions']+['grayscale']
    fig,axes=plt.subplots(3,3,figsize=(9,7),layout='constrained');fg=style(fig,axes,bg)
    for ax,condition in zip(axes.ravel(),conditions):
        ax.imshow(shown(rgb,condition),extent=extent,aspect='auto',interpolation='nearest')
        ax.set_title(condition,fontsize=9);ax.set_xticks([]);ax.set_yticks([])
        display=ListedColormap(shown(np.array([g.at(i/512) for i in range(513)]),condition)/255)
        bar=fig.colorbar(__import__('matplotlib').cm.ScalarMappable(norm=norm,cmap=display),ax=ax,orientation='horizontal',fraction=.12,pad=.04)
        bar.ax.tick_params(colors=fg,labelsize=6)
    fig.suptitle(f'{name.title()} Â· {bg} Â· {label}\nSame synthetic field/range; 8-bit output; numeric screens pass / supported collection',color=fg,fontsize=10)
    save(fig,f'{name}-{bg}-conditions.png')


def applications(bg):
    import matplotlib.pyplot as plt
    from matplotlib.colors import LightSource
    from matplotlib.cm import ScalarMappable
    from matplotlib.patches import Patch
    from scipy.ndimage import distance_transform_edt
    f=seismic();fig,axes=plt.subplots(1,3,figsize=(11,5),layout='constrained');fg=style(fig,axes,bg)
    for ax,name in zip(axes[:2],('balance','strata')):
        g=hv.gradient(name,background=bg);rgb,cmap,norm=map_values(g,f['data'],-1,1,0)
        ax.imshow(shown(rgb,'normal'),extent=(0,12,2.4,0),aspect='auto',interpolation='nearest')
        ax.set_title(name.title()+' Â· signed raster',fontsize=10);ax.set_xlabel('Distance (km)');ax.set_ylabel('Two-way time (s)')
        bar=fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),ax=ax,orientation='horizontal',fraction=.06)
        bar.set_label('Amplitude (a.u.)',color=fg,fontsize=8);bar.ax.tick_params(colors=fg,labelsize=7)
    ax=axes[2];g=hv.gradient('balance',background=bg)
    for i in range(0,len(f['x']),8):
        x=f['x'][i];v=f['data'][:,i];line=x+.43*v
        ax.plot(line,f['time'],color=fg,lw=.6)
        ax.fill_betweenx(f['time'],x,line,where=v>=0,color=g.at(.8),linewidth=0)
        ax.fill_betweenx(f['time'],x,line,where=v<0,color=g.at(.2),linewidth=0)
    ax.set_ylim(2.4,0);ax.set_xlim(0,12);ax.set_xlabel('Distance (km)');ax.set_ylabel('Two-way time (s)')
    ax.set_title('Wiggles Â· positive / negative fill',fontsize=10)
    fig.suptitle('Synthetic seismic Â· 25 Hz Ricker Â· dipping/faulted horizons Â· 18 ms thin bed Â· weak reflector\nPositive central lobe is positive reflectivity; downward time does not reverse polarity',color=fg,fontsize=10)
    save(fig,f'seismic-{bg}.png')

    f=terrain();z=f['data'];land=hv.gradient('highland',background=bg);water=hv.gradient('bathymetry',background=bg)
    landrgb,lc,ln=map_values(land,np.maximum(z,0),0,3000)
    waterrgb,wc,wn=map_values(water,np.maximum(-z,0),0,4000)
    rgb=np.where((z>=0)[:,:,None],landrgb,waterrgb);rgb[~np.isfinite(z)]=.55
    # Fill only the lighting derivative calculation, preserving original data
    # and the displayed missing mask; a zero fill would create a false cliff.
    nearest=distance_transform_edt(~np.isfinite(z),return_distances=False,return_indices=True)
    lighting_surface=z[tuple(nearest)]
    shaded=LightSource(azdeg=315,altdeg=45).shade_rgb(rgb,lighting_surface,dx=80000/(z.shape[1]-1),dy=60000/(z.shape[0]-1),vert_exag=8,blend_mode='soft')
    shaded[~np.isfinite(z)]=.55
    fig,axes=plt.subplots(1,2,figsize=(10,5),layout='constrained');fg=style(fig,axes,bg)
    for ax,image,title in zip(axes,(rgb,shaded),('Unshaded branches','Hillshade composite Â· separate review')):
        ax.imshow(shown(image,'normal'),origin='lower',extent=(0,80,0,60),interpolation='nearest')
        ax.contour(f['x'],f['y'],z,levels=[0],colors=fg,linewidths=.6)
        ax.set_title(title,fontsize=10);ax.set_xlabel('Distance (km)');ax.set_ylabel('Distance (km)')
    for cmap,norm,label in ((wc,wn,'Water depth (m below sea level)'),(lc,ln,'Land elevation (m above sea level)')):
        bar=fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),ax=list(axes),orientation='horizontal',fraction=.055,pad=.06)
        bar.set_label(label,color=fg,fontsize=8);bar.ax.tick_params(colors=fg,labelsize=7)
    fig.suptitle('Synthetic terrain Â· explicit sea level at 0 m Â· two independent sequential branches\nGray patch: missing data. Shading uses 8Ã— vertical exaggeration; combined/shaded colors have no palette-profile pass.',color=fg,fontsize=10)
    save(fig,f'terrain-{bg}.png')

    f=atmosphere();fig,axes=plt.subplots(1,3,figsize=(11,4),layout='constrained');fg=style(fig,axes,bg)
    for ax,name,key,limits,center,log,label in (
        (axes[0],'lagoon','moisture',(0,18),None,False,'Moisture (g/kg; linear)'),
        (axes[1],'aerosol','concentration',(.01,100),None,True,'Concentration (a.u.; log10)'),
        (axes[2],'thermal','anomaly',(-4,4),0,False,'Temperature anomaly (K; center 0)')):
        values=f[key];rgb,cmap,norm=map_values(hv.gradient(name,background=bg),values,*limits,center,log)
        if log:rgb[np.isfinite(values)&(values<=0)]=[.90,.84,.70]
        ax.imshow(shown(rgb,'normal'),origin='lower',extent=(0,1000,0,700),aspect='auto',interpolation='nearest')
        ax.set_title(label,fontsize=9);ax.set_xlabel('Distance (km)');ax.set_ylabel('Distance (km)')
        bar=fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),ax=ax,orientation='horizontal',fraction=.10)
        bar.ax.tick_params(colors=fg,labelsize=7)
    axes[1].legend(handles=[Patch(facecolor=(.9,.84,.7),label='No signal (â‰¤0; outside log)'),Patch(facecolor='.55',label='Missing')],fontsize=6,loc='upper right',facecolor='#ffffff' if bg=='light' else '#121212',labelcolor=fg)
    fig.suptitle('Synthetic atmosphere Â· same original units and explicitly stated normalization\nNo-signal and missing cells remain distinct; these fields are illustrative.',color=fg,fontsize=10)
    save(fig,f'atmosphere-{bg}.png')

    f=structure();fig,axes=plt.subplots(2,2,figsize=(9,6),layout='constrained');fg=style(fig,axes,bg)
    for ax,name in zip(axes.ravel(),('mineral','ember','ink','rosewood')):
        rgb,cmap,norm=map_values(hv.gradient(name,background=bg),f['data'],2,5)
        ax.imshow(shown(rgb,'normal'),extent=(0,12,5,0),aspect='auto',interpolation='nearest')
        ax.set_title(name.title(),fontsize=10);ax.set_xlabel('Distance (km)');ax.set_ylabel('Depth (km)')
        bar=fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),ax=ax,orientation='horizontal',fraction=.09)
        bar.set_label('Velocity (km/s)',color=fg,fontsize=8);bar.ax.tick_params(colors=fg,labelsize=7)
    fig.suptitle('Synthetic structure Â· identical 2â€“5 km/s range Â· weak 0.04 km/s anomaly',color=fg,fontsize=10)
    save(fig,f'structure-{bg}.png')


def negative_panel():
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(3,2,figsize=(9,6),layout='constrained');fg=style(fig,axes,'light')
    for row,(name,rgb,family) in enumerate(control_arrays()):
        axes[row,0].imshow(shown(rgb[None,:,:],'normal'),aspect='auto',interpolation='nearest')
        axes[row,0].set_title(name+' Â· rejected',fontsize=10)
        data=seismic()['data'] if family=='diverging' else (structure()['data']-2)/3
        if family=='diverging':data=(data+1)/2
        colors=rgb[np.rint(np.clip(data,0,1)*256).astype(int)]
        axes[row,1].imshow(shown(colors,'normal'),aspect='auto',interpolation='nearest')
        axes[row,1].set_title('Same reference field Â· normal vision',fontsize=9)
        for ax in axes[row]:ax.set_xticks([]);ax.set_yticks([])
    fig.suptitle('Deliberately bad controls Â· retained failures under the unchanged profiles',color=fg,fontsize=11)
    save(fig,'negative-controls.png')


def render(data):
    import matplotlib
    matplotlib.use('Agg')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    for bg in ('light','dark'):
        overview(bg);applications(bg)
        for name in data['candidates']:
            if bg in data['candidates'][name]['variants']:diagnostics(name,bg)
    negative=controls();write_json(OUTPUT/'negative-controls.json',negative);negative_panel()
    cards=[]
    for name,entry in data['candidates'].items():
        m=entry['metadata'];thumbs=''.join(f'<a href="{name}-{bg}-conditions.png">{bg}: all CVD and grayscale</a> ' for bg in entry['variants'])
        counts={bg:[int(k.split('/')[1]) for k,r in v['discrete'].items() if k.startswith('filled-fields/') and r['screen_pass']] for bg,v in entry['variants'].items()}
        cards.append(f'<article data-family="{m["family"]}" data-domains="{" ".join(m["domains"])}"><h3>{m["label"]}</h3><p>{m["route"]}</p><p>{m["family"]} Â· {", ".join(m["domains"])} Â· {m["orientation"]}</p><p>{thumbs}</p><p>Prepared passing uniform counts: {counts}</p><code>hv.gradient("{name}", background="light")</code></article>')
    apps=''.join(f'<section><h2>{label}</h2><div class="pair"><img src="{kind}-light.png" alt="{label}, light background" loading="lazy"><img src="{kind}-dark.png" alt="{label}, dark background" loading="lazy"></div></section>' for kind,label in [('seismic','Seismic polarity and weak features'),('structure','Structural properties and weak anomalies'),('terrain','Sea level, terrain and separate hillshade review'),('atmosphere','Moisture, concentration and anomalies')])
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Huevat Â· gradient collection</title><style>body{font:16px/1.55 system-ui;background:#eef0f3;color:#26313d;margin:auto;max-width:1350px;padding:30px}h1{font-size:38px;letter-spacing:-1px}h2{font-size:25px}section,article{background:white;padding:22px;border-radius:12px;margin:20px 0}img{max-width:100%;height:auto}.pair{display:grid;grid-template-columns:1fr 1fr;gap:14px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px}article{margin:0;overflow-wrap:anywhere}a{color:#27658f}select{font:inherit;padding:8px;margin:6px}code{font-size:13px}@media(max-width:850px){.pair{grid-template-columns:1fr}}</style><h1>Eighteen routes for scientific figures</h1><p>H4b gradient collection Â· supported for release Â· screened numerically</p><p>Twelve sequential routes and six diverging routes, each shown on light and dark backgrounds. All eighteen named gradients are supported. Factory defaults are unchanged; choose a route that suits your data.</p><section><h2>Compare the complete collection</h2><p>Each row uses its stated low-to-high direction. Diverging neutrals are at the midpoint; the ramps have no marker overlays. Bathymetry darkens with depth; Highland lightens with elevation across both backgrounds.</p><div class="pair"><img src="overview-light.png" alt="All eighteen routes, light background"><img src="overview-dark.png" alt="All eighteen routes, dark background"></div></section>'''+apps+'''<section><h2>Find a route and inspect its evidence</h2><label>Family <select id="family"><option value="">All</option><option>sequential</option><option>diverging</option></select></label><label>Application <select id="domain"><option value="">All</option><option>general</option><option>seismic</option><option>structure</option><option>geography</option><option>atmosphere</option></select></label></section><div class="cards">'''+''.join(cards)+'''</div><section><h2>Methods and limits</h2><p>Every shipped variant passes unchanged normal/CVD float/8-bit Oklab and CAM02-UCS profiles, complete-segment numerical checks and the denser ordering audit. Sampling counts are screened individually; uniform and optimized sampling remain distinct. A plotted view, shaded composite or domain label has no universal accessibility or scientific-validity guarantee.</p><p><a href="../../docs/METHODS_H4B.md">Construction and application protocol</a> Â· <a href="../../src/huevat/data/collection-v1.json">Full recipes, searches and numeric reports</a> Â· <a href="negative-controls.json">Deliberately bad controls and failed criteria</a> Â· <a href="review.json">Review inventory</a></p></section><script>function filter(){const f=document.getElementById('family').value,d=document.getElementById('domain').value;document.querySelectorAll('article').forEach(a=>a.hidden=Boolean((f&&a.dataset.family!==f)||(d&&!a.dataset.domains.split(' ').includes(d))))}document.querySelectorAll('select').forEach(s=>s.addEventListener('change',filter));</script></html>'''
    page=page.replace('<section><h2>Methods and limits</h2>','<section><h2>Deliberately bad controls</h2><img src="negative-controls.png" alt="Three rejected negative controls" loading="lazy"><p>These failures remain visible; they are not candidate palettes.</p></section><section><h2>Methods and limits</h2>')
    (OUTPUT/'index.html').write_text(page,encoding='utf-8',newline='\n')
    write_json(OUTPUT/'review.json',{'status':'pending','approved_defaults':[],
        'panels':[{'file':p.name,'layout':'pending inspection','perceptual_review':'pending'} for p in sorted(OUTPUT.glob('*.png'))],
        'versions':{n:md.version(n) for n in ('numpy','scipy','colorspacious','matplotlib')},
        'data':'deterministic synthetic illustrations; no external field observations',
        'shading':'separate review; combined terrain and hillshade receive no palette-profile pass'})
    write_json(OUTPUT/'manifest.json',{'implementation_sha256_lf':implementation_hashes(),
        'tool_sha256_lf':{n:digest(ROOT/'tools'/n) for n in ('build_collection.py','collection_fields.py','verify.py')},
        'resource_sha256_lf':digest(RESOURCE),
        'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUTPUT.iterdir()) if p.is_file() and p.name!='manifest.json'}})


def check():
    from huevat._data import load_data
    data=load_data('collection-v1.json');assert data['implementation_sha256_lf']==implementation_hashes()
    assert set(data['candidates'])==set(SPECS) and not data['approved_defaults']
    count=0
    for name,entry in data['candidates'].items():
        assert set(entry['variants'])=={'light','dark'},name
        for bg,v in entry['variants'].items():
            params=v['report']['search']['parameters']
            # JSON key sorting changes parameter order; pass explicit fields.
            rebuilt=make_recipe(name,bg,params['chroma_scale'],params['endpoint_shift'],params['arm_balance'],
                                params['arm_lightness_shift'],params['curve_skew'],params['lightness_range'],
                                spec_version=int(v['recipe']['identifier'].rsplit('-v',1)[1]))
            compact_compare(v['recipe'],rebuilt,path=name+'/'+bg+'/construction')
            old={k:value for k,value in v['report'].items() if k!='search'}
            compact_compare(old,audit(name,v['recipe']))
            g=Gradient(v['recipe'],QualityReport(v['report']),{})
            for key,stored in v['discrete'].items():
                context,n=key.split('/');n=int(n)
                fresh=screen_discrete(tuple(g.at(i/(n-1)) for i in range(n)),g.at(.5),g.family,g.background,context)
                compact_compare(stored,fresh)
            count+=1
    for identifier,v in data.get('archived',{}).items():
        name,bg=identifier.removeprefix('h4b-').rsplit('-v',1)[0].rsplit('-',1)
        params=v['report']['search']['parameters']
        rebuilt=make_recipe(name,bg,params['chroma_scale'],params['endpoint_shift'],params['arm_balance'],
                            params['arm_lightness_shift'],params['curve_skew'],params['lightness_range'],spec_version=1)
        compact_compare(v['recipe'],rebuilt,path=identifier+'/construction')
        compact_compare({k:value for k,value in v['report'].items() if k!='search'},audit(name,v['recipe']))
        g=Gradient(v['recipe'],QualityReport(v['report']),{})
        for key,stored in v['discrete'].items():
            context,n=key.split('/');n=int(n)
            compact_compare(stored,screen_discrete(tuple(g.at(i/(n-1)) for i in range(n)),g.at(.5),g.family,g.background,context))
        count+=1
    negative=json.loads((OUTPUT/'negative-controls.json').read_text())
    compact_compare(negative,controls())
    manifest=json.loads((OUTPUT/'manifest.json').read_text())
    assert manifest['implementation_sha256_lf']==implementation_hashes()
    assert manifest['resource_sha256_lf']==digest(RESOURCE)
    for name,d in manifest['tool_sha256_lf'].items():assert digest(ROOT/'tools'/name)==d,name
    for name,d in manifest['files'].items():assert hashlib.sha256((OUTPUT/name).read_bytes()).hexdigest()==d,name
    print(f'Reproduced {count} free-knot paths, all prepared counts and negative controls; verified H4b hashes')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--construct',action='store_true');parser.add_argument('--check',action='store_true')
    parser.add_argument('--no-render',action='store_true',help='Construct resources without regenerating the gallery')
    parser.add_argument('--refresh',nargs='+',choices=list(SPECS),help='Regenerate selected routes after a declared control refinement')
    args=parser.parse_args()
    if args.check:return check()
    data=construct(args.refresh) if args.construct or args.refresh or not RESOURCE.exists() else json.loads(RESOURCE.read_text())
    if data['failures']:raise SystemExit('Unresolved variants retained in the resource; finish their search before rendering')
    if args.no_render:return
    render(data)
    print('Built H4b offline gradient/application gallery',flush=True)


if __name__=='__main__':main()
