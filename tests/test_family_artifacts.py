import json
from pathlib import Path
from huevat._data import load_data


def test_h3_corpus_and_complete_review_inventory():
    data=load_data('families-v1.json')
    assert set(data['categorical'])=={f'{bg}/{n}' for bg in ('light','dark') for n in range(2,13)}
    assert set(data['ordered'])=={f'{f}/{bg}' for f in ('multihue','spectral') for bg in ('light','dark')}
    for entry in data['categorical'].values():assert entry['report']['screen_pass']
    for entry in data['ordered'].values():
        assert entry['report']['screen_pass']
        assert entry['report']['certificate']['passed']
        assert any(not r['screen_pass'] for r in entry['discrete'].values())
        assert any(r['screen_pass'] for r in entry['discrete'].values())
    output=Path(__file__).resolve().parents[1]/'research/families-v1'
    review=json.loads((output/'review.json').read_text(encoding='utf-8'))
    assert review['status']=='pending' and len(review['panels'])==18
    assert all(p['status']=='pending' and (output/p['file']).is_file() for p in review['panels'])
    results=json.loads((output/'results.json').read_text(encoding='utf-8'))
    assert results['approved_defaults']==[]
    assert not results['benchmark']['optional_modules_loaded']
