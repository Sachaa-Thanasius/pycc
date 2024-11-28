"""AST nodes for representing ASDL, as well as a visitor class.

The following classes define nodes into which the ASDL description is parsed.
Note: this is a "meta-AST". ASDL files (such as Python.asdl) describe the AST
structure used by a programming language. But ASDL files themselves need to be
parsed. This module parses ASDL files and uses a simple AST to represent them.
See the EBNF at the top of the file to understand the logical connection
between the various node types.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Union


__all__ = ("AST", "Module", "Type", "Constructor", "Field", "Sum", "Product", "NodeVisitor")


class AST:
    __slots__ = ()

    def __repr__(self) -> str:
        raise NotImplementedError


class Module(AST):
    __slots__ = ("name", "dfns", "types")

    def __init__(self, name: str, dfns: list[Type]):
        self.name = name
        self.dfns = dfns
        self.types = {type_.name: type_.value for type_ in dfns}

    def __repr__(self):
        return f"{self.__class__}({self.name}, {self.dfns})"


class Type(AST):
    __slots__ = ("name", "value")

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


class Field(AST):
    __slots__ = ("type", "name", "seq", "opt")

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


class Sum(AST):
    def __init__(self, types: list[Constructor], attributes: Optional[list[Field]] = None):
        self.types = types
        self.attributes = attributes or []

    def __repr__(self):
        if self.attributes:
            return f"{self.__class__}({self.types}, {self.attributes})"
        else:
            return f"{self.__class__}({self.types})"


class Product(AST):
    def __init__(self, fields: list[Field], attributes: Optional[list[Field]] = None):
        self.fields = fields
        self.attributes = attributes or []

    def __repr__(self):
        if self.attributes:
            return f"{self.__class__}({self.fields}, {self.attributes})"
        else:
            return f"{self.__class__}({self.fields})"


class NodeVisitor:
    """Generic tree visitor for the meta-AST that describes ASDL.

    This can be used by emitters. Note that this visitor does not provide a generic visit method, so a
    subclass needs to define visit methods from visitModule to as deep as the
    interesting node.
    """

    def __init__(self):
        self.cache: dict[type[AST], Optional[Callable[..., Any]]] = {}

    def visit(self, obj: AST, *args: Any) -> Any:
        klass = obj.__class__
        meth = self.cache.get(klass)
        if meth is None:
            methname = f"visit_{klass.__name__}"
            meth = getattr(self, methname, None)
            self.cache[klass] = meth
        if meth:
            try:
                meth(obj, *args)
            except Exception as e:
                print(f"Error visiting {obj!r}: {e}")
                raise
