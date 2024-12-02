"""AST nodes for representing ASDL, as well as a visitor class.

The following classes define nodes into which the ASDL description is parsed.
Note: this is a "meta-AST". ASDL files (such as Python.asdl) describe the AST
structure used by a programming language. But ASDL files themselves need to be
parsed. This module parses ASDL files and uses a simple AST to represent them.
See the EBNF at the top of the file to understand the logical connection
between the various node types.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Generator
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Union


if TYPE_CHECKING:
    from types import GeneratorType
else:
    GeneratorType = type(_ for _ in ())

__all__ = ("AST", "Module", "Type", "Constructor", "Field", "Sum", "Product", "NodeVisitor")


class AST:
    __slots__ = ()

    _fields: ClassVar[tuple[str, ...]] = ()

    def __repr__(self) -> str:
        raise NotImplementedError


class Module(AST):
    __slots__ = ("name", "dfns", "types")

    _fields = ("dfns",)

    def __init__(self, name: str, dfns: list[Type]):
        self.name = name
        self.dfns = dfns
        self.types = {type_.name: type_.value for type_ in dfns}

    def __repr__(self):
        return f"{self.__class__}({self.name}, {self.dfns})"


class Type(AST):
    __slots__ = ("name", "value")

    _fields = ("value",)

    def __init__(self, name: str, value: Union[Product, Sum]):
        self.name = name
        self.value = value

    def __repr__(self):
        return f"{self.__class__}({self.name}, {self.value})"


class Constructor(AST):
    __slots__ = ("name", "fields")

    def __init__(self, name: str, fields: Optional[list[Field]] = None):
        self.name = name
        self.fields = fields or []

    def __repr__(self):
        return f"{self.__class__}({self.name}, {self.fields})"


class Sum(AST):
    __slots__ = ("types", "attributes")

    _fields = ("types",)

    def __init__(self, types: list[Constructor], attributes: Optional[list[Field]] = None):
        self.types = types
        self.attributes = attributes or []

    def __repr__(self):
        if self.attributes:
            return f"{self.__class__}({self.types}, {self.attributes})"
        else:
            return f"{self.__class__}({self.types})"


class Product(AST):
    __slots__ = ("fields", "attributes")

    _fields = ("fields",)

    def __init__(self, fields: list[Field], attributes: Optional[list[Field]] = None):
        self.fields = fields
        self.attributes = attributes or []

    def __repr__(self):
        if self.attributes:
            return f"{self.__class__}({self.fields}, {self.attributes})"
        else:
            return f"{self.__class__}({self.fields})"


class Field(AST):
    __slots__ = ("type", "name", "seq", "opt")

    _fields = ()

    def __init__(self, type, name: Optional[str] = None, seq: Optional[bool] = False, opt: Optional[bool] = False):
        self.type = type
        self.name = name
        self.seq = seq
        self.opt = opt

    def __str__(self):
        if self.seq:
            extra = "*"
        elif self.opt:
            extra = "?"
        else:
            extra = ""

        return f"{self.type}{extra} {self.name}"

    def __repr__(self):
        if self.seq:
            extra = ", seq=True"
        elif self.opt:
            extra = ", opt=True"
        else:
            extra = ""

        if self.name is None:
            return f"{self.__class__}({self.type}{extra})"
        else:
            return f"{self.__class__}({self.type}, {self.name}{extra})"


def iter_child_nodes(node: AST) -> Generator[AST]:
    for field in node._fields:
        potential_subnode = getattr(node, field)

        if isinstance(potential_subnode, AST):
            yield potential_subnode

        elif isinstance(potential_subnode, list):
            for subsub in potential_subnode:  # pyright: ignore [reportUnknownVariableType]
                if isinstance(subsub, AST):
                    yield subsub


def walk(node: AST) -> Generator[AST]:
    """Walk through an AST, breadth first."""

    stack: deque[AST] = deque([node])
    while stack:
        curr_node = stack.popleft()
        stack.extend(iter_child_nodes(curr_node))
        yield curr_node


class NodeVisitor:
    """Generic tree visitor for the meta-AST that describes ASDL. This can be used by emitters."""

    def _visit(self, node: AST) -> Generator[Any, Any, Any]:
        """Wrapper for visit methods to ensure visit() only deals with generators."""

        result: Any = getattr(self, f"visit_{node.__class__.__name__}", self.generic_visit)(node)
        if isinstance(result, GeneratorType):
            result = yield from result
        return result

    def visit(self, node: AST) -> Any:
        """Visit a node."""

        stack: deque[Generator[Any, Any, Any]] = deque([self._visit(node)])
        result: Any = None
        exception: Optional[BaseException] = None

        while stack:
            try:
                if exception is not None:
                    node = stack[-1].throw(exception)
                else:
                    node = stack[-1].send(result)
            except StopIteration as exc:  # noqa: PERF203
                stack.pop()
                result = exc.value
            except BaseException as exc:  # noqa: BLE001
                # Manually propogate the exception up the stack of generators.
                stack.pop()
                exception = exc
            else:
                stack.append(self._visit(node))
                result = None

        if exception is not None:
            raise exception
        else:
            return result

    def generic_visit(self, node: AST) -> Generator[AST, Any, Any]:
        """Called if no explicit visitor function exists for a node."""

        yield from iter_child_nodes(node)
