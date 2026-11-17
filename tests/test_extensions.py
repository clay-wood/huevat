"""Scientific and native-backend checks for the expanded public features."""
import csv
import io
import json
import importlib.util
import subprocess
import sys
from concurrent.futures import CancelledError

import pytest
import huevat as hv
from huevat import doctor
from huevat.gradients import fingerprint

HAS_DESIGN=importlib.util.find_spec('colorspacious') is not None
research=pytest.mark.skipif(not HAS_DESIGN,reason='requires design extras')


def test_core_alias_and_all_new_saved_designs():
    assert hv.categorical_names()==('core','earth','gem','max-separation')
    for bg in ('light','dark'):
        for n in range(2,13):assert hv.categorical(n,style='core',background=bg).colors==hv.categorical(n,style='clearer',background=bg).colors
        for style in ('earth','gem'):
            for n in range(2,9):
                p=hv.categorical(n,style=style,background=bg)
                assert len(set(p.colors))==n and p.report.screen_pass
                assert p.report['style']==style
                assert hv.load_export(hv.export(p)).design.colors==p.colors
                assert hv.get_design(f'h5-{style}-{bg}-{n}').colors==p.colors


@research
def test_new_categorical_colors_repeat_all_unchanged_gates():
    from huevat.styles import validate
    for bg in ('light','dark'):
        for style in ('earth','gem'):
            for n in range(2,9):
                p=hv.categorical(n,style=style,background=bg)
                assert validate(p.report.to_dict()['recipe'])['screen_pass']


def test_cyclic_seam_counts_exports_and_tampering():
    for bg in ('light','dark'):
        g=hv.cyclic(background=bg)
        assert g.at(0)==g.at(1) and g.reversed().at(0)==g.reversed().at(1)
        assert g.report['certificate']['derivative_error']<1e-12
        assert g.reversed().at(.25)==g.at(.75)
        for n in hv.known_counts(g):
            p=g.discrete(n);assert len(set(p.colors))==n
            assert hv.load_export(hv.export(g,n=n)).design.colors==p.colors
            assert hv.load_export(hv.export(g,n=n),validate=False).design.colors==p.colors
        rows=list(csv.DictReader(io.StringIO(hv.export(g,n=4,format='csv').text)))
        assert float(rows[-1]['position'])==.75
        assert hv.load_export(hv.export(g)).design.at(.37)==g.at(.37)
        envelope=g.to_recipe();envelope['recipe']['segments'][0][0][0]+=.1
        with pytest.raises(ValueError):hv.load_recipe(envelope)
        envelope['sha256']=fingerprint(envelope['recipe'])
        with pytest.raises(hv.QualityError):hv.load_recipe(envelope)


def test_prepared_optimized_selection_without_optional_imports():
    code='''
import importlib.abc,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'numpy','scipy','colorspacious','matplotlib','plotly','ultraplot'}:
   raise AssertionError(fullname)
sys.meta_path.insert(0,Block())
import huevat as h
p=h.optimized_discrete(h.diverging(),8)
assert len(p)==8 and p.report.screen_pass
assert h.categorical(8,style='gem').report.screen_pass
assert h.cyclic().discrete(7).report.screen_pass
assert h.cyclic().reversed().discrete(7).report.screen_pass
assert len(h.design_ids())==124
'''
    subprocess.run([sys.executable,'-I','-c',code],check=True)


@research
def test_nearby_counts_include_optimized_eight():
    report=hv.count_options(hv.diverging(),8,radius=1)
    options={c['count']:c for c in report['choices']}
    assert set(report['passing_counts'])=={7,8,9}
    assert options[8]['method']=='optimized' and options[7]['method']=='uniform'
    with pytest.raises(ValueError):hv.count_options(hv.diverging(),8,radius=100)
    with pytest.raises(ValueError):hv.optimized_discrete(None,8)
    with pytest.raises(ValueError):hv.optimized_discrete(hv.cyclic(),4)


def test_search_progress_and_cancellation():
    stages=[]
    with hv.start_search('categorical',n=3,style='earth',progress=lambda s: stages.append(s)) as job:
        assert job.result(timeout=20).colors==hv.categorical(3,style='earth').colors
        assert job.result().colors==hv.categorical(3,style='earth').colors
    assert stages and all(s['elapsed_seconds']>=0 for s in stages)
    with hv.start_search('categorical',n=64,max_seconds=60,starts=32) as job:
        assert job.cancel()
        assert job.status=='cancelled'
        with pytest.raises(CancelledError):job.result()


