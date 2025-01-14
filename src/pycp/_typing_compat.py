"""Shim for typing- and annotation-related symbols to avoid runtime dependencies on `typing` or `typing-extensions`.

Warning: Do not directly import annotation-related symbols from this module (e.g. `from ._typing_compat import Any`)!
Doing so will trigger the module-level `__getattr__`, causing `typing` to get imported. Instead, import the module and
use symbols via attribute access as needed (e.g. `from . import _typing_compat [as _t]`). To avoid those symbols being
evaluated at runtime, which would also cause `typing` to get imported, make sure to put
`from __future__ import annotations` at the top of the module.
"""

from __future__ import annotations

import sys


TYPE_CHECKING = False


class _PlaceholderMeta(type):
    _source_module: str

    def __init__(self, *args: object, **kwargs: object):
        super().__init__(*args, **kwargs)
        self.__doc__ = f"Placeholder for {self._source_module}.{self.__name__}."

    def __repr__(self):
        return f"<import placeholder for {self._source_module}.{self.__name__}>"


__all__ = (
    # Annotation symbols.
    "Any",
    "ClassVar",
    "Literal",
    "Optional",
    "Union",
    # Annotation symbols with version-dependent handling.
    "Self",
    "TypeAlias",
    # Used at runtime.
    "cast",
)


def __getattr__(name: str, /) -> object:
    # Save the imported symbols in the globals to avoid future imports.

    if name in {"Any", "ClassVar", "Literal", "Optional", "Union"}:
        global Any, ClassVar, Literal, Optional, Union  # noqa: PLW0603

        from typing import Any, ClassVar, Literal, Optional, Union

        return globals()[name]

    if (
        (name == "TypeAlias" and sys.version_info >= (3, 10))
        or (name == "Self" and sys.version_info >= (3, 11))
    ):  # fmt: skip
        import typing

        globals()[name] = symbol = getattr(typing, name)

        return symbol

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return sorted(set(globals()).union(__all__))


# TypeAlias: For 3.10+, import on demand in __getattr__. Otherwise, create a placeholder.
if TYPE_CHECKING:
    from typing_extensions import TypeAlias
elif sys.version_info < (3, 10):

    class TypeAlias(metaclass=_PlaceholderMeta):
        _source_module = "typing"


# Self: For 3.11+, import on demand in __getattr__. Otherwise, create a placeholder.
if TYPE_CHECKING:
    from typing_extensions import Self
elif sys.version_info < (3, 11):

    class Self(metaclass=_PlaceholderMeta):
        _source_module = "typing"


# cast: Used at runtime.
if TYPE_CHECKING:
    from typing import cast
else:

    def cast(typ: object, val: object) -> object:
        return val
