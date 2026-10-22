"""Optional Clearer construction: hard screens followed by target preservation."""
import time

try:
    import numpy as np
    from scipy.optimize import minimize
except ImportError:
    raise ImportError("Custom Clearer construction requires huevat[design]") from None

from .categorical import VERSION, CLEARER_ANCHORS, check_recipe, legacy_recipe
from .design_h3 import (_pair_data, validate_categorical as _validate_legacy,
                        _Deadline, _search_report, _exhausted)
from .evaluation import _lab, _linear
from .families import CategoricalPalette, _count
from .gradients import QualityReport, background_rgb, fingerprint, _request_options
from .space import from_hex, gamut_map, oklab_to_oklch, oklch_to_oklab


def _is_light(bg):
    return bool(_linear(np.array([bg]))[0] @ np.array([.2126,.7152,.0722]) > .2)


def target_colors(n, colors, bg):
    """Return supplied preferences plus their coherent floating design targets."""
    light = _is_light(bg)
    preferences = list(CLEARER_ANCHORS[:n]) if colors is None else list(colors)
    if colors is None:
        # Larger custom counts keep the same target family. Search exhaustion
        # remains possible; no claim that 64 colors satisfy the profile.
        for i in range(len(preferences),n):
            L = (.52,.65,.58,.68,.61)[(i-len(CLEARER_ANCHORS))%5]
            h = (250+137.507764*i)%360
            from .space import to_hex
            preferences.append(to_hex(gamut_map((L,.12,h))))
    target = _lab(np.array([from_hex(c) for c in preferences]))
    if colors is None:
        target[:,1:] *= 1.18
        if not light:
            target[:,0] += .12
    else:
        # Supplied preferences retain their identity; only project targets into
        # the declared style region. Reports still compare with original RGB.
        lo,hi = (.44,.70) if light else (.59,.85)
        for i,row in enumerate(target):
            L,C,h = oklab_to_oklch(row)
            target[i] = oklch_to_oklab((min(hi,max(lo,L)),min(.17,max(.05,C)),h))
    return preferences,target


def validate_categorical(recipe):
    check_recipe(recipe)
    report = _validate_legacy(legacy_recipe(recipe))
    rgb = np.array(recipe['rgb']);lab = _lab(rgb)
    target = np.array(recipe['targets'])
    movement = np.linalg.norm(lab-target,axis=1)
    C = np.linalg.norm(lab[:,1:],axis=1)
    light = _is_light(recipe['background'])
    lo,hi = (.43,.72) if light else (.57,.87)
    values = {'lightness_min':float(lab[:,0].min()),'lightness_max':float(lab[:,0].max()),
              'chroma_min':float(C.min()),'chroma_max':float(C.max()),
              'target_movement_max':float(movement.max())}
    for name,threshold,relation in (('lightness_min',lo,'>='),('lightness_max',hi,'<='),
                                    ('chroma_min',.04,'>='),('chroma_max',.18,'<='),
                                    ('target_movement_max',.065,'<=')):
        measured = values[name]
        report['checks'].append({'name':'clearer/'+name,'condition':'normal','level':'construction',
                                 'measured':measured,'threshold':threshold,'relation':relation,
                                 'passed':bool(measured>=threshold-1e-7 if relation=='>=' else measured<=threshold+1e-7)})
    report.update(algorithm_version=VERSION,style='clearer',recipe=recipe,recipe_sha256=fingerprint(recipe),
                  aesthetic={'objective':'minimize squared Oklab target movement after hard separation floors',
                             'targets':recipe['targets'],'movement_by_color':movement.tolist(),
                             'squared_target_error':float(np.sum((lab-target)**2)),**values},
                  style_review={'status':'user-selected','reviewed_counts':[4,6,8],
                                'scope':'Clearer direction selected; expanded counts and H4 review remain separate'})
    report['screen_pass'] = all(c['passed'] for c in report['checks'])
    return report


