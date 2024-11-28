from __future__ import annotations

from enum import Enum, auto
from typing import Optional


class ASDLSyntaxError(Exception):
    def __init__(self, msg: str, lineno: Optional[int] = None):
        self.msg = msg
        self.lineno = lineno or "<unknown>"

    def __str__(self):
        return f"Syntax error on line {self.lineno}: {self.msg}"


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
