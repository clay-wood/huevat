import csv
from dataclasses import FrozenInstanceError
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys

import pytest
import huevat as hv
from huevat.gradients import fingerprint, QualityReport, Palette

HAS_DESIGN = importlib.util.find_spec('colorspacious') is not None
research = pytest.mark.skipif(not HAS_DESIGN, reason='requires huevat[design]')


def test_registry_roles_exact_hashes_and_immutable_cached_objects():
    assert len(hv.design_ids()) == 76
    assert {role:len(hv.design_ids(role=role)) for role in ('default','legacy','experimental')} == {'default':30,'legacy':22,'experimental':24}
    for identifier in hv.design_ids():
        info = hv.design_info(identifier); design = hv.get_design(identifier)
        assert info['identifier'] == identifier
        assert hv.get_design(identifier) is design
        assert design.report.screen_pass and not info['human_discrimination_validated']
        body = design._recipe if isinstance(design, hv.Gradient) else design.report['recipe']
        from huevat.gradients import _thaw
        assert fingerprint(_thaw(body)) == info['recipe_sha256']
        assert info['reversed'] == getattr(design,'_reverse',False)
        with pytest.raises(TypeError): info['role'] = 'invented'
    for kwargs in ({'family':'cyclic'},{'background':'blue'},{'role':'best'}):
        with pytest.raises(ValueError): hv.design_ids(**kwargs)
    for identifier in ('missing', None):
        with pytest.raises(ValueError): hv.get_design(identifier)


def test_release_discovery_does_not_load_large_resources():
    code = '''
import sys
import huevat as h
assert len(h.design_ids()) == 76
assert h.design_info(h.design_ids()[0])
from huevat.gradients import _ordered_data
from huevat.families import _prepared_data
from huevat.categorical import _data
from huevat.catalog import _catalog
assert all(f.cache_info().currsize == 0 for f in (_ordered_data,_prepared_data,_data,_catalog))
assert 'huevat.design' not in sys.modules
'''
    subprocess.run([sys.executable,'-I','-c',code],check=True)


def test_all_ids_and_compact_exports_work_without_optional_packages():
    code = '''
import importlib.abc,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'numpy','scipy','colorspacious','matplotlib','plotly','ultraplot','PIL','sketchplot'}:
   raise AssertionError('Unexpected optional import '+fullname)
sys.meta_path.insert(0,Block())
import huevat as h
for identifier in h.design_ids():
 d=h.get_design(identifier); out=h.export(d); loaded=h.load_export(out).design
 if isinstance(d,h.Gradient):assert loaded.at(.37)==d.at(.37)
 else:assert loaded.colors==d.colors
g=h.diverging();assert h.load_export(h.export(g,n=7)).design.colors==g.discrete(7).colors
assert h.nearby_counts(g,8)[:2]==(7,9)
assert h.export(h.categorical(4),format='css').report['approximation_pass']
assert h.export(g,format='css').report['approximation_pass']
'''
    subprocess.run([sys.executable,'-I','-c',code],check=True)


@pytest.mark.parametrize('factory',[hv.sequential,hv.diverging,hv.multihue,hv.spectral])
@pytest.mark.parametrize('background',['light','dark'])
def test_exact_gradient_roundtrip_uniform_selection_and_orientation(factory,background):
    g=factory(background=background)
    for source in (g,g.reversed()):
        output=hv.export(source)
        assert len(output.text)<5000 and output.report['lossless']
        loaded=hv.load_export(output).design
        assert loaded.to_recipe()['sha256']==source.to_recipe()['sha256']
        assert [loaded.at(t) for t in (0,.2,.5,.8,1)]==[source.at(t) for t in (0,.2,.5,.8,1)]
        output=hv.export(source,n=7,labels=list('ABCDEFG'))
        result=hv.load_export(output)
        assert result.design.colors==source.discrete(7).colors
        assert list(result.color_map)==list('ABCDEFG')
        with pytest.raises(TypeError): result.color_map['A']='#000000'
        unvalidated=hv.load_export(output,validate=False)
        assert not unvalidated.design.report.screen_pass


def test_palette_json_labels_csv_hex_and_uniform_source_requirement(tmp_path):
    p=hv.categorical(4)
    labels=['Control, first','Unicode α','two\nlines','last']
    out=hv.export(p,labels=labels)
    loaded=hv.load_export(out)
    assert loaded.labels==tuple(labels) and loaded.design.colors==p.colors
    assert len(out.text)<4000 and len(out.text)<len(p.to_json())/10
    text=hv.export(p,format='csv',labels=labels)
    rows=list(csv.DictReader(io.StringIO(text.text)))
    assert [r['label'] for r in rows]==labels and [r['hex'] for r in rows]==list(p.colors)
    assert all(r['position']=='' for r in rows)
    assert hv.export(p,format='hex').text.splitlines()==list(p.colors)
    path=tmp_path/'palette.json';assert out.write(path)==path
    assert path.read_bytes()==out.text.encode()
    import hashlib
    assert hashlib.sha256(path.read_bytes()).hexdigest()==out.sha256
    with pytest.raises(FrozenInstanceError): out.text='changed'
    g=hv.diverging();p=g.discrete(7)
    with pytest.raises(ValueError,match='provenance'):hv.export(p)
    assert hv.load_export(hv.export(p,source=g)).design.colors==p.colors
    with pytest.raises(ValueError,match='do not match'):hv.export(hv.categorical(7),source=g)
    table=list(csv.DictReader(io.StringIO(hv.export(g,n=7,format='csv').text)))
    assert [float(r['position']) for r in table]==[i/6 for i in range(7)]


