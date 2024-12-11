from __future__ import annotations


TYPE_CHECKING = False

if TYPE_CHECKING:
    from types import GenericAlias
else:
    GenericAlias = type(list[int])

__all__ = ("TYPE_CHECKING", "Any", "Optional", "Self", "TypeAlias", "Union", "cast")


class _PlaceholderGenericAlias(GenericAlias):
    def __repr__(self) -> str:
        name = f'typing.{super().__repr__().rpartition(".")[2]}'
        return f"<import placeholder for {name}>"


class _PlaceholderMeta(type):
    def __repr__(self) -> str:
        return f"<import placeholder for typing.{self.__name__}>"

    @classmethod
    def for_typing_name(cls, name: str):  # noqa: ANN206 # pyright doesn't allow Self in metaclasses.
        return cls(name, (), {"__doc__": f"Placeholder for typing.{name}."})


class _PlaceholderGenericMeta(_PlaceholderMeta):
    def __getitem__(self, item: object) -> _PlaceholderGenericAlias:
        return _PlaceholderGenericAlias(self, item)


if TYPE_CHECKING:
    from typing import Any, Optional, Union, cast

    from typing_extensions import Self, TypeAlias
else:
    Any = _PlaceholderMeta.for_typing_name("Any")
    Optional = _PlaceholderGenericMeta.for_typing_name("Optional")
    Union = _PlaceholderGenericMeta.for_typing_name("Union")

    Self = _PlaceholderMeta.for_typing_name("Self")
    TypeAlias = _PlaceholderMeta.for_typing_name("TypeAlias")

    def cast(typ: Any, val: Any) -> Any:
        return val
