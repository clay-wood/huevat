"""Explicit scalar recoloring, uncertainty styles and actual-size proof sheets."""
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path

from ..gradients import fingerprint,QualityReport


def _targets(fig):
    from ._backends import backend
    if backend(fig)=='plotly':
        return [(f'trace/{i}',o) for i,o in enumerate(fig.data) if o.type in ('heatmap','contour')]
    result=[]
    for i,ax in enumerate(fig.axes):
        if hasattr(ax,'_colorbar'):continue
        result.extend((f'axes/{i}/image/{j}',o) for j,o in enumerate(ax.images) if o.get_array().ndim==2)
        result.extend((f'axes/{i}/collection/{j}',o) for j,o in enumerate(ax.collections)
                      if hasattr(o,'get_array') and o.get_array() is not None and hasattr(o,'get_cmap'))
    return result


def fields(figure):
    """List editable scalar mappings; all centers and data limits remain explicit."""
    from ._backends import backend,_hash_array
    result=[]
    for key,o in _targets(figure):
        if backend(figure)=='plotly':
            axis=getattr(figure.layout,o.coloraxis) if o.coloraxis else o
            lo,hi=(axis.cmin,axis.cmax) if o.coloraxis else (o.zmin,o.zmax)
            result.append({'key':key,'limits':[lo,hi],'coloraxis':o.coloraxis,'data_sha256':_hash_array(o.z)})
        else:
            result.append({'key':key,'limits':list(o.get_clim()),'normalizer':type(o.norm).__name__,
                           'center':getattr(o.norm,'vcenter',None),'data_sha256':_hash_array(o.get_array())})
    return tuple(result)


def _digest(fig):
    from ._backends import backend,_hash_array
    if backend(fig)=='plotly':return fingerprint(json.loads(fig.to_json()))
    result=[]
    for key,o in _targets(fig):
        result.append({'key':key,'data_sha256':_hash_array(o.get_array()),'colors':[list(o.cmap(i/256)) for i in range(257)],
            'norm':{k:repr(getattr(o.norm,k,None)) for k in ('vmin','vmax','vcenter','boundaries','clip','linthresh','linscale')}})
    return fingerprint(result)


@dataclass
class FieldChange:
    report: object
    _figure: object
    _after: str
    _restore: object
    _undone: bool=False
    def undo(self):
        if self._undone:raise ValueError('This change was already undone')
        if _digest(self._figure)!=self._after:raise ValueError('Figure changed after recoloring; undo would overwrite newer changes')
        self._restore();self._undone=True


