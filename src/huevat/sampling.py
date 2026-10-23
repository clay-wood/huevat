"""Explicit optimized sampling and data-only positioned palette recipes."""
from dataclasses import dataclass
import json

from .gradients import (Gradient,Palette,QualityReport,QualityError,ConstraintConflictError,
                        _finite,_arc_bound,_freeze,_thaw,fingerprint)
from .categorical import load_recipe as _load_previous
from .space import to_hex


@dataclass(frozen=True)
class SampledPalette(Palette):
    positions: tuple
    source: dict

    def __post_init__(self):
        super().__post_init__()
        object.__setattr__(self,'positions',tuple(self.positions))
        object.__setattr__(self,'source',_freeze(_thaw(self.source)))
        _positions(self.positions,len(self.colors))

    def to_recipe(self):
        recipe={'schema_version':1,'algorithm_version':'h4-sampling-v1','family':'sampled',
                'source':_thaw(self.source),'positions':list(self.positions),'context':self.report['context']}
        return {'recipe':recipe,'sha256':fingerprint(recipe),'evidence':self.report.to_dict()}

    def to_json(self):return json.dumps(self.to_recipe(),indent=2,sort_keys=True,allow_nan=False)

    def reversed(self):
        source=_load_previous(_thaw(self.source),validate=False).reversed().to_recipe()
        source['evidence']={}
        report=self.report.to_dict();report['hex']=list(self.colors[::-1]);report['positions']=[1-t for t in self.positions[::-1]]
        report['reversed']=not report.get('reversed',False)
        report['source_sha256']=fingerprint(source['recipe'])
        if report.get('family') in ('diverging','spectral'):
            for item in report.get('checks',[]):
                item['name']=item['name'].replace('order_arm_0','order_arm_TEMP').replace('order_arm_1','order_arm_0').replace('order_arm_TEMP','order_arm_1')
        report['metric_parameterization']='selected colors; reversal reindexes invariant metrics'
        for m in report.get('measurements',{}).values():
            if 'closest_pair' in m:m['closest_pair']=sorted(len(self)-1-i for i in m['closest_pair'])
        return SampledPalette(self.colors[::-1],QualityReport(report),tuple(report['positions']),source)


def _positions(positions,n):
    if not isinstance(positions,(list,tuple)) or len(positions)!=n or not 2<=n<=1025:
        raise ValueError('Supply between 2 and 1025 sample positions')
    for t in positions:_finite(t,'position')
    if positions[0]!=0 or positions[-1]!=1 or any(a>=b for a,b in zip(positions,positions[1:])):
        raise ValueError('Positions must strictly increase from 0 to 1')


def _request(gradient,n,context,grid,max_seconds):
    if not isinstance(gradient,Gradient):raise ValueError('Expected a Huevat gradient')
    if isinstance(n,bool) or not isinstance(n,int) or n<2:raise ValueError('n must be an integer of at least two')
    if context not in ('filled-fields','data-marks'):raise ValueError('Unknown context')
    if isinstance(grid,bool) or not isinstance(grid,int) or not 33<=grid<=1025 or grid%2!=1:
        raise ValueError('grid must be an odd integer in [33, 1025]')
    if _finite(max_seconds,'max_seconds')<=0:raise ValueError('max_seconds must be positive')
    minimum=.04 if context=='filled-fields' else .08
    bound=_arc_bound(gradient._recipe['segments'])
    if (n-1)*minimum>bound+1e-12:
        raise ConstraintConflictError('Requested count exceeds this fixed path\'s length bound',
            {'screen_pass':False,'outcome':'constraint-conflict','scope':'this fixed path with retained endpoints',
             'requested_count':n,'required_total_distance':(n-1)*minimum,'path_length_upper_bound':bound})
    if n>grid:raise ValueError('grid must contain at least n candidates')
    if not gradient.report.screen_pass:
        raise QualityError('Optimize a screened gradient; revalidate imported recipes first',gradient.report.to_dict())


