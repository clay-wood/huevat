"""Native backend use, explicit data semantics and approximation failure."""
import importlib
import json

import pytest

import huevat as hv


@pytest.fixture(params=['matplotlib','ultraplot'])
def native(request):
    mpl = pytest.importorskip('matplotlib')
    mpl.use('Agg')
    pytest.importorskip(request.param)
    return importlib.import_module('huevat.adapters.'+request.param)


def test_native_types_center_range_special_values_and_render(native,tmp_path):
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgba
    g = hv.diverging()
    cmap = native.colormap(g,bad='#aaaaaa',under='#111111',over='#ffeeaa')
    norm = native.normalizer(-2,8,center=0)
    assert tuple(norm([-2,0,8])) == (0.,.5,1.)
    assert cmap(norm(0))[:3] == pytest.approx(g.at(.5),abs=1e-9)
    assert cmap(norm(-3)) == pytest.approx(to_rgba('#111111'))
    assert cmap(norm(9)) == pytest.approx(to_rgba('#ffeeaa'))
    assert cmap(norm(float('nan'))) == pytest.approx(to_rgba('#aaaaaa'))
    report = cmap.huevat_report
    assert report['approximation_pass'] and not report['adapter_profile_revalidated']
    assert report['maximum_float_error_oklab'] <= .002
    assert report['float_condition_errors']['deutan-100'] > 1e-5
    assert set(report['float_condition_errors']) == set(hv.load_profile()['conditions'])
    if native.__name__.endswith('ultraplot'):
        import ultraplot as uplt
        assert isinstance(cmap,uplt.ContinuousColormap)
        fig,ax = uplt.subplots()
        image = ax.pcolormesh(np.linspace(-2,8,100).reshape(10,10),cmap=cmap,norm=norm,discrete=False)
        assert isinstance(image.cmap,uplt.ContinuousColormap)
        fig.colorbar(image,loc='r')
    else:
        fig,ax = plt.subplots()
        image = ax.imshow(np.linspace(-2,8,100).reshape(10,10),cmap=cmap,norm=norm)
        fig.colorbar(image,ax=ax)
    fig.savefig(tmp_path/'native.png')
    plt.close(fig)
    assert (tmp_path/'native.png').stat().st_size > 1000


def test_native_discrete_bins_cycles_labels_and_contours(native,tmp_path):
    import numpy as np
    from matplotlib.colors import to_rgb
    import matplotlib.pyplot as plt
    p = hv.categorical(4)
    cmap = native.colormap(p)
    norm = native.boundary_normalizer(p,[-2,-1,0,2,8])
    assert [hv.to_hex(cmap(norm(v))[:3]) for v in (-1.5,-.5,1.,5.)] == list(p.colors)
    names = ['sand','silt','clay','basalt']
    assert list(native.color_map(p,names)) == names
    cycle = native.cycle(p,markers=['o','s','^','D'],linestyles=['-','--',':','-.'])
    assert len(cycle) == len(p)
    assert [c['color'] for c in cycle] == list(p.colors)
    assert [c['marker'] for c in cycle] == ['o','s','^','D']
    assert set(cycle.by_key()) == {'color','marker','linestyle'}
    if native.__name__.endswith('ultraplot'):
        import ultraplot as uplt
        assert isinstance(cmap,uplt.DiscreteColormap)
        fig,ax = uplt.subplots()
        image = ax.contourf(np.linspace(-2,8,100).reshape(10,10),cmap=cmap,norm=norm,levels=[-2,-1,0,2,8])
        fig.colorbar(image,loc='r')
    else:
        fig,ax = plt.subplots()
        image = ax.contourf(np.linspace(-2,8,100).reshape(10,10),cmap=cmap,norm=norm,levels=[-2,-1,0,2,8])
        fig.colorbar(image,ax=ax)
    fig.savefig(tmp_path/'discrete.png')
    plt.close(fig)
    assert (tmp_path/'discrete.png').stat().st_size > 1000
    if native.__name__.endswith('ultraplot'):
        fig,axs = uplt.subplots()
        ax = axs[0]
    else:
        fig,ax = plt.subplots()
    ax.set_prop_cycle(cycle)
    lines = [ax.plot([0,1],[i,i+1])[0] for i in range(4)]
    assert [hv.to_hex(to_rgb(l.get_color())) for l in lines] == list(p.colors)
    assert [l.get_marker() for l in lines] == ['o','s','^','D']
    assert [l.get_linestyle() for l in lines] == ['-','--',':','-.']
    plt.close(fig)


