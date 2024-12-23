from __future__ import annotations


TYPE_CHECKING = False

if TYPE_CHECKING:
    from types import GenericAlias
else:
    GenericAlias = type(list[int])


__all__ = ("TYPE_CHECKING", "Any", "Optional", "Self", "TypeAlias", "Union", "cast")


class _PlaceholderGenericAlias(GenericAlias):
    def __repr__(self):
        return f"<import placeholder for {super().__repr__()}>"


class _PlaceholderMeta(type):
    def __init__(self, *args: object, **kwargs: object):
        super().__init__(*args, **kwargs)
        self.__doc__ = f"Placeholder for {self.__module__}.{self.__name__}."

    def __repr__(self):
        return f"<import placeholder for {super().__repr__()}>"


class _PlaceholderGenericMeta(_PlaceholderMeta):
    def __getitem__(self, item: object) -> _PlaceholderGenericAlias:
        return _PlaceholderGenericAlias(self, item)


if TYPE_CHECKING:
    from typing import Any, Optional, Union, cast

    from typing_extensions import Self, TypeAlias
else:

    def cast(typ: Any, val: Any) -> Any:
        return val

    class Any(metaclass=_PlaceholderMeta):
        __module__ = "typing"

    class Optional(metaclass=_PlaceholderGenericMeta):
        __module__ = "typing"

    class Union(metaclass=_PlaceholderGenericMeta):
        __module__ = "typing"

    class Self(metaclass=_PlaceholderMeta):
        __module__ = "typing"

    class TypeAlias(metaclass=_PlaceholderMeta):
        __module__ = "typing"
