"""Check or reconstruct the separately declared H5 colors and selections."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'src/huevat/data'


def write(name,value):
    (DATA/name).write_text(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def construct():
    import huevat as hv
    from huevat.styles import generate
    from huevat.gradients import fingerprint,QualityReport
    from huevat.cyclic import recipe,validate,screen,CyclicGradient
    from huevat.sampling import optimized_discrete
    palettes={'version':'h5-categorical-v1','designs':{},'failures':{}}
    for style in ('earth','gem'):
        for bg in ('light','dark'):
            for n in range(2,9):
                p=generate(style,n,background=bg,max_seconds=35.,starts=3)
                report=p.report.to_dict();body=report['recipe'];body['identifier']=f'h5-{style}-{bg}-{n}'
                report['recipe_sha256']=fingerprint(body)
                palettes['designs'][f'{style}/{bg}/{n}']={'recipe':body,'report':report}
    write('categorical-v3.json',palettes)
    cycles={'version':'h5-cyclic-v1','designs':{}}
    for bg in ('light','dark'):
        body=recipe(bg);report=validate(body)
        assert report['screen_pass'],report
        g=CyclicGradient(body,QualityReport(report),{})
        counts={f'{context}/{n}':screen([g.at(i/n) for i in range(n)],g.background,context)
                for context in ('filled-fields','data-marks') for n in range(2,13)}
        cycles['designs'][bg]={'recipe':body,'report':report,'discrete':counts}
    write('cyclic-v1.json',cycles)
    selections={'version':'h5-optimized-v1','selections':{}}
    for bg in ('light','dark'):
        for factory in (hv.sequential,hv.diverging,hv.multihue,hv.spectral):
            g=factory(background=bg)
            for n in (5,7,8):
                p=optimized_discrete(g,n,max_seconds=20.)
                source=p.to_recipe()['recipe']['source'];source['evidence']={}
                key=f'{fingerprint(g.to_recipe()["recipe"])}/filled-fields/{n}'
                selections['selections'][key]={'colors':p.colors,'positions':p.positions,'source':source,'report':p.report.to_dict()}
    write('optimized-v1.json',selections)
    registry={'version':'h5-registry-v1','designs':{}}
    for key,entry in palettes['designs'].items():
        style,bg,n=key.split('/');body=entry['recipe']
        registry['designs'][body['identifier']]=dict(identifier=body['identifier'],family='categorical',background=bg,
            count=int(n),factory='categorical',style=style,role='experimental',recipe_sha256=fingerprint(body),
            view_sha256=fingerprint(body),reversed=False,human_discrimination_validated=False,numerical_profile='h1-screening-v1')
    for bg,entry in cycles['designs'].items():
        body=entry['recipe']
        registry['designs'][body['identifier']]=dict(identifier=body['identifier'],family='cyclic',background=bg,
            count=None,factory='cyclic',role='experimental',recipe_sha256=fingerprint(body),view_sha256=fingerprint({**body,'reversed':False}),
            reversed=False,human_discrimination_validated=False,numerical_profile='h5-cyclic-v1')
    write('registry-v2.json',registry)
    manifest=json.loads((DATA/'manifest-v1.json').read_text())
    for name in ('categorical-v3.json','cyclic-v1.json','optimized-v1.json','registry-v2.json'):
        manifest['sha256_lf'][name]=hashlib.sha256((DATA/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    write('manifest-v1.json',manifest)


def check():
    import huevat as hv
    from huevat._data import load_data
    from huevat.styles import validate
    from huevat.cyclic import validate as validate_cycle,screen as screen_cycle,CyclicGradient
    from huevat._sampling_design import screen
    from huevat.gradients import QualityReport
    for d in load_data('categorical-v3.json')['designs'].values():assert validate(d['recipe'])['screen_pass']
    for d in load_data('cyclic-v1.json')['designs'].values():
        assert validate_cycle(d['recipe'])['screen_pass']
        g=CyclicGradient(d['recipe'],QualityReport(d['report']),{})
        for key,stored in d['discrete'].items():
            context,n=key.split('/');n=int(n)
            fresh=screen_cycle([g.at(i/n) for i in range(n)],g.background,context)
            assert fresh['screen_pass']==stored['screen_pass'],key
            for a,b in zip(fresh['checks'],stored['checks']):
                assert a['passed']==b['passed'] and abs(a.get('measured',0)-b.get('measured',0))<=1e-8,key
    entries=load_data('optimized-v1.json')['selections']
    for d in entries.values():
        source=hv.load_recipe(d['source']);report=screen(source,d['positions'],d['report']['context'])
        assert report['screen_pass'] and tuple(hv.to_hex(source.at(t)) for t in d['positions'])==tuple(d['colors'])
    print('Checked 28 count/background categorical palettes, two periodic paths and',len(entries),'optimized selections')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--construct',action='store_true');args=parser.parse_args()
    if args.construct:construct()
    check()
