"""Closed cubic paths for directions and phase; never an ordered-field claim."""
import json
import math
from functools import lru_cache
from .gradients import Gradient,Palette,QualityReport,QualityError,fingerprint,_thaw,_finite
from ._data import load_data
from .space import to_hex

VERSION='h5-cyclic-v1'


@lru_cache(maxsize=1)
def _data(): return load_data('cyclic-v1.json')


class CyclicGradient(Gradient):
    def at(self,t):
        _finite(t,'t')
        return super().at(0. if t==1 else t)
    def reversed(self): return CyclicGradient(self._recipe,self._report,self._discrete_records,not self._reverse)
    def discrete(self,n=9,*,context=None):
        if isinstance(n,bool) or not isinstance(n,int) or not 2<=n<=64: raise ValueError('n must be in [2,64]')
        context=context or 'filled-fields'
        if context not in ('filled-fields','data-marks'):raise ValueError('Unknown context')
        positions=tuple(i/n for i in range(n))
        colors=tuple(self.at(t) for t in positions)
        # Reversal changes the sampled phase; do not reverse a cached list.
        report=self._discrete_records.get(f'{context}/{n}')
        if report is None: report=screen(colors,self.background,context)
        report=_thaw(report);report.update(family='cyclic',positions=positions,sampling='uniform periodic; duplicate endpoint excluded')
        if not report['screen_pass']:raise QualityError('Cyclic selection fails its closing-pair/color checks',report)
        return Palette(tuple(map(to_hex,colors)),QualityReport(report))


def cyclic(*,background='light'):
    if background not in ('light','dark'):raise ValueError('Choose light or dark')
    d=_data()['designs'][background]
    return CyclicGradient(d['recipe'],QualityReport(d['report']),d['discrete'])


def recipe(background):
    from .gradients import background_rgb
    points=[]
    for i in range(8):
        h=2*math.pi*i/8
        points.append((.64+.10*math.sin(h+.7),.075*math.cos(h),.075*math.sin(h)))
    segments=[]
    for i,p in enumerate(points):
        q=points[(i+1)%8]
        d=tuple((points[(i+1)%8][j]-points[(i-1)%8][j])/2 for j in range(3))
        e=tuple((points[(i+2)%8][j]-points[i][j])/2 for j in range(3))
        segments.append([[p[j],d[j],3*(q[j]-p[j])-2*d[j]-e[j],2*(p[j]-q[j])+d[j]+e[j]] for j in range(3)])
    return dict(schema_version=1,algorithm_version=VERSION,family='cyclic',context='filled-fields',
                background=list(background_rgb(background)),identifier=f'h5-phase-{background}',
                knots=[i/8 for i in range(9)],segments=segments,preferences=[])


