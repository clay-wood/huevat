import json
from pathlib import Path

from huevat._data import load_data

ROOT = Path(__file__).resolve().parents[1]


def test_all_four_prepared_contexts_and_discrete_records_are_complete():
    data = load_data('ordered-v1.json')
    assert set(data['designs']) == {'sequential/light','sequential/dark','diverging/light','diverging/dark'}
    for entry in data['designs'].values():
        assert entry['report']['screen_pass']
        for context in ('filled-fields','data-marks'):
            counts=sorted(int(k.split('/')[1]) for k in entry['discrete'] if k.startswith(context+'/'))
            assert counts == list(range(2,counts[-1]+1))
        assert entry['discrete']['filled-fields/7']['screen_pass']
        assert entry['report']['preferred_changes']
        assert not entry['report']['approved_default']


def test_review_artifacts_are_present_without_claiming_approval():
    output = ROOT/'research/ordered-v1'
    if not output.exists():
        import pytest
        pytest.skip('Review artifacts are retained in the repository, not base wheels')
    review = json.loads((output/'review.json').read_text(encoding='utf-8'))
    assert review['status'] == 'pending'
    assert len(review['panels']) == 8
    assert all((output/entry['file']).is_file() and entry['status']=='pending' for entry in review['panels'])
