from __future__ import annotations


__all__ = ("TYPE_CHECKING", "Any", "Self", "TypeAlias", "Union", "cast")

TYPE_CHECKING = False


class _PlaceholderGenericAlias(type(list[int])):
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
        return _PlaceholderGenericAlias(self, item)  # pyright: ignore [reportCallIssue]


if TYPE_CHECKING:
    from typing import Any, Union, cast

    from typing_extensions import Self, TypeAlias
else:
    Any = _PlaceholderMeta.for_typing_name("Any")
    Self = _PlaceholderMeta.for_typing_name("Self")
    TypeAlias = _PlaceholderMeta.for_typing_name("TypeAlias")
    Union = _PlaceholderGenericMeta.for_typing_name("Union")

    def cast(typ: Any, val: Any) -> Any:
        return val
