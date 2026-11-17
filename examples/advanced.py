"""Scalar repair, a cyclic phase field and an actual-size proof sheet."""
import os
from pathlib import Path
import huevat as hv
from huevat import doctor
from huevat.adapters import matplotlib as hmpl

ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache/matplotlib'))


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    output=ROOT/'artifacts/h5/examples';output.mkdir(parents=True,exist_ok=True)
    x,y=np.meshgrid(np.linspace(-3,3,140),np.linspace(-2,2,90))
    z=8*np.exp(-((x-.7)**2+y**2))-2*np.exp(-((x+1)**2+y**2)/.4)
    fig,axes=plt.subplots(1,2,figsize=(9,3.6),layout='constrained')
    image=axes[0].imshow(z,origin='lower',cmap='jet',vmin=-2,vmax=8)
    fig.colorbar(image,ax=axes[0],label='Signed amplitude')
    axes[0].set_title('Recolored field · zero at neutral')
    phase=(np.arctan2(y,x)+np.pi)/(2*np.pi)
    phase=np.ma.masked_where(x*x+y*y>3.8,phase)
    image=axes[1].imshow(phase,origin='lower',cmap=hmpl.colormap(hv.cyclic(),bad='#f8f8f8'),vmin=0,vmax=1)
    fig.colorbar(image,ax=axes[1],label='Phase / full turn')
    axes[1].set_title('Cyclic · the ends join')
    # Select only the signed field. The phase field retains its own mapping.
    key=doctor.fields(fig)[0]['key']
    change=doctor.recolor(fig,hv.diverging(),keys=[key],center=0)
    fig.savefig(output/'fields.png',dpi=180)
    doctor.proof_sheet(fig,output/'proof.pdf',width_mm=180)
    change.undo()
    plt.close(fig)

    fig,ax=plt.subplots(figsize=(6,3.5),layout='constrained')
    labels=['Control','A','B'];palette=hv.categorical(3,style='earth')
    styles=doctor.band_styles(palette,labels,alpha=.2)['styles']
    t=np.linspace(0,10,100)
    for i,label in enumerate(labels):
        v=np.sin(t/2+i/2);style=styles[label]
        ax.plot(t,v,color=style['color'],label=label)
        ax.fill_between(t,v-.12,v+.12,color=style['fill'],label=label)
    ax.legend(handles=ax.lines,labels=labels)
    scene=doctor.inspect(fig,fills=True)
    options=doctor.propose(scene,palettes=('core','earth','gem'))
    preview=doctor.preview(fig,options[1]);preview.savefig(output/'bands.png',dpi=180)
    plt.close(fig);plt.close(preview)
    print('Wrote scalar, phase, uncertainty and proof examples to',output)


if __name__=='__main__':main()
