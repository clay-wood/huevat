import json
import subprocess
import sys
from dataclasses import FrozenInstanceError

import pytest
import huevat as hv
from huevat.families import HueGradient
from huevat.gradients import fingerprint


@pytest.mark.parametrize("background",["light","dark"])
def test_count_specific_prepared_categories(background):
    palettes=[hv.categorical(n,background=background) for n in range(2,13)]
    for n,p in zip(range(2,13),palettes):
        assert isinstance(p,hv.Palette) and len(p)==len(set(p))==n
        assert p.report.screen_pass and all(c['passed'] for c in p.report['checks'])
        assert not p.report['approved_default']
        assert min(hv.contrast(rgb,hv.from_hex('#ffffff' if background=='light' else '#121212')) for rgb in p.rgb)>=3
        assert p.report['count']==n
        assert hv.load_recipe(p.to_json()).colors==p.colors
        assert len(p.report['measurements']['u8']['conditions']['deutan-100']['oklab']['distance_matrix'])==n
    assert palettes[4].colors[:4]!=palettes[2].colors
    with pytest.raises((AttributeError,FrozenInstanceError)):
        palettes[0].colors=('#ffffff','#000000')
    with pytest.raises(TypeError):
        palettes[0].report['measurements']['u8']['count']=999


@pytest.mark.parametrize("factory",[hv.multihue,hv.spectral])
@pytest.mark.parametrize("background",['light','dark'])
def test_h3_ordered_paths_reversal_serialization_and_bins(factory,background):
    g=factory(background=background)
    assert isinstance(g,HueGradient) and isinstance(g,hv.Gradient)
    assert g.report.screen_pass and g.report['certificate']['passed']
    assert all(r['hue_span_degrees']>=20 and r['backward_degrees']<=.1 for r in g.report['hue_routes'])
    assert not g.report['approved_default']
    for t in (0,.01,.25,.5,.6,1):
        assert hv.in_gamut(g.at(t))
        assert g.reversed().at(1-t)==pytest.approx(g.at(t),abs=1e-14)
    assert g.reversed().family==g.family
    assert g.reversed().reversed().to_recipe()==g.to_recipe()
    assert hv.load_recipe(g.to_json()).at(.3)==g.at(.3)
    assert hv.load_recipe(g.reversed().to_json()).at(.3)==pytest.approx(g.at(.7),abs=1e-14)
    successes=0
    for n in range(2,28):
        try:
            p=g.discrete(n)
        except hv.QualityError as e:
            assert not e.report.screen_pass
        else:
            successes+=1
            assert p.report.screen_pass
            assert tuple(p)==tuple(hv.to_hex(g.at(i/(n-1))) for i in range(n))
            assert tuple(g.reversed().discrete(n))==tuple(p)[::-1]
    assert successes>=3
    with pytest.raises(hv.ConstraintConflictError):g.discrete(129)
    if factory==hv.spectral:
        assert hv.oklab_to_oklch(hv.srgb_to_oklab(g.at(.5)))[1]<1e-6
        left=hv.srgb_to_oklab(g.at(.5-1e-5));right=hv.srgb_to_oklab(g.at(.5+1e-5))
        assert hv.distance(left,right)<1e-7


def test_recipe_hash_forged_evidence_and_structure():
    p=hv.categorical(6)
    envelope=p.to_recipe();envelope['evidence']={'screen_pass':False,'arbitrary_claim':True}
    assert hv.load_recipe(envelope).report.screen_pass
    envelope['recipe']['rgb'][0][0]=.123
    with pytest.raises(ValueError,match='hash'):hv.load_recipe(envelope)
    envelope['sha256']=fingerprint(envelope['recipe'])
    assert not hv.load_recipe(envelope,validate=False).report.screen_pass
    envelope['recipe']['rgb'][0][0]=float('nan')
    with pytest.raises(ValueError):hv.load_recipe(envelope)
    g=hv.spectral();envelope=g.to_recipe();envelope['recipe']['preferences']=['#0072b2']
    envelope['sha256']=fingerprint(envelope['recipe'])
    with pytest.raises(ValueError):hv.load_recipe(envelope)


@pytest.mark.parametrize('call',[
    lambda:hv.categorical(True),lambda:hv.categorical(1),lambda:hv.categorical(65),
    lambda:hv.categorical(4,colors=['red']*4),lambda:hv.categorical(4,colors=['#0072b2']*3),
    lambda:hv.categorical(4,background='transparent'),lambda:hv.categorical(4,starts=0),
    lambda:hv.multihue(colors=['#000000']),lambda:hv.spectral(colors=['#000000']*3),
    lambda:hv.multihue(seed=-1),lambda:hv.spectral(max_seconds=0),
    lambda:hv.multihue(context='universal'),lambda:hv.load_recipe({},validate='yes')])
def test_invalid_requests_fail_before_optional_imports(call):
    with pytest.raises(ValueError):call()


def test_all_h3_lookups_and_all_counts_work_without_optional_imports():
    script='''
import importlib.abc,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'numpy','scipy','colorspacious','matplotlib','PIL','playwright'}:
   raise AssertionError('Optional import: '+fullname)
sys.meta_path.insert(0,Block())
import huevat as hv
for bg in ('light','dark'):
 for n in range(2,13):
  p=hv.categorical(n,background=bg)
  assert p.report.screen_pass and len(hv.load_recipe(p.to_json()))==n
 for factory in (hv.multihue,hv.spectral):
  g=factory(background=bg)
  assert hv.load_recipe(g.to_json()).at(.3)==g.at(.3)
  for n in range(2,60):
   try:g.discrete(n)
   except hv.QualityError:pass
'''
    subprocess.run([sys.executable,'-I','-c',script],check=True)
