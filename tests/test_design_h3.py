import pytest
np=pytest.importorskip('numpy')
pytest.importorskip('scipy');pytest.importorskip('colorspacious')
import huevat as hv
from huevat.design_h3 import generate_categorical,generate_ordered,validate_categorical,validate_ordered
from huevat.families import MULTIHUE_COLORS,SPECTRAL_COLORS,HueGradient
from huevat.gradients import QualityReport,fingerprint

pytestmark=pytest.mark.research


@pytest.mark.parametrize('bg',['light','dark'])
def test_joint_categorical_search_is_repeatable_and_records_auxiliary_variable(bg):
    a=generate_categorical(4,background=bg,starts=2,max_seconds=60)
    b=generate_categorical(4,background=bg,starts=2,max_seconds=60)
    assert a.report.screen_pass and b.report.screen_pass
    assert a.to_recipe()['sha256']==b.to_recipe()['sha256']
    runs=a.report['search']['optimizer_runs']
    assert len(runs)==2 and all(r['auxiliary_minimum']>=.041 for r in runs)
    assert not a.report['search']['deadline_reached']


def test_preferences_are_adjustable_and_custom_background_is_audited():
    p=hv.categorical(4,colors=['#0072b2']*4,background='#202a30',style='max-separation',starts=2,max_seconds=60)
    assert p.report.screen_pass and len(set(p))==4
    assert len(p.report['preferred_changes'])==4
    assert all(hv.contrast(c,hv.from_hex('#202a30'))>=3 for c in p.rgb)
    loaded=hv.load_recipe(p.to_json())
    assert loaded.colors==p.colors and loaded.report.screen_pass


@pytest.mark.parametrize('family,colors',[('multihue',MULTIHUE_COLORS),('spectral',SPECTRAL_COLORS)])
def test_completed_h3_ordered_search_repeats(family,colors):
    a=generate_ordered(family,colors,starts=1,max_seconds=120)
    b=generate_ordered(family,colors,starts=1,max_seconds=120)
    assert a.report.screen_pass and a.to_recipe()['sha256']==b.to_recipe()['sha256']
    assert len(a.report['search']['optimizer_runs'])>=1
    assert not a.report['search']['deadline_reached']


@pytest.mark.parametrize('call',[lambda:generate_categorical(4,max_seconds=1e-9),
                                lambda:generate_ordered('spectral',SPECTRAL_COLORS,max_seconds=1e-9)])
def test_budget_failure_never_claims_infeasibility(call):
    with pytest.raises(hv.SearchExhaustedError) as e:call()
    assert e.value.report['outcome']=='search-exhausted'
    assert e.value.report['deadline_reached'] and not e.value.report['infeasibility_proven']


def test_unknown_recipes_cannot_claim_passing_and_constant_hue_is_rejected():
    envelope=hv.categorical(4).to_recipe()
    envelope['recipe']['rgb'][1]=envelope['recipe']['rgb'][0]
    envelope['sha256']=fingerprint(envelope['recipe']);envelope['evidence']={'screen_pass':True}
    with pytest.raises(hv.QualityError):hv.load_recipe(envelope)
    assert not hv.load_recipe(envelope,validate=False).report.screen_pass
    envelope=hv.sequential().to_recipe();recipe=envelope['recipe'];recipe.pop('reversed')
    recipe.update(algorithm_version='h3-families-v1',family='multihue',preferences=list(MULTIHUE_COLORS))
    report=validate_ordered(HueGradient(recipe,QualityReport({}),{}))
    assert not report['screen_pass']
    assert any(not c['passed'] and 'hue_span' in c['name'] for c in report['checks'])
    envelope={'recipe':recipe,'sha256':fingerprint(recipe),'evidence':{'screen_pass':True}}
    with pytest.raises(hv.QualityError):hv.load_recipe(envelope)


def test_unknown_h3_path_is_reaudited_and_bins_have_cam02_results():
    envelope=hv.spectral(background='dark').to_recipe()
    envelope['recipe']['identifier']='independently-audited-h3-copy'
    envelope['sha256']=fingerprint(envelope['recipe'])
    g=hv.load_recipe(envelope)
    assert g.report.screen_pass
    for n in (3,5):
        try:p=g.discrete(n)
        except hv.QualityError:continue
        assert all('minimum_cam02_distance' in m for m in p.report['measurements'].values())
