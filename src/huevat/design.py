"""Optional deterministic constrained construction for ordered H2 paths."""
import math
import time
import importlib.metadata as md

try:
    import numpy as np
    from scipy.interpolate import PchipInterpolator, CubicHermiteSpline
    from scipy.optimize import minimize
except ImportError:
    raise ImportError("Custom gradient construction requires huevat[design]") from None

from ._certify import certify
from .evaluation import evaluate, condition_colors, _lab
from .gradients import (Gradient, QualityReport, SearchExhaustedError, background_rgb,
                        fingerprint, _request_options)
from .space import from_hex, srgb_to_oklab, oklab_to_oklch, distance, contrast, linearize

ALGORITHM_VERSION = "h2-ordered-v1"
SEEDS = {
    "sequential": (.18086006396175972, .9331138986771751, .051227349123792294, .130302760527744, .01437878479680791, 277.28839923306685),
    "diverging-light": (.4028821244051755, .9701417820496183, .03401269719017903, .06104075033313252, .07334973201391229, 78.94478174104086),
    "diverging-dark": (.7794034181258568, .18723827452445815, .05881288523164351, .07131459164181025, .08738727464098396, 90.33541352362626),
}


def _local_coefficients(spline, left, right):
    return np.array([float(spline(left, nu=k))*(right-left)**k/math.factorial(k) for k in range(4)])


def make_recipe(family, parameters, preferences, background, context, identifier="custom"):
    endpoint, center, c0, c1, c2, hue = parameters
    vector = np.array([np.cos(np.radians(hue)), np.sin(np.radians(hue))])
    if family == "sequential":
        knots = [0., .5, 1.]
        L = PchipInterpolator(knots, [endpoint, (endpoint+center)/2, center])
        C = PchipInterpolator(knots, [c0, c1, c2])
        segments = [[_local_coefficients(L,a,b).tolist(),
                     (_local_coefficients(C,a,b)*vector[0]).tolist(),
                     (_local_coefficients(C,a,b)*vector[1]).tolist()] for a,b in zip(knots,knots[1:])]
    else:
        radius = [0., .02, .25, .6, 1.]
        span = center-endpoint
        L = CubicHermiteSpline([0,.02,1], [center,center-.02*span,endpoint], [0,-span,-span])
        raw_C = PchipInterpolator([0,.25,.6,1], [0,c0,c1,c2])
        chroma_slopes = raw_C(radius, nu=1)
        chroma_slopes[0] = 0.
        C = CubicHermiteSpline(radius, raw_C(radius), chroma_slopes)
        arms = [[_local_coefficients(L,a,b), _local_coefficients(C,a,b)*vector[0],
                 _local_coefficients(C,a,b)*vector[1]] for a,b in zip(radius,radius[1:])]
        # Left arm is traversed from radius 1 to 0, with opposite Cartesian
        # chromatic coordinates. Both first derivatives match at the neutral.
        reverse_u = np.polynomial.Polynomial([1.,-1.])
        left = []
        for segment in arms[::-1]:
            channels = []
            for i,c in enumerate(segment):
                coefficients = np.polynomial.Polynomial(c)(reverse_u).coef
                coefficients = np.pad(coefficients,(0,4-len(coefficients)))
                channels.append((coefficients*(1 if i == 0 else -1)).tolist())
            left.append(channels)
        segments = left + [[c.tolist() for c in segment] for segment in arms]
        knots = [(1-r)/2 for r in radius[::-1]] + [(1+r)/2 for r in radius[1:]]
    return {"schema_version": 1, "algorithm_version": ALGORITHM_VERSION, "family": family,
            "background": list(background), "context": context, "knots": knots, "segments": segments,
            "preferences": list(preferences), "identifier": identifier}


def _raw_rgb(recipe, n=257):
    # Sampling through the shipped, dependency-free implementation is deliberate:
    # export validation must test exactly the representation users receive.
    gradient = Gradient(recipe, QualityReport({}), {})
    try:
        return np.array([gradient.at(i/(n-1)) for i in range(n)])
    except (ValueError, OverflowError):
        return None