def recolor(figure,gradient,*,keys=None,center=None,vmin=None,vmax=None):
    """Recolor selected fields, preserving their data, bounds and native normalizers.

    Supplying center explicitly requests a new centered normalizer. Discrete
    boundaries are always preserved. Return a stale-guarded undo handle.
    """
    from ._backends import backend,clone
    from ..adapters._common import checked,bounds
    from ..gradients import Gradient
    checked(gradient,Gradient)
    targets=_targets(figure);all_keys={k for k,o in targets}
    if keys is not None:
        if not isinstance(keys,(tuple,list)) or not keys or len(set(keys))!=len(keys) or set(keys)-all_keys:
            raise ValueError('Choose unique field keys returned by doctor.fields')
        targets=[(k,o) for k,o in targets if k in keys]
    if not targets:raise ValueError('No supported scalar fields in this figure')
    if (vmin is None)!=(vmax is None):raise ValueError('Supply both vmin and vmax')
    kind=backend(figure)
    # Build every mapping first, so an invalid field cannot leave a partial edit.
    operations=[];records=[]
    if kind=='plotly':
        from ..adapters import plotly as adapter
        selected={k for k,o in targets}
        for key,o in targets:
            if o.coloraxis and any(other.coloraxis==o.coloraxis and k not in selected for k,other in _targets(figure)):
                raise ValueError('Select all fields sharing a color axis')
            axis=getattr(figure.layout,o.coloraxis) if o.coloraxis else o
            lo,hi=(axis.cmin,axis.cmax) if o.coloraxis else (o.zmin,o.zmax)
            lo,hi=(vmin,vmax) if vmin is not None else (lo,hi)
            if lo is None or hi is None:raise ValueError('Set explicit field limits or supply vmin and vmax')
            if gradient.family in ('diverging','spectral') and center is None:raise ValueError('Supply the physical center for a signed field')
            scale=adapter.coloraxis(gradient,lo,hi,center=center)
            names=('colorscale','cmin','cmax','cauto','cmid') if o.coloraxis else ('colorscale','zmin','zmax','zauto','zmid')
            old={n:deepcopy(getattr(axis,n)) for n in names}
            new=dict(scale) if o.coloraxis else dict(colorscale=scale['colorscale'],zmin=lo,zmax=hi,zauto=False,zmid=None)
            operations.append((axis,old,new));records.append({'key':key,'limits':[lo,hi],'center':center})
        def apply():
            for axis,old,new in operations:axis.update(new)
        def restore():
            for axis,old,new in operations:axis.update(old)
    else:
        from ..adapters import matplotlib as adapter
        from matplotlib.colors import BoundaryNorm
        for key,o in targets:
            lo,hi=(vmin,vmax) if vmin is not None else o.get_clim()
            if lo is None or hi is None:raise ValueError('Initialize field limits before recoloring')
            bounds(lo,hi,center)
            old_cmap,old_norm=o.cmap,o.norm
            if isinstance(old_norm,BoundaryNorm):
                if center is not None or vmin is not None:raise ValueError('A binned field retains its existing boundaries; do not supply center/limits')
                edges=tuple(map(float,old_norm.boundaries));p=gradient.discrete(len(edges)-1)
                cmap=adapter.colormap(p,bad=old_cmap.get_bad(),under=old_cmap.get_under(),over=old_cmap.get_over())
                norm=BoundaryNorm(edges,len(p),clip=old_norm.clip)
            else:
                cmap=adapter.colormap(gradient,bad=old_cmap.get_bad(),under=old_cmap.get_under(),over=old_cmap.get_over())
                norm=old_norm if center is None and vmin is None else adapter.normalizer(lo,hi,center=center)
            operations.append((o,old_cmap,old_norm,cmap,norm));records.append({'key':key,'limits':[lo,hi],'center':getattr(norm,'vcenter',None)})
        def apply():
            for o,old_cmap,old_norm,cmap,norm in operations:o.set_cmap(cmap);o.set_norm(norm)
        def restore():
            for o,old_cmap,old_norm,cmap,norm in operations:o.set_cmap(old_cmap);o.set_norm(old_norm)
    try:apply();after=_digest(figure)
    except BaseException:restore();raise
    return FieldChange(QualityReport({'fields':records,'scope':'scalar colors only; data and existing boundaries preserved',
                                     'source_screen_pass':gradient.report.screen_pass}),figure,after,restore)


def field_preview(figure,gradient,**options):
    from ._backends import clone
    result=clone(figure);recolor(result,gradient,**options);return result


def band_styles(palette,labels,*,alpha=.2,background='light'):
    """Paired line/fill/boundary colors, with explicit alpha and fill checks."""
    from ..adapters._common import labels as label_map
    from ..gradients import _finite,background_rgb
    from ..space import from_hex
    from ._filled import audit
    if not 0<_finite(alpha,'alpha')<=1:raise ValueError('alpha must be in (0,1]')
    colors=label_map(palette,labels);bg=background_rgb(background)
    marks=[];styles={}
    for label,color in colors.items():
        styles[label]={'color':color,'fill':(*from_hex(color),alpha),'edge':color}
        marks.append(dict(key=label,panel='panel',category=label,kind='band',channels=[{'kind':'face','rgb':from_hex(color),'alpha':alpha}],
                          background=bg,points=[],line_visible=False,marker_visible=False,marker='none',dash='none'))
    scene={'marks':marks,'axes':[{'key':'panel','background':bg}],'coverage':{'complete':False},'includes_fills':True}
    report=audit(scene)
    return {'styles':styles,'report':QualityReport(report)}


