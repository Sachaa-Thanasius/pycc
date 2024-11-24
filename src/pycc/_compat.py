from __future__ import annotations

import sys
from typing import TYPE_CHECKING


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


__all__ = ("TypeAlias",)


if sys.version_info >= (3, 10):
    from typing import TypeAlias
elif TYPE_CHECKING:
    from typing_extensions import TypeAlias
else:
    TypeAlias = _PlaceholderMeta.from_typing_name("TypeAlias")
