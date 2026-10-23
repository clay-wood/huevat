"""Shared, dependency-free adapter validation and approximation evidence."""
from bisect import bisect_right

from ..gradients import Gradient, Palette, QualityError, QualityReport, _finite, fingerprint
from ..space import distance, from_hex, srgb_to_oklab, to_hex
from ..references import load_profile
from ..vision import simulate


def checked(source, kind):
    if not isinstance(source,kind):
        raise ValueError(f'Expected a Huevat {kind.__name__}')
    if not source.report.screen_pass:
        raise QualityError('Adapters require a screened Huevat source',source.report.to_dict())
    return source


def labels(palette, names):
    checked(palette,Palette)
    if not isinstance(names,(list,tuple)) or len(names)!=len(palette) or any(not isinstance(n,str) for n in names) or len(set(names))!=len(names):
        raise ValueError('Supply one unique string label per palette color')
    return dict(zip(names,palette.colors))


def palette_evidence(palette, backend):
    """Identify the exact exported colors without inventing a new approval."""
    data = palette.report.to_dict()
    source_hash=data.get('source_sha256') or data.get('recipe_sha256') or fingerprint(data.get('recipe',data))
    return {
        'algorithm_version': 'h4-adapter-v1', 'backend': backend,
        'source_sha256': source_hash,
        'exported_colors_sha256': fingerprint(list(palette.colors)),
        'source_screen_pass': True, 'approximation_pass': True,
        'background': data.get('background'), 'context': data.get('context',data.get('profile_context')),
        'adapter_profile_revalidated': False,
        'scope': 'exact exported colors; explicit data boundaries required; mutations invalidate this evidence',
    }


def bounds(vmin,vmax,center=None):
    _finite(vmin,'vmin');_finite(vmax,'vmax')
    if not vmin<vmax:raise ValueError('vmin must be smaller than vmax')
    if center is not None:
        _finite(center,'center')
        if not vmin<center<vmax:raise ValueError('center must be strictly between vmin and vmax')
    return vmin,vmax,center


def edges(palette,boundaries):
    checked(palette,Palette)
    if not isinstance(boundaries,(tuple,list)) or len(boundaries)!=len(palette)+1:
        raise ValueError('Supply n+1 explicit data boundaries for n colors')
    for x in boundaries:_finite(x,'boundary')
    if any(a>=b for a,b in zip(boundaries,boundaries[1:])):raise ValueError('Boundaries must strictly increase')
    return tuple(boundaries)


def settings(gradient,tolerance,samples,max_samples):
    checked(gradient,Gradient)
    if _finite(tolerance,'tolerance')<=0:raise ValueError('tolerance must be positive')
    for value,name in ((samples,'samples'),(max_samples,'max_samples')):
        if isinstance(value,bool) or not isinstance(value,int) or not 3<=value<=65537 or value%2!=1:
            raise ValueError(f'{name} must be an odd integer in [3, 65537] to retain the center')
    if max_samples<samples:raise ValueError('max_samples must be at least samples')


def rgb_string(rgb):
    # Floating RGB channels retain precision; hex stops would impose 8-bit
    # rounding before the backend even interpolates the scale.
    return 'rgb('+','.join(f'{255*x:.10f}' for x in rgb)+')'


def interpolate(positions,colors,t):
    i=max(0,min(bisect_right(positions,t)-1,len(positions)-2))
    u=(t-positions[i])/(positions[i+1]-positions[i])
    return tuple((1-u)*a+u*b for a,b in zip(colors[i],colors[i+1]))


def audit(gradient,sample,backend,count,tolerance):
    # The reported grid is finite evidence, not a continuous error certificate.
    grid=max(8193,2*count+1)
    worst=0.;where=0.
    for i in range(grid):
        t=i/(grid-1)
        error=distance(srgb_to_oklab(gradient.at(t)),srgb_to_oklab(sample(t)))
        if error>worst:worst=error;where=t
    condition_errors={};quantized_errors={}
    # Avoid grids aligned to the lookup knots: e.g. 257 uniformly spaced
    # positions hit exact entries in a 1025-entry map and hide lookup errors.
    condition_grid=1021 if (count-1)%1020 else 1032
    for condition in load_profile()['conditions']:
        maximum=quantized=0.
        for i in range(condition_grid):
            t=i/(condition_grid-1)
            a,b=gradient.at(t),sample(t)
            qa,qb=from_hex(to_hex(a)),from_hex(to_hex(b))
            if condition!='normal':
                name,severity=condition.rsplit('-',1)
                a,b=simulate(a,name,severity=int(severity)),simulate(b,name,severity=int(severity))
                qa,qb=simulate(qa,name,severity=int(severity)),simulate(qb,name,severity=int(severity))
            maximum=max(maximum,distance(srgb_to_oklab(a),srgb_to_oklab(b)))
            quantized=max(quantized,distance(srgb_to_oklab(qa),srgb_to_oklab(qb)))
        condition_errors[condition]=maximum;quantized_errors[condition]=quantized
    measured=max(worst,*condition_errors.values())
    return QualityReport({'algorithm_version':'h4-adapter-v1','backend':backend,
        'source_sha256':fingerprint(gradient.to_recipe()['recipe']),'source_screen_pass':True,
        'background':gradient.background,'context':gradient._recipe['context'],
        'samples':count,'tolerance_oklab':tolerance,'maximum_float_error_oklab':measured,
        'worst_normal_parameter':where,'normal_grid_samples':grid,'condition_grid_samples':condition_grid,
        'float_condition_errors':condition_errors,'u8_condition_errors':quantized_errors,
        'approximation_pass':measured<=tolerance,'adapter_profile_revalidated':False,
        'scope':'finite-grid color approximation; not a new H1 profile approval; mutating the backend object invalidates this evidence'})


def approximate(gradient,build,sample,backend,*,tolerance=.002,samples=1025,max_samples=16385):
    settings(gradient,tolerance,samples,max_samples)
    count=samples
    while True:
        positions=tuple(i/(count-1) for i in range(count))
        colors=tuple(gradient.at(t) for t in positions)
        result=build(positions,colors,count)
        report=audit(gradient,lambda t:sample(result,t),backend,count,tolerance)
        if report['approximation_pass']:
            result.huevat_report=report
            return result
        if count==max_samples:
            raise QualityError('Adapter cannot meet the requested approximation tolerance within max_samples',report.to_dict())
        count=min(max_samples,2*count-1)


def source_name(source,name):
    if name is not None:
        if not isinstance(name,str) or not name:raise ValueError('name must be a nonempty string')
        return name
    return 'huevat-'+fingerprint(source.to_recipe()['recipe'])[:12]