def proof_sheet(figure,path,*,width_mm=85.,dpi=200,conditions=('normal','deutan-100','grayscale'),proposal=None):
    """Save actual-size raster proofs and a combined PNG/PDF sheet.

    Simulations transform the entire rendered image, including fills/colorbars.
    Plotly raster export additionally requires Kaleido and a supported browser.
    """
    from ._backends import backend,clone
    from . import preview
    from ..gradients import _finite
    from ..references import load_profile
    if not 20<=_finite(width_mm,'width_mm')<=500:raise ValueError('width_mm must be in [20,500]')
    if isinstance(dpi,bool) or not isinstance(dpi,int) or not 72<=dpi<=1200:raise ValueError('dpi must be in [72,1200]')
    allowed=load_profile()['conditions']+['grayscale']
    if not isinstance(conditions,(tuple,list)) or not 1<=len(conditions)<=9 or len(set(conditions))!=len(conditions) or any(c not in allowed for c in conditions):
        raise ValueError('Choose unique supported proof conditions')
    path=Path(path)
    if path.suffix.lower() not in ('.png','.pdf'):raise ValueError('Save a .png or .pdf proof sheet')
    import io
    import numpy as np
    import matplotlib.image as mpimg
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from ._backends import _hash_array
    from ..evaluation import condition_colors,gray_rgb
    source=preview(figure,proposal) if proposal is not None else clone(figure)
    width=round(width_mm/25.4*dpi)
    if backend(source)=='plotly':
        ratio=(source.layout.height or 450)/(source.layout.width or 700)
        try:raw=source.to_image(format='png',width=width,height=round(width*ratio),scale=1)
        except Exception as e:raise ImportError('Plotly proof sheets need Kaleido and a supported browser; install huevat[proof]') from e
        rgb=mpimg.imread(io.BytesIO(raw))[:,:,:3]
    else:
        w,h=source.get_size_inches();source.set_size_inches(width_mm/25.4,h/w*width_mm/25.4)
        buffer=io.BytesIO();source.savefig(buffer,format='png',dpi=dpi,facecolor=source.get_facecolor())
        buffer.seek(0);rgba=mpimg.imread(buffer);rgb=rgba[:,:,:3]*rgba[:,:,3:4]+(1-rgba[:,:,3:4])
    height=rgb.shape[0];panels=[];files=[];path.parent.mkdir(parents=True,exist_ok=True)
    for condition in conditions:
        pixels=rgb.reshape(-1,3)
        shown=gray_rgb(pixels) if condition=='grayscale' else condition_colors(pixels,condition)[0]
        shown=np.asarray(shown).reshape(rgb.shape);panels.append(shown)
        filename=path.with_name(path.stem+'-'+condition+'.png')
        mpimg.imsave(filename,shown);files.append(str(filename))
    header=round(.27*dpi);fig=Figure(figsize=(rgb.shape[1]*len(panels)/dpi,(height+header)/dpi),dpi=dpi,facecolor='white')
    FigureCanvasAgg(fig)
    for i,(condition,panel) in enumerate(zip(conditions,panels)):
        ax=fig.add_axes((i/len(panels),0,1/len(panels),height/(height+header)))
        ax.imshow(panel,interpolation='nearest');ax.set_axis_off()
        fig.text((i+.5)/len(panels),1-header/(height+header)/2,condition,ha='center',va='center',fontsize=9)
    fig.savefig(path,dpi=dpi)
    report={'width_mm':width_mm,'dpi':dpi,'panel_pixels':[rgb.shape[1],height],'conditions':list(conditions),'files':files,
            'source_raster_sha256':_hash_array(rgb),'simulation':'entire rendered raster; not a human-readability certificate'}
    path.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return QualityReport(report)
