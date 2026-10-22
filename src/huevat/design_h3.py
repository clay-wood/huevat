"""Optional joint maximin palettes and constrained multi-hue cubic paths."""
import importlib.metadata as md
import math
import time

try:
    import numpy as np
    from scipy.optimize import minimize
    from scipy.interpolate import CubicHermiteSpline
    from colorspacious import cspace_convert
except ImportError:
    raise ImportError("Custom H3 construction requires huevat[design]") from None

from .evaluation import evaluate, condition_colors, _lab, _linear
from .gradients import (Gradient, QualityReport, SearchExhaustedError, background_rgb,
                        _request_options, _thaw, fingerprint)
from .families import (HueGradient, CategoricalPalette, proxy_recipe, check_recipe,
                       _count, _colors)
from .space import contrast, from_hex, to_hex, srgb_to_oklab, oklab_to_srgb, distance
from .design import make_recipe as make_base, SEEDS, _local_coefficients, validate_gradient

VERSION = "h3-families-v1"
CONDITIONS = ("normal", "protan-50", "protan-80", "protan-100", "deutan-50", "deutan-80", "deutan-100", "tritan-100")
# Feasible prototype spines, not reviewed defaults. They only initialize a
# count-independent constrained search and undergo the full final audit.
ORDERED_SEEDS = {
    "multihue": (*SEEDS["sequential"], -45.),
    "spectral-light": (.311566758314164,.9,.06175,.114,.07425663163820921,94.77254042713679,55.),
    "spectral-dark": (.7794034181258568,.18723827452445815,.06175352949322569,.07488032122390077,.065,80.,25.),
}


class _Deadline(Exception):
    pass


def _search_report(seed, starts, runs, started, expired):
    return {"seed": seed, "requested_starts": starts, "optimizer_runs": runs,
            "deadline_reached": expired, "elapsed_seconds": time.perf_counter()-started,
            "versions": {p:md.version(p) for p in ("numpy", "scipy", "colorspacious")},
            "reproducibility": "Completed starts are deterministic for the recorded numerical stack; deadline-truncated runs may select different candidates."}


def _exhausted(family, search, failures):
    raise SearchExhaustedError(f"{family} search found no passing design within its budget. Increase starts/max_seconds or change preferences/background.",
        {"outcome": "search-exhausted", "screen_pass": False, "infeasibility_proven": False,
         "deadline_reached": search["deadline_reached"], "search": search, "closest_failures": failures})


def validate_categorical(recipe):
    check_recipe(recipe)
    rgb = np.asarray(recipe["rgb"])
    bg = tuple(recipe["background"])
    reports, checks = {}, []
    for encoding in ("float", "u8"):
        r = evaluate(rgb, "categorical", context="data-marks", background="light", encoding=encoding)
        values = rgb if encoding == "float" else np.rint(rgb*255)/255
        r["background_contrast"] = [contrast(row,bg) for row in values]
        for c in r["criteria"]:
            if c["name"] == "background_contrast":
                c["measured"] = min(r["background_contrast"])
                c["passed"] = c["measured"] >= c["threshold"]
            checks.append(dict(c, name=encoding+"/"+c["name"]))
        r["screen_pass"] = all(c["passed"] for c in r["criteria"])
        reports[encoding] = r
    lab = _lab(rgb)
    chroma = np.linalg.norm(lab[:,1:],axis=1)
    bounds = {"lightness_min":float(lab[:,0].min()),"lightness_max":float(lab[:,0].max()),
              "chroma_min":float(chroma.min()),"chroma_max":float(chroma.max())}
    for name,threshold,relation in (("lightness_min",.22,">="),("lightness_max",.95,"<="),
                                    ("chroma_min",.02,">="),("chroma_max",.26,"<=")):
        measured = bounds[name]
        checks.append({"name":"construction/"+name,"condition":"normal","level":"construction",
                       "measured":measured,"threshold":threshold,"relation":relation,
                       "passed":measured>=threshold-1e-7 if relation==">=" else measured<=threshold+1e-7})
    produced = np.rint(rgb*255)/255
    return {"algorithm_version": VERSION, "family": "categorical", "count": len(rgb),
            "profile_version": "h1-screening-v1", "profile_context": "data-marks", "background": list(bg),
            "recipe": recipe, "recipe_sha256": fingerprint(recipe), "hex": list(map(to_hex, rgb)),
            "checks": checks, "measurements": reports, "controlled_ranges": bounds,
            "preferred_changes": [{"index": i, "supplied": color, "produced": to_hex(produced[i]),
                                    "oklab_distance": distance(srgb_to_oklab(from_hex(color)), srgb_to_oklab(produced[i]))}
                                   for i,color in enumerate(recipe["preferences"])],
            "screen_pass": all(c["passed"] for c in checks), "visual_review": "pending", "approved_default": False,
            "validation_scope": "This exact floating design and its exported count; model screens do not prove human distinguishability."}


