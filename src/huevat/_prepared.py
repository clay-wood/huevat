"""Reusable immutable runtime views, leaving frozen numerical engines intact."""
from functools import cached_property, lru_cache, wraps
from inspect import signature
from dataclasses import dataclass

from .gradients import Gradient, Palette, QualityReport
from .families import HueGradient, proxy_recipe


def _view(source, cls, *, reverse=None, recipe=None):
    # Only reuse structures already frozen by the original constructors. Never
    # accept arbitrary MappingProxyType inputs as proof of deep immutability.
    result = object.__new__(cls)
    for name, value in (("_recipe", source._recipe if recipe is None else recipe),
                        ("_report", source._report), ("_discrete_records", source._discrete_records),
                        ("_reverse", source._reverse if reverse is None else reverse)):
        object.__setattr__(result, name, value)
    return result


@dataclass(frozen=True, repr=False, eq=False)
class _Gradient(Gradient):
    def reversed(self): return _view(self, _Gradient, reverse=not self._reverse)

    @cached_property
    def report(self): return Gradient.report.fget(self)


@dataclass(frozen=True, repr=False, eq=False)
class _HueGradient(HueGradient):
    def reversed(self): return _view(self, _HueGradient, reverse=not self._reverse)

    @cached_property
    def report(self): return HueGradient.report.fget(self)

    @cached_property
    def _proxy(self):
        from .gradients import _freeze
        return _view(self, _Gradient, recipe=_freeze(proxy_recipe(self._recipe)))

    def discrete(self, n, *, context=None):
        palette = self._proxy.discrete(n, context=context)
        report = palette.report.to_dict()
        report.update(family=self.family, algorithm_version="h3-discrete-v1")
        return Palette(palette.colors, QualityReport(report))


def view(source):
    if type(source) is HueGradient: return _view(source, _HueGradient)
    if type(source) is Gradient: return _view(source, _Gradient)
    return source


@lru_cache(maxsize=64)
def _lookup(factory, typed_arguments):
    return view(factory(**{name:value for name,kind,value in typed_arguments}))


def prepared(factory):
    """Cache only prepared requests; custom searches still execute explicitly.

    Preserve argument types in the key so bool/int/float equality cannot bypass
    the original input validation. Unhashable preferences use the old path.
    """
    sig = signature(factory)
    defaults = {name:p.default for name,p in sig.parameters.items() if p.default is not p.empty}

    @wraps(factory)
    def call(*args, **kwargs):
        bound = sig.bind(*args, **kwargs); bound.apply_defaults()
        values = bound.arguments
        standard = values.get("background") in ("light", "dark")
        for name, default in defaults.items():
            if name in ("background", "style"): continue
            standard &= values[name] == default
        if "n" in values:
            n = values["n"]
            standard &= type(n) is int and 2 <= n <= 12
        if standard:
            key = tuple((name,type(value),value) for name,value in values.items())
            try: hash(key)
            except TypeError: pass
            else: return _lookup(factory, key)
        return view(factory(*args, **kwargs))
    return call


def loader(original):
    @wraps(original)
    def load(*args, **kwargs): return view(original(*args, **kwargs))
    return load
