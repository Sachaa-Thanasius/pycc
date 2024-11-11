__all__ = ("TYPE_CHECKING", "MappingProxyType", "Any", "TypeAlias", "cast")

TYPE_CHECKING = False

if TYPE_CHECKING:
    from types import MappingProxyType
    from typing import Any, TypeAlias, cast
else:
    MappingProxyType = type(type.__dict__)
    Any = object

    class TypeAlias:
        """Placeholder for typing.TypeAlias."""

    def cast(typ, val):  # noqa: ANN001, ANN202
        return val