def _pair_data(rgb):
    rendered = np.array([condition_colors(rgb,c)[0] for c in CONDITIONS])
    labs = _lab(rendered.reshape(-1,3)).reshape(8,len(rgb),3)
    cam = cspace_convert(rendered,"sRGB1","CAM02-UCS")
    i,j = np.triu_indices(len(rgb),1)
    d = np.linalg.norm(labs[:,i]-labs[:,j],axis=2)
    dc = np.linalg.norm(cam[:,i]-cam[:,j],axis=2)
    # Normal vision retains its separately stricter (2x) frozen threshold.
    d[0] /= 2; dc[0] /= 2
    return d,dc,labs[0]


def generate_categorical(n, colors=None, *, background="light", seed=4403, max_seconds=30., starts=4):
    """Optimize all 3*n RGB coordinates and an explicit weakest-distance z."""
    _count(n); _request_options("data-marks", seed, max_seconds, starts)
    bg = background_rgb(background)
    preferences = [] if colors is None else list(colors)
    if preferences and len(preferences) != n:
        raise ValueError("Supply one preference per category")
    for color in preferences:
        from_hex(color)
    started = time.perf_counter(); deadline = started+max_seconds
    rng = np.random.default_rng(seed+n)
    Y_bg = _linear(np.array([bg]))[0] @ np.array([.2126,.7152,.0722])
    light = Y_bg > .2
    candidates, runs, failures = [], [], []
    expired = False

    def check_time():
        if time.perf_counter() >= deadline:
            raise _Deadline

    def constraints(x):
        check_time()
        rgb = x[:-1].reshape(n,3); d,dc,lab = _pair_data(rgb)
        Y = _linear(rgb) @ np.array([.2126,.7152,.0722])
        lum = (Y_bg+.05)/3-.05-Y if light else Y-(3*(Y_bg+.05)-.05)
        C = np.linalg.norm(lab[:,1:],axis=1)
        return np.r_[(d-x[-1]).ravel(), (dc-4.15).ravel(), lum-.005,
                     lab[:,0]-.22, .95-lab[:,0], C-.02, .26-C]

    def consider(x):
        check_time()
        if np.min(constraints(x)) < -1e-7:
            return
        recipe = {"schema_version": 1,"algorithm_version": VERSION,"family": "categorical",
                  "background": list(bg), "context": "data-marks", "rgb": x[:-1].reshape(n,3).tolist(),
                  "preferences": preferences,"identifier": "custom"}
        report = validate_categorical(recipe)
        if report["screen_pass"]:
            preference = sum(c["oklab_distance"]**2 for c in report["preferred_changes"])
            candidates.append((-float(_pair_data(np.array(recipe["rgb"]))[0].min()), preference, recipe, report))
        else:
            failures[:] = [c for c in report["checks"] if not c["passed"]][:8]

    try:
        check_time()
        # Independent count-specific farthest-point seeds; no published palette
        # is relabeled and no larger generated palette is truncated.
        bank = rng.uniform(.015,.985,(max(1400,n*100),3))
        Y = _linear(bank) @ np.array([.2126,.7152,.0722])
        bank = bank[Y<(Y_bg+.05)/3-.055] if light else bank[Y>3*(Y_bg+.05)-.045]
        labs = _lab(bank)
        bank = bank[(labs[:,0]>.22)&(labs[:,0]<.95)&(np.linalg.norm(labs[:,1:],axis=1)>.02)]
        if len(bank) < n:
            _exhausted("categorical", _search_report(seed,starts,runs,started,False), [{"reason":"insufficient feasible seed colors for this background branch"}])
        sim = np.array([_lab(condition_colors(bank,c)[0]) for c in CONDITIONS]);sim[0]*=.5
        for start in range(starts):
            check_time()
            chosen = [int(rng.integers(len(bank)))]
            for _ in range(1,n):
                ds = np.linalg.norm(sim[:,:,None,:]-sim[:,chosen,:][:,None,:,:],axis=3).min(axis=(0,2))
                chosen.append(int(ds.argmax()))
            initial_rgb = np.array([from_hex(c) for c in preferences]) if start==0 and preferences else bank[chosen]
            x = np.r_[initial_rgb.ravel(),.041]
            result = minimize(lambda v:-v[-1],x,method="SLSQP",bounds=[(.002,.998)]*(3*n)+[(.041,.4)],
                              constraints={"type":"ineq","fun":constraints},options={"maxiter":150,"ftol":1e-8})
            runs.append({"start":start,"phase":"maximin","success":bool(result.success),"iterations":int(result.nit),
                         "auxiliary_minimum":float(result.x[-1]),"message":str(result.message)})
            consider(result.x)
            if preferences and np.min(constraints(result.x)) >= -1e-7:
                target = np.array([srgb_to_oklab(from_hex(c)) for c in preferences])
                lower = float(result.x[-1])-1e-6
                def preserve(v):
                    check_time()
                    return float(np.sum((_lab(v[:-1].reshape(n,3))-target)**2))
                second = minimize(preserve,result.x,method="SLSQP",bounds=[(.002,.998)]*(3*n)+[(max(.041,lower),.4)],
                                  constraints={"type":"ineq","fun":constraints},options={"maxiter":60,"ftol":1e-8})
                runs.append({"start":start,"phase":"preferences","success":bool(second.success),"iterations":int(second.nit)})
                consider(second.x)
    except _Deadline:
        expired = True
    search = _search_report(seed,starts,runs,started,expired)
    search.update(objective="maximize auxiliary z with every normal/2 and simulated Oklab pair distance >= z",
                  hard_constraints="sRGB bounds, all-pair CAM02-UCS minima with quantization margin, 3:1 contrast, L=[.22,.95], C=[.02,.26]",
                  priorities=["hard constraints","weakest pair","supplied preferences within 1e-6 of z"])
    if not candidates:
        _exhausted("categorical",search,failures)
    # Treat the explicit 1e-6 maximin tolerance as a tie for preference selection.
    best_z = min(c[0] for c in candidates)
    _,_,recipe,report = min((c for c in candidates if c[0]<=best_z+1e-6),key=lambda c:(c[1],c[0]))
    report["search"] = search
    return CategoricalPalette(tuple(report["hex"]),QualityReport(report))