def validate_gradient(gradient):
    """Apply unchanged H1 profiles to float/u8 paths, plus continuous checks."""
    certificate = certify(dict(gradient._recipe))
    rgb = np.array([gradient.at(i/256) for i in range(257)])
    # H1 thresholds are background-independent except mark contrast. Preserve
    # the original evaluator and explicitly replace only that measured gate
    # when an arbitrary background is supplied.
    is_light = gradient.background == from_hex("#ffffff")
    is_dark = gradient.background == from_hex("#121212")
    profile_bg = "light" if is_light else "dark" if is_dark else "light"
    checks = []
    summaries = {}
    for encoding in ("float", "u8"):
        result = evaluate(rgb, gradient.family, context=gradient._recipe["context"], background=profile_bg, encoding=encoding)
        values = rgb if encoding == "float" else np.rint(rgb*255)/255
        for criterion in result["criteria"]:
            item = dict(criterion)
            item["name"] = encoding + "/" + item["name"]
            if criterion["name"] == "background_contrast":
                item["measured"] = min(contrast(row, gradient.background) for row in values)
                item["passed"] = item["measured"] >= item["threshold"]
            checks.append(item)
        summaries[encoding] = {condition: {
            "clipping": data["clipping"],
            "oklab_arms": [{key:value for key,value in arm.items() if key not in ("lightness","steps")} for arm in data["oklab_path"]["arms"]],
            "cam02_arms": [{key:value for key,value in arm.items() if key not in ("lightness","steps")} for arm in data["cam02_path"]["arms"]],
            "oklab_center": data["oklab_path"]["center"], "cam02_center": data["cam02_path"]["center"],
        } for condition,data in result["conditions"].items()}
    # Denser unquantized audit catches between-grid gamut/order anomalies. The
    # H1 local-step thresholds remain attached to their fixed 257-sample grid.
    dense = np.array([gradient.at(i/4096) for i in range(4097)])
    dense_order = True
    for condition in ("normal", "protan-50", "protan-80", "protan-100", "deutan-50", "deutan-80", "deutan-100", "tritan-100"):
        lab = _lab(condition_colors(dense, condition)[0])
        arms = (lab,) if gradient.family == "sequential" else (lab[:2049],lab[2048:][::-1])
        for arm in arms:
            L = arm[:,0]
            direction = 1 if L[-1] >= L[0] else -1
            values = direction*L
            dense_order &= float(np.max(np.maximum.accumulate(values)-values)) <= 1e-7
    changes = []
    for index, preferred in enumerate(gradient._recipe["preferences"]):
        target = srgb_to_oklab(from_hex(preferred))
        indices = range(len(rgb)) if gradient.family == "sequential" else range(0,129) if index == 0 else range(128,257)
        closest = min(indices, key=lambda i:distance(srgb_to_oklab(rgb[i]),target))
        from .space import to_hex
        changes.append({"supplied": preferred, "produced": to_hex(rgb[closest]), "parameter": closest/256,
                        "oklab_distance": distance(srgb_to_oklab(rgb[closest]),target)})
    return {"algorithm_version": ALGORITHM_VERSION, "profile_version": "h1-screening-v1",
            "profile_context": gradient._recipe["context"], "background": gradient.background,
            "background_status": "standard numerical context" if is_light or is_dark else "custom separately evaluated; no visual review",
            "recipe_sha256": fingerprint({key:value for key,value in gradient.to_recipe()["recipe"].items() if key != "reversed"}),
            "checks": checks, "measurements": summaries, "certificate": certificate,
            "dense_audit": {"samples": 4097, "cvd_order_pass": bool(dense_order)},
            "screen_pass": bool(certificate["passed"] and dense_order and all(c["passed"] for c in checks)),
            "preferred_changes": changes, "visual_review": "pending", "approved_default": False,
            "validation_scope": "continuous numerical certificate; finite-grid float/u8 perceptual screens, not a proof of human distinguishability"}


class _Deadline(Exception):
    pass


