"""Types for describing tokens in an ASDL specification, as well as a tokenizer based on them."""

from __future__ import annotations

import re
from collections.abc import Generator
from enum import Enum, auto

from .errors import ASDLSyntaxError


__all__ = ("TokenKind", "operator_table", "Token", "tokenize_asdl")


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


def _get_identifier_end(buf: str, start: int) -> int:
    for i in range(start, len(buf)):
        if not (buf[i].isalpha() or buf == "_"):
            return i

    return start


def tokenize_asdl2(buffer: str) -> Generator[Token]:
    """Tokenize the given buffer. Yield Token objects."""

    for lineno, line in enumerate(buffer.splitlines(), start=1):
        colno = 0
        while colno < len(line):
            char = line[colno]

            # Discard whitespace.
            if char.isspace():
                colno += 1

            # Capture identifiers.
            elif char.isalpha():
                id_start = colno + 1
                colno = _get_identifier_end(line, id_start)

                if char.isupper():
                    id_kind = TokenKind.ConstructorId
                else:
                    id_kind = TokenKind.TypeId

                yield Token(id_kind, line[id_start:colno], lineno)

            # Discard the rest of the line as a comment.
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
