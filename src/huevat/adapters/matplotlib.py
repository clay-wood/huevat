"""Matplotlib-native colormaps, cycles and explicit data normalization."""
from ._common import checked,labels,bounds,edges,approximate,source_name,palette_evidence,settings
from ..gradients import Gradient,Palette,QualityReport


def _colors():
    try:from matplotlib import colors
    except ImportError:raise ImportError('Install huevat[matplotlib] for this adapter') from None
    return colors


def colormap(source,*,name=None,tolerance=.002,samples=1025,max_samples=16385,bad='#808080',under=None,over=None):
    checked(source,Palette if isinstance(source,Palette) else Gradient)
    if not isinstance(source,Palette):settings(source,tolerance,samples,max_samples)
    if name is not None and (not isinstance(name,str) or not name):raise ValueError('name must be a nonempty string')
    colors=_colors()
    if isinstance(source,Palette):
        checked(source,Palette)
        cmap=colors.ListedColormap(source.colors,name=name or 'huevat-discrete')
        cmap.huevat_report=QualityReport(palette_evidence(source,'matplotlib'))
    else:
        checked(source,Gradient)
        cmap=approximate(source,lambda p,c,n:colors.ListedColormap(c,name=source_name(source,name)),
                         lambda c,t:c(float(t))[:3],'matplotlib',tolerance=tolerance,samples=samples,max_samples=max_samples)
    report=cmap.huevat_report.to_dict()
    cmap=cmap.with_extremes(bad=bad,under=under,over=over)
    report.update(missing_rgba=list(cmap.get_bad()),under_rgba=list(cmap.get_under()),over_rgba=list(cmap.get_over()))
    cmap.huevat_report=QualityReport(report)
    return cmap


def cycle(palette,*,markers=None,linestyles=None):
    checked(palette,Palette)
    try:from cycler import cycler
    except ImportError:raise ImportError('Install huevat[matplotlib] for property cycles') from None
    result=cycler(color=list(palette.colors))
    for values,key in ((markers,'marker'),(linestyles,'linestyle')):
        if values is not None:
            if not isinstance(values,(list,tuple)) or len(values)!=len(palette):raise ValueError(f'Supply one {key} per color')
            result+=cycler(**{key:list(values)})
    return result


def color_map(palette,names):return labels(palette,names)


def normalizer(vmin,vmax,*,center=None,clip=False):
    bounds(vmin,vmax,center)
    if not isinstance(clip,bool):raise ValueError('clip must be boolean')
    colors=_colors()
    if center is not None:
        if clip:raise ValueError('Centered normalization uses explicit under/over colors; clip=True is not supported')
        return colors.TwoSlopeNorm(center,vmin=vmin,vmax=vmax)
    return colors.Normalize(vmin=vmin,vmax=vmax,clip=clip)


def boundary_normalizer(palette,boundaries):
    boundaries=edges(palette,boundaries)
    return _colors().BoundaryNorm(boundaries,len(palette),clip=False)


def register(cmap,*,name=None):
    import matplotlib as mpl
    # Never replace somebody else's registration implicitly.
    key=cmap.name if name is None else name
    if key in mpl.colormaps:raise ValueError(f'A colormap named {key!r} is already registered')
    mpl.colormaps.register(cmap,name=name,force=False)