def optimized_discrete(gradient,n,*,context=None,grid=257,max_seconds=10.):
    """Choose endpoint-inclusive positions explicitly, preserving the source path.

    Filled fields use adjacent-distance dynamic programming; data marks enforce
    all pairs. Diverging/Spectral positions are mirrored and odd counts include
    the exact center. Results are not physical data-bin boundaries.
    """
    context=gradient._recipe['context'] if context is None and isinstance(gradient,Gradient) else context
    _request(gradient,n,context,grid,max_seconds)
    from ._sampling_design import optimize
    return optimize(gradient,n,context,grid,max_seconds)


def known_counts(gradient,*,context=None):
    """Prepared passing uniform counts only; unknown counts are not failures.

    This lookup never searches or imports optional dependencies. Optimized
    selections are separate and are not inferred from uniform-count evidence.
    """
    if not isinstance(gradient,Gradient):raise ValueError('Expected a Huevat gradient')
    context=gradient._recipe['context'] if context is None else context
    if context not in ('filled-fields','data-marks'):raise ValueError('Unknown context')
    if not gradient.report.screen_pass:
        raise QualityError('Count discovery requires a screened source',gradient.report.to_dict())
    canonical=gradient.reversed() if gradient._reverse else gradient
    result=[]
    for key,report in gradient._discrete_records.items():
        kind,count=key.split('/');n=int(count)
        if kind==context and report['screen_pass']:
            actual=tuple(to_hex(canonical.at(i/(n-1))) for i in range(n))
            if tuple(report['hex'])==actual:result.append(n)
    return tuple(sorted(result))


def summarize(source):
    """Return a small JSON-ready status view without copying detailed checks."""
    if isinstance(source,Gradient):
        report=source._report
        family=source.family
        background=source.background
        count=None
    elif isinstance(source,Palette):
        report=source.report
        family=report.get('family','categorical' if 'style' in report else 'discrete')
        background=report.get('background')
        count=len(source)
    else:raise ValueError('Expected a Huevat gradient or palette')
    return {'family':family,'count':count,'screen_pass':report.screen_pass,
            'approved_default':report.get('approved_default',False),
            'context':report.get('context',report.get('profile_context')),'background':None if background is None else to_hex(background),
            'failed_checks':tuple(sorted({c['name'] for c in report.get('checks',()) if not c['passed']}))}


def load_recipe(value,*,validate=True):
    if not isinstance(validate,bool):raise ValueError('validate must be boolean')
    if isinstance(value,str):
        try:value=json.loads(value)
        except ValueError:raise ValueError('Invalid recipe JSON') from None
    if not isinstance(value,dict) or set(value)!={'recipe','sha256','evidence'}:raise ValueError('Expected a Huevat recipe envelope')
    body=value['recipe']
    if not isinstance(body,dict) or body.get('algorithm_version')!='h4-sampling-v1':return _load_previous(value,validate=validate)
    try:matches=fingerprint(body)==value['sha256']
    except (ValueError,TypeError):raise ValueError('Recipe must contain finite JSON data') from None
    if not matches:raise ValueError('Recipe hash mismatch')
    if set(body)!={'schema_version','algorithm_version','family','source','positions','context'} or body['schema_version']!=1 or body['family']!='sampled':
        raise ValueError('Invalid sampled recipe schema')
    if body['context'] not in ('filled-fields','data-marks'):raise ValueError('Unknown context')
    positions=body['positions'];_positions(positions,len(positions) if isinstance(positions,(list,tuple)) else 0)
    source=_load_previous(body['source'],validate=validate)
    if not isinstance(source,Gradient):raise ValueError('Sampled source must be a gradient')
    if source.family in ('diverging','spectral'):
        if any(abs(a+b-1)>1e-12 for a,b in zip(positions,positions[::-1])) or (len(positions)%2 and positions[len(positions)//2]!=.5):
            raise ValueError('Diverging positions must be mirrored with an exact odd-count center')
    rgb=tuple(source.at(t) for t in positions)
    report={'screen_pass':False,'outcome':'unvalidated-recipe','approved_default':False,'context':body['context'],'positions':positions}
    if validate:
        from ._sampling_design import screen
        report=screen(source,positions,body['context'])
        if not report['screen_pass']:raise QualityError('Imported selection fails its exact discrete profile',report)
    return SampledPalette(tuple(map(to_hex,rgb)),QualityReport(report),tuple(positions),body['source'])