def generate(family, preferences, *, background="light", context="filled-fields", seed=4402, max_seconds=20., starts=8):
    """Deterministic multi-start SLSQP with fully screened candidate selection."""
    _request_options(context, seed, max_seconds, starts)
    if family not in ("sequential", "diverging") or not isinstance(preferences,(tuple,list)) or len(preferences)!=(1 if family=="sequential" else 2):
        raise ValueError("Choose an ordered family and the corresponding preferred #rrggbb colors")
    for color in preferences:
        from_hex(color)
    bg = background_rgb(background)
    started = time.perf_counter()
    deadline = started+max_seconds
    light = sum(w*linearize(c) for w,c in zip((.2126,.7152,.0722),bg)) > .2
    key = "sequential" if family == "sequential" else "diverging-light" if light else "diverging-dark"
    initial = np.array(SEEDS[key])
    preferred = [oklab_to_oklch(srgb_to_oklab(from_hex(c))) for c in preferences]
    if family == "sequential":
        target_hue = preferred[0][2] if preferred[0][1] > .01 else initial[5]
        initial[5] = target_hue
    else:
        # Opposed Cartesian axes avoid an undefined hue at the shared neutral.
        first = np.exp(1j*np.radians(preferred[0][2]+180))
        second = np.exp(1j*np.radians(preferred[1][2]))
        target_hue = np.degrees(np.angle(first+second)) % 360 if abs(first+second) > 1e-8 else initial[5]
        initial[5] = target_hue
    bounds = [(.16,.34),(.90,.985),(.005,.08),(.025,.17),(.002,.04),(target_hue-80,target_hue+80)] if family == "sequential" else ([
        (.30,.54),(.90,.985),(.015,.11),(.04,.16),(.05,.17),(target_hue-80,target_hue+80)] if light else [
        (.70,.90),(.17,.34),(.02,.11),(.04,.16),(.05,.17),(target_hue-80,target_hue+80)])
    if context == "data-marks":
        if family == "sequential":
            bounds[:2] = [(.16,.24),(.57,.67)] if light else [(.49,.56),(.95,.985)]
        else:
            bounds[:2] = [(.16,.27),(.58,.67)] if light else [(.90,.985),(.49,.58)]
    rng = np.random.default_rng(seed)
    initial = np.array([min(hi,max(lo,x)) for x,(lo,hi) in zip(initial,bounds)])
    candidates, optimizer_runs = [], []
    best_failure = None
    statistics={"candidates_tested":0,"gamut_rejected":0,"grid_screen_rejected":0,"dense_or_context_rejected":0}

    def check_time():
        if time.perf_counter() >= deadline:
            raise _Deadline

    def raw(x):
        return _raw_rgb(make_recipe(family,x,preferences,bg,context),65)

    def constraints(x):
        check_time()
        # Strict interior gamut at collocation nodes; the final Bernstein
        # certificate checks the complete returned cubic path.
        recipe = make_recipe(family,x,preferences,bg,context)
        rgb = raw(x)
        if rgb is None:
            # Use unconstrained conversion so SLSQP receives signed distances.
            from .space import oklab_to_srgb
            from .gradients import _polynomial
            rgb = []
            for t in np.linspace(0,1,65):
                knots = recipe["knots"]
                i = min(np.searchsorted(knots,t,side="right")-1,len(knots)-2)
                u=(t-knots[i])/(knots[i+1]-knots[i])
                rgb.append(oklab_to_srgb(tuple(_polynomial(c,u) for c in recipe["segments"][i])))
            rgb=np.array(rgb)
        values=[rgb.ravel()-1e-6,1-1e-6-rgb.ravel(),np.array([abs(x[1]-x[0])-(.401 if family=="sequential" else .301)])]
        if context == "data-marks":
            Y_bg=sum(w*linearize(c) for w,c in zip((.2126,.7152,.0722),bg))
            Y=np.array([sum(w*linearize(c) for w,c in zip((.2126,.7152,.0722),row)) for row in rgb])
            values.append((Y_bg+.05)/3-.05-Y if light else Y-(3*(Y_bg+.05)-.05))
        return np.concatenate(values)

    def relationship(x):
        check_time()
        rgb = raw(x)
        if rgb is None:
            return -1.
        minimum = float("inf")
        for condition in ("normal","protan-100","deutan-100","tritan-100"):
            lab = _lab(condition_colors(rgb,condition)[0])
            if family == "sequential":
                L=lab[:,0]
                value=float(np.min(abs(np.diff(L))))
            else:
                value=float(np.min(np.linalg.norm(lab[[0,8,16,24]]-lab[[64,56,48,40]],axis=1)))
            minimum=min(minimum,value)
        return minimum

    def preference_cost(x):
        rgb=raw(x)
        if rgb is None:
            return 10.
        labs=_lab(rgb)
        total=0.
        for index, color in enumerate(preferences):
            target=np.array(srgb_to_oklab(from_hex(color)))
            values=labs if family=="sequential" else labs[:33] if index==0 else labs[32:]
            total+=float(np.min(np.linalg.norm(values-target,axis=1)))
        return total

    def consider(x):
        nonlocal best_failure
        check_time()
        statistics["candidates_tested"]+=1
        x=np.array(x,copy=True)
        recipe=make_recipe(family,x,preferences,bg,context)
        rgb=_raw_rgb(recipe)
        chroma_scale=1.
        if rgb is None:
            # Global constant-L/h reduction preserves the cubic shape and C1
            # join. Pointwise channel clipping is never a candidate repair.
            for _ in range(8):
                check_time()
                x[2:5]*=.85
                chroma_scale*=.85
                recipe=make_recipe(family,x,preferences,bg,context)
                rgb=_raw_rgb(recipe)
                if rgb is not None:
                    break
            if rgb is None:
                statistics["gamut_rejected"]+=1
                return
        # Cheap final export screen before expensive continuous/dense audits.
        for encoding in ("u8","float"):
            result=evaluate(rgb,family,context=context,background="light" if light else "dark",encoding=encoding)
            failures=[c for c in result["criteria"] if not c["passed"] and c["name"]!="background_contrast"]
            if failures:
                statistics["grid_screen_rejected"]+=1
                if best_failure is None or len(failures)<len(best_failure):
                    best_failure=failures
                return
        gradient=Gradient(recipe,QualityReport({}),{})
        report=validate_gradient(gradient)
        report["gamut_fallback"]={"global_chroma_scale":chroma_scale,"lightness_and_hue_preserved":True}
        report["construction_parameters"]=x.tolist()
        if report["screen_pass"]:
            # Lexicographic: feasibility first; weakest relationship, then
            # preference displacement, then unnecessary chromatic curvature.
            score=(-relationship(x),preference_cost(x),abs(x[2]-2*x[3]+x[4]))
            candidates.append((score,recipe,report))
        else:
            statistics["dense_or_context_rejected"]+=1
            failures=[c for c in report["checks"] if not c["passed"]]
            if not report["certificate"]["passed"]:
                failures.append({"name":"continuous_numerical_certificate","passed":False})
            if not report["dense_audit"]["cvd_order_pass"]:
                failures.append({"name":"dense_cvd_lightness_order","passed":False})
            if best_failure is None or len(failures)<len(best_failure):
                best_failure=failures

    exhausted = False
    try:
        for index in range(starts):
            check_time()
            if index == 0:
                x0=initial.copy()
            elif index == 1:
                x0=np.array(SEEDS[key])
                x0[5]=target_hue+((x0[5]-target_hue+180)%360-180)
                x0=np.array([min(hi,max(lo,x)) for x,(lo,hi) in zip(x0,bounds)])
            else:
                x0=np.array([rng.uniform(lo,hi) for lo,hi in bounds])
            consider(x0)
            optimized=minimize(lambda x:-relationship(x),x0,method="SLSQP",bounds=bounds,
                               constraints=[{"type":"ineq","fun":constraints}],
                               options={"maxiter":18,"ftol":1e-8})
            optimizer_runs.append({"start":index,"success":bool(optimized.success),"message":str(optimized.message),"iterations":int(optimized.nit)})
            consider(optimized.x)
            if optimized.success:
                floor=relationship(optimized.x)-1e-6
                preferred_fit=minimize(preference_cost,optimized.x,method="SLSQP",bounds=bounds,
                                      constraints=[{"type":"ineq","fun":constraints},
                                                   {"type":"ineq","fun":lambda x:relationship(x)-floor}],
                                      options={"maxiter":12,"ftol":1e-8})
                consider(preferred_fit.x)
    except _Deadline:
        exhausted=True
    elapsed=time.perf_counter()-started
    if not candidates:
        report={"outcome":"search-exhausted", "screen_pass":False,"algorithm_version":ALGORITHM_VERSION,
                "seed":seed,"starts_requested":starts,"optimizer_runs":optimizer_runs,
                "deadline_reached":exhausted,"max_seconds":max_seconds,"elapsed_seconds":elapsed,
                "closest_failures":best_failure or [],"infeasibility_proven":False}
        report["candidate_statistics"]=statistics
        report["profile_version"]="h1-screening-v1"
        raise SearchExhaustedError("Search exhausted without a passing result. Increase the budget, change the preferred colors/context, or use a prepared path. This is not proof of infeasibility.",report)
    _,recipe,report=min(candidates,key=lambda item:item[0])
    if family=="sequential" and light:
        # Use a view reversal; no resampling or new interpolation is introduced.
        reverse=True
    else:
        reverse=False
    report["search"]={"seed":seed,"starts_requested":starts,"optimizer_runs":optimizer_runs,
                      "deadline_reached":exhausted,"max_seconds":max_seconds,"elapsed_seconds":elapsed,
                      "passing_candidates":len(candidates),"determinism":"fixed seed and completed starts; a wall-time cutoff may stop earlier on slower hosts",
                      "candidate_statistics":statistics,
                      "versions":{name:md.version(name) for name in ("numpy","scipy","colorspacious")}}
    return Gradient(recipe,QualityReport(report),{},reverse)