@research
def test_filled_bars_bands_palette_choices_and_exact_undo():
    mpl=pytest.importorskip('matplotlib');mpl.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    fig,ax=plt.subplots()
    a=ax.bar([1,2],[2,3],color='red',label='A')
    ax.bar([3,4],[1,4],color='red',label='B')
    band=ax.fill_between([1,2],[.5,1],[1,1.5],color='red',alpha=.3,label='A')
    ax.legend()
    original=[p.get_facecolor() for p in ax.patches];original_band=band.get_facecolor().copy()
    before=doctor.inspect(fig,fills=True)
    assert before.categories==('A','B') and {m['kind'] for m in before.marks}=={'bar','band'}
    options=doctor.propose(before,palettes=('core','earth','gem'))
    q=options[1];preview=doctor.preview(fig,q,condition='grayscale')
    assert doctor.inspect(fig,fills=True).fingerprint==before.fingerprint
    change=doctor.apply(fig,q)
    assert a.patches[0].get_facecolor()!=original[0]
    assert band.get_alpha()==.3
    change.undo()
    assert [p.get_facecolor() for p in ax.patches]==original
    np.testing.assert_array_equal(band.get_facecolor(),original_band)
    plt.close(fig);plt.close(preview)


@research
def test_field_recolor_keeps_mask_center_limits_boundaries_and_guards_undo():
    mpl=pytest.importorskip('matplotlib');mpl.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm,BoundaryNorm
    import numpy as np
    fig,axes=plt.subplots(1,2)
    z=np.ma.array(np.arange(12.).reshape(3,4),mask=False);z.mask[0,0]=True
    norm=TwoSlopeNorm(0,vmin=-2,vmax=9)
    image=axes[0].imshow(z,norm=norm);fig.colorbar(image,ax=axes[0])
    edges=(-2,-1,0,1,3,5,7,9)
    mesh=axes[1].pcolormesh(z,norm=BoundaryNorm(edges,256))
    original=image.cmap
    change=doctor.recolor(fig,hv.diverging())
    assert image.norm is norm and image.norm(0)==.5
    np.testing.assert_array_equal(np.ma.getmaskarray(image.get_array()),z.mask)
    assert tuple(mesh.norm.boundaries)==edges and image.get_clim()==(-2.,9.)
    # Drawing may settle constrained layout; it must not invalidate a scalar-only undo.
    fig.canvas.draw()
    change.undo();assert image.cmap is original
    change=doctor.recolor(fig,hv.diverging(),keys=[doctor.fields(fig)[0]['key']],center=0)
    image.set_data(z+1)
    with pytest.raises(ValueError,match='changed'):change.undo()
    plt.close(fig)


@research
def test_plotly_scalar_center_and_bar_colors_preserve_data():
    go=pytest.importorskip('plotly.graph_objects')
    fig=go.Figure(go.Heatmap(z=[[-2,0],[4,8]],coloraxis='coloraxis'))
    fig.update_layout(coloraxis=dict(cmin=-2,cmax=8))
    before=fig.to_json();data=fig.data[0].z
    change=doctor.recolor(fig,hv.diverging(),center=0)
    stops=fig.layout.coloraxis.colorscale
    assert any(abs(t-.2)<1e-12 for t,c in stops)
    assert fig.data[0].z==data
    change.undo();assert fig.to_json()==before
    bars=go.Figure([go.Bar(x=['x','y'],y=[1,2],name='A',marker_color='red'),go.Bar(x=['x','y'],y=[3,1],name='B',marker_color='red')])
    scene=doctor.inspect(bars,fills=True);q=doctor.propose(scene,palette='gem')[0]
    before=bars.to_json();change=doctor.apply(bars,q);change.undo();assert bars.to_json()==before


@research
def test_proofs_at_requested_size_and_uncertainty_alpha(tmp_path):
    mpl=pytest.importorskip('matplotlib');mpl.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    styles=doctor.band_styles(hv.categorical(2),['A','B'],alpha=.2)
    assert styles['styles']['A']['fill'][3]==.2
    assert 'filled_checks' in styles['report']
    fig,ax=plt.subplots();ax.plot([0,1],[1,0],color='red')
    old_size=fig.get_size_inches().copy()
    numbers=plt.get_fignums();active=plt.gcf();old_backend=mpl.get_backend()
    report=doctor.proof_sheet(fig,tmp_path/'proof.pdf',width_mm=85,dpi=100)
    assert abs(report['panel_pixels'][0]-85/25.4*100)<=1
    gray=plt.imread(tmp_path/'proof-grayscale.png')
    np.testing.assert_array_equal(gray[:,:,0],gray[:,:,1]);np.testing.assert_array_equal(gray[:,:,1],gray[:,:,2])
    np.testing.assert_array_equal(fig.get_size_inches(),old_size)
    assert plt.get_fignums()==numbers and plt.gcf() is active and mpl.get_backend()==old_backend
    assert (tmp_path/'proof.pdf').is_file() and (tmp_path/'proof.json').is_file()
    plt.close(fig)
