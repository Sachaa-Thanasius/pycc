# -------------------------------------------------------------------------------
# Parser for ASDL [1] definition files. Reads in an ASDL description and parses
# it into an AST that describes it.
#
# The EBNF we're parsing here: Figure 1 of the paper [1]. Extended to support
# modules and attributes after a product. Words starting with Capital letters
# are terminals. Literal tokens are in "double quotes". Others are
# non-terminals. Id is either TokenId or ConstructorId.
#
# module        ::= "module" Id "{" [definitions] "}"
# definitions   ::= { TypeId "=" type }
# type          ::= product | sum
# product       ::= fields ["attributes" fields]
# fields        ::= "(" { field, "," } field ")"
# field         ::= TypeId ["?" | "*"] [Id]
# sum           ::= constructor { "|" constructor } ["attributes" fields]
# constructor   ::= ConstructorId [fields]
#
# [1] "The Zephyr Abstract Syntax Description Language" by Wang, et. al. See
#     http://asdl.sourceforge.net/
# -------------------------------------------------------------------------------
from __future__ import annotations

import re
from collections.abc import Generator
from enum import Enum, auto
from typing import Optional, Union

from .ast import Constructor, Field, Module, NodeVisitor, Product, Sum, Type
from .tokenize import *


__all__ = [
    "builtin_types",
    "parse",
    "Check",
    "check",
]


builtin_types = {"identifier", "string", "int", "constant"}


class Check(NodeVisitor):
    """A visitor that checks a parsed ASDL tree for correctness.

    Errors are printed and accumulated.
    """

    def __init__(self):
        super().__init__()
        self.cons: dict[str, str] = {}
        self.errors: int = 0
        self.types: dict[str, list[str]] = {}

    def visit_Module(self, mod: Module) -> None:
        for dfn in mod.dfns:
            self.visit(dfn)

    def visit_Type(self, type: Type) -> None:
        self.visit(type.value, str(type.name))

    def visit_Sum(self, sum: Sum, name: str) -> None:
        for t in sum.types:
            self.visit(t, name)

    def visit_Constructor(self, cons: Constructor, name: str) -> None:
        key = str(cons.name)
        conflict = self.cons.get(key)
        if conflict is None:
            self.cons[key] = name
        else:
            print(f"Redefinition of constructor {key}")
            print(f"Defined in {conflict} and {name}")
            self.errors += 1

        for f in cons.fields:
            self.visit(f, key)

    def visit_Field(self, field: Field, name: str) -> None:
        key = str(field.type)
        l = self.types.setdefault(key, [])
        l.append(name)

    def visit_Product(self, prod: Product, name: str) -> None:
        for f in prod.fields:
            self.visit(f, name)


def check(mod: Module) -> bool:
    """Check the parsed ASDL tree for correctness.

    Return True if success. For failure, the errors are printed out and False
    is returned.
    """

    v = Check()
    v.visit(mod)

    for t in v.types:
        if t not in mod.types and t not in builtin_types:
            v.errors += 1
            uses = ", ".join(v.types[t])
            print(f"Undefined type {t}, used in {uses}")
    return not v.errors


# The ASDL parser itself comes next. The only interesting external interface
# here is the top-level parse function.


def parse(filename: str) -> Module:
    """Parse ASDL from the given file and return a Module node describing it."""

    with open(filename, encoding="utf-8") as f:
        parser = ASDLParser()
        return parser.parse(f.read())


# Types for describing tokens in an ASDL specification.
class TokenKind(Enum):
    """TokenKind provides a scope for enumerated token kinds."""

    # fmt: off
    ConstructorId   = auto()
    TypeId          = auto()
    Equals          = auto()
    Comma           = auto()
    Question        = auto()
    Pipe            = auto()
    Asterisk        = auto()
    LParen          = auto()
    RParen          = auto()
    LBrace          = auto()
    RBrace          = auto()
    # fmt: on


operator_table = {
    "=": TokenKind.Equals,
    ",": TokenKind.Comma,
    "?": TokenKind.Question,
    "|": TokenKind.Pipe,
    "(": TokenKind.LParen,
    ")": TokenKind.RParen,
    "*": TokenKind.Asterisk,
    "{": TokenKind.LBrace,
    "}": TokenKind.RBrace,
}


class Token:
    __slots__ = ("kind", "value", "lineno")

    def __init__(self, kind: TokenKind, value: str, lineno: int):
        self.kind = kind
        self.value = value
        self.lineno = lineno

    def __repr__(self):
        return f"{self.__class__}(kind={self.kind}, value={self.value}, lineno={self.lineno})"


class ASDLSyntaxError(Exception):
    def __init__(self, msg: str, lineno: Optional[int] = None):
        self.msg = msg
        self.lineno = lineno or "<unknown>"

    def __str__(self):
        return f"Syntax error on line {self.lineno}: {self.msg}"


def get_identifier_end(buf: str, start: int) -> int:
    for i in range(start, len(buf)):
        if not (buf[i].isalpha() or buf == "_"):
            return i

    return start + 1


def tokenize_asdl2(buffer: str) -> Generator[Token]:
    """Tokenize the given buffer. Yield Token objects."""

    for lineno, line in enumerate(buffer.splitlines(), start=1):
        colno = 0
        while colno < len(line):
            char = line[colno]

            # Discard whitespace.
            if char.isspace():
                colno += 1
                continue

            # Capture identifiers.
            elif char.isalpha():
                id_start = colno
                colno = get_identifier_end(line, id_start)

                if char.isupper():
                    id_kind = TokenKind.ConstructorId
                else:
                    id_kind = TokenKind.TypeId

                yield Token(id_kind, line[id_start:colno], lineno)

            # Discard the commented section of a line.
            elif line.startswith("--", colno):
                break

            # Capture operators.
            elif (op_kind := operator_table.get(char)) is not None:
                # Operators can only be 1 character long.
                colno += 1
                yield Token(op_kind, char, lineno)

            # Panic on unknowns.
            else:
                msg = f"Invalid operator {char}"
                raise ASDLSyntaxError(msg, lineno) from None


