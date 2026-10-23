"""UltraPlot-native continuous/discrete colormaps and coordinated cycles."""
from ._common import checked,approximate,source_name,palette_evidence,settings
from .matplotlib import normalizer,boundary_normalizer,color_map
from ..gradients import Gradient,Palette,QualityReport


def _backend():
    try:import ultraplot as uplt
    except ImportError:raise ImportError('Install huevat[ultraplot] for this adapter') from None
    return uplt


def colormap(source,*,name=None,tolerance=.002,samples=1025,max_samples=16385,bad='#808080',under=None,over=None):
    checked(source,Palette if isinstance(source,Palette) else Gradient)
    if not isinstance(source,Palette):settings(source,tolerance,samples,max_samples)
    if name is not None and (not isinstance(name,str) or not name):raise ValueError('name must be a nonempty string')
    uplt=_backend()
    if isinstance(source,Palette):
        checked(source,Palette)
        cmap=uplt.DiscreteColormap(list(source.colors),name=name or 'huevat-discrete')
        cmap.huevat_report=QualityReport(palette_evidence(source,'ultraplot'))
    else:
        checked(source,Gradient)
        cmap=approximate(source,lambda p,c,n:uplt.ContinuousColormap.from_list(source_name(source,name),list(c),N=n),
                         lambda c,t:c(float(t))[:3],'ultraplot',tolerance=tolerance,samples=samples,max_samples=max_samples)
    report=cmap.huevat_report.to_dict()
    cmap=cmap.with_extremes(bad=bad,under=under,over=over)
    report.update(missing_rgba=list(cmap.get_bad()),under_rgba=list(cmap.get_under()),over_rgba=list(cmap.get_over()))
    cmap.huevat_report=QualityReport(report)
    return cmap


def cycle(palette,*,markers=None,linestyles=None):
    checked(palette,Palette)
    properties={}
    for values,key in ((markers,'marker'),(linestyles,'linestyle')):
        if values is not None:
            if not isinstance(values,(list,tuple)) or len(values)!=len(palette):raise ValueError(f'Supply one {key} per color')
            properties[key]=list(values)
    # Build all properties together: in-place Cycler addition on UltraPlot's
    # subclass can lose keys in by_key(), which Axes uses when copying it.
    return _backend().Cycle(colormap(palette),**properties)
