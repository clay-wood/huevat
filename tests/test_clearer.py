import json
import subprocess
import sys
from pathlib import Path

import pytest
import huevat as hv
from huevat._data import load_data
from huevat.gradients import fingerprint


@pytest.mark.parametrize('background',['light','dark'])
def test_all_prepared_clearer_counts_pass_and_preserve_the_selected_colors(background):
    study=json.loads((Path(__file__).resolve().parents[1]/'research/categorical-aesthetics-v1/results.json').read_text(encoding='utf-8'))
    for n in range(2,13):
        p=hv.categorical(n,background=background)
        assert len(p)==len(set(p))==n
        assert p.report.screen_pass and p.report['style']=='clearer'
        assert p.report['algorithm_version']=='h3-categorical-v2'
        assert p.report['aesthetic']['chroma_max']<=.18+1e-7
        assert p.report['aesthetic']['target_movement_max']<=.065+1e-7
        assert not p.report['approved_default']
        assert hv.load_recipe(p.to_json()).colors==p.colors
        if n in (4,6,8):
            assert list(p.colors)==study['candidates'][f'clear/{background}/{n}']['report']['hex']
    assert hv.categorical(8,background=background,style='max-separation').colors!=hv.categorical(8,background=background).colors


def test_original_recipes_remain_loadable_and_forged_claims_are_ignored():
    old=hv.categorical(6,style='max-separation')
    assert old.report['algorithm_version']=='h3-families-v1'
    assert hv.load_recipe(old.to_json()).colors==old.colors
    new=hv.categorical(6).to_recipe();new['evidence']={'screen_pass':False}
    assert hv.load_recipe(new).report.screen_pass
    new['recipe']['targets'][0][0]+=.01
    with pytest.raises(ValueError,match='hash'):hv.load_recipe(new)
    new['sha256']=fingerprint(new['recipe'])
    assert not hv.load_recipe(new,validate=False).report.screen_pass


@pytest.mark.parametrize('change',[
    lambda r:r.update(style='unknown'),lambda r:r.update(targets=[]),
    lambda r:r['targets'][0].__setitem__(0,float('inf')),
    lambda r:r.update(unexpected='field'),lambda r:r.update(family='sequential')])
def test_bad_clearer_recipes_are_rejected(change):
    envelope=hv.categorical(4).to_recipe();change(envelope['recipe'])
    try:envelope['sha256']=fingerprint(envelope['recipe'])
    except ValueError:pass
    with pytest.raises(ValueError):hv.load_recipe(envelope,validate=False)


def test_invalid_style_fails_before_optional_imports():
    with pytest.raises(ValueError,match='style'):hv.categorical(4,style='anything')


def test_new_and_old_prepared_styles_work_without_optional_packages():
    script='''
import sys,importlib.abc
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'numpy','scipy','colorspacious','matplotlib','PIL','playwright'}:
   raise AssertionError(fullname)
sys.meta_path.insert(0,Block())
import huevat as hv
for b in ('light','dark'):
 for n in range(2,13):
  for style in ('clearer','max-separation'):
   p=hv.categorical(n,background=b,style=style)
   assert p.report.screen_pass and hv.load_recipe(p.to_json()).colors==p.colors
'''
    subprocess.run([sys.executable,'-I','-c',script],check=True)


def test_clearer_artifact_inventory():
    data=load_data('categorical-v2.json')
    assert len(data['designs'])==22
    output=Path(__file__).resolve().parents[1]/'research/categorical-v2'
    review=json.loads((output/'review.json').read_text(encoding='utf-8'))
    assert review['direction']=='selected by user'
    assert not review['approved_H4_default']
    assert len(review['panels'])==10
