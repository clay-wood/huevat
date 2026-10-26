"""Optional finite construction search for the declared H4b free-knot routes."""
import importlib.metadata as md
import itertools
import math
import time

import numpy as np
from scipy.interpolate import PchipInterpolator, CubicHermiteSpline

from ._collection_specs import SPECS, VERSION, specification
from .design import _local_coefficients, _raw_rgb, validate_gradient
from .evaluation import evaluate
from .gradients import Gradient, QualityReport, SearchExhaustedError, background_rgb, _finite
from .space import gamut_map, to_hex


def _spline(knots, values, neutral=False):
    values=np.asarray(values)
    slopes=PchipInterpolator(knots,values,axis=0).derivative()(knots)
    if neutral:slopes[0]=0.
    spline=CubicHermiteSpline(knots,values,slopes,axis=0)
    return [[_local_coefficients(lambda x,nu=0,j=j:spline(x,nu=nu)[j],a,b).tolist()
             for j in range(3)] for a,b in zip(knots,knots[1:])]


def _coordinates(L,C,hue):
    h=np.radians(hue)
    return np.column_stack((L,C*np.cos(h),C*np.sin(h)))


def make_recipe(name, background, scale=1., endpoint_shift=0., balance=1., arm_shift=0., curve_skew=0., range_mode=0, *, spec_version=None):
    spec=specification(name,spec_version);dark=background=='dark'
    knots=np.array(spec['knots']);nominal_fraction=knots+spec['skew']*knots*(1-knots)
    fraction=knots+(spec['skew']+curve_skew)*knots*(1-knots)
    if spec['family']=='sequential':
        low,high=([(.10,.97),(.19,.94),(.16,.975),(.17,.985)] if dark else [(.12,.985),(.22,.95),(.17,.985),(.16,.975)])[range_mode]
        low+=endpoint_shift;high-=endpoint_shift/4
        L=low+(high-low)*fraction
        C=scale*np.array(spec['chroma'])*np.array([.20 if range_mode!=1 else 1.,1.,1.,1.,1.,.20 if range_mode!=1 else 1.])
        controls=_coordinates(L,C,spec['hues'])
        segments=_spline(knots,controls)
        i=3
        preferences=[to_hex(gamut_map((float((.10 if dark else .12)+((.97 if dark else .985)-(.10 if dark else .12))*nominal_fraction[i]),
                                      spec['chroma'][i],spec['hues'][i])))]
    else:
        center=(.12 if dark else .965) if range_mode==0 else (.19 if dark else .98)
        end=((.86 if dark else .38) if range_mode==0 else (.80 if dark else .42))+endpoint_shift
        C=np.array(spec['chroma'])*scale
        if dark:C=C*np.array([1.,1.,1.,1.,.9,spec.get('dark_endpoint_factor',.42 if range_mode==0 else .65)])
        arms=[];preferences=[]
        for sign,hues,multiplier in ((1,spec['left'],math.sqrt(balance)),(-1,spec['right'],1/math.sqrt(balance))):
            L=center+(end-center)*fraction+sign*arm_shift*knots**spec.get('arm_offset_power',2)
            arms.append(_spline(knots,_coordinates(L,C*multiplier,hues),neutral=True))
            i=4
            nominal_center=.12 if dark else .965
            preferences.append(to_hex(gamut_map((float(nominal_center+((.86 if dark else .38)-nominal_center)*nominal_fraction[i]),
                spec['chroma'][i]*(.9 if dark else 1),hues[i]))))
        reverse_u=np.polynomial.Polynomial([1.,-1.])
        left=[]
        for segment in arms[0][::-1]:
            left.append([np.pad(np.polynomial.Polynomial(c)(reverse_u).coef,
                                (0,4-len(np.polynomial.Polynomial(c)(reverse_u).coef))).tolist() for c in segment])
        segments=left+arms[1]
        knots=np.r_[(1-knots[::-1])/2,(1+knots[1:])/2]
    return {'schema_version':1,'algorithm_version':'h2-ordered-v1','family':spec['family'],
        'background':list(background_rgb(background)),'context':'filled-fields','knots':knots.tolist(),
        'segments':segments,'preferences':preferences,'identifier':f'h4b-{name}-{background}-v{spec.get("version",1)}'}


