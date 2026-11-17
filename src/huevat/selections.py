"""Prepared optimized colors and bounded advice for nearby counts."""
from functools import lru_cache
from time import monotonic
from ._data import load_data
from .gradients import fingerprint,QualityReport,QualityError,SearchExhaustedError,ConstraintConflictError,_thaw
from .sampling import SampledPalette,optimized_discrete as _search,known_counts as _known


@lru_cache(maxsize=1)
def _data():return load_data('optimized-v1.json')


def optimized_discrete(gradient,n,*,context=None,grid=257,max_seconds=10.):
    from .sampling import _request
    from .gradients import Gradient
    if not isinstance(gradient,Gradient):raise ValueError('Expected a Huevat gradient')
    if gradient.family=='cyclic':raise ValueError('Use cyclic.discrete(n); ordered sampling does not apply to a closed path')
    context=context or gradient._recipe['context']
    _request(gradient,n,context,grid,max_seconds)
    key=f'{fingerprint(gradient.to_recipe()["recipe"])}/{context}/{n}'
    if grid==257:
        entry=_data()['selections'].get(key)
        if entry is not None:
            return SampledPalette(tuple(entry['colors']),QualityReport(entry['report']),tuple(entry['positions']),entry['source'])
    return _search(gradient,n,context=context,grid=grid,max_seconds=max_seconds)


def known_counts(gradient,*,context=None):
    if gradient.family=='cyclic':
        context=context or 'filled-fields'
        if context not in ('filled-fields','data-marks'):raise ValueError('Unknown context')
        return tuple(sorted(int(k.split('/')[1]) for k,v in gradient._discrete_records.items()
                            if k.startswith(context+'/') and v['screen_pass']))
    return _known(gradient,context=context)


def count_options(gradient,n,*,radius=2,context=None,max_seconds=10.):
    if isinstance(n,bool) or not isinstance(n,int) or n<2:raise ValueError('n must be an integer of at least two')
    if isinstance(radius,bool) or not isinstance(radius,int) or not 0<=radius<=8:raise ValueError('radius must be in [0,8]')
    from .gradients import _finite
    if _finite(max_seconds,'max_seconds')<=0:raise ValueError('max_seconds must be positive')
    context=context or gradient._recipe['context'];deadline=monotonic()+max_seconds
    choices=[]
    for count in sorted(range(max(2,n-radius),n+radius+1),key=lambda k:(abs(k-n),k)):
        try:
            p=gradient.discrete(count,context=context);method='uniform'
        except ImportError as e:
            choices.append({'count':count,'status':'unknown','reason':str(e)});continue
        except QualityError:
            if gradient.family=='cyclic':choices.append({'count':count,'status':'failed'});continue
            if monotonic()>=deadline:choices.append({'count':count,'status':'unknown','reason':'time budget'});continue
            try:p=optimized_discrete(gradient,count,context=context,max_seconds=max(.001,deadline-monotonic()));method='optimized'
            except (SearchExhaustedError,ImportError) as e:
                choices.append({'count':count,'status':'unknown','reason':str(e)});continue
            except QualityError:
                choices.append({'count':count,'status':'failed'});continue
        choices.append({'count':count,'status':'passed','method':method,'colors':p.colors})
    return QualityReport({'choices':choices,'passing_counts':[c['count'] for c in choices if c['status']=='passed'],
                          'scope':'bounded nearby search; unknown is not failure','context':context})
