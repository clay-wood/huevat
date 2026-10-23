"""Real-backend acceptance tests for inspection, negotiation and guarded edits."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from copy import deepcopy

import pytest
from huevat import doctor
from huevat.gradients import fingerprint

ROOT = Path(__file__).resolve().parents[1]
HAS_DESIGN = importlib.util.find_spec("colorspacious") is not None
research = pytest.mark.skipif(not HAS_DESIGN, reason="requires huevat[design]")


@pytest.fixture(autouse=True)
def close_native_figures():
    yield
    if 'matplotlib.pyplot' in sys.modules:
        sys.modules['matplotlib.pyplot'].close('all')


def test_module_import_has_no_optional_dependencies():
    subprocess.run([sys.executable, "-I", "-c", '''
import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.split('.')[0] in {'numpy','scipy','colorspacious','matplotlib','plotly','ultraplot','PIL','sketchplot'}:
   raise AssertionError('Unexpected optional import: '+fullname)
sys.meta_path.insert(0,Block())
from huevat import doctor
assert doctor.__all__
try: doctor.inspect(object())
except TypeError: pass
else: raise AssertionError('Unsupported figure accepted')
'''], check=True)


def mpl_figure(background="#ffffff", scatter=False):
    mpl = pytest.importorskip("matplotlib"); mpl.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(8, 3))
    fig.set_facecolor(background)
    for ax in axes:
        ax.set_facecolor(background)
        for k, y in (("B", [1., .3, 0.]), ("A", [0., .7, 1.])):
            if scatter: ax.scatter([0., .5, 1.], y, label=k, color="red")
            else: ax.plot([0., .5, 1.], y, label=k, color="red", linewidth=1.25)
        ax.legend()
    return fig, axes


@research
@pytest.mark.parametrize("scatter", [False, True])
def test_inspect_preview_apply_undo_and_immutable_data(scatter):
    fig, axes = mpl_figure(scatter=scatter)
    import matplotlib.pyplot as plt
    numbers = plt.get_fignums()
    manager = plt.get_current_fig_manager()
    state = [(a.stale, a._stale_viewlims.copy(), a.dataLim.bounds) for a in axes]
    scene = doctor.inspect(fig)
    assert scene.categories == ("A", "B") and len(scene.marks) == 4
    assert state == [(a.stale, a._stale_viewlims.copy(), a.dataLim.bounds) for a in axes]
    assert not doctor.diagnose(scene)["color_screen_pass"]
    with pytest.raises(TypeError): scene.marks[0]["category"] = "other"
    options = doctor.propose(scene)
    assert [q.name for q in options] == ["closer", "separation", "simple"]
    assert all(q.report["color_screen_pass"] for q in options)
    q = options[0]
    with pytest.raises(TypeError): q.assignments["A"]["color"] = "#000000"
    copied = doctor.preview(fig, q, condition="deutan-100")
    assert copied is not fig and copied.huevat_doctor_preview["condition"] == "deutan-100"
    assert plt.get_fignums() == numbers and plt.get_current_fig_manager() is manager
    assert copied.canvas.manager is None
    assert doctor.inspect(fig).fingerprint == scene.fingerprint
    changed = doctor.apply(fig, doctor.load_proposal(q.to_json()))
    assert changed.after.fingerprint != scene.fingerprint
    assert [m["data_sha256"] for m in changed.after.marks] == [m["data_sha256"] for m in scene.marks]
    assert changed.before.axes == changed.after.axes
    assert not changed.report["complete_figure_screen_pass"]
    for category in scene.categories:
        styles = [(m["channels"][0]["rgb"], m["marker"], m["dash"]) for m in changed.after.marks if m["category"] == category]
        assert styles[0] == styles[1]
    changed.undo()
    assert doctor.inspect(fig).fingerprint == scene.fingerprint
    with pytest.raises(ValueError, match="already undone"): changed.undo()


@research
def test_absent_reordered_categories_reserve_identities_and_locks():
    fig, axes = mpl_figure()
    q = doctor.propose(doctor.inspect(fig), locked={"A": {"color": "#4379a3"}})[0]
    assert q.assignments["A"]["color"] == "#4379a3"
    axes[0].lines[1].remove(); axes[1].lines[1].remove()
    q2 = doctor.propose(doctor.inspect(fig), assignments=q.assignments)[0]
    assert q2.assignments == q.assignments
    with pytest.raises(ValueError, match="conflicts"):
        doctor.propose(doctor.inspect(fig), assignments=q.assignments, locked={"A": {"color": "#000000"}})
    with pytest.raises(ValueError, match="Unknown locked"):
        doctor.propose(doctor.inspect(fig), locked={"A": {"width": 5}})
    with pytest.raises(ValueError, match="12 reserved"):
        doctor.propose(doctor.inspect(fig), locked={str(i): {"color": "#4379a3"} for i in range(13)})


@research
def test_locked_duplicate_colors_keep_failed_color_status_with_redundancy():
    fig, _ = mpl_figure()
    q = doctor.propose(doctor.inspect(fig), locked={k: {"color": "#4379a3"} for k in ("A", "B")})[0]
    assert not q.report["color_screen_pass"]
    assert q.report["redundant_pairs"] and not q.report["unresolved_pairs"]
    assert q.report["multichannel_screen_pass"] is None
    change = doctor.apply(fig, q)
    assert not change.report["color_screen_pass"] and change.report["redundant_pairs"]
    change.undo()


@research
def test_relationships_crossing_and_gaps():
    fig, axes = mpl_figure()
    assert all(e["crossing"] and e["weight"] == 3 for e in doctor.diagnose(doctor.inspect(fig))["relationships"])
    axes[0].lines[0].set_ydata([1., float("nan"), 0.])
    axes[1].lines[0].set_ydata([1., float("nan"), 0.])
    assert not any(e["crossing"] for e in doctor.diagnose(doctor.inspect(fig))["relationships"])


@research
def test_transparency_composites_actual_background_and_preserves_alpha():
    fig, axes = mpl_figure(background="#ddddee")
    axes[0].lines[0].set_color((1., 0., 0., .4))
    axes[1].lines[0].set_alpha(.6)
    scene = doctor.inspect(fig)
    report = doctor.diagnose(scene)
    color = report["panels"][0]["displayed"][0]["rgb"]
    bg = scene.axes[0]["background"]
    assert color == pytest.approx([.4+.6*bg[0], .6*bg[1], .6*bg[2]])
    assert not report["coverage"]["complete"]
    change = doctor.apply(fig, doctor.propose(scene)[0])
    assert [m["channels"][0]["alpha"] for m in change.after.marks] == [m["channels"][0]["alpha"] for m in scene.marks]
    change.undo(); assert doctor.inspect(fig).fingerprint == scene.fingerprint


@research
def test_uncertainty_bands_colorbar_and_unsupported_patch_preserved():
    import numpy as np
    from matplotlib.patches import Rectangle
    fig, axes = mpl_figure()
    band = axes[0].fill_between([0, 1], [.2, .3], [.4, .5], color="red", alpha=.15)
    image = axes[1].imshow(np.arange(9).reshape(3, 3), extent=(0, 1, 0, 1), alpha=.3)
    cb = fig.colorbar(image, ax=axes[1]); cb.set_label("Velocity (km/s)")
    rect = axes[0].add_patch(Rectangle((.2, .2), .2, .1, color="purple"))
    before = (band.get_facecolors().copy(), image.get_array().copy(), image.norm.vmin, image.norm.vmax,
              image.cmap.name, rect.get_facecolor(), cb.ax.get_ylabel())
    scene = doctor.inspect(fig)
    assert scene.coverage["read_only"] >= 3 and scene.coverage["unsupported"] >= 1
    q = doctor.propose(scene)[0]
    preview = doctor.preview(fig, q, condition="grayscale")
    assert not preview.huevat_doctor_preview["complete_simulation"]
    change = doctor.apply(fig, q)
    after = (band.get_facecolors(), image.get_array(), image.norm.vmin, image.norm.vmax,
             image.cmap.name, rect.get_facecolor(), cb.ax.get_ylabel())
    for a, b in zip(before, after): assert np.array_equal(a, b)
    assert not change.report["coverage"]["complete"]
    change.undo()


@research
def test_mixed_backgrounds_are_audited_independently():
    fig, axes = mpl_figure(); axes[1].set_facecolor("#121212")
    report = doctor.propose(doctor.inspect(fig))[0].report
    assert len(report["panels"]) == 2
    for panel in report["panels"]:
        assert panel["background"] in ([1., 1., 1.], [18/255]*3) or tuple(panel["background"]) in ((1., 1., 1.), (18/255,)*3)
    # One shared identity cannot be claimed good on both backgrounds merely by
    # looking up the prepared light-background report.
    assert all(g["threshold"] == 3 for g in report["criteria"] if g["name"] == "background_contrast")


@research
def test_serialization_rejects_tampering_and_apply_reaudits_evidence():
    fig, _ = mpl_figure(); scene = doctor.inspect(fig)
    q = doctor.propose(scene, locked={k: {"color": "#4379a3"} for k in scene.categories})[0]
    envelope = json.loads(q.to_json()); envelope["proposal"]["report"]["color_screen_pass"] = True
    with pytest.raises(ValueError, match="hash"): doctor.load_proposal(envelope)
    envelope["sha256"] = fingerprint(envelope["proposal"])
    forged = doctor.load_proposal(envelope)
    assert not doctor.apply(fig, forged).report["color_screen_pass"]


@research
def test_stale_data_styles_layout_and_undo_guard():
    fig, axes = mpl_figure(); q = doctor.propose(doctor.inspect(fig))[0]
    axes[0].lines[0].set_ydata([0, 0, 0])
    with pytest.raises(ValueError, match="Stale"): doctor.apply(fig, q)
    q = doctor.propose(doctor.inspect(fig))[0]
    axes[1].set_ylabel("new units")
    with pytest.raises(ValueError, match="Stale"): doctor.preview(fig, q)
    change = doctor.apply(fig, doctor.propose(doctor.inspect(fig))[0])
    axes[0].lines[0].set_color("black")
    with pytest.raises(ValueError, match="newer styles"): change.undo()


@research
def test_failed_native_mutation_rolls_back(monkeypatch):
    from huevat.doctor import _backends
    fig, _ = mpl_figure(); scene = doctor.inspect(fig); q = doctor.propose(scene)[0]
    original = _backends.mutate
    def failing(target, *args):
        original(target, *args)
        if target is fig: raise RuntimeError("injected native setter failure")
    monkeypatch.setattr(_backends, "mutate", failing)
    with pytest.raises(RuntimeError, match="injected"): doctor.apply(fig, q)
    assert doctor.inspect(fig).fingerprint == scene.fingerprint


@research
def test_log_axes_and_unsupported_transforms_and_variable_scatter():
    fig, axes = mpl_figure()
    axes[0].set_xscale("log"); axes[0].set_xlim(.1, 2)
    axes[0].axhline(.5, color="black")
    axes[1].scatter([0, 1], [.2, .8], c=[0, 1], label="scalar field")
    scene = doctor.inspect(fig)
    assert scene.axes[0]["xscale"] == "log"
    assert any("transform" in item["reason"] for item in scene.to_dict()["unsupported"])
    assert any("scalar" in item["reason"] for item in scene.to_dict()["read_only"])
    doctor.propose(scene)


@research
def test_ultraplot_native_workflow():
    uplt = pytest.importorskip("ultraplot")
    fig, axes = uplt.subplots(ncols=2, share=False)
    for ax in axes:
        ax.plot([0, 1], [0, 1], color="red", label="A")
        ax.plot([0, 1], [1, 0], color="red", label="B")
    scene = doctor.inspect(fig)
    assert scene.to_dict()["backend"] == "ultraplot" and len(scene.marks) == 4
    q = doctor.propose(scene)[0]
    copied = doctor.preview(fig, q)
    assert type(copied) is type(fig)
    change = doctor.apply(fig, q); change.undo()
    assert doctor.inspect(fig).fingerprint == scene.fingerprint


def plotly_figure():
    go = pytest.importorskip("plotly.graph_objects")
    fig = go.Figure([go.Scatter(x=[0., .5, 1.], y=y, name=k, mode="lines", line_color="red")
                     for k, y in (("B", [1., .3, 0.]), ("A", [0., .7, 1.]))])
    fig.update_layout(template="plotly_white", xaxis_title="Distance (km)", yaxis_title="Displacement (mm)")
    return fig


@research
def test_plotly_workflow_preserves_native_data_and_json():
    fig = plotly_figure(); original = fig.to_json(); scene = doctor.inspect(fig)
    assert scene.to_dict()["backend"] == "plotly" and scene.categories == ("A", "B")
    q = doctor.propose(scene)[0]
    preview = doctor.preview(fig, q, condition="grayscale")
    assert preview.layout.meta["huevat_doctor_preview"]["condition"] == "grayscale"
    assert preview.to_json() and fig.to_json() == original
    change = doctor.apply(fig, q)
    assert change.report["color_screen_pass"]
    assert list(fig.data[0].y) == [1., .3, 0.]
    assert fig.layout.yaxis.title.text == "Displacement (mm)"
    change.undo(); assert fig.to_json() == original


@research
def test_plotly_defaults_unresolved_colors_fills_and_opacity():
    go = pytest.importorskip("plotly.graph_objects")
    fig = plotly_figure()
    fig.data[0].line.color = "rgba(255,0,0,0.4)"; fig.data[0].opacity = .5
    fig.add_trace(go.Scatter(x=[0, 1], y=[.2, .3], mode="lines", fill="tozeroy", line_color="blue", name="band"))
    fig.add_trace(go.Scatter(x=[0, 1], y=[.2, .3], name="unresolved"))
    scene = doctor.inspect(fig)
    assert scene.coverage["unsupported"] == 2 and not scene.coverage["complete"]
    assert scene.marks[0]["channels"][0]["alpha"] == pytest.approx(.2)
    q = doctor.propose(scene)[0]; before = fig.data[2].to_plotly_json()
    change = doctor.apply(fig, q)
    assert change.after.marks[0]["channels"][0]["alpha"] == pytest.approx(.2)
    assert fig.data[2].to_plotly_json() == before
    change.undo(); assert doctor.inspect(fig).fingerprint == scene.fingerprint


@research
def test_plotly_unsupported_heatmap_is_untouched_by_apply_and_undo():
    go = pytest.importorskip("plotly.graph_objects")
    fig = plotly_figure()
    fig.add_trace(go.Heatmap(z=[[0, 1], [2, 3]], zmin=0, zmax=3, colorbar_title="Temperature (K)"))
    original = fig.to_json()
    scene = doctor.inspect(fig)
    assert scene.coverage["unsupported"] == 1
    change = doctor.apply(fig, doctor.propose(scene)[0])
    change.undo()
    assert fig.to_json() == original


@research
def test_errorbar_artists_are_read_only_and_no_implicit_children_repairs():
    fig, axes = mpl_figure()
    axes[0].errorbar([0, 1], [.2, .8], yerr=.1, color="black", label="uncertain", capsize=4)
    scene = doctor.inspect(fig)
    assert scene.categories == ("A", "B")
    assert any("container semantics" in item["reason"] for item in scene.to_dict()["unsupported"])
    original = [line.get_color() for line in axes[0].lines[2:]]
    doctor.apply(fig, doctor.propose(scene)[0])
    assert [line.get_color() for line in axes[0].lines[2:]] == original


@research
def test_single_panel_color_screens_match_frozen_h1_evaluator():
    import huevat as hv
    from huevat.evaluation import evaluate
    import matplotlib.pyplot as plt
    for bg, actual in (("light", "#ffffff"), ("dark", "#121212")):
        colors = hv.categorical(5, background=bg)
        fig, ax = plt.subplots(); ax.set_facecolor(actual)
        for i, color in enumerate(colors): ax.plot([0, 1], [i, i+.5], label=str(i), color=color)
        report = doctor.diagnose(doctor.inspect(fig))
        for encoding in ("float", "u8"):
            expected = evaluate(colors.rgb, "categorical", context="data-marks", background=bg, encoding=encoding)
            actual_gates = [g for g in report["criteria"] if g["encoding"] == encoding]
            for gate in actual_gates:
                source = next(g for g in expected["criteria"] if g["name"] == gate["name"] and g["condition"] == gate["condition"])
                assert gate["measured"] == pytest.approx(source["measured"], abs=1e-10)
                assert gate["passed"] == source["passed"]


@research
def test_invalid_conditions_locks_and_unsupported_empty_scene():
    fig, _ = mpl_figure(); scene = doctor.inspect(fig)
    q = doctor.propose(scene)[0]
    with pytest.raises(ValueError, match="condition"): doctor.preview(fig, q, condition="invented")
    with pytest.raises(ValueError, match="remove"): doctor.propose(scene, locked={"A": {"dash": "none"}})
    import matplotlib.pyplot as plt
    empty, _ = plt.subplots()
    with pytest.raises(ValueError, match="No supported"): doctor.propose(doctor.inspect(empty))


@research
def test_inset_and_unresolved_plotly_background_have_explicit_coverage():
    fig, axes = mpl_figure(); inset = axes[0].inset_axes([.2, .2, .3, .3]); inset.plot([0, 1], [0, 1])
    assert not doctor.inspect(fig).coverage["complete"]
    fig = plotly_figure(); fig.layout.plot_bgcolor = 'aliceblue'
    scene = doctor.inspect(fig)
    assert not scene.marks and scene.coverage["unsupported"] == 1
    with pytest.raises(ValueError, match="No supported"): doctor.propose(scene)
    with pytest.raises(ValueError, match="Background unresolved"): doctor.preview(fig, condition='grayscale')


@research
def test_simulation_retains_transparent_hollow_marker_face():
    fig, axes = mpl_figure()
    axes[0].lines[0].set_marker('o'); axes[0].lines[0].set_markerfacecolor((1, 0, 0, 0))
    copy = doctor.preview(fig, condition='grayscale')
    from matplotlib.colors import to_rgba
    assert to_rgba(copy.axes[0].lines[0].get_markerfacecolor())[3] == 0


@research
def test_plotly_per_trace_type_template_inheritance_and_native_axes_arrays():
    import numpy as np
    go = pytest.importorskip('plotly.graph_objects')
    template = go.layout.Template(data={'scatter': [go.Scatter(mode='lines', line_color='#4379a3'),
                                                   go.Scatter(mode='lines', line_color='#bd6c60')]})
    fig = go.Figure([go.Bar(x=[0, 1], y=[0, 1]), go.Scatter(x=[0, 1], y=[0, 1], name='A'),
                     go.Scatter(x=[0, 1], y=[1, 0], name='B')])
    fig.update_layout(template=template, xaxis_tickvals=np.array([0, 1]))
    scene = doctor.inspect(fig)
    assert len(scene.marks) == 2
    from huevat.space import to_hex
    assert [to_hex(m['channels'][0]['rgb']) for m in scene.marks] == ['#4379a3', '#bd6c60']
    original = fig.to_json()
    change = doctor.apply(fig, doctor.propose(scene)[0]); change.undo()
    assert fig.to_json() == original
