"""Measure Huevat operational costs and optimizer hotspots for project review."""
import cProfile
import importlib.metadata as md
import json
from pathlib import Path
import platform
import pstats
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'research/project-review-v1'


def child(script):
    return json.loads(subprocess.check_output([sys.executable,'-I','-c',script],text=True))


def timings(func,repeats=5,number=1):
    values=[]
    for _ in range(repeats):
        t=time.perf_counter()
        for _ in range(number):func()
        values.append((time.perf_counter()-t)/number)
    return {'median_seconds':statistics.median(values),'min_seconds':min(values),'max_seconds':max(values),
            'repeats':repeats,'operations_per_repeat':number}


def profile(func):
    profiler=cProfile.Profile();profiler.runcall(func)
    stats=pstats.Stats(profiler)
    entries=[]
    for (file,line,name),(primitive,total,self_time,cumulative,_) in stats.stats.items():
        if 'huevat' not in file and 'colorspacious' not in file and 'scipy' not in file and 'json' not in file:
            continue
        location=file.replace('\\','/')
        if '/src/huevat/' in location:location='huevat/'+location.split('/src/huevat/')[1]
        elif '/site-packages/' in location:location=location.split('/site-packages/')[1]
        entries.append({'function':f'{location}:{line}:{name}','primitive_calls':primitive,'total_calls':total,
                        'self_seconds':self_time,'cumulative_seconds':cumulative})
    return sorted(entries,key=lambda r:r['cumulative_seconds'],reverse=True)[:22]


def main():
    import huevat as hv
    data={'date':'2026-10-22','host':{'platform':platform.platform(),'python':platform.python_version()},
          'versions':{p:md.version(p) for p in ('numpy','scipy','colorspacious','matplotlib')},
          'method':'Fresh isolated processes for cold timings (3 runs); separate tracemalloc processes; warmed medians; profiled timing is not an absolute benchmark.',
          'cold':{},'memory':{},'warm':{},'profiles':{}}
    operations={'import':'pass','clearer8':'p=hv.categorical(8)','legacy8':"p=hv.categorical(8,style='max-separation')",
                'sequential':'g=hv.sequential()','spectral':'g=hv.spectral()',
                'all_families':'p=hv.categorical(8);s=hv.sequential();d=hv.diverging();m=hv.multihue();g=hv.spectral()',
                'first_custom4_one_start':'p=hv.categorical(4,starts=1,max_seconds=60)'}
    for name,operation in operations.items():
        runs=[]
        for _ in range(3):
            script="import json,sys,time\nt=time.perf_counter();import huevat as hv\nimport_seconds=time.perf_counter()-t\nt=time.perf_counter()\n"+operation+"\nprint(json.dumps({'import_seconds':import_seconds,'operation_seconds':time.perf_counter()-t,'optional_modules_loaded':[n for n in ('numpy','scipy','colorspacious','matplotlib') if n in sys.modules]}))"
            runs.append(child(script))
        data['cold'][name]={'import_median_seconds':statistics.median(r['import_seconds'] for r in runs),
                            'operation_median_seconds':statistics.median(r['operation_seconds'] for r in runs),
                            'runs':runs}
        if name in ('clearer8','spectral','all_families'):
            script="import tracemalloc,json;tracemalloc.start();import huevat as hv\n"+operation+"\ncurrent,peak=tracemalloc.get_traced_memory();print(json.dumps({'retained_traced_bytes':current,'peak_traced_bytes':peak}))"
            data['memory'][name]=child(script)
    p=hv.categorical(8);g=hv.spectral();s=hv.sequential()
    operations={'clearer8_lookup':(lambda:hv.categorical(8),20),'spectral_lookup':(hv.spectral,10),
                'palette_report_access':(lambda:p.report,1000),'spectral_report_access':(lambda:g.report,10),
                'palette_recipe':(p.to_recipe,20),'palette_json':(p.to_json,10),'spectral_json':(g.to_json,5),
                'spectral_reversal':(g.reversed,10),'spectral_7_bins':(lambda:g.discrete(7),10),
                'sequential_4096_samples':(lambda:[s.at(i/4095) for i in range(4096)],1)}
    envelope=p.to_recipe();operations['clearer_recipe_reload']=(lambda:hv.load_recipe(envelope),10)
    for name,(func,number) in operations.items():
        data['warm'][name]=timings(func,number=number)
    data['profiles']['cold_clearer']=child("""
import cProfile,pstats,json
import huevat as hv
p=cProfile.Profile();p.runcall(hv.categorical,8)
out=[]
for (file,line,name),v in pstats.Stats(p).stats.items():
 if 'huevat' in file or 'json' in file:
  out.append({'file':file,'line':line,'name':name,'calls':v[1],'self_seconds':v[2],'cumulative_seconds':v[3]})
print(json.dumps(sorted(out,key=lambda r:r['cumulative_seconds'],reverse=True)[:20]))
""")
    data['profiles']['spectral_report']=profile(lambda:[g.report for _ in range(10)])
    from huevat.design_categorical import generate
    data['profiles']['clearer8_generation']=profile(lambda:generate(8,starts=1,max_seconds=60))
    data['generation_seconds']={}
    for n in (4,8,12):
        runs=[]
        for _ in range(2):
            t=time.perf_counter();result=generate(n,starts=3,max_seconds=60)
            runs.append({'wall_seconds':time.perf_counter()-t,'search_seconds':result.report['search']['elapsed_seconds'],
                         'screen_pass':result.report.screen_pass,'optimizer_runs':result.report.to_dict()['search']['optimizer_runs']})
        data['generation_seconds'][str(n)]=runs
    data['resource_sizes_bytes']={p.name:p.stat().st_size for p in (ROOT/'src/huevat/data').glob('*.json')}
    data['resource_sha256_lf']=json.loads((ROOT/'src/huevat/data/manifest-v1.json').read_text(encoding='utf-8'))['sha256_lf']
    data['distribution_sizes_bytes']={p.name:p.stat().st_size for p in (ROOT/'dist').iterdir() if p.suffix in ('.whl','.gz')}
    data['json_sizes_bytes']={'palette8_envelope':len(p.to_json().encode()),'spectral_envelope':len(g.to_json().encode())}
    OUTPUT.mkdir(parents=True,exist_ok=True)
    (OUTPUT/'benchmarks.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'cold':{k:{a:b for a,b in v.items() if a!='runs'} for k,v in data['cold'].items()},
                      'warm':{k:v['median_seconds'] for k,v in data['warm'].items()},
                      'memory':data['memory'],'generation_seconds':{k:[r['wall_seconds'] for r in v] for k,v in data['generation_seconds'].items()}},indent=2))


if __name__=='__main__':main()
