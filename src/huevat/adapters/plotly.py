"""Plotly-native scales and label maps with explicit asymmetric centers."""
from ._common import checked,labels,bounds,edges,approximate,interpolate,rgb_string,palette_evidence
from ..gradients import Gradient,Palette,QualityReport


class ColorScale(list):
    """Native list-compatible Plotly stops, with separately attached evidence."""
    pass


class ColorAxis(dict):
    """Native coloraxis dictionary; evidence is an attribute, never a JSON key."""
    pass


def colorscale(gradient,*,tolerance=.002,samples=257,max_samples=4097):
    checked(gradient,Gradient)
    def build(positions,colors,count):
        result=ColorScale([[t,rgb_string(c)] for t,c in zip(positions,colors)])
        result._huevat_positions=positions
        result._huevat_colors=tuple(tuple(float(v)/255 for v in stop[1][4:-1].split(',')) for stop in result)
        return result
    result=approximate(gradient,build,lambda c,t:interpolate(c._huevat_positions,c._huevat_colors,t),'plotly',
                       tolerance=tolerance,samples=samples,max_samples=max_samples)
    return result


def coloraxis(gradient,vmin,vmax,*,center=None,**kwargs):
    bounds(vmin,vmax,center)
    scale=colorscale(gradient,**kwargs)
    q=None if center is None else (center-vmin)/(vmax-vmin)
    # Plotly's explicit limits and cmid do not impose a TwoSlopeNorm. Warp the
    # stops instead, preserving the requested physical center with fixed limits.
    stops=[[t if q is None else 2*q*t if t<=.5 else q+2*(1-q)*(t-.5),c] for t,c in scale]
    result=ColorAxis(colorscale=stops,cmin=vmin,cmax=vmax,cauto=False)
    report=scale.huevat_report.to_dict()
    report.update(vmin=vmin,vmax=vmax,center=center,center_normalized=q,
                  under_over_policy='endpoint clamp; independent under/over colors are unsupported',
                  missing_policy='Plotly null/gap; no custom missing color is implied')
    result.huevat_report=QualityReport(report)
    return result


def sequence(palette):
    checked(palette,Palette)
    return list(palette.colors)


def color_map(palette,names):return labels(palette,names)


def discrete_coloraxis(palette,boundaries):
    boundaries=edges(palette,boundaries)
    lo,hi=boundaries[0],boundaries[-1];stops=[]
    for a,b,color in zip(boundaries,boundaries[1:],palette.colors):
        stops.extend([[(a-lo)/(hi-lo),color],[(b-lo)/(hi-lo),color]])
    result=ColorAxis(colorscale=stops,cmin=lo,cmax=hi,cauto=False)
    report=palette_evidence(palette,'plotly')
    report.update(boundaries=boundaries,under_over_policy='endpoint clamp',
                  missing_policy='Plotly null/gap; no custom missing color is implied')
    result.huevat_report=QualityReport(report)
    return result
