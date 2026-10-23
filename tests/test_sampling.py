"""Exact returned selections, failure semantics and portable data recipes."""
import json
import subprocess
import sys
from dataclasses import FrozenInstanceError

import pytest

import huevat as hv
from huevat.gradients import Gradient, QualityReport, fingerprint


def test_sampling_preflight_and_adapter_imports_need_no_optional_packages():
    script = '''
import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'numpy','scipy','colorspacious','matplotlib','plotly','ultraplot','cycler'}:
            raise AssertionError('Optional import: ' + fullname)
sys.meta_path.insert(0, Block())
import huevat as h
from huevat.adapters import matplotlib as m, plotly as p, ultraplot as u
for adapter in (m,u):
    try: adapter.colormap(None)
    except ValueError: pass
    else: raise AssertionError('Expected invalid source')
try: h.optimized_discrete(h.sequential(),10000)
except h.ConstraintConflictError as e:
    assert e.report['required_total_distance'] > e.report['path_length_upper_bound']
else: raise AssertionError('Expected fixed-path bound')
g=h.sequential()
assert 7 in h.known_counts(g)
assert h.summarize(g)['screen_pass']
body={'schema_version':1,'algorithm_version':'h4-sampling-v1','family':'sampled',
      'source':g.to_recipe(),'positions':[0.,.5,1.],'context':'filled-fields'}
from huevat.gradients import fingerprint
palette=h.load_recipe({'recipe':body,'sha256':fingerprint(body),'evidence':{'screen_pass':True}},validate=False)
assert not palette.report.screen_pass
assert palette.positions == (0.,.5,1.)
'''
    subprocess.run([sys.executable, '-I', '-c', script], check=True)


@pytest.fixture
def design():
    pytest.importorskip('numpy')
    pytest.importorskip('colorspacious')


@pytest.mark.parametrize('factory', [hv.sequential, hv.diverging, hv.multihue, hv.spectral])
@pytest.mark.parametrize('background', ['light','dark'])
@pytest.mark.parametrize('n', [7,8])
def test_returned_selection_passes_each_condition_and_retains_path(design, factory, background, n):
    g = factory(background=background)
    original = g.to_json()
    p = hv.optimized_discrete(g,n,max_seconds=30)
    assert g.to_json() == original
    assert len(p) == n and len(set(p)) == n
    assert p.positions[0] == 0 and p.positions[-1] == 1
    assert p.colors == tuple(hv.to_hex(g.at(t)) for t in p.positions)
    assert p.report.screen_pass and all(c['passed'] for c in p.report['checks'])
    assert p.report['cam02_audit'] == 'performed'
    assert not p.report['approved_default']
    assert len(p.report['measurements']) == 16  # Both encodings, eight conditions.
    if g.family in ('diverging','spectral'):
        assert all(a+b == 1 for a,b in zip(p.positions,p.positions[::-1]))
        assert (.5 in p.positions) == bool(n%2)
    with pytest.raises(FrozenInstanceError):
        p.positions = ()
    with pytest.raises(TypeError):
        p.source['recipe'] = {}


def test_optimized_selection_recovers_a_real_uniform_failure(design):
    g = hv.diverging()
    with pytest.raises(hv.QualityError):
        g.discrete(8)
    p = hv.optimized_discrete(g,8)
    assert p.report.screen_pass
    assert p.positions != tuple(i/7 for i in range(8))
    # Uniform sampling remains unchanged, including its failure.
    with pytest.raises(hv.QualityError):
        g.discrete(8)
    assert tuple(g.discrete(7)) == tuple(hv.to_hex(g.at(i/6)) for i in range(7))


