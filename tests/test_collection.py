import hashlib
import importlib
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest
import huevat as hv
from huevat.gradients import fingerprint

ROOT=Path(__file__).resolve().parents[1]


def test_names_domains_and_immutable_metadata():
    names=hv.gradient_names()
    assert len(names)==12 and len(set(names))==12
    assert len(hv.gradient_names(family='sequential'))==8
    assert len(hv.gradient_names(family='diverging'))==4
    assert {'bathymetry','highland'}<=set(hv.gradient_names(domain='geography'))
    assert {'balance','strata'}<=set(hv.gradient_names(domain='seismic'))
    assert {'lagoon','aerosol','thermal'}<=set(hv.gradient_names(domain='atmosphere'))
    info=hv.gradient_info('highland')
    assert info['orientation']=='elevation-lightens'
    assert not info['approved_default']
    with pytest.raises(TypeError):info['label']='changed'
    with pytest.raises(TypeError):info['domains'][0]='changed'
    for kwargs in ({'family':'cyclic'},{'domain':'unknown'}):
        with pytest.raises(ValueError):hv.gradient_names(**kwargs)
    with pytest.raises(ValueError):hv.gradient('missing')
    with pytest.raises(ValueError):hv.gradient('ink',background='#ffffff')


@pytest.mark.parametrize('background',['light','dark'])
def test_every_named_path_and_known_recipe_loads_without_optional_packages(background):
    script='''
import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'numpy','scipy','colorspacious','matplotlib','plotly','ultraplot','PIL','sketchplot'}:
            raise AssertionError('Unexpected optional import: '+fullname)
sys.meta_path.insert(0,Block())
import huevat as h
assert 'huevat._collection_design' not in sys.modules
for name in h.gradient_names():
    g=h.gradient(name,background=BACKGROUND)
    assert g.report.screen_pass and not g.report['approved_default']
    assert g.report['certificate']['passed'] and g.report['dense_audit']['cvd_order_pass']
    assert all(c['passed'] for c in g.report['checks'])
    assert h.load_recipe(g.to_recipe()).at(.37)==g.at(.37)
    assert h.load_recipe(g.reversed().to_recipe()).at(.37)==g.at(.63)
    counts=h.known_counts(g)
    assert counts
    assert g.discrete(counts[0]).report.screen_pass
assert 'huevat._collection_design' not in sys.modules
'''.replace('BACKGROUND',repr(background))
    subprocess.run([sys.executable,'-I','-c',script],check=True)


@pytest.mark.parametrize('background',['light','dark'])
def test_physical_directions_and_neutrals_are_explicit(background):
    for name,ascending in (('bathymetry',False),('highland',True)):
        g=hv.gradient(name,background=background)
        lo,hi=[hv.srgb_to_oklab(g.at(t))[0] for t in (0,1)]
        assert (hi>lo)==ascending
    for name in hv.gradient_names(family='diverging'):
        g=hv.gradient(name,background=background)
        L,a,b=hv.srgb_to_oklab(g.at(.5))
        assert math.hypot(a,b)<1e-7
        assert (L>hv.srgb_to_oklab(g.at(0))[0])==(background=='light')
        assert g.reversed().reversed().to_recipe()['sha256']==g.to_recipe()['sha256']


def test_recipe_evidence_is_ignored_and_unknown_edits_are_unvalidated():
    g=hv.gradient('mineral')
    recipe=g.to_recipe();recipe['evidence']={'screen_pass':False,'made_up':True}
    loaded=hv.load_recipe(recipe)
    assert loaded.report.screen_pass and 'made_up' not in loaded.report
    recipe['recipe']['reversed']=1
    recipe['sha256']=fingerprint(recipe['recipe'])
    with pytest.raises(ValueError,match='boolean'):hv.load_recipe(recipe)
    recipe=g.to_recipe();recipe['recipe']['identifier']+='-custom'
    recipe['sha256']=fingerprint(recipe['recipe'])
    inspected=hv.load_recipe(recipe,validate=False)
    assert not inspected.report.screen_pass and inspected.at(.4)==g.at(.4)
    recipe['recipe']['segments'][0][0][0]+=.1
    with pytest.raises(ValueError,match='hash'):hv.load_recipe(recipe)


