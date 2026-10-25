"""Build/check the H4a offline examples and source-linked numerical evidence."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'research/adapters-v1'
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache/matplotlib'))

import numpy as np
import huevat as hv
from huevat.adapters import matplotlib as hmpl, plotly as hplotly, ultraplot as huplt


def write_json(path,value):
    path.write_text(json.dumps(value,separators=(',',':'),sort_keys=True,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def source_hashes():
    names = ['sampling.py','_sampling_design.py','__init__.py']
    names += ['adapters/'+p.name for p in sorted((ROOT/'src/huevat/adapters').glob('*.py'))]
    return {name:hashlib.sha256((ROOT/'src/huevat'/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            for name in names}


def field():
    x,y = np.meshgrid(np.linspace(-3,3,160),np.linspace(-2,2,100))
    z = 8*np.exp(-((x-.7)**2+(y-.1)**2)) - 2*np.exp(-((x+1.1)**2+(y+.2)**2)/.4)
    z[(x<-2.4)&(y>1.1)] = np.nan
    return z


def native_figure(adapter,gradient,palette,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    bg = hv.to_hex(gradient.background)
    fg = '#222222' if bg=='#ffffff' else '#eeeeee'
    z=field();cmap=adapter.colormap(gradient,bad='#a0a0a0')
    norm=adapter.normalizer(-2,8,center=0)
    edges=[-2,-1.5,-1,-.5,0,1,2,4,8]
    if adapter is huplt:
        import ultraplot as uplt
        fig,axs=uplt.subplots(ncols=3,figwidth=12,figheight=3.5,share=False)
        im=axs[0].pcolormesh(z,cmap=cmap,norm=norm,discrete=False)
        discrete=axs[1].pcolormesh(z,cmap=adapter.colormap(palette),norm=adapter.boundary_normalizer(palette,edges))
        axs[0].colorbar(im,loc='b');axs[1].colorbar(discrete,loc='b')
    else:
        fig,axs=plt.subplots(1,3,figsize=(12,3.5),layout='constrained')
        im=axs[0].imshow(z,cmap=cmap,norm=norm,origin='lower')
        discrete=axs[1].imshow(z,cmap=adapter.colormap(palette),norm=adapter.boundary_normalizer(palette,edges),origin='lower')
        fig.colorbar(im,ax=axs[0],orientation='horizontal',fraction=.1)
        fig.colorbar(discrete,ax=axs[1],orientation='horizontal',fraction=.1)
    cats=hv.categorical(5,background='light' if bg=='#ffffff' else 'dark')
    axs[2].set_prop_cycle(adapter.cycle(cats,markers=['o','s','^','D','v'],linestyles=['-','--',':','-.','-']))
    x=np.linspace(0,1,25)
    for i in range(5):axs[2].plot(x,.12*i+.08*np.sin(2*np.pi*x+i/2),label=['Blue','Teal','Ochre','Coral','Purple'][i],markevery=4)
    legend=axs[2].legend(fontsize=8,loc='upper right',facecolor=bg,labelcolor=fg,ncols=1)
    legend.get_frame().set_facecolor(bg)
    legend.get_frame().set_edgecolor('#bbbbbb' if bg=='#ffffff' else '#555555')
    fig.patch.set_facecolor(bg)
    for ax,title in zip(axs,['Continuous · zero at neutral','8 colors · explicit data boundaries','Clearer · specified markers and dashes']):
        ax.set_facecolor(bg);ax.set_title(title,color=fg,fontsize=10)
        ax.tick_params(colors=fg,labelsize=8)
        for spine in ax.spines.values():spine.set_edgecolor(fg)
    for ax in fig.axes:
        ax.tick_params(colors=fg,labelsize=8)
    for colorbar in (im.colorbar,discrete.colorbar):
        if colorbar is not None:
            colorbar.ax.tick_params(colors=fg,labelsize=8)
            for text in colorbar.ax.get_xticklabels()+colorbar.ax.get_yticklabels():text.set_color(fg)
    fig.savefig(path,dpi=180,facecolor=bg)
    plt.close(fig)
    return cmap.huevat_report.to_dict()


def plotly_figure(path):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    g=hv.diverging();axis=hplotly.coloraxis(g,-2,8,center=0)
    fig=make_subplots(rows=1,cols=2,subplot_titles=['Continuous signed field','Same color axis · hover for original values'])
    z=field()[::3,::3]
    fig.add_trace(go.Heatmap(z=z.tolist(),coloraxis='coloraxis',hoverongaps=False),row=1,col=1)
    fig.add_trace(go.Scatter(x=[0,1,2,3,4],y=[1,2,1,3,2],mode='markers+text',text=['−2','−1','0','4','8'],textposition='top center',
        marker={'size':24,'color':[-2,-1,0,4,8],'coloraxis':'coloraxis'}),row=1,col=2)
    fig.update_layout(coloraxis=axis,height=420,template='plotly_white',margin={'l':35,'r':35,'b':35,'t':60})
    fig.write_html(path,include_plotlyjs=True,div_id='huevat-h4a-example',config={'displaylogo':False})
    # Plotly's writer uses platform newlines; retained artifact hashes use LF.
    path.write_text(path.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
    return axis.huevat_report.to_dict()


def check():
    manifest=json.loads((OUTPUT/'manifest.json').read_text())
    assert manifest['implementation_sha256_lf']==source_hashes(),'H4a source changed; rebuild evidence'
    for name,digest in manifest['files'].items():
        assert hashlib.sha256((OUTPUT/name).read_bytes()).hexdigest()==digest,name
    data=json.loads((OUTPUT/'evidence.json').read_text())
    for name,envelope in data['sampling'].items():
        p=hv.load_recipe(envelope)
        assert p.report.screen_pass,name
        source=hv.load_recipe(envelope['recipe']['source'])
        repeated=hv.optimized_discrete(source,len(p),grid=257,max_seconds=30)
        assert repeated.positions==p.positions,name
    # Render actual native objects, with masks, colorbars, cycles and data bins.
    scratch=ROOT/'artifacts/h4a-check';scratch.mkdir(parents=True,exist_ok=True)
    g=hv.diverging();p=hv.optimized_discrete(g,8)
    for adapter in (hmpl,huplt):native_figure(adapter,g,p,scratch/(adapter.__name__.split('.')[-1]+'.png'))
    plotly_figure(scratch/'plotly.html')
    print('Reaudited 10 optimized selections and all three native exports; verified H4a source/gallery hashes')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if args.check:return check()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    evidence={'versions':{name:metadata.version(name) for name in ('huevat','numpy','colorspacious','matplotlib','plotly','ultraplot')},
              'sampling':{},'adapters':{},'human_review':'pending','approved_H4_default':False}
    cards=[]
    for bg in ('light','dark'):
        for factory in (hv.sequential,hv.diverging,hv.multihue,hv.spectral):
            g=factory(background=bg)
            for n in ([7,8] if g.family=='diverging' else [8]):
                p=hv.optimized_discrete(g,n,max_seconds=30)
                evidence['sampling'][f'{bg}/{g.family}/{n}']=p.to_recipe()
        g=hv.diverging(background=bg);p=hv.optimized_discrete(g,8)
        for adapter in (hmpl,huplt):
            backend=adapter.__name__.split('.')[-1];name=f'{backend}-{bg}.png'
            evidence['adapters'][f'{backend}/{bg}']=native_figure(adapter,g,p,OUTPUT/name)
            cards.append(f'<section><h2>{backend.title()} / {bg}</h2><img src="{name}" alt="Native {backend} figure, {bg} background"></section>')
    evidence['adapters']['plotly/light']=plotly_figure(OUTPUT/'plotly.html')
    write_json(OUTPUT/'evidence.json',evidence)
    p=hv.load_recipe(evidence['sampling']['light/diverging/8'])
    swatches=''.join(f'<div class="swatch" style="background:{c}" title="t={t:.8f}"></div>' for c,t in zip(p.colors,p.positions))
    positions=', '.join(f'{t:.6f}' for t in p.positions)
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Huevat: plotting adapters and optimized sampling</title><style>body{font:16px/1.6 system-ui;max-width:1200px;margin:auto;padding:30px;background:#f0f1f4;color:#202a35}section{background:white;border-radius:12px;padding:24px;margin:24px 0}img{width:100%;height:auto}iframe{width:100%;height:460px;border:0}.row{display:flex;height:70px}.swatch{flex:1}code{overflow-wrap:anywhere}a{color:#27628f}</style><h1>Huevat: plotting adapters and optimized sampling</h1><p>H4a · Matplotlib, Plotly and UltraPlot · the selected Clearer categorical design</p><section><h2>Eight colors from the same diverging path</h2><p>The uniform eight-color selection fails the existing profile. Explicit optimized positions pass every float/8-bit normal/CVD discrete gate. Both endpoints and mirrored arms are retained. These positions represent colors; the physical data boundaries in the figures are chosen separately.</p><div class="row">'''+swatches+f'''</div><p><code>t = [{positions}]</code></p><p>Existing uniform sampling and all H0–H3 numerical implementations remain unchanged.</p></section>'''+''.join(cards)+'''<section><h2>Plotly / shared asymmetric range</h2><p>Both panels use −2 to +8, with zero at the source neutral. Hover and zoom work offline. Missing cells use the native gap behavior.</p><iframe src="plotly.html" title="Interactive native Plotly example"></iframe></section><section><h2>Evidence and limits</h2><p>Continuous exports pass a finite-grid Oklab approximation tolerance of .002. Reports include float and quantized errors for all eight conditions. This is approximation evidence; figure-wide accessibility and new default approval remain separate.</p><p><a href="evidence.json">Full recipes, errors and backend versions</a> · <a href="../../docs/METHODS_H4A.md">Usage and methods</a> · <a href="../../examples/README.md">Plotting examples</a></p></section></html>'''
    (OUTPUT/'index.html').write_text(page,encoding='utf-8',newline='\n')
    write_json(OUTPUT/'manifest.json',{'implementation_sha256_lf':source_hashes(),
        'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUTPUT.iterdir()) if p.is_file() and p.name!='manifest.json'}})
    print('Built H4a native figures, offline Plotly example and evidence')


if __name__=='__main__':main()