def test_native_approximation_budget_failure_and_preflight(native):
    with pytest.raises(hv.QualityError) as error:
        native.colormap(hv.diverging(),samples=3,max_samples=3,tolerance=1e-8)
    assert not error.value.report['approximation_pass']
    for kwargs in ({'samples':4},{'max_samples':3},{'tolerance':0}):
        with pytest.raises(ValueError):
            native.colormap(hv.sequential(),**kwargs)
    with pytest.raises(ValueError):native.normalizer(0,1,center=2)
    with pytest.raises(ValueError):native.boundary_normalizer(hv.categorical(4),[0,1])
    with pytest.raises(ValueError):native.color_map(hv.categorical(2),['same','same'])
    with pytest.raises(ValueError):native.cycle(hv.categorical(2),markers=['o'])


def test_matplotlib_registration_is_explicit_and_never_overwrites():
    mpl = pytest.importorskip('matplotlib')
    from huevat.adapters import matplotlib as adapter
    name = 'huevat-test-explicit-registration'
    cmap = adapter.colormap(hv.categorical(4),name=name)
    assert name not in mpl.colormaps
    try:
        adapter.register(cmap)
        assert name in mpl.colormaps
        with pytest.raises(ValueError):adapter.register(cmap)
    finally:
        mpl.colormaps.unregister(name)


def test_condition_audit_avoids_user_selected_lookup_alignment():
    pytest.importorskip('matplotlib')
    from huevat.adapters import matplotlib as adapter
    cmap=adapter.colormap(hv.diverging(),samples=1021,max_samples=1021)
    assert cmap.huevat_report['condition_grid_samples'] != 1021
    assert cmap.huevat_report['float_condition_errors']['deutan-100'] > 1e-5


def test_plotly_shared_asymmetric_axis_and_actual_figure_serialization(tmp_path):
    go = pytest.importorskip('plotly.graph_objects')
    from plotly.colors import sample_colorscale,unlabel_rgb
    from huevat.adapters import plotly as adapter
    g = hv.diverging()
    axis = adapter.coloraxis(g,-2,8,center=0)
    central = sample_colorscale(axis['colorscale'],[.2])[0]
    assert tuple(c/255 for c in unlabel_rgb(central)) == pytest.approx(g.at(.5),abs=.5/255)
    fig = go.Figure([
        go.Heatmap(z=[[-2,None],[0,8]],coloraxis='coloraxis'),
        go.Scatter(x=[0,1],y=[0,1],mode='markers',marker={'color':[0,8],'coloraxis':'coloraxis'})])
    fig.update_layout(coloraxis=axis)
    data = json.loads(fig.to_json())
    assert data['layout']['coloraxis']['cauto'] is False
    assert data['layout']['coloraxis']['cmin'] == -2
    assert data['layout']['coloraxis']['cmax'] == 8
    assert 'cmid' not in data['layout']['coloraxis']
    assert 'huevat_report' not in data['layout']['coloraxis']
    assert data['data'][0]['z'][0][1] is None
    assert 'unsupported' in axis.huevat_report['under_over_policy']
    fig.write_html(tmp_path/'plotly.html',include_plotlyjs=True)
    assert (tmp_path/'plotly.html').stat().st_size > 10000
    with pytest.raises(hv.QualityError):
        adapter.colorscale(g,samples=3,max_samples=3,tolerance=1e-8)


def test_plotly_discrete_bins_and_label_identity():
    go = pytest.importorskip('plotly.graph_objects')
    from huevat.adapters import plotly as adapter
    p = hv.categorical(4)
    axis = adapter.discrete_coloraxis(p,[-2,-1,0,2,8])
    assert [s[0] for s in axis['colorscale']] == [0,.1,.1,.2,.2,.4,.4,1.]
    assert [s[1] for s in axis['colorscale'][::2]] == list(p.colors)
    go.Figure(go.Heatmap(z=[[-1,0,4]],coloraxis='coloraxis'),layout={'coloraxis':axis}).to_json()
    assert adapter.sequence(p) == list(p.colors)
    labels = ['B','A','D','C']
    assert list(adapter.color_map(p,labels)) == labels
    with pytest.raises(ValueError):adapter.discrete_coloraxis(p,[0,1,1,2,3])