def test_gallery_inventory_and_negative_controls_are_complete():
    out=ROOT/'research/collection-v1'
    review=json.loads((out/'review.json').read_text())
    assert review['status']=='pending' and not review['approved_defaults']
    assert len(review['panels'])>=32
    assert all((out/p['file']).is_file() and p['perceptual_review']=='pending' for p in review['panels'])
    failures=json.loads((out/'negative-controls.json').read_text())
    assert set(failures)=={'hue-rainbow','gray-plateau','misplaced-neutral'}
    assert all(not f['screen_pass'] and f['failed_criteria'] for f in failures.values())
    manifest=json.loads((out/'manifest.json').read_text())
    for name,digest in manifest['files'].items():
        assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest,name


def test_synthetic_fields_keep_units_polarity_and_missing_data_separate():
    np=pytest.importorskip('numpy')
    spec=importlib.util.spec_from_file_location('collection_fields',ROOT/'tools/collection_fields.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    s=module.seismic()
    assert np.array_equal(s['data'],module.seismic()['data'])
    assert s['data'].min()<0<s['data'].max()
    assert s['time'][0]==0 and s['time'][-1]==2.4 and s['center']==0
    assert s['thin_bed_separation_s']==.018 and s['wavelet_frequency_hz']==25
    assert np.array_equal(s['wavelet'],s['wavelet'][::-1])
    assert s['wavelet_time'][len(s['wavelet'])//2]==0
    assert s['wavelet'][len(s['wavelet'])//2]==1
    t=module.terrain()
    assert t['sea_level_m']==0 and np.isnan(t['data']).any()
    assert np.nanmin(t['data'])<0<np.nanmax(t['data'])
    assert not t['combined_profile_screened'] and not t['hillshade_profile_screened']
    a=module.atmosphere()
    assert (a['concentration']==0).any() and np.isnan(a['concentration']).any()
    assert a['concentration_normalization']=='log10' and a['anomaly_center']==0


def test_unknown_named_copy_gets_real_audit_and_optimized_sampling():
    pytest.importorskip('numpy');pytest.importorskip('colorspacious');pytest.importorskip('scipy')
    g=hv.gradient('strata')
    recipe=g.to_recipe();recipe['recipe']['identifier']+='-custom';recipe['sha256']=fingerprint(recipe['recipe'])
    assert hv.load_recipe(recipe).report.screen_pass
    p=hv.optimized_discrete(g,7,max_seconds=30)
    assert p.report.screen_pass and hv.load_recipe(p.to_json()).colors==p.colors
    assert hv.load_recipe(p.reversed().to_json()).colors==p.colors[::-1]


def test_construction_budget_reports_exhaustion_honestly():
    pytest.importorskip('numpy');pytest.importorskip('scipy');pytest.importorskip('colorspacious')
    from huevat._collection_design import generate
    with pytest.raises(hv.SearchExhaustedError) as error:
        generate('ink','light',max_seconds=1e-12)
    assert error.value.report['deadline_reached'] and not error.value.report['infeasibility_proven']


@pytest.mark.parametrize('backend',['matplotlib','plotly','ultraplot'])
def test_new_free_paths_work_in_actual_adapters(backend):
    pytest.importorskip(backend)
    adapter=importlib.import_module('huevat.adapters.'+backend)
    g=hv.gradient('thermal')
    native=adapter.colorscale(g) if backend=='plotly' else adapter.colormap(g)
    assert native.huevat_report['approximation_pass']
    assert native.huevat_report['maximum_float_error_oklab']<=.002
