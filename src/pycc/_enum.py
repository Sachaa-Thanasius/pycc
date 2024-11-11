# region -------- License --------
#
# Copyright 2024 Sachaa-Thanasius
# Copyright 2022 Brett Cannon
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# endregion

"""An API-compatible re-implementation of ``enum.Enum`` and related code."""

from __future__ import annotations

import collections.abc

from ._typing_compat import TYPE_CHECKING, Any, MappingProxyType, TypeAlias, cast


__all__ = ("Enum", "auto", "unique")


# Copied from enum in typeshed.
_EnumNames: TypeAlias = (
    str
    | collections.abc.Iterable[str]
    | collections.abc.Iterable[collections.abc.Iterable[str | Any]]
    | collections.abc.Mapping[str, Any]
)

_AUTO = object()


class _EnumMember:
    """Representation of an enum member."""

    # The class overall tries to preserve object identity for fast object comparison.

    _cls: EnumMeta

    def __init__(self, name: str, value: Any) -> None:
        self._name_ = name
        self._value_ = value

    @property
    def name(self) -> str:
        return self._name_

    @property
    def value(self) -> Any:
        return self._value_

    def __str__(self):
        return f"{self._cls.__name__}.{self._name_}"

    def __repr__(self):
        return f"<{self._cls.__name__}.{self._name_}: {self._value_!r}>"

    def __hash__(self):
        """Hash the name of the member.

        This matches the semantics of the ``enum`` module from the stdlib.
        """

        return hash(self._name_)

    # Could also use __getnewargs(_ex)__, but this was the simplest solution.
    def __reduce__(self):
        """Pickle by specifying the containing class and name of the member.

        Unpickling retains object identity.
        """

        return getattr, (self._cls, self._name_)


def _is_descriptor(obj: object) -> bool:
    return hasattr(obj, "__get__") or hasattr(obj, "__set__") or hasattr(obj, "__delete__")


def _set_names(
    ns: collections.abc.MutableMapping[str, Any],
    qualname: str | None,
    module: str | None,
    name: str,
) -> None:
    """Set various names in the namespace."""

    if qualname is not None:
        ns["__qualname__"] = qualname
    elif module is not None:
        ns["__qualname__"] = f"{module}.{name}"
    else:
        ns["__qualname__"] = name
    ns["__module__"] = module or None


