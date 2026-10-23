"""Explicit, optional figure inspection and repair. Importing uses only stdlib.

Inspection needs the figure's plotting backend; numerical diagnosis/proposals
also need ``huevat[design]``. Nothing registers styles or changes a figure at
import. See docs/METHODS_H4C.md for the deliberately conservative coverage.
"""
from copy import deepcopy
from dataclasses import dataclass, field
import json
from collections.abc import Mapping

from ..gradients import _freeze, _thaw, fingerprint

VERSION = "h4c-doctor-v1"
MARKERS = ("circle", "square", "triangle", "diamond", "cross", "triangle-down", "none")
DASHES = ("solid", "dash", "dot", "dashdot", "none")


@dataclass(frozen=True)
class Scene:
    """Immutable backend-neutral description; contains no artist references."""
    _data: Mapping

    def __post_init__(self):
        object.__setattr__(self, "_data", _freeze(deepcopy(_thaw(self._data))))

    @property
    def marks(self): return self._data["marks"]
    @property
    def axes(self): return self._data["axes"]
    @property
    def coverage(self): return self._data["coverage"]
    @property
    def fingerprint(self): return fingerprint(self.to_dict())
    @property
    def categories(self): return tuple(sorted({m["category"] for m in self.marks}))
    def to_dict(self): return _thaw(self._data)


@dataclass(frozen=True)
class Proposal:
    _data: Mapping

    def __post_init__(self):
        data = deepcopy(_thaw(self._data))
        _validate(data)
        object.__setattr__(self, "_data", _freeze(data))

    @property
    def assignments(self): return self._data["assignments"]
    @property
    def report(self): return self._data["report"]
    @property
    def name(self): return self._data["name"]
    def to_dict(self): return _thaw(self._data)
    def to_json(self):
        body = self.to_dict()
        return json.dumps({"proposal": body, "sha256": fingerprint(body)}, sort_keys=True,
                          indent=2, allow_nan=False)


def _styles(assignments):
    from ..space import from_hex
    if not isinstance(assignments, Mapping): raise ValueError("Assignments must be a category mapping")
    for category, style in assignments.items():
        if not isinstance(category, str) or not category or not isinstance(style, Mapping):
            raise ValueError("Expected nonempty category names and style mappings")
        if set(style) != {"color", "marker", "dash"}: raise ValueError("A style needs color, marker and dash")
        from_hex(style["color"])
        if style["marker"] not in MARKERS or style["dash"] not in DASHES:
            raise ValueError("Unknown portable marker or dash")


def _validate(data):
    if set(data) != {"version", "scene_sha256", "name", "assignments", "report"} or data["version"] != VERSION:
        raise ValueError("Unknown figure-doctor proposal schema/version")
    digest = data["scene_sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Invalid scene fingerprint")
    if data["name"] not in ("closer", "separation", "simple"): raise ValueError("Unknown tradeoff")
    _styles(data["assignments"])
    if not isinstance(data["report"], dict): raise ValueError("Expected a report mapping")
    # Reject non-JSON/non-finite content, including in untrusted evidence.
    fingerprint(data)


def load_proposal(value):
    """Read hashed data. Saved reports are historical; apply recomputes them."""
    data = json.loads(value) if isinstance(value, str) else deepcopy(value)
    if not isinstance(data, dict) or set(data) != {"proposal", "sha256"}:
        raise ValueError("Expected a hashed proposal envelope")
    if fingerprint(data["proposal"]) != data["sha256"]: raise ValueError("Proposal hash mismatch")
    return Proposal(data["proposal"])


def inspect(figure):
    """Inspect a private copy, including lazy backend state, without drawing."""
    from ._backends import extract, clone
    return Scene(extract(clone(figure)))


def diagnose(scene):
    """Audit actual composited mark colors; never certify human readability."""
    from ._audit import audit
    if not isinstance(scene, Scene): raise TypeError("Expected doctor.inspect(figure)")
    return _freeze(audit(scene.to_dict()))


def propose(scene, *, locked=None, assignments=None):
    """Return three audited tradeoffs. Retain assignments to reserve absent labels.

    ``locked={'label': {'color': '#4379a3'}}`` fixes any supplied style fields.
    ``assignments=previous.assignments`` fixes complete earlier identities.
    A failing proposal remains available for explicit visual review; its report
    retains color-only failures and never asserts a multichannel screen pass.
    """
    from ._search import negotiate
    if not isinstance(scene, Scene): raise TypeError("Expected doctor.inspect(figure)")
    return tuple(Proposal(item) for item in negotiate(scene, locked, assignments))


def _prepare(figure, proposal):
    from ._backends import mutate, clone
    if not isinstance(proposal, Proposal): raise TypeError("Expected a Proposal")
    scene = inspect(figure)
    if scene.fingerprint != proposal._data["scene_sha256"]:
        raise ValueError("Stale proposal: figure data, styles or modeled layout changed; inspect again")
    if not set(scene.categories) <= set(proposal.assignments): raise ValueError("Missing category assignments")
    copied = clone(figure)
    mutate(copied, scene.to_dict(), _thaw(proposal.assignments))
    # Re-extraction verifies native rendering properties rather than trusting
    # the saved report or just substituting hypothetical RGB into a scene.
    after = inspect(copied)
    report = diagnose(after)
    return copied, scene, after, report


def preview(figure, proposal=None, *, condition="normal"):
    """Return a native independent figure, with explicit simulation coverage.

    ``huevat_doctor_preview`` describes partial simulation when unsupported
    content exists. Original figures and their scalar fields are untouched.
    """
    from ._backends import simulate_copy, clone
    if proposal is None:
        copied = clone(figure)
        after = inspect(copied)
        report = diagnose(after)
    else:
        copied, before, after, report = _prepare(figure, proposal)
    return simulate_copy(copied, after.to_dict(), condition, report)


@dataclass
class Change:
    """Before/after evidence and a single-use, stale-guarded undo operation."""
    before: Scene
    after: Scene
    report: Mapping
    _figure: object = field(repr=False)
    _restore: object = field(repr=False)
    _undone: bool = field(default=False, repr=False)

    def undo(self):
        if self._undone: raise ValueError("This change was already undone")
        if inspect(self._figure).fingerprint != self.after.fingerprint:
            raise ValueError("Figure changed after apply; undo would overwrite newer styles")
        self._restore()
        self._undone = True
        return self.before


def apply(figure, proposal):
    """Explicit transactional style edit. Returns a guarded undo handle.

    Failed color-only proposals require visual judgment; applying them does not
    promote their status. All setters are rehearsed on a copy before mutation.
    """
    from ._backends import mutate, snapshot
    _, before, _, _ = _prepare(figure, proposal)
    restore = snapshot(figure, before.to_dict())
    try:
        mutate(figure, before.to_dict(), _thaw(proposal.assignments))
        after = inspect(figure)
        report = diagnose(after)
    except Exception:
        restore()
        raise
    return Change(before, after, report, figure, restore)


__all__ = ["inspect", "diagnose", "propose", "preview", "apply", "load_proposal",
           "Scene", "Proposal", "Change"]
