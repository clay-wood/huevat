"""Optional deterministic grid maximin search; never changes the source curve."""
import time

try:
    import numpy as np
    from colorspacious import cspace_convert
except ImportError:
    raise ImportError('Optimized sampling requires huevat[design]') from None

from ._data import load_data
from ._discrete import screen_discrete
from .evaluation import condition_colors,_lab
from .gradients import QualityReport,SearchExhaustedError,fingerprint
from .sampling import SampledPalette
from .space import contrast,to_hex


class _Deadline(Exception):pass


def screen(gradient,positions,context):
    rgb=tuple(gradient.at(t) for t in positions)
    family='diverging' if gradient.family in ('diverging','spectral') else 'sequential'
    report=screen_discrete(rgb,gradient.at(.5),family,gradient.background,context)
    profile=load_data('profiles-v1.json')
    for encoding in ('float','u8'):
        values=np.array(rgb)
        if encoding=='u8':values=np.rint(values*255)/255
        for condition in profile['conditions']:
            L=_lab(condition_colors(values,condition)[0])[:,0]
            arms=[L] if family=='sequential' else [L[:(len(L)+1)//2],L[len(L)//2:][::-1]]
            for i,arm in enumerate(arms):
                direction=1 if arm[-1]>=arm[0] else -1
                directed=direction*arm
                excursion=float(np.max(np.maximum.accumulate(directed)-directed))
                threshold=profile['numerical'][f'lightness_backward_{encoding}_max']
                report['checks'].append({'name':f'{encoding}/lightness_order_arm_{i}','condition':condition,
                    'measured':excursion,'threshold':threshold,'relation':'<=','passed':excursion<=threshold})
    report.update(algorithm_version='h4-sampling-v1',positions=list(positions),family=gradient.family,
                  source_sha256=fingerprint(gradient.to_recipe()['recipe']),
                  sampling='explicit endpoint-inclusive positions; mirrored diverging arms; not data-bin boundaries')
    report['screen_pass']=all(c['passed'] for c in report['checks'])
    report['outcome']='passed' if report['screen_pass'] else 'selection-failed'
    return report


def optimize(gradient,n,context,grid,max_seconds):
    started=time.perf_counter();deadline=started+max_seconds
    profile=load_data('profiles-v1.json');thresholds=profile['contexts'][context]
    diverging=gradient.family in ('diverging','spectral')
    best=None;expired=False;nodes_visited=0
    def check():
        if time.perf_counter()>=deadline:raise _Deadline
    try:
        check()
        positions=np.linspace(0,1,grid)
        rgb=np.array([gradient.at(float(t)) for t in positions]);center=grid//2
        score=np.full((grid,grid),np.inf);allowed=np.ones(grid,dtype=bool)
        for encoding in ('float','u8'):
            actual=rgb if encoding=='float' else np.rint(rgb*255)/255
            if context=='data-marks':allowed &= np.array([contrast(c,gradient.background)>=3 for c in actual])
            for condition in profile['conditions']:
                check()
                shown=condition_colors(actual,condition)[0];lab=_lab(shown)
                cam=cspace_convert(shown,'sRGB1','CAM02-UCS')
                kind='normal' if condition=='normal' else 'cvd'
                for coords,space in ((lab,'oklab'),(cam,'cam02')):
                    key=f'{space}_distance_{kind}_min' if context=='data-marks' else f'discrete_{space}_{kind}_min'
                    d=np.linalg.norm(coords[:,None,:]-coords[None,:,:],axis=2)/thresholds[key]
                    score=np.minimum(score,d)
                if diverging:
                    a,b=lab,lab[::-1]
                    da,db=np.linalg.norm(a-lab[center],axis=1),np.linalg.norm(b-lab[center],axis=1)
                    ratio=abs(da-db)/np.maximum(np.maximum(da,db),1e-12)
                    good=(abs(a[:,0]-b[:,0])<=profile['ordered']['arm_lightness_difference_max']) & (ratio<=profile['ordered']['arm_distance_relative_difference_max']) & (np.linalg.norm(a-b,axis=1)>=profile['ordered']['arm_separation_oklab_min'])
                    good[center]=True
                    allowed &= good
        if diverging:
            size=center;k=n//2
            matrix=np.minimum(score[:size,:size],score[grid-1:center:-1,grid-1:center:-1])
            valid=allowed[:size]&allowed[grid-1:center:-1]
            terminal=np.minimum(score[:size,center],score[grid-1:center:-1,center]) if n%2 else score[np.arange(size),grid-1-np.arange(size)]
            if n%2 and not allowed[center]:valid[:]=False
            if context=='data-marks':
                matrix=np.minimum(matrix,np.minimum(score[:size,grid-1:center:-1],score[grid-1:center:-1,:size]))
                terminal=np.minimum(terminal,score[np.arange(size),grid-1-np.arange(size)])
        else:
            size=grid;k=n;matrix=score;valid=allowed;terminal=np.full(size,-np.inf);terminal[-1]=np.inf

        def assemble(indices):
            if diverging:
                indices=list(indices)+([center] if n%2 else [])+[grid-1-i for i in indices[::-1]]
            return tuple(float(positions[i]) for i in indices)

        if context=='filled-fields':
            # Exact maximin dynamic programming on this finite candidate grid.
            dp=np.full((k,size),-np.inf);cost=np.full((k,size),np.inf);parent=np.full((k,size),-1,dtype=int)
            if valid[0]:dp[0,0]=np.inf;cost[0,0]=0.
            for level in range(1,k):
                check()
                for j in range(level,size):
                    if not valid[j]:continue
                    values=np.minimum(dp[level-1,:j],matrix[:j,j]);value=float(values.max())
                    if not np.isfinite(value):continue
                    ties=np.flatnonzero(abs(values-value)<=1e-12)
                    i=int(ties[np.argmin(cost[level-1,ties])])
                    dp[level,j]=value;cost[level,j]=cost[level-1,i]+(positions[j]-level/(n-1))**2;parent[level,j]=i
            values=np.minimum(dp[k-1],terminal);value=float(values.max())
            if value>=1:
                ties=np.flatnonzero(abs(values-value)<=1e-12);j=int(ties[np.argmin(cost[k-1,ties])]);indices=[j]
                for level in range(k-1,0,-1):j=int(parent[level,j]);indices.append(j)
                best=assemble(indices[::-1])
        else:
            # An all-pair compatible clique, including mandatory endpoints.
            # Binary threshold search improves its weakest relationship.
            def feasible(threshold):
                nonlocal nodes_visited
                if not valid[0] or terminal[0]<threshold:return None
                pool=[i for i in range(1,size) if valid[i] and matrix[0,i]>=threshold and terminal[i]>=threshold]
                if not diverging:
                    if not valid[-1]:return None
                    pool=[i for i in pool if i<size-1 and matrix[i,size-1]>=threshold]
                    if matrix[0,size-1]<threshold:return None
                    need=k-2;initial=[0];end=[size-1]
                else:need=k-1;initial=[0];end=[]
                def visit(chosen,pool,left):
                    nonlocal nodes_visited
                    nodes_visited+=1
                    if nodes_visited%32==0:check()
                    if not left:return chosen+end
                    if len(pool)<left:return None
                    for at,i in enumerate(pool):
                        remaining=[j for j in pool[at+1:] if matrix[i,j]>=threshold]
                        found=visit(chosen+[i],remaining,left-1)
                        if found is not None:return found
                    return None
                return visit(initial,pool,need)
            # Sequential endpoints require no terminal restrictions on inner
            # nodes; terminal above is only for filled-field endpoint DP.
            if not diverging:terminal=np.full(size,np.inf)
            indices=feasible(1.)
            if indices is not None:
                best=assemble(indices);lo=1.;hi=float(np.max(matrix[np.isfinite(matrix)]))
                for _ in range(12):
                    check();mid=(lo+hi)/2;indices=feasible(mid)
                    if indices is None:hi=mid
                    else:lo=mid;best=assemble(indices)
        check()
    except _Deadline:
        expired=True
    if best is None:
        raise SearchExhaustedError('No passing optimized selection found on this grid within its budget; try another count/grid/context',
            {'screen_pass':False,'outcome':'search-exhausted','infeasibility_proven':False,'deadline_reached':expired,
             'context':context,'count':n,'grid':grid,'elapsed_seconds':time.perf_counter()-started})
    report=screen(gradient,best,context)
    report['search']={'grid':grid,'elapsed_seconds':time.perf_counter()-started,'deadline_reached':expired,
        'method':'adjacent maximin dynamic programming' if context=='filled-fields' else 'all-pair compatibility search',
        'nodes_visited':nodes_visited,'global_continuous_optimum':False}
    if not report['screen_pass']:
        raise SearchExhaustedError('Grid candidate failed final independent discrete audit',
            {**report,'outcome':'search-exhausted','infeasibility_proven':False,'deadline_reached':expired})
    source=gradient.to_recipe();source['evidence']={}
    return SampledPalette(tuple(report['hex']),QualityReport(report),best,source)