def tokenize_asdl(buf: str) -> Generator[Token]:
    """Tokenize the given buffer. Yield Token objects."""

    for lineno, line in enumerate(buf.splitlines(), start=1):
        for m in re.finditer(r"\s*(\w+|--.*|.)", line.strip()):
            c = m.group(1)
            if c[0].isalpha():
                # Some kind of identifier
                if c[0].isupper():
                    yield Token(TokenKind.ConstructorId, c, lineno)
                else:
                    yield Token(TokenKind.TypeId, c, lineno)
            elif c[:2] == "--":
                # Comment
                break
            else:
                # Operators
                try:
                    op_kind = operator_table[c]
                except KeyError:
                    msg = f"Invalid operator {c}"
                    raise ASDLSyntaxError(msg, lineno) from None
                yield Token(op_kind, c, lineno)


class ASDLParser:
    """Parser for ASDL files.

    Create, then call the parse method on a buffer containing ASDL.
    This is a simple recursive descent parser that uses tokenize_asdl for the
    lexing.
    """

    _id_kinds = (TokenKind.ConstructorId, TokenKind.TypeId)

    cur_token: Optional[Token]

    def __init__(self):
        self._tokenizer = None
        self.cur_token = None

    def parse(self, buf: str) -> Module:
        """Parse the ASDL in the buffer and return an AST with a Module root."""

        self._tokenizer = tokenize_asdl(buf)
        self._advance()
        return self._parse_module()

    def _parse_module(self) -> Module:
        if self._at_keyword("module"):
            self._advance()
        else:
            msg = f'Expected "module" (found {self.cur_token.value})'
            raise ASDLSyntaxError(msg, self.cur_token.lineno)
        name = self._match(self._id_kinds)
        self._match(TokenKind.LBrace)
        defs = self._parse_definitions()
        self._match(TokenKind.RBrace)
        return Module(name, defs)

    def _parse_definitions(self) -> list[Type]:
        defs: list[Type] = []
        while self.cur_token.kind == TokenKind.TypeId:
            typename = self._advance()
            self._match(TokenKind.Equals)
            type = self._parse_type()
            defs.append(Type(typename, type))
        return defs

    def _parse_type(self) -> Union[Product, Sum]:
        if self.cur_token.kind == TokenKind.LParen:
            # If we see a (, it's a product
            return self._parse_product()
        else:
            # Otherwise it's a sum. Look for ConstructorId
            sumlist = [Constructor(self._match(TokenKind.ConstructorId), self._parse_optional_fields())]
            while self.cur_token.kind == TokenKind.Pipe:
                # More constructors
                self._advance()
                sumlist.append(Constructor(self._match(TokenKind.ConstructorId), self._parse_optional_fields()))
            return Sum(sumlist, self._parse_optional_attributes())

    def _parse_product(self) -> Product:
        return Product(self._parse_fields(), self._parse_optional_attributes())

    def _parse_fields(self) -> list[Field]:
        fields: list[Field] = []
        self._match(TokenKind.LParen)
        while self.cur_token.kind == TokenKind.TypeId:
            typename = self._advance()
            is_seq, is_opt = self._parse_optional_field_quantifier()
            id = self._advance() if self.cur_token.kind in self._id_kinds else None
            fields.append(Field(typename, id, seq=is_seq, opt=is_opt))
            if self.cur_token.kind == TokenKind.RParen:
                break
            elif self.cur_token.kind == TokenKind.Comma:
                self._advance()
        self._match(TokenKind.RParen)
        return fields

    def _parse_optional_fields(self) -> Optional[list[Field]]:
        if self.cur_token.kind == TokenKind.LParen:
            return self._parse_fields()
        else:
            return None

    def _parse_optional_attributes(self) -> Optional[list[Field]]:
        if self._at_keyword("attributes"):
            self._advance()
            return self._parse_fields()
        else:
            return None

    def _parse_optional_field_quantifier(self) -> tuple[bool, bool]:
        is_seq, is_opt = False, False
        if self.cur_token.kind == TokenKind.Asterisk:
            is_seq = True
            self._advance()
        elif self.cur_token.kind == TokenKind.Question:
            is_opt = True
            self._advance()
        return is_seq, is_opt

    def _advance(self) -> Optional[str]:
        """Return the value of the current token and read the next one into self.cur_token."""

        cur_val = None if self.cur_token is None else self.cur_token.value
        try:
            self.cur_token = next(self._tokenizer)
        except StopIteration:
            self.cur_token = None
        return cur_val

    def _match(self, kind: Union[TokenKind, tuple[TokenKind, ...]]) -> str:
        """The 'match' primitive of RD parsers.

        *   Verifies that the current token is of the given kind (kind can be a tuple, in which the kind must match one
            of its members).
        *   Returns the value of the current token
        *   Reads in the next token
        """

        if (isinstance(kind, tuple) and self.cur_token.kind in kind) or self.cur_token.kind == kind:
            value = self.cur_token.value
            self._advance()
            return value
        else:
            msg = f"Unmatched {kind} (found {self.cur_token.kind})"
            raise ASDLSyntaxError(msg, self.cur_token.lineno)

    def _at_keyword(self, keyword: str) -> bool:
        return self.cur_token.kind == TokenKind.TypeId and self.cur_token.value == keyword
