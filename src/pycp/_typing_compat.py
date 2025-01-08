"""Shim for typing- and annotation-related symbols to avoid runtime dependencies on `typing` or `typing-extensions`.

A warning for annotation-related symbols: Do not directly import them from this module
(e.g. `from ._typing_compat import Any`)! Doing so will trigger the module-level `__getattr__`, causing `typing` to
get imported. Instead, import the module and use symbols via attribute access as needed
(e.g. `from . import _typing_compat [as _t]`). To avoid those symbols being evaluated at runtime, which would also cause
`typing` to get imported, make sure to put `from __future__ import annotations` at the top of the module.
"""

from __future__ import annotations

import sys


TYPE_CHECKING = False

if TYPE_CHECKING:
    from types import GenericAlias
else:
    GenericAlias = type(list[int])


__all__ = (
    # Used at runtime
    "cast",
    # Somewhat version-dependent
    "Self",
    "TypeAlias",
    # Everything else
    "Any",
    "ClassVar",
    "Literal",
    "Optional",
    "Union",
)


class _PlaceholderGenericAlias(GenericAlias):
    def __repr__(self):
        return f"<import placeholder for {super().__repr__()}>"


class _PlaceholderMeta(type):
    _source_module: str

    def __init__(self, *args: object, **kwargs: object):
        super().__init__(*args, **kwargs)
        self.__doc__ = f"Placeholder for {self._source_module}.{self.__name__}."

    def __repr__(self):
        return f"<import placeholder for {self._source_module}.{self.__name__}>"


class _PlaceholderGenericMeta(_PlaceholderMeta):  # pyright: ignore [reportUnusedClass] # Might be used yet.
    def __getitem__(self, item: object) -> _PlaceholderGenericAlias:
        return _PlaceholderGenericAlias(self, item)


# cast is used at runtime, so there's no point importing it on demand from the right place.
if TYPE_CHECKING:
    from typing import cast
else:

    def cast(typ: object, val: object) -> object:
        return val


# TypeAlias: Below 3.10, create a placeholder. For 3.10 and above, import on demand in __getattr__.
if TYPE_CHECKING:
    from typing_extensions import TypeAlias
elif sys.version_info < (3, 10):

    class TypeAlias(metaclass=_PlaceholderMeta):
        _source_module = "typing"


# Self: Below 3.11, create a placeholder. For 3.11 and above, import on demand in __getattr__.
if TYPE_CHECKING:
    from typing_extensions import Self
elif sys.version_info < (3, 11):

    class Self(metaclass=_PlaceholderMeta):
        _source_module = "typing"


def __getattr__(name: str, /) -> object:
    # Save the imported symbols in the globals to avoid future imports.

    global Any, ClassVar, Literal, Optional, Union  # noqa: PLW0603

    if name in {"Any", "ClassVar", "Literal", "Optional", "Union"}:
        from typing import Any, ClassVar, Literal, Optional, Union

        return globals()[name]

    if (
        (name == "TypeAlias" and sys.version_info >= (3, 10))
        or (name == "Self" and sys.version_info >= (3, 11))
    ):  # fmt: skip
        import typing

        symbol = getattr(typing, name)
        globals()[name] = symbol

        return symbol

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return sorted(set(globals()).union(__all__))