class EnumMeta(type):
    """An API-compatible re-implementation of ``enum.EnumMeta``."""

    if TYPE_CHECKING:
        _member_map_: dict[str, _EnumMember]
        _value2member_map_: dict[Any, _EnumMember]
        _member_names_: list[str]

    def __new__(cls, name: str, bases: tuple[type, ...], namespace: dict[str, Any]):
        """Convert class attributes to enum members."""

        member_map: dict[str, _EnumMember] = {}
        value_map: dict[Any, _EnumMember] = {}
        member_names: list[str] = []
        last_auto = 0

        if (custom_auto := namespace.get("_generate_next_value_")) is None:
            for base in bases:
                if hasattr(base, "_generate_next_value_"):
                    custom_auto = base._generate_next_value_  # pyright: ignore
                    break

        # The rules in `enum` are much stricter for what gets skipped.
        # Need to do this upfront so enumerate() returns what's expected for _generate_next_value_().
        members_iter = (
            (name, value) for name, value in namespace.items() if not _is_descriptor(value) and not name.startswith("_")
        )
        for index, (mem_name, mem_value) in enumerate(members_iter):
            if mem_value is _AUTO:
                if custom_auto is None:
                    last_auto += 1
                    mem_value = last_auto  # noqa: PLW2901
                else:
                    mem_value = custom_auto(  # noqa: PLW2901 # pyright: ignore [reportUnknownVariableType]
                        mem_name,
                        1,  # No way to specify a different starting value.
                        index,
                        [member._value_ for member in member_map.values()],
                    )
            elif isinstance(mem_value, int):
                last_auto = mem_value

            try:
                member = value_map[mem_value]
            except KeyError:
                member = value_map[mem_value] = _EnumMember(mem_name, mem_value)
                member_names.append(mem_name)

            member_map[mem_name] = member
            namespace[mem_name] = member

        namespace["_member_map_"] = member_map
        namespace["_value2member_map_"] = value_map
        namespace["_member_names_"] = member_names

        return super().__new__(cls, name, bases, namespace)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        for mem_value in self._member_map_.values():
            mem_value._cls = self

    @property
    def __members__(self) -> MappingProxyType[str, Any]:
        return MappingProxyType(self._member_map_)

    def __repr__(self):
        return f"<enum {self.__name__!r}>"

    def __call__(self, value: Any, /):
        """Search members by value."""

        try:
            return self._value2member_map_[value]
        except KeyError:
            msg = f"no enum member with a value of {value!r}"
            raise ValueError(msg) from None

    def __getitem__(self, name: str, /):
        """Search by member name."""

        return self._member_map_[name]

    def __contains__(self, value: object, /) -> bool:
        """Check if the argument is a member or value of the enum."""

        return self.__instancecheck__(value) or any(member._value_ == value for member in self)

    def __iter__(self):
        """Iterate through the members."""

        return iter(self._member_map_[name] for name in self._member_names_)

    def __reversed__(self):
        return iter(self._member_map_[name] for name in reversed(self._member_names_))

    def __len__(self) -> int:
        return len(self._member_names_)

    def __setattr__(self, name: str, value: Any, /) -> None:
        if name in self._member_map_:
            msg = f"Cannot reassign member {name!r}."
            raise AttributeError(msg)

        return super().__setattr__(name, value)

    def __delattr__(self, name: str, /) -> None:
        if name in self._member_map_:
            msg = f"{self.__name__!r} cannot delete member {name!r}."
            raise AttributeError(msg)

        return super().__delattr__(name)

    def __instancecheck__(self, instance: object, /) -> bool:
        """Check if a member belongs to the enum."""

        return getattr(instance, "_cls", None) is self

    def _create_(  # noqa: ANN202, PLR0913
        self,
        enum_name: str,
        member_names: _EnumNames,
        /,
        *,
        module: str | None = None,
        qualname: str | None = None,
        type: type | None = None,
        start: int = 1,
    ):
        """Create an enum using the equivalent functional API for ``enum.Enum``."""

        ns: dict[str, Any]

        if isinstance(member_names, str):
            ns = {name: index for index, name in enumerate(member_names.replace(",", " ").split(), start=start)}

        elif not isinstance(member_names, collections.abc.Mapping):
            names_seq = list(member_names)
            if names_seq:
                if isinstance(names_seq[0], str):
                    names_seq = cast("list[str]", names_seq)
                    ns = {name: index for index, name in enumerate(names_seq, start=start)}
                else:
                    names_seq = cast("list[tuple[str, Any]]", names_seq)
                    ns = dict(names_seq)
            else:
                ns = {}

        else:
            ns = member_names  # pyright: ignore

        _set_names(ns, qualname, module, enum_name)

        bases = (type,) if type else ()

        return self.__class__(enum_name, bases, ns)


if TYPE_CHECKING:
    from enum import Enum
else:

    class Enum(metaclass=EnumMeta):
        """An API-compatible re-implementation of ``enum.Enum``."""


if TYPE_CHECKING:
    from enum import auto
else:

    def auto() -> object:
        """Specify that the member should be an auto-incremented int."""

        return _AUTO


if TYPE_CHECKING:
    from enum import unique
else:

    def unique(cls):  # noqa: ANN001, ANN202
        """Make sure all enum members have unique values.

        Raises
        ------
        ValueError
            If any duplicate values are found.
        """

        seen: list[Any] = []
        for value in (member.value for member in cls._member_map_.values()):
            if value in seen:
                msg = f"{cls!r} enum reused {value!r}"
                raise ValueError(msg)

            seen.append(value)

        return cls