def _lab_samples(recipe):
    values=[]
    for t in np.linspace(0,1,65):
        i=min(np.searchsorted(recipe['knots'],t,side='right')-1,len(recipe['segments'])-1)
        u=(t-recipe['knots'][i])/(recipe['knots'][i+1]-recipe['knots'][i])
        values.append(np.array(recipe['segments'][i])@np.array([1,u,u*u,u*u*u]))
    return np.array(values)


def _failure(check):
    return {k:(v if not isinstance(v,(float,np.floating)) or math.isfinite(v) else 'non-finite') for k,v in check.items()}


def generate(name, background, *, max_seconds=60.):
    """Closest feasible path in a finite, declared parameter grid; no clipping."""
    spec=SPECS[name]
    version=spec.get('construction_version',VERSION)
    started=time.perf_counter()
    if _finite(max_seconds,'max_seconds')<=0:raise ValueError('max_seconds must be positive')
    def exhausted(rejected,grid_candidates,best):
        raise SearchExhaustedError(f'No passing {name}/{background} candidate in the declared search',
            {'screen_pass':False,'outcome':'search-exhausted','infeasibility_proven':False,'algorithm_version':version,
             'name':name,'background':background,'candidates_tested':len(rejected),'grid_candidates':grid_candidates,
             'deadline_reached':time.perf_counter()-started>max_seconds,'closest_failures':best or [],'rejected':rejected})
    if time.perf_counter()-started>max_seconds:exhausted([],0,None)
    target=_lab_samples(make_recipe(name,background))
    options=[]
    div=spec['family']=='diverging'
    parameters=itertools.product((1.,.9,.8,.7,.675,.65),
        (0.,-.025,.025) if div else (0.,-.0125,.0125,-.025,.025),
        (1.,.85,1.15) if div else (1.,),(0.,-.01,.01,-.0175,.0175) if div else (0.,),
        (0.,.06,.12,.18,.24,.30,.36) if not div else (0.,.1),range(2 if div else 4))
    for i,params in enumerate(parameters):
        if i%32==0 and time.perf_counter()-started>max_seconds:exhausted([],len(options),None)
        recipe=make_recipe(name,background,*params)
        error=float(np.mean(np.sum((_lab_samples(recipe)-target)**2,axis=1)))
        options.append((error,params,recipe))
    options.sort(key=lambda v:(v[0],v[1]))
    rejected=[];best=None
    for at,(error,params,recipe) in enumerate(options):
        if time.perf_counter()-started>max_seconds:break
        rgb=_raw_rgb(recipe)
        failures=[]
        if rgb is None:failures=[{'name':'sampled-gamut','passed':False}]
        else:
            for encoding in ('float','u8'):
                r=evaluate(rgb,spec['family'],context='filled-fields',background=background,encoding=encoding)
                failures += [dict(c,name=encoding+'/'+c['name']) for c in r['criteria'] if not c['passed']]
        if not failures:
            report=validate_gradient(Gradient(recipe,QualityReport({}),{}))
            if report['screen_pass']:
                orientation=spec['orientation']
                reverse=spec['family']=='sequential' and (orientation=='depth-darkens' or (orientation=='background' and background=='light'))
                report.update(collection_construction_version=spec.get('construction_version',VERSION),collection_name=name,family=spec['family'])
                report['search']={'algorithm_version':version,'candidates_tested':at+1,'grid_candidates':len(options),
                    'elapsed_seconds':time.perf_counter()-started,'deadline_reached':time.perf_counter()-started>max_seconds,
                    'parameters':dict(zip(('chroma_scale','endpoint_shift','arm_balance','arm_lightness_shift','curve_skew','lightness_range'),params)),
                    'mean_squared_oklab_displacement':error,'rejected':rejected,
                    'versions':{n:md.version(n) for n in ('numpy','scipy','colorspacious')},
                    'scope':'closest passing candidate in the declared finite control grid; no global optimum claim'}
                return Gradient(recipe,QualityReport(report),{},reverse)
            failures=[c for c in report['checks'] if not c['passed']]
            if not report['certificate']['passed']:failures.append({'name':'continuous-certificate','passed':False})
            if not report['dense_audit']['cvd_order_pass']:failures.append({'name':'dense-CVD-order','passed':False})
        record={'parameters':list(params),'failures':[_failure(c) for c in failures]}
        rejected.append(record)
        rank=lambda fs:(any(c['name']=='sampled-gamut' for c in fs),len(fs))
        if best is None or rank(record['failures'])<rank(best):best=record['failures']
    exhausted(rejected,len(options),best)
