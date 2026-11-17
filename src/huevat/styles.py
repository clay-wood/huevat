"""Short palette names and separately checked categorical alternatives."""
from functools import lru_cache
import json

from .categorical import categorical as _core, load_recipe as _previous
from .families import CategoricalPalette, _count
from .gradients import QualityReport, QualityError, fingerprint, _thaw, background_rgb
from ._data import load_data
from .space import to_hex

VERSION = 'h5-categorical-v1'
ANCHORS = {
    'earth': ('#a45f46','#4d8490','#8d803e','#7c7192','#4c8871','#a66d83','#64829d','#8c815a'),
    'gem': ('#5268ac','#bb5779','#168e8d','#b38422','#985ba2','#427fbc','#a56849','#66894e'),
}


def categorical_names():
    return ('core','earth','gem','max-separation')


@lru_cache(maxsize=1)
def _data():
    return load_data('categorical-v3.json')


def categorical(n, colors=None, *, background='light', style='core', seed=14507,
                max_seconds=30., starts=3):
    if not isinstance(style,str):raise ValueError('Choose a categorical style name')
    if style in ('core','clearer','max-separation'):
        return _core(n,colors,background=background,style='clearer' if style=='core' else style,
                     seed=seed,max_seconds=max_seconds,starts=starts)
    if style not in ANCHORS: raise ValueError('Choose core, earth, gem or max-separation')
    _count(n); background_rgb(background)
    from .gradients import _request_options
    _request_options('data-marks',seed,max_seconds,starts)
    if colors is None and background in ('light','dark') and (seed,max_seconds,starts)==(14507,30.,3):
        entry=_data()['designs'].get(f'{style}/{background}/{n}')
        if entry is not None:
            return CategoricalPalette(tuple(entry['report']['hex']),QualityReport(entry['report']))
    return generate(style,n,colors,background=background,seed=seed,max_seconds=max_seconds,starts=starts)


def generate(style,n,colors=None,**options):
    from .design_categorical import generate as search
    from .space import from_hex, srgb_to_oklab, oklab_to_oklch, gamut_map
    bg=background_rgb(options.get('background','light'))
    preferences=list(colors) if colors is not None else list(ANCHORS[style][:n])
    if colors is None:
        from .design_categorical import target_colors
        baseline,_=target_colors(n,None,bg)
        preferences.extend(baseline[len(preferences):n])
        if sum(bg)<1.5:
            preferences=[to_hex(gamut_map((min(.84,L+.12),C,h)))
                         for L,C,h in [oklab_to_oklch(srgb_to_oklab(from_hex(c))) for c in preferences]]
    p=search(n,preferences,**options)
    report=p.report.to_dict(); recipe=report['recipe']
    recipe.update(algorithm_version=VERSION,style=style)
    report.update(algorithm_version=VERSION,style=style,recipe=recipe,recipe_sha256=fingerprint(recipe),
                  style_review={'status':'appearance review pending','scope':'independent count/background numerical checks'})
    return CategoricalPalette(p.colors,QualityReport(report))


def validate(recipe):
    if recipe.get('algorithm_version')!=VERSION or recipe.get('style') not in ANCHORS:
        raise ValueError('Unknown categorical recipe version/style')
    from .design_categorical import validate_categorical
    proxy=_thaw(recipe); proxy.update(algorithm_version='h3-categorical-v2',style='clearer')
    result=validate_categorical(proxy)
    result.update(algorithm_version=VERSION,style=recipe['style'],recipe=_thaw(recipe),recipe_sha256=fingerprint(recipe))
    return result


def load_recipe(value,*,validate=True):
    if not isinstance(validate,bool): raise ValueError('validate must be boolean')
    if isinstance(value,str):
        try: value=json.loads(value)
        except ValueError: raise ValueError('Invalid recipe JSON') from None
    if not isinstance(value,dict) or not isinstance(value.get('recipe'),dict) or value['recipe'].get('algorithm_version')!=VERSION:
        return _previous(value,validate=validate)
    if set(value)!={'recipe','sha256','evidence'} or fingerprint(value['recipe'])!=value['sha256']:
        raise ValueError('Recipe hash mismatch')
    body=value['recipe']
    for entry in _data()['designs'].values():
        if fingerprint(body)==fingerprint(entry['recipe']):
            return CategoricalPalette(tuple(entry['report']['hex']),QualityReport(entry['report']))
    # Structural validation is required even when numerical checking is skipped.
    from .categorical import check_recipe
    proxy=_thaw(body);proxy.update(algorithm_version='h3-categorical-v2',style='clearer');check_recipe(proxy)
    report={'screen_pass':False,'outcome':'unvalidated-recipe','recipe':body}
    if validate:
        report=globals()['validate'](body)
        if not report['screen_pass']: raise QualityError('Imported palette fails its color checks',report)
    return CategoricalPalette(tuple(map(to_hex,body['rgb'])),QualityReport(report))
