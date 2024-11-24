"""C token enum, mappings, and container."""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from enum import Enum, auto
else:
    from ._enum import Enum, auto

__all__ = ("TokenKind", "KEYWORD_TOKEN_MAP", "Token")


class TokenKind(Enum):
    """C token types."""

    # fmt: off
    NEWLINE             = auto()

    LINE_COMMENT        = auto()
    BLOCK_COMMENT       = auto()

    # Keywords (see keyword-token map)
    AUTO                = auto()
    BREAK               = auto()
    CASE                = auto()
    CHAR                = auto()
    CONST               = auto()
    CONTINUE            = auto()
    DEFAULT             = auto()
    DO                  = auto()
    DOUBLE              = auto()
    ELSE                = auto()
    ENUM                = auto()
    EXTERN              = auto()
    FLOAT               = auto()
    FOR                 = auto()
    GOTO                = auto()
    IF                  = auto()
    INLINE              = auto()
    INT                 = auto()
    LONG                = auto()
    REGISTER            = auto()
    OFFSETOF            = auto()
    RESTRICT            = auto()
    RETURN              = auto()
    SHORT               = auto()
    SIGNED              = auto()
    SIZEOF              = auto()
    STATIC              = auto()
    STRUCT              = auto()
    SWITCH              = auto()
    TYPEDEF             = auto()
    UNION               = auto()
    UNSIGNED            = auto()
    VOID                = auto()
    VOLATILE            = auto()
    WHILE               = auto()
    INT128__            = auto()

    # New keywords (see keyword-token map)
    ALIGNAS_            = auto()
    ALIGNOF_            = auto()
    ATOMIC_             = auto()
    BOOL_               = auto()
    COMPLEX_            = auto()
    NORETURN_           = auto()
    PRAGMA_             = auto()
    STATIC_ASSERT_      = auto()
    THREAD_LOCAL_       = auto()

    # Identifier
    ID                  = auto()

    # Type identifier (an identifier previously defined as a type with typedef)
    TYPE_ID             = auto()

    # Constants
    INT_CONST_DEC       = auto()
    INT_CONST_OCT       = auto()
    INT_CONST_HEX       = auto()
    INT_CONST_BIN       = auto()
    INT_CONST_CHAR      = auto()
    FLOAT_CONST         = auto()
    HEX_FLOAT_CONST     = auto()
    CHAR_CONST          = auto()
    WCHAR_CONST         = auto()
    U8CHAR_CONST        = auto()
    U16CHAR_CONST       = auto()
    U32CHAR_CONST       = auto()

    # String literals
    STRING_LITERAL      = auto()
    WSTRING_LITERAL     = auto()
    U8STRING_LITERAL    = auto()
    U16STRING_LITERAL   = auto()
    U32STRING_LITERAL   = auto()

    # Operators
    PLUS                = auto()    # +
    MINUS               = auto()    # -
    TIMES               = auto()    # *
    DIVIDE              = auto()    # /
    MOD                 = auto()    # %
    OR                  = auto()    # |
    AND                 = auto()    # &
    NOT                 = auto()    # ~
    XOR                 = auto()    # ^
    LSHIFT              = auto()    # <<
    RSHIFT              = auto()    # >>
    LOR                 = auto()    # ||
    LAND                = auto()    # &&
    LNOT                = auto()    # !
    LT                  = auto()    # <
    GT                  = auto()    # >
    LE                  = auto()    # <=
    GE                  = auto()    # >=
    EQ                  = auto()    # ==
    NE                  = auto()    # !=

    # Assignment operators
    EQUALS              = auto()    # =
    TIMESEQUAL          = auto()    # *=
    DIVEQUAL            = auto()    # /=
    MODEQUAL            = auto()    # %=
    PLUSEQUAL           = auto()    # +=
    MINUSEQUAL          = auto()    # -=
    LSHIFTEQUAL         = auto()    # <<=
    RSHIFTEQUAL         = auto()    # >>=
    ANDEQUAL            = auto()    # &=
    OREQUAL             = auto()    # |=
    XOREQUAL            = auto()    # ^=

    # Increment/decrement
    PLUSPLUS            = auto()    # ++
    MINUSMINUS          = auto()    # --

    # Structure dereference
    ARROW               = auto()    # ->

    # Conditional operator
    CONDOP              = auto()    # ?

    # Delimiters
    LPAREN              = auto()    # (
    RPAREN              = auto()    # )
    LBRACKET            = auto()    # [
    RBRACKET            = auto()    # ]
    COMMA               = auto()    # ,
    PERIOD              = auto()    # .
    SEMICOLON           = auto()    # ;
    COLON               = auto()    # :

    # Scope delimiters
    LBRACE              = auto()    # {
    RBRACE              = auto()    # }

    # Variadic parameter specifier
    ELLIPSIS            = auto()    # ...

    # Pre-processor
    PP_OCTO             = auto()    # #
    PP_PRAGMA           = auto()
    PP_PRAGMASTR        = auto()
    # fmt: on


KEYWORD_TOKEN_MAP = {
    # Keywords
    "auto":             TokenKind.AUTO,
    "break":            TokenKind.BREAK,
    "case":             TokenKind.CASE,
    "char":             TokenKind.CHAR,
    "const":            TokenKind.CONST,
    "continue":         TokenKind.CONTINUE,
    "default":          TokenKind.DEFAULT,
    "do":               TokenKind.DO,
    "double":           TokenKind.DOUBLE,
    "else":             TokenKind.ELSE,
    "enum":             TokenKind.ENUM,
    "extern":           TokenKind.EXTERN,
    "float":            TokenKind.FLOAT,
    "for":              TokenKind.FOR,
    "goto":             TokenKind.GOTO,
    "if":               TokenKind.IF,
    "inline":           TokenKind.INLINE,
    "int":              TokenKind.INT,
    "long":             TokenKind.LONG,
    "offsetof":         TokenKind.OFFSETOF,
    "register":         TokenKind.REGISTER,
    "restrict":         TokenKind.RESTRICT,
    "return":           TokenKind.RETURN,
    "short":            TokenKind.SHORT,
    "signed":           TokenKind.SIGNED,
    "sizeof":           TokenKind.SIZEOF,
    "static":           TokenKind.STATIC,
    "struct":           TokenKind.STRUCT,
    "switch":           TokenKind.SWITCH,
    "typedef":          TokenKind.TYPEDEF,
    "union":            TokenKind.UNION,
    "unsigned":         TokenKind.UNSIGNED,
    "void":             TokenKind.VOID,
    "volatile":         TokenKind.VOLATILE,
    "while":            TokenKind.WHILE,
    "__int128":         TokenKind.INT128__,

    # New keywords
    "_Alignas":         TokenKind.ALIGNAS_,
    "_Alignof":         TokenKind.ALIGNOF_,
    "_Atomic":          TokenKind.ATOMIC_,
    "_Bool":            TokenKind.BOOL_,
    "_Complex":         TokenKind.COMPLEX_,
    "_Noreturn":        TokenKind.NORETURN_,
    "_Pragma":          TokenKind.PRAGMA_,
    "_Static_assert":   TokenKind.STATIC_ASSERT_,
    "_Thread_local":    TokenKind.THREAD_LOCAL_,
}  # fmt: skip


class Token:
    """The token container.

    Parameters
    ----------
    type: TokenType
        The type of the token.
    value: str
        String value, as taken from the input.
    """

    __slots__ = ("type", "value")

    def __init__(self, type: TokenKind, value: str) -> None:
        self.type = type
        self.value = value

    def __repr__(self) -> str:
        return f"{type(self).__name__}(type={self.type!r}, value={self.value!r})"
