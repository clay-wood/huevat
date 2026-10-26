"""Lazy, dependency-free discovery of screened H4b gradient candidates."""
from functools import lru_cache
import json

from ._data import load_data
from .gradients import Gradient, QualityReport, QualityError, fingerprint
from .sampling import load_recipe as _load_previous


@lru_cache(maxsize=1)
def _catalog():
    data=load_data('collection-v1.json')
    if data['version']!='h4b-collection-v1':raise ValueError('Unsupported collection version')
    return data


def _selection(name, background=None):
    if not isinstance(name,str) or not name:raise ValueError('Supply a gradient name')
    suffixes=set()
    while name.endswith(('_r','_d')):
        suffix=name[-1]
        if suffix in suffixes:raise ValueError('Gradient suffixes may occur only once')
        suffixes.add(suffix);name=name[:-2]
    if background not in (None,'light','dark'):raise ValueError('Named candidates support light or dark')
    if 'd' in suffixes and background=='light':raise ValueError('_d conflicts with background="light"')
    return name, ('dark' if 'd' in suffixes else background or 'light'), 'r' in suffixes


def _entry(name):
    if not isinstance(name,str) or not name:raise ValueError('Supply a gradient name')
    try:return _catalog()['candidates'][name]
    except KeyError:raise ValueError(f'Unknown gradient {name!r}; use gradient_names()') from None


def gradient_names(*,family=None,domain=None):
    """Names of supported gradients; filters are metadata, not rankings."""
    if family not in (None,'sequential','diverging'):raise ValueError('Unknown family')
    if domain not in (None,'general','seismic','structure','geography','atmosphere'):raise ValueError('Unknown domain')
    return tuple(name for name,entry in _catalog()['candidates'].items()
                 if (family is None or entry['metadata']['family']==family)
                 and (domain is None or domain in entry['metadata']['domains']))


def gradient_info(name):
    """Immutable route, domain, direction and support metadata."""
    name,_,_=_selection(name)
    return QualityReport(_entry(name)['metadata'])


def gradient(name,*,background=None):
    """Load a named candidate; _d selects dark and _r reverses, in either order."""
    name,background,reverse=_selection(name,background)
    entry=_entry(name)
    if background not in entry['variants']:
        raise QualityError(f'No screened {background} variant for {name}',
                           {'screen_pass':False,'outcome':'unavailable-variant','name':name,'background':background})
    v=entry['variants'][background]
    return Gradient(v['recipe'],QualityReport(v['report']),v['discrete'],v['reversed'] ^ reverse)


def _variants():
    for entry in _catalog()['candidates'].values():
        yield from entry['variants'].values()
    yield from _catalog().get('archived',{}).values()


def _gradient_by_id(identifier):
    for v in _variants():
        if v['recipe']['identifier']==identifier:
            return Gradient(v['recipe'],QualityReport(v['report']),v['discrete'],v['reversed'])
    raise ValueError('Unknown collection design ID')


@lru_cache(maxsize=1)
def _known_recipes():
    return {fingerprint(v['recipe']):v for v in _variants()}


def load_recipe(value,*,validate=True):
    """Recognize shipped collection paths, then preserve every earlier loader."""
    if not isinstance(validate,bool):raise ValueError('validate must be boolean')
    if isinstance(value,str):
        try:value=json.loads(value)
        except ValueError:raise ValueError('Invalid recipe JSON') from None
    if isinstance(value,dict) and set(value)=={'recipe','sha256','evidence'}:
        body=value['recipe']
        if isinstance(body,dict) and isinstance(body.get('identifier'),str) and body['identifier'].startswith('h4b-'):
            try:matches=fingerprint(body)==value['sha256']
            except (ValueError,TypeError):raise ValueError('Recipe must contain finite JSON data') from None
            if not matches:raise ValueError('Recipe hash mismatch')
            reverse=body.get('reversed',False)
            if not isinstance(reverse,bool):raise ValueError('reversed must be boolean')
            canonical={k:v for k,v in body.items() if k!='reversed'}
            known=_known_recipes().get(fingerprint(canonical))
            if known is not None:
                return Gradient(known['recipe'],QualityReport(known['report']),known['discrete'],reverse)
    return _load_previous(value,validate=validate)
