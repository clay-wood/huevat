"""Small native examples. Output goes to artifacts/quickstart; no browser opens."""
import argparse
from pathlib import Path

import huevat as hv


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--backend',choices=('matplotlib','plotly','ultraplot'),default='matplotlib');args=parser.parse_args()
    output=Path('artifacts/quickstart');output.mkdir(parents=True,exist_ok=True)
    labels=['Control','A','B','C','D','E']
    palette=hv.categorical(6);gradient=hv.diverging()
    hv.export(palette,labels=labels).write(output/'palette.json')
    hv.export(gradient,n=7).write(output/'seven-colors.json')
    hv.export(gradient,n=7,format='csv').write(output/'seven-colors.csv')
    if args.backend=='plotly':
        import plotly.graph_objects as go
        from huevat.adapters import plotly as adapter
        fig=go.Figure(go.Heatmap(z=[[-2,None,0],[1,4,8]],coloraxis='coloraxis'))
        fig.update_layout(coloraxis=adapter.coloraxis(gradient,-2,8,center=0))
        (output/'plotly.json').write_text(fig.to_json()+'\n',encoding='utf-8',newline='\n')
    else:
        import os
        os.environ.setdefault('MPLCONFIGDIR',str(Path('.cache/matplotlib').resolve()))
        import matplotlib;matplotlib.use('Agg')
        import numpy as np
        if args.backend=='ultraplot':
            import ultraplot as plt
            from huevat.adapters import ultraplot as adapter
            fig,axs=plt.subplots(ncols=2,share=False,figwidth=9,figheight=3.5);axes=[axs[0],axs[1]]
        else:
            import matplotlib.pyplot as plt
            from huevat.adapters import matplotlib as adapter
            fig,axes=plt.subplots(1,2,figsize=(9,3.5),layout='constrained')
        colors=adapter.color_map(palette,labels);x=np.linspace(0,10,41)
        for i,label in enumerate(labels):axes[0].plot(x,np.sin(x/2+i/3),label=label,color=colors[label])
        axes[0].legend(fontsize=7);axes[0].set(xlabel='Distance (km)',ylabel='Displacement (mm)')
        z=np.linspace(-2,8,120).reshape(10,12)
        kwargs={'discrete':False} if args.backend=='ultraplot' else {}
        image=axes[1].pcolormesh(z,cmap=adapter.colormap(gradient),norm=adapter.normalizer(-2,8,center=0),**kwargs)
        fig.colorbar(image,ax=axes[1],label='Anomaly (K)')
        fig.savefig(output/(args.backend+'.png'),dpi=160)
        import matplotlib.pyplot as mplplt
        mplplt.close(fig)
    print(f'Wrote {args.backend} example and compact exports to {output}')


if __name__=='__main__': main()
