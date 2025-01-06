"""Compatibility shim for typing- and annotation-related symbols, to avoid accidentally importing from typing or
having a dependency on typing-extensions.
"""

from __future__ import annotations

import sys


TYPE_CHECKING = False

if TYPE_CHECKING:
    from types import GenericAlias
else:
    GenericAlias = type(list[int])


__all__ = (
    "Any",
    "ClassVar",
    "Literal",
    "Optional",
    "Self",
    "TypeAlias",
    "Union",
    "cast",
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


class _PlaceholderGenericMeta(_PlaceholderMeta):
    def __getitem__(self, item: object) -> _PlaceholderGenericAlias:
        return _PlaceholderGenericAlias(self, item)


if TYPE_CHECKING:
    from typing import cast
else:

    def cast(typ: object, val: object) -> object:
        return val


if TYPE_CHECKING:
    from typing_extensions import TypeAlias
elif sys.version_info < (3, 10):

    class TypeAlias(metaclass=_PlaceholderMeta):
        _source_module = "typing"


if TYPE_CHECKING:
    from typing_extensions import Self
elif sys.version_info < (3, 11):

    class Self(metaclass=_PlaceholderMeta):
        _source_module = "typing"


def __getattr__(name: str, /) -> object:
    global Any, ClassVar, Literal, Optional, Union  # noqa: PLW0603

    if name in {"Any", "ClassVar", "Literal", "Optional", "Union"}:
        from typing import Any, ClassVar, Literal, Optional, Union

        return globals()[name]

    if name == "TypeAlias" and sys.version_info >= (3, 10):
        from typing import TypeAlias

        globals()[name] = TypeAlias
        return globals()[name]

    if name == "Self" and sys.version_info >= (3, 11):
        from typing import TypeAlias

        globals()[name] = TypeAlias
        return globals()[name]

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return sorted(set(globals()).union(__all__))