def make_ordered_recipe(family, parameters, preferences, background, context, identifier="custom"):
    """Cubic Hermite approximation of an ordered rotation of an H2 spine.

    The spectral rotation is quadratic in radius; chroma and its derivative
    vanish at the neutral. Its two arms share Cartesian center derivatives.
    """
    base_family = "sequential" if family == "multihue" else "diverging"
    base = make_base(base_family,parameters[:6],preferences[:1 if base_family=="sequential" else 2],background,context)
    old = base["knots"]
    knots = sorted(set(old+[(a+b)/2 for a,b in zip(old,old[1:])]))
    values, slopes = [], []
    for t in knots:
        i = min(np.searchsorted(old,t,side="right")-1,len(old)-2)
        u = (t-old[i])/(old[i+1]-old[i]);c=np.array(base["segments"][i])
        v = c@np.array([1,u,u*u,u*u*u]);d=c@np.array([0,1,2*u,3*u*u])/(old[i+1]-old[i])
        r = t if base_family=="sequential" else abs(2*t-1)
        dr = 1 if base_family=="sequential" else (-2 if t<.5 else 2)
        phase = r-.5 if base_family=="sequential" else r*r
        dp = dr if base_family=="sequential" else 2*r*dr
        angle = np.radians(parameters[6]*phase); da=np.radians(parameters[6]*dp)
        R = np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
        z = R@v[1:];dz=R@d[1:]+da*np.array([-z[1],z[0]])
        values.append([v[0],*z]);slopes.append([d[0],*dz])
    spline = CubicHermiteSpline(knots,values,slopes,axis=0)
    base.update(algorithm_version=VERSION,family=family,preferences=list(preferences),identifier=identifier,knots=knots,
                segments=[[_local_coefficients(lambda x,nu=0:spline(x,nu=nu)[j],a,b).tolist() for j in range(3)] for a,b in zip(knots,knots[1:])])
    return base


