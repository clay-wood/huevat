"""Refresh Julia's checked colors, cubic paths and cross-language test samples."""
from pathlib import Path
import json
import hashlib
import huevat as hv
from huevat.gradients import _thaw

ROOT=Path(__file__).resolve().parents[1]


def main():
    data={'version':'h5-julia-v1','categorical':{},'gradients':{}}
    reference={};reference_counts={}
    for bg in ('light','dark'):
        for style in hv.categorical_names():
            for n in range(2,13 if style in ('core','max-separation') else 9):
                p=hv.categorical(n,style=style,background=bg)
                data['categorical'][f'{style}/{bg}/{n}']=p.colors
        designs={name:getattr(hv,name)(background=bg) for name in ('sequential','diverging','multihue','spectral','cyclic')}
        designs.update({name:hv.gradient(name,background=bg) for name in hv.gradient_names()})
        for name,g in designs.items():
            counts={}
            canonical=g.reversed() if g._reverse else g
            reference_counts[f'{name}/{bg}']={}
            for context in ('filled-fields','data-marks'):
                for n in hv.known_counts(g,context=context):
                    counts[f'{context}/{n}']=canonical.discrete(n,context=context).colors
                    reference_counts[f'{name}/{bg}'][f'{context}/{n}']=g.discrete(n,context=context).colors
            data['gradients'][f'{name}/{bg}']={'recipe':_thaw(g._recipe),'reversed':g._reverse,'counts':counts}
            reference[f'{name}/{bg}']=[g.at(i/64) for i in range(65)]
    output=ROOT/'julia/Huevat/data';output.mkdir(parents=True,exist_ok=True)
    (output/'palettes.json').write_text(json.dumps(data,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
    checksum=hashlib.sha256((output/'palettes.json').read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    (ROOT/'julia/Huevat/src/checksum.jl').write_text(f'const DATA_SHA256 = "{checksum}"\n',encoding='utf-8')
    test=ROOT/'julia/Huevat/test';test.mkdir(parents=True,exist_ok=True)
    (test/'reference.json').write_text(json.dumps(reference,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
    (test/'counts.json').write_text(json.dumps(reference_counts,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
    print('Exported',len(data['categorical']),'categorical variants and',len(reference),'continuous paths for Julia')


if __name__=='__main__':main()