def generate(n, colors=None, *, background='light', seed=14507, max_seconds=30., starts=3):
    _count(n);_request_options('data-marks',seed,max_seconds,starts)
    if colors is not None:
        if not isinstance(colors,(tuple,list)) or len(colors)!=n:
            raise ValueError('Supply one preferred #rrggbb color per category')
        for c in colors:from_hex(c)
    bg = background_rgb(background)
    started = time.perf_counter();deadline = started+max_seconds
    rng = np.random.default_rng(seed+n)
    candidates,runs,failures = [],[],[]
    expired = False

    def check_time():
        if time.perf_counter() >= deadline:raise _Deadline

    def objective(x):
        check_time()
        lab = _lab(x[:-1].reshape(n,3))
        return float(np.sum((lab-target)**2))

    def constraints(x):
        check_time()
        rgb = x[:-1].reshape(n,3);d,dc,lab = _pair_data(rgb)
        Y = _linear(rgb)@np.array([.2126,.7152,.0722])
        lum = (Ybg+.05)/3-.05-Y if light else Y-(3*(Ybg+.05)-.05)
        C = np.linalg.norm(lab[:,1:],axis=1)
        movement = np.linalg.norm(lab-target,axis=1)
        return np.r_[(d-x[-1]).ravel(),(dc-4.15).ravel(),lum-.004,
                     lab[:,0]-Llo,Lhi-lab[:,0],C-.04,.18-C,.065-movement]

    def consider(x):
        check_time()
        residual = float(min(constraints(x)))
        recipe = {'schema_version':1,'algorithm_version':VERSION,'family':'categorical',
                  'background':list(bg),'context':'data-marks','rgb':x[:-1].reshape(n,3).tolist(),
                  'preferences':preferences,'identifier':'custom','style':'clearer','targets':target.tolist()}
        report = validate_categorical(recipe)
        if residual>=-1e-7 and report['screen_pass']:
            candidates.append((objective(x),recipe,report))
        else:
            failures[:] = [c for c in report['checks'] if not c['passed']][:10]
            if residual < -1e-7:
                failures.append({'name':'search/constraint_residual','measured':residual,'threshold':-1e-7,
                                 'passed':False,'reason':'outside declared separation margins or aesthetic envelope'})

    try:
        check_time()
        preferences,target = target_colors(n,colors,bg)
        light = _is_light(bg)
        Ybg = _linear(np.array([bg]))[0] @ np.array([.2126,.7152,.0722])
        Llo,Lhi = (.43,.72) if light else (.57,.87)
        for start in range(starts):
            check_time()
            lab = target.copy()
            if start:lab += rng.normal(0,.018,lab.shape)
            rgb = np.array([gamut_map(oklab_to_oklch(row)) for row in lab])
            initial = np.r_[rgb.ravel(),.043]
            result = minimize(objective,initial,method='SLSQP',bounds=[(.002,.998)]*(3*n)+[(.043,.043)],
                              constraints={'type':'ineq','fun':constraints},options={'maxiter':200,'ftol':1e-10})
            runs.append({'start':start,'phase':'aesthetic-targets','success':bool(result.success),
                         'iterations':int(result.nit),'message':str(result.message),
                         'minimum_constraint_residual':float(min(constraints(result.x))),
                         'auxiliary_minimum':.043})
            consider(result.x)
    except _Deadline:
        expired = True
    search = _search_report(seed,starts,runs,started,expired)
    search.update(objective='meet normal/2 and simulated Oklab floor z=.043, then preserve Clearer targets',
                  priorities=['hard H1 screens and aesthetic envelope','minimum target movement'],
                  scope='local deterministic search; no infeasibility proof or global optimum claim')
    if not candidates:_exhausted('Clearer categorical',search,failures)
    _,recipe,report = min(candidates,key=lambda c:c[0])
    report['search'] = search
    return CategoricalPalette(tuple(report['hex']),QualityReport(report))