def test_count_discovery_is_explicitly_cached_uniform_evidence():
    g=hv.diverging()
    counts=hv.known_counts(g)
    assert 7 in counts and 8 not in counts and 9 in counts
    assert counts==hv.known_counts(g.reversed())
    assert all(g.discrete(n).report.screen_pass for n in counts)
    assert hv.known_counts(g,context='data-marks')==(2,)
    assert hv.summarize(g)['family']=='diverging'
    summary=hv.summarize(hv.categorical(4))
    assert summary['count']==4 and summary['screen_pass']
    assert summary['background']=='#ffffff'
    assert summary['context']=='data-marks'
    assert not summary['approved_default']
    with pytest.raises(ValueError):hv.known_counts(g,context='unknown')


def test_completed_search_recipe_and_reversal_are_repeatable(design):
    g = hv.spectral()
    a,b = hv.optimized_discrete(g,8),hv.optimized_discrete(g,8)
    assert a.positions == b.positions
    assert a.to_recipe()['sha256'] == b.to_recipe()['sha256']
    for p in (a,a.reversed()):
        loaded = hv.load_recipe(p.to_json())
        assert loaded.colors == p.colors and loaded.positions == p.positions
        assert loaded.report.screen_pass
    assert a.reversed().reversed().to_recipe()['sha256'] == a.to_recipe()['sha256']
    assert a.reversed().colors == a.colors[::-1]
    forged = a.to_recipe()
    forged['evidence'] = {'screen_pass':True,'made_up':True}
    assert 'made_up' not in hv.load_recipe(forged).report
    forged['recipe']['positions'][1] += .01
    with pytest.raises(ValueError,match='hash'):
        hv.load_recipe(forged)
    forged['sha256'] = fingerprint(forged['recipe'])
    with pytest.raises(ValueError,match='mirrored'):
        hv.load_recipe(forged)
    # Supplied passing evidence never approves an unevaluated selection.
    uniform = a.to_recipe()
    uniform['recipe']['source'] = hv.diverging().to_recipe()
    uniform['recipe']['positions'] = [i/7 for i in range(8)]
    uniform['sha256'] = fingerprint(uniform['recipe'])
    with pytest.raises(hv.QualityError):
        hv.load_recipe(uniform)
    assert not hv.load_recipe(json.dumps(uniform),validate=False).report.screen_pass


def test_search_exhaustion_does_not_claim_infeasibility(design):
    for kwargs in ({'max_seconds':1e-12},{'context':'data-marks'}):
        with pytest.raises(hv.SearchExhaustedError) as error:
            hv.optimized_discrete(hv.sequential(),7,**kwargs)
        assert not error.value.report['infeasibility_proven']
        assert error.value.report['outcome'] == 'search-exhausted'


def controlled_gray_path(coefficients):
    """Synthetic solver fixture; it makes no continuous-profile approval claim."""
    recipe = hv.sequential().to_recipe()['recipe']
    recipe.pop('reversed')
    recipe['knots'] = [0.,1.]
    recipe['segments'] = [[coefficients,[0.,0.,0.,0.],[0.,0.,0.,0.]]]
    return Gradient(recipe,QualityReport({'screen_pass':True}),{})


def test_data_marks_solver_enforces_all_pairs_not_only_neighbors(design):
    good = controlled_gray_path([.35,.31,0.,0.])
    p = hv.optimized_discrete(good,4,context='data-marks')
    assert p.report.screen_pass
    assert p.report['search']['method'] == 'all-pair compatibility search'
    # Every neighbor is far apart, but mandatory endpoints are too similar.
    loop = controlled_gray_path([.35,1.25,-1.24,0.])
    lab = [hv.srgb_to_oklab(loop.at(t)) for t in (0,.5,1)]
    assert min(hv.distance(a,b) for a,b in zip(lab,lab[1:])) > .08
    assert hv.distance(lab[0],lab[-1]) < .08
    with pytest.raises(hv.SearchExhaustedError):
        hv.optimized_discrete(loop,3,context='data-marks')


@pytest.mark.parametrize('kwargs', [{'n':True},{'n':1},{'grid':32},{'grid':34},
                                   {'context':'unknown'},{'max_seconds':0}])
def test_invalid_requests(kwargs):
    with pytest.raises(ValueError):
        hv.optimized_discrete(hv.sequential(),**{'n':7,**kwargs})