def validate(body,*,measure=True):
    from ._certify import _bernstein,_split,_gamut_bounds
    if set(body)!={'schema_version','algorithm_version','family','context','background','identifier','knots','segments','preferences'}:
        raise ValueError('Invalid cyclic recipe fields')
    if body['schema_version']!=1 or body['algorithm_version']!=VERSION or body['family']!='cyclic' or body['context']!='filled-fields':
        raise ValueError('Invalid cyclic recipe version/family')
    knots,segments=body['knots'],body['segments']
    if not isinstance(knots,(list,tuple)) or not 3<=len(knots)<=65 or len(segments)!=len(knots)-1:
        raise ValueError('Invalid cyclic knot count')
    for t in knots:_finite(t,'knot')
    if knots[0]!=0 or knots[-1]!=1 or any(a>=b for a,b in zip(knots,knots[1:])):raise ValueError('Invalid knots')
    from .gradients import background_rgb
    background_rgb(body['background'])
    if not isinstance(body['identifier'],str) or len(body['identifier'])>256:raise ValueError('Invalid identifier')
    continuity=derivative=0.
    for i,s in enumerate(segments):
        if len(s)!=3 or any(len(c)!=4 for c in s):raise ValueError('Expected cubic triples')
        for c in s:
            for v in c:_finite(v,'coefficient')
        prev=segments[i-1]; left=knots[i]-knots[i-1] if i else knots[-1]-knots[-2]
        right=knots[i+1]-knots[i]
        continuity=max(continuity,*(abs(sum(a)-b[0]) for a,b in zip(prev,s)))
        derivative=max(derivative,*(abs((a[1]+2*a[2]+3*a[3])/left-b[1]/right) for a,b in zip(prev,s)))
    pending=[(tuple(_bernstein(c) for c in s),0) for s in segments];cells=0;gamut=True
    while pending:
        controls,depth=pending.pop();cells+=1
        if all(lo>=-1e-12 and hi<=1+1e-12 for lo,hi in _gamut_bounds(controls)):continue
        if depth>=16 or cells>100000:gamut=False;break
        halves=[_split(c) for c in controls]
        pending.extend([(tuple(p[0] for p in halves),depth+1),(tuple(p[1] for p in halves),depth+1)])
    certificate={'gamut_pass':gamut,'closure_error':continuity,'derivative_error':derivative,'interval_cells':cells}
    checks=[{'name':'continuous_gamut','passed':gamut},{'name':'periodic_C1','passed':continuity<=1e-9 and derivative<=2e-7},
            {'name':'nonconstant_path','passed':any(abs(v)>1e-8 for s in segments for c in s for v in c[1:])}]
    if not all(c['passed'] for c in checks):return dict(screen_pass=False,certificate=certificate,checks=checks)
    if not measure:return dict(screen_pass=True,certificate=certificate,checks=checks,
                              scope='structural/gamut checks only; perceptual measurements not repeated')
    import numpy as np
    from .evaluation import condition_colors,_lab
    from .references import load_profile
    g=CyclicGradient(body,QualityReport({}),{});rgb=np.array([g.at(i/256) for i in range(257)])
    measurements={}
    for condition in load_profile()['conditions']:
        lab=_lab(condition_colors(rgb,condition)[0]);steps=np.linalg.norm(np.diff(lab,axis=0),axis=1)
        measurements[condition]={'step_min':float(steps.min()),'step_max':float(steps.max()),'speed_cv':float(steps.std()/steps.mean())}
    checks.append({'name':'normal_step_max','measured':measurements['normal']['step_max'],'threshold':.025,
                   'passed':measurements['normal']['step_max']<=.025})
    return dict(screen_pass=all(c['passed'] for c in checks),algorithm_version=VERSION,certificate=certificate,
                checks=checks,measurements=measurements,visual_review='pending',approved_default=False,
                scope='periodic C1/gamut/normal-step checks; CVD step variation reported, not ordered-field or human approval')


def screen(colors,background,context):
    import numpy as np
    from colorspacious import cspace_convert
    from .evaluation import condition_colors,_lab
    from .references import load_profile
    from .space import contrast
    checks=[]
    for encoding in ('float','u8'):
        rgb=np.array(colors)
        if encoding=='u8':rgb=np.rint(rgb*255)/255
        if context=='data-marks':checks.append({'name':encoding+'/contrast','passed':min(contrast(c,background) for c in rgb)>=3})
        for condition in load_profile()['conditions']:
            shown=condition_colors(rgb,condition)[0]
            for space,coords in (('oklab',_lab(shown)),('cam02',cspace_convert(shown,'sRGB1','CAM02-UCS'))):
                if context=='data-marks':
                    pairs=[(i,j) for i in range(len(rgb)) for j in range(i+1,len(rgb))]
                else:pairs=[(i,(i+1)%len(rgb)) for i in range(len(rgb))]
                minimum=min(float(np.linalg.norm(coords[i]-coords[j])) for i,j in pairs)
                threshold=(.08 if condition=='normal' else .04) if space=='oklab' else (8. if condition=='normal' else 4.)
                if context=='filled-fields':threshold/=2
                checks.append({'name':f'{encoding}/{condition}/{space}','measured':minimum,'threshold':threshold,'passed':minimum>=threshold})
    return {'screen_pass':all(c['passed'] for c in checks),'checks':checks,'context':context,'family':'cyclic','background':list(background)}


def load_recipe(value,*,validate=True):
    if not isinstance(validate,bool):raise ValueError('validate must be boolean')
    if isinstance(value,str):value=json.loads(value)
    if not isinstance(value,dict) or not isinstance(value.get('recipe'),dict) or value['recipe'].get('algorithm_version')!=VERSION:
        from .catalog import load_recipe as previous
        return previous(value,validate=validate)
    if set(value)!={'recipe','sha256','evidence'} or fingerprint(value['recipe'])!=value['sha256']:raise ValueError('Recipe hash mismatch')
    body=dict(value['recipe']);reverse=body.pop('reversed',False)
    if not isinstance(reverse,bool):raise ValueError('reversed must be boolean')
    for d in _data()['designs'].values():
        if fingerprint(body)==fingerprint(d['recipe']):return CyclicGradient(d['recipe'],QualityReport(d['report']),d['discrete'],reverse)
    report=globals()['validate'](body,measure=validate)
    if not report['screen_pass']:raise QualityError('Cyclic path failed its periodic checks',report)
    if not validate:report.update(screen_pass=False,outcome='unvalidated-recipe')
    return CyclicGradient(body,QualityReport(report),{},reverse)
