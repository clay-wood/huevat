"""Focused runtime/resource verification; --research repeats independent audits."""
import argparse
import hashlib
from importlib.resources import files
import json

import huevat as hv
from huevat._certify import certify
from huevat.families import proxy_recipe


def compare(old,new,path='root'):
    """Historical report comparison tolerance; decisions/shape remain exact."""
    import math
    if isinstance(old,dict):
        if set(old)!=set(new):raise ValueError('Different report keys at '+path)
        for key in old:compare(old[key],new[key],path+'/'+key)
    elif isinstance(old,(list,tuple)):
        if len(old)!=len(new):raise ValueError('Different report length at '+path)
        for i,(a,b) in enumerate(zip(old,new)):compare(a,b,path+'/'+str(i))
    elif isinstance(old,(int,float)) and not isinstance(old,bool):
        if not math.isclose(old,new,rel_tol=1e-8,abs_tol=1e-8):raise ValueError('Different measurement at '+path)
    elif old!=new:raise ValueError('Different report value at '+path)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--research',action='store_true');args=parser.parse_args()
    root=files('huevat').joinpath('data')
    manifest=json.loads(root.joinpath('manifest-v1.json').read_text(encoding='utf-8'))
    for name,sha in manifest['sha256_lf'].items():
        assert hashlib.sha256(root.joinpath(name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==sha,name
    gradients=palettes=0
    for identifier in hv.design_ids():
        source=hv.get_design(identifier);loaded=hv.load_export(hv.export(source)).design
        assert source.report.screen_pass
        if isinstance(source,hv.Gradient):
            gradients+=1
            recipe=dict(source._recipe)
            if source.family in ('multihue','spectral'):recipe=proxy_recipe(recipe)
            assert certify(recipe)['passed'],identifier
            assert all(source.at(t)==loaded.at(t) for t in (0,.125,.5,.875,1)),identifier
            assert source.reversed().at(.25)==source.at(.75),identifier
            for context in ('filled-fields','data-marks'):
                for n in hv.known_counts(source,context=context):
                    assert source.discrete(n,context=context).report.screen_pass,(identifier,context,n)
            if args.research:
                if source.family in ('multihue','spectral'):
                    from huevat.design_h3 import validate_ordered
                    report=validate_ordered(source)
                else:
                    from huevat.design import validate_gradient
                    report=validate_gradient(source)
                assert report['screen_pass'],identifier
        else:
            palettes+=1
            assert loaded.colors==source.colors and len(set(source.colors))==len(source),identifier
            if args.research:
                if source.report.get('style')=='clearer':
                    from huevat.design_categorical import validate_categorical
                else:
                    from huevat.design_h3 import validate_categorical
                assert validate_categorical(dict(source.report['recipe']))['screen_pass'],identifier
    print(f'Verified {len(manifest["sha256_lf"])} resource hashes, {gradients} certified paths, {palettes} palettes, recipe roundtrips and prepared counts'
          + ('; independent normal/CVD float/u8 audits passed' if args.research else ' without optional dependencies'))


if __name__=='__main__':main()
