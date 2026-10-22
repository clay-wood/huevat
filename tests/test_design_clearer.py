import pytest
np=pytest.importorskip('numpy')
pytest.importorskip('scipy');pytest.importorskip('colorspacious')
import huevat as hv
from huevat.design_categorical import generate
from huevat.gradients import fingerprint

pytestmark=pytest.mark.research


def test_clearer_completed_search_repeats():
    a=generate(6,starts=2,max_seconds=60)
    b=generate(6,starts=2,max_seconds=60)
    assert a.report.screen_pass and a.to_recipe()['sha256']==b.to_recipe()['sha256']
    assert len(a.report['search']['optimizer_runs'])==2
    assert not a.report['search']['deadline_reached']


def test_clearer_custom_background_and_supplied_preferences_are_audited():
    p=hv.categorical(4,colors=('#4379a3','#348b83','#ae883b','#bd6c60'),background='#202a30',starts=2,max_seconds=60)
    assert p.report.screen_pass and len(p.report['preferred_changes'])==4
    assert all(hv.contrast(c,hv.from_hex('#202a30'))>=3 for c in p.rgb)
    assert hv.load_recipe(p.to_json()).colors==p.colors


def test_clearer_deadline_and_conflicting_targets_never_claim_infeasibility():
    with pytest.raises(hv.SearchExhaustedError) as error:generate(6,max_seconds=1e-9)
    assert error.value.report['deadline_reached'] and not error.value.report['infeasibility_proven']


def test_unknown_clearer_recipe_checks_aesthetic_gates_in_addition_to_H1():
    envelope=hv.categorical(4).to_recipe()
    envelope['recipe']['targets'][0]=[.1,0,0]
    envelope['sha256']=fingerprint(envelope['recipe']);envelope['evidence']={'screen_pass':True}
    with pytest.raises(hv.QualityError) as error:hv.load_recipe(envelope)
    assert any(c['name']=='clearer/target_movement_max' and not c['passed'] for c in error.value.report['checks'])