def validate_ordered(gradient):
    check_recipe(_thaw(gradient._recipe))
    proxy = Gradient(proxy_recipe(gradient._recipe),QualityReport({}),{})
    report = validate_gradient(proxy)
    source = HueGradient(gradient._recipe,QualityReport({}),{})
    rgb = np.array([source.at(i/256) for i in range(257)])
    lab = _lab(rgb)
    # Hue is only defined away from the neutral. Record route order separately
    # from the frozen H1 lightness and feature-preservation requirements.
    arms = [lab] if gradient.family=="multihue" else [lab[:129][::-1],lab[128:]]
    routes = []
    for arm in arms:
        chromatic = arm[np.linalg.norm(arm[:,1:],axis=1) >= .015]
        if len(chromatic) < 2:
            raise ValueError("Multi-hue arms need chromatic samples away from the neutral")
        hue = np.unwrap(np.arctan2(chromatic[:,2],chromatic[:,1]))*180/np.pi
        directed = hue if hue[-1]>=hue[0] else -hue
        routes.append({"hue_span_degrees":float(abs(hue[-1]-hue[0])),
                       "backward_degrees":float(np.max(np.maximum.accumulate(directed)-directed))})
    for i,route in enumerate(routes):
        for name,relation,threshold in (("hue_span_degrees",">=",20.),("backward_degrees","<=",.1)):
            measured = route[name]
            report["checks"].append({"name":f"route_{i}/{name}","condition":"normal","level":"construction",
                                     "measured":measured,"relation":relation,"threshold":threshold,
                                     "passed":measured>=threshold if relation==">=" else measured<=threshold})
    changes = []
    preferences = gradient._recipe["preferences"]
    half = len(preferences)//2
    for i,color in enumerate(preferences):
        target = srgb_to_oklab(from_hex(color))
        indices = range(257) if gradient.family=="multihue" else range(129) if i<half else range(128,257)
        k = min(indices,key=lambda k:distance(lab[k],target))
        changes.append({"supplied":color,"produced":to_hex(rgb[k]),"parameter":k/256,
                        "oklab_distance":distance(lab[k],target)})
    report.update(algorithm_version=VERSION,family=gradient.family,hue_routes=routes,preferred_changes=changes,
                  recipe_sha256=fingerprint(_thaw(gradient._recipe)))
    report["screen_pass"] = bool(report["screen_pass"] and all(c["passed"] for c in report["checks"]))
    return report