def test_bad_inputs_hashes_schema_claims_and_labels():
    g=hv.diverging();output=hv.export(g,n=7)
    data=json.loads(output.text);data['payload']['hex'][0]='#ffffff'
    with pytest.raises(ValueError,match='hash'):hv.load_export(data)
    data['sha256']=fingerprint(data['payload'])
    with pytest.raises(ValueError,match='do not match'):hv.load_export(data)
    data=json.loads(output.text);data['payload']['selection']['count']=True;data['sha256']=fingerprint(data['payload'])
    with pytest.raises(ValueError,match='count'):hv.load_export(data)
    data=json.loads(output.text);data['payload']['source']['evidence']={'screen_pass':False,'approved_default':True}
    data['sha256']=fingerprint(data['payload'])
    loaded=hv.load_export(data)
    assert loaded.source.report.screen_pass and not loaded.source.report['approved_default']
    for kwargs in ({'format':'unknown'},{'format':'csv'},{'labels':['A']},{'n':7,'labels':['A']*7}):
        with pytest.raises(ValueError):hv.export(g,**kwargs)
    with pytest.raises(hv.QualityError):hv.export(Palette(('#000000','#ffffff'),QualityReport({'screen_pass':False})))
    with pytest.raises(ValueError):hv.load_export('not JSON')
    with pytest.raises(ValueError,match='boolean'):hv.load_export(output,validate=1)
    data=json.loads(output.text);data['payload']['hex'][0]=float('nan')
    with pytest.raises(ValueError,match='finite'):hv.load_export(data)
    assert not hv.load_export(hv.export(g)).labels
    with pytest.raises(ValueError,match='labels'):hv.load_export(hv.export(g)).color_map


@pytest.mark.parametrize('factory',[hv.sequential,hv.diverging,hv.multihue,hv.spectral])
def test_continuous_css_audits_serialized_srgb_stops_and_retains_center(factory):
    import re
    from huevat.adapters._common import interpolate
    g=factory();out=hv.export(g,format='css')
    assert out.text.startswith('linear-gradient(90deg in srgb, ')
    assert out.report['approximation_pass'] and not out.report['adapter_profile_revalidated']
    assert not out.report['browser_render_verified']
    matches=re.findall(r'rgb\(([^)]+)\) ([0-9.]+)%',out.text)
    positions=tuple(float(t)/100 for _,t in matches)
    colors=tuple(tuple(float(v)/255 for v in rgb.split(',')) for rgb,_ in matches)
    assert positions[0]==0 and positions[-1]==1 and .5 in positions
    for t in (0,.03,.33,.5,.69,.97,1):
        assert hv.distance(hv.srgb_to_oklab(g.at(t)),hv.srgb_to_oklab(interpolate(positions,colors,t)))<=.002
    assert interpolate(positions,colors,.5)==pytest.approx(g.at(.5),abs=1e-11)


def test_css_failure_and_discrete_steps_do_not_invent_physical_boundaries():
    with pytest.raises(hv.QualityError,match='tolerance'):hv.export(hv.spectral(),format='css',max_stops=3,tolerance=1e-8)
    for kwargs in ({'max_stops':4},{'max_stops':True},{'tolerance':float('nan')},{'tolerance':0}):
        with pytest.raises(ValueError):hv.export(hv.sequential(),format='css',**kwargs)
    p=hv.categorical(4);out=hv.export(p,format='css')
    assert all(c in out.text for c in p.colors) and '25% 50%' in out.text
    assert 'not a physical-data mapping' in out.report['scope']


@research
def test_positioned_export_revalidates_and_preserves_exact_positions():
    sampled=hv.optimized_discrete(hv.diverging(),8,max_seconds=5)
    for source in (sampled,sampled.reversed()):
        out=hv.export(source);loaded=hv.load_export(out).design
        assert loaded.positions==source.positions and loaded.colors==source.colors
        assert loaded.report.screen_pass
        assert not hv.load_export(out,validate=False).design.report.screen_pass


@research
@pytest.mark.parametrize('backend',['matplotlib','ultraplot','plotly'])
def test_exported_recipe_and_labeled_palette_reach_native_backends(backend):
    import importlib
    pytest.importorskip(backend)
    adapter=importlib.import_module('huevat.adapters.'+backend)
    g=hv.load_export(hv.export(hv.diverging(background='dark').reversed())).design
    result=hv.load_export(hv.export(hv.categorical(4,background='dark'),labels=list('ABCD')))
    if backend=='plotly':
        import plotly.graph_objects as go
        fig=go.Figure(go.Heatmap(z=[[-2,None,0],[1,4,8]],coloraxis='coloraxis'))
        fig.update_layout(coloraxis=adapter.coloraxis(g,-2,8,center=0))
        assert fig.layout.coloraxis.cmin==-2 and fig.layout.coloraxis.cmax==8
        assert fig.to_json()
        assert adapter.color_map(result.design,list(result.labels))==dict(result.color_map)
    else:
        cmap=adapter.colormap(g);norm=adapter.normalizer(-2,8,center=0)
        assert hv.distance(hv.srgb_to_oklab(cmap(norm(0))[:3]),hv.srgb_to_oklab(g.at(.5)))<=.002
        cycle=adapter.cycle(result.design)
        assert len(list(cycle))==4
