"""Opt-in uniform filled regions; compositing and data remain explicit."""
from copy import deepcopy
from itertools import combinations
from ..gradients import fingerprint


def extract(fig,data):
    from ._backends import backend,_hash_array,_points,_channel,_css
    data['includes_fills']=True
    added=set()
    if backend(fig)=='plotly':
        for i,obj in enumerate(fig.data):
            band=obj.type=='scatter' and obj.fill in ('tonexty','tozeroy','toself')
            if obj.type!='bar' and not band:continue
            if obj.xaxis not in (None,'x') or obj.yaxis not in (None,'y'):continue
            color=obj.fillcolor if band else obj.marker.color
            if not isinstance(color,str) or (not band and obj.orientation not in (None,'v')):continue
            if band:
                import math
                if obj.x is None or obj.y is None or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in [*obj.x,*obj.y]):continue
            try:rgba=_css(color)
            except ValueError:continue
            if obj.opacity is not None:rgba=(*rgba[:3],rgba[3]*obj.opacity)
            panel='xy';axis=data['axes'][0] if data['axes'] else None
            if axis is None:continue
            key=f'trace/{i}';added.add(key)
            data['marks']=[m for m in data['marks'] if m['key']!=key]
            ch=_channel('face',rgba);ch['color_alpha']=_css(color)[3]
            data['marks'].append(dict(key=key,panel=axis['key'],category=obj.name or '@'+key,kind='band' if band else 'bar',
                channels=[ch],marker='none',dash='none',width=0.,line_visible=False,
                marker_visible=False,background=axis['background'],points=[],
                data_sha256=fingerprint([list(obj.x) if obj.x is not None else None,list(obj.y)])))
    else:
        import numpy as np
        from matplotlib.collections import PolyCollection,PatchCollection
        from matplotlib.container import BarContainer
        from matplotlib.colors import to_rgba
        for ai,ax in enumerate(fig.axes):
            if hasattr(ax,'_colorbar') or ax.name!='rectilinear' or ax.get_xscale()!='linear' or ax.get_yscale()!='linear':continue
            axis=data['axes'][ai];panel=axis['key'];bar_labels={}
            for ci,c in enumerate(ax.containers):
                if isinstance(c,BarContainer):
                    for p in c.patches:bar_labels[id(p)]=c.get_label()
                    added.add(f'{panel}/container/{ci}')
            candidates=[(f'{panel}/patch/{i}',p,'bar' if id(p) in bar_labels else 'region') for i,p in enumerate(ax.patches)]
            candidates += [(f'{panel}/collection/{i}',p,'band') for i,p in enumerate(ax.collections)
                           if isinstance(p,(PolyCollection,PatchCollection)) and p.get_array() is None]
            for key,obj,kind in candidates:
                transform=obj.get_data_transform() if hasattr(obj,'get_data_transform') else obj.get_transform()
                if not obj.get_visible() or transform!=ax.transData or obj.get_path_effects():continue
                faces=np.atleast_2d(obj.get_facecolor())
                if len(faces)!=1 or faces[0,3]<=0:continue
                category=bar_labels.get(id(obj),obj.get_label())
                category=category if category and not category.startswith('_') else '@'+key
                paths=[obj.get_path()] if hasattr(obj,'get_path') else obj.get_paths()
                vertices=np.concatenate([p.vertices for p in paths])
                if hasattr(obj,'get_patch_transform'):vertices=obj.get_patch_transform().transform(vertices)
                rgba=tuple(faces[0]);alpha=obj.get_alpha()
                if alpha is not None:rgba=(*rgba[:3],alpha)
                data['marks'].append(dict(key=key,panel=panel,category=category,kind=kind,
                    channels=[_channel('face',rgba)],marker='none',dash='none',width=0.,
                    line_visible=False,marker_visible=False,background=axis['background'],
                    points=_points(vertices[:,0],vertices[:,1],axis['xscale'],axis['yscale'],[axis['xlim'],axis['ylim']]),
                    data_sha256=_hash_array(vertices),zorder=float(obj.get_zorder())))
                added.add(key)
    for field in ('unsupported','read_only'):data[field]=[r for r in data[field] if r['key'] not in added]
    data['coverage'].update(editable_marks=len(data['marks']),unsupported=len(data['unsupported']),read_only=len(data['read_only']),
                            complete=False)
    data['warnings'].append('Filled regions are composited over axes; overlaps/shading remain outside the color checks')
    return data


def audit(data):
    from ._audit import audit as old
    from ..cyclic import screen
    # Preserve existing data-mark gates; filled regions use the declared
    # filled-field distance floors without a 3:1 pale-fill requirement.
    marks=[m for m in data['marks'] if m['kind'] not in ('region','band','bar')]
    base=deepcopy(data);base['marks']=marks
    result=old(base);checks=[];pairs=[]
    for axis in data['axes']:
        fills=[m for m in data['marks'] if m['panel']==axis['key'] and m['kind'] in ('region','band','bar')]
        for a,b in combinations(fills,2):
            if a['category']==b['category']:continue
            colors=[]
            for m in (a,b):
                c=m['channels'][0]
                colors.append([v*c['alpha']+bg*(1-c['alpha']) for v,bg in zip(c['rgb'],m['background'])])
            report=screen(colors,axis['background'],'filled-fields');checks.extend(report['checks'])
            pairs.append({'categories':[a['category'],b['category']],'color_confusable':not report['screen_pass'],
                          'grayscale_confusable':False,'distinct_secondary_encoding':False,'minimum_ratio':
                          min((c.get('measured',1)/c.get('threshold',1) for c in report['checks']),default=0)})
    result['filled_checks']=checks;result['pairs'].extend(pairs)
    result['color_screen_pass']=(result['color_screen_pass'] if marks else True) and all(c['passed'] for c in checks)
    result['includes_fills']=True
    result['unresolved_pairs'].extend(p['categories'] for p in pairs if p['color_confusable'])
    result['color_scope']='data-mark checks plus filled-region pair checks over solid backgrounds; overlaps excluded'
    return result