def generate_ordered(family, colors, *, background="light", context="filled-fields", seed=4403, max_seconds=30., starts=4):
    if family not in ("multihue","spectral"):
        raise ValueError("Choose multihue or spectral")
    colors = _colors(colors)
    if family=="spectral" and len(colors)%2:
        raise ValueError("Spectral preferences need equally sized arms")
    _request_options(context,seed,max_seconds,starts);bg=background_rgb(background)
    started=time.perf_counter();deadline=started+max_seconds
    rng=np.random.default_rng(seed);runs=[];candidates=[];failures=[];expired=False
    light = bool(_linear(np.array([bg]))[0]@np.array([.2126,.7152,.0722])>.2)
    initial=np.array(ORDERED_SEEDS['multihue' if family=='multihue' else 'spectral-light' if light else 'spectral-dark'])
    bounds=[(.17,.34),(.88,.985),(.015,.085),(.05,.16),(.005,.04),(230.,305.),(-75.,-25.)] if family=='multihue' else [
        ((.30,.53) if light else (.73,.89)),((.90,.985) if light else (.17,.28)),(.025,.065),(.045,.12),(.035,.10),(65.,100.),(25.,55.)]
    if context=='data-marks':
        bounds[:2]=([(.17,.24),(.58,.67)] if light else [(.50,.56),(.94,.985)]) if family=='multihue' else ([ (.17,.27),(.58,.67)] if light else [(.92,.985),(.50,.58)])

    def check_time():
        if time.perf_counter()>=deadline: raise _Deadline

    def raw(x,n=65):
        recipe=make_ordered_recipe(family,x,colors,bg,context)
        # Unconstrained RGB is used only by the optimizer, never returned.
        from .gradients import _polynomial
        result=[]
        for t in np.linspace(0,1,n):
            knots=recipe['knots'];i=min(np.searchsorted(knots,t,side='right')-1,len(knots)-2)
            u=(t-knots[i])/(knots[i+1]-knots[i])
            result.append(oklab_to_srgb(tuple(_polynomial(c,u) for c in recipe['segments'][i])))
        return np.array(result)

    def constraints(x):
        check_time();rgb=raw(x)
        values=[rgb.ravel()-1e-5,1-1e-5-rgb.ravel(),np.array([abs(x[1]-x[0])-(.401 if family=='multihue' else .301)])]
        # CVD display clipping is part of the fixed simulation convention.
        displayed=np.clip(rgb,0,1)
        for condition in CONDITIONS:
            labs=_lab(condition_colors(displayed,condition)[0])
            arms=[labs] if family=='multihue' else [labs[:33],labs[32:][::-1]]
            for arm in arms:
                sign=1 if arm[-1,0]>=arm[0,0] else -1
                values.append(np.diff(arm[:,0])*sign)
            if family=='spectral':
                a,b=arms
                values.extend([.039-abs(a[:,0]-b[:,0]),np.linalg.norm(a[[0,8,16,24]]-b[[0,8,16,24]],axis=1)-.041])
        if context=='data-marks':
            Y=_linear(displayed)@np.array([.2126,.7152,.0722]);Ybg=_linear(np.array([bg]))[0]@np.array([.2126,.7152,.0722])
            values.append((Ybg+.05)/3-.05-Y if light else Y-(3*(Ybg+.05)-.05))
        return np.concatenate(values)

    def relationship(x):
        check_time();rgb=np.clip(raw(x,17),0,1);distances=[]
        for condition in CONDITIONS:
            lab=_lab(condition_colors(rgb,condition)[0])
            d=np.linalg.norm(np.diff(lab,axis=0),axis=1) if family=='multihue' else np.linalg.norm(lab[[0,2,4,6]]-lab[[16,14,12,10]],axis=1)
            distances.extend(d/(2 if condition=='normal' else 1))
        return float(min(distances))

    target=np.array([srgb_to_oklab(from_hex(c)) for c in colors])
    def preference(x):
        check_time();lab=_lab(np.clip(raw(x,33),0,1))
        if family=='multihue':
            return float(sum(np.min(np.sum((lab-v)**2,axis=1)) for v in target))
        half=len(colors)//2
        return float(sum(np.min(np.sum(((lab[:17] if i<half else lab[16:])-v)**2,axis=1)) for i,v in enumerate(target)))

    def consider(x):
        check_time()
        recipe=make_ordered_recipe(family,x,colors,bg,context)
        gradient=HueGradient(recipe,QualityReport({}),{})
        try:
            report=validate_ordered(gradient)
        except (ValueError,OverflowError):
            return
        if report['screen_pass']:
            preference=sum(c['oklab_distance']**2 for c in report['preferred_changes'])
            curvature=sum(sum(float(v)**2 for v in c[2:]) for seg in recipe['segments'] for c in seg[1:])
            candidates.append((-relationship(x),preference,curvature,x.copy(),recipe,report))
        else:
            failed=[c for c in report['checks'] if not c['passed']]
            if not failures or len(failed)<len(failures):failures[:]=failed

    try:
        for start in range(starts):
            check_time()
            x=initial.copy() if start==0 else np.array([rng.uniform(a,b) for a,b in bounds])
            x=np.array([min(b,max(a,v)) for v,(a,b) in zip(x,bounds)])
            # Screen the feasible seed as well as the constrained optimum;
            # quantization can reject an otherwise improved floating optimum.
            consider(x)
            result=minimize(lambda v:-relationship(v),x,method='SLSQP',bounds=bounds,
                            constraints={'type':'ineq','fun':constraints},options={'maxiter':35,'ftol':1e-7})
            runs.append({'start':start,'phase':'weakest-relationship','success':bool(result.success),'iterations':int(result.nit),'message':str(result.message)})
            consider(result.x)
            if np.min(constraints(result.x))>=-1e-7:
                lower=relationship(result.x)-1e-6
                second=minimize(preference,result.x,method='SLSQP',bounds=bounds,
                                constraints=[{'type':'ineq','fun':constraints},
                                             {'type':'ineq','fun':lambda v:relationship(v)-lower}],
                                options={'maxiter':15,'ftol':1e-7})
                runs.append({'start':start,'phase':'preferences','success':bool(second.success),'iterations':int(second.nit)})
                consider(second.x)
            # A uniform chroma reduction preserves L and the ordered hue route.
            # Every reduced path receives the same complete export audit.
            for scale in (.95,.85,.7):
                reduced=result.x.copy();reduced[2:5]*=scale
                consider(reduced)
    except _Deadline:
        expired=True
    search=_search_report(seed,starts,runs,started,expired)
    search.update(priorities=['hard gamut/order/context constraints','weakest simulated relationship','supplied preferences','curvature'],
                  model='seven-parameter rotating cubic Hermite spine; no claim of global optimality')
    if not candidates:_exhausted(family,search,failures[:12])
    best=min(c[0] for c in candidates)
    _,_,_,parameters,recipe,report=min((c for c in candidates if c[0]<=best+1e-6),key=lambda c:c[1:3])
    report.update(search=search,construction_parameters=parameters.tolist())
    return HueGradient(recipe,QualityReport(report),{},family=='multihue' and light)
