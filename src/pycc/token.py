"""C token enum, mappings, and container."""

from __future__ import annotations

from collections.abc import Iterable
from itertools import chain

from ._compat import TYPE_CHECKING


if TYPE_CHECKING:
    from enum import Enum, auto
else:
    from ._enum import Enum, auto

__all__ = ("TokenKind", "KEYWORD_TOKEN_MAP", "PUNCTUATION_TOKEN_MAP", "Token")


class TokenKind(Enum):
    """C token kinds."""

    # fmt: off

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
    PP_NUM              = auto()
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

PUNCTUATION_TOKEN_MAP = {
    # Operators
    "+":    TokenKind.PLUS,
    "-":    TokenKind.MINUS,
    "*":    TokenKind.TIMES,
    "/":    TokenKind.DIVIDE,
    "%":    TokenKind.MOD,
    "|":    TokenKind.OR,
    "&":    TokenKind.AND,
    "~":    TokenKind.NOT,
    "^":    TokenKind.XOR,
    "<<":   TokenKind.LSHIFT,
    ">>":   TokenKind.RSHIFT,
    "||":   TokenKind.LOR,
    "&&":   TokenKind.LAND,
    "!":    TokenKind.LNOT,
    "<":    TokenKind.LT,
    ">":    TokenKind.GT,
    "<=":   TokenKind.LE,
    ">=":   TokenKind.GE,
    "==":   TokenKind.EQ,
    "!=":   TokenKind.NE,

    # Assignment operators
    "=":    TokenKind.EQUALS,
    "*=":   TokenKind.TIMESEQUAL,
    "/=":   TokenKind.DIVEQUAL,
    "%=":   TokenKind.MODEQUAL,
    "+=":   TokenKind.PLUSEQUAL,
    "-=":   TokenKind.MINUSEQUAL,
    "<<=":  TokenKind.LSHIFTEQUAL,
    ">>=":  TokenKind.RSHIFTEQUAL,
    "&=":   TokenKind.ANDEQUAL,
    "|=":   TokenKind.OREQUAL,
    "^=":   TokenKind.XOREQUAL,

    # Increment/decrement
    "++":   TokenKind.PLUSPLUS,
    "--":   TokenKind.MINUSMINUS,

    # Structure dereference
    "->":   TokenKind.ARROW,

    # Conditional operator
    "?":    TokenKind.CONDOP,

    # Delimiters
    "(":    TokenKind.LPAREN,
    ")":    TokenKind.RPAREN,
    "[":    TokenKind.LBRACKET,
    "]":    TokenKind.RBRACKET,
    ",":    TokenKind.COMMA,
    ".":    TokenKind.PERIOD,
    ";":    TokenKind.SEMICOLON,
    ":":    TokenKind.COLON,

    # Scope delimiters
    "{":    TokenKind.LBRACE,
    "}":    TokenKind.RBRACE,
}  # fmt: skip


class Token:
    """The token container.

    Parameters
    ----------
    kind: TokenKind
        The kind of the token.
    value: str
        String value, as taken from the input.
    """

    __slots__ = ("kind", "value", "length", "filename", "at_bol", "has_space")

    def __init__(  # noqa: PLR0913
        self,
        kind: TokenKind,
        value: str,
        start: int,
        end: int,
        filename: str,
        at_bol: bool,
        has_space: bool,
    ) -> None:
        self.kind = kind
        self.value = value
        self.length = start - end
        self.filename = filename
        self.at_bol = at_bol
        self.has_space = has_space

    def __repr__(self) -> str:
        return f"{type(self).__name__}(type={self.kind!r}, value={self.value!r})"


def _charify_inclusive_ranges(*ranges: tuple[int, int]) -> Iterable[str]:
    return chain.from_iterable(map(chr, range(first, second + 1)) for first, second in ranges)


class CharSets:
    ignored_whitespace = frozenset(" \t")

    ascii_lowercase = "abcdefghijklmnopqrstuvwxyz"
    ascii_uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    ascii_letters = ascii_lowercase + ascii_uppercase

    digits = "0123456789"
    hex_digits = digits + "abcdef" + "ABCDEF"
    oct_digits = "01234567"
    bin_digits = "01"

    alphanumeric = ascii_letters + digits

    identifier_start = ascii_letters + "".join(
        chain(
            ("_", "$", "\u00a8", "\u00aa", "\u00ad", "\u00af"),
            _charify_inclusive_ranges(
                (0x00B2, 0x00B5),
                (0x00B7, 0x00BA),
                (0x00BC, 0x00BE),
                (0x00C0, 0x00D6),
                (0x00D8, 0x00F6),
                (0x00F8, 0x00FF),
                (0x0100, 0x02FF),
                (0x0370, 0x167F),
                (0x1681, 0x180D),
                (0x180F, 0x1DBF),
                (0x1E00, 0x1FFF),
                (0x200B, 0x200D),
                (0x202A, 0x202E),
                (0x203F, 0x2040),
                (0x2054, 0x2054),
                (0x2060, 0x206F),
                (0x2070, 0x20CF),
                (0x2100, 0x218F),
                (0x2460, 0x24FF),
                (0x2776, 0x2793),
                (0x2C00, 0x2DFF),
                (0x2E80, 0x2FFF),
                (0x3004, 0x3007),
                (0x3021, 0x302F),
                (0x3031, 0x303F),
                (0x3040, 0xD7FF),
                (0xF900, 0xFD3D),
                (0xFD40, 0xFDCF),
                (0xFDF0, 0xFE1F),
                (0xFE30, 0xFE44),
                (0xFE47, 0xFFFD),
                (0x10000, 0x1FFFD),
                (0x20000, 0x2FFFD),
                (0x30000, 0x3FFFD),
                (0x40000, 0x4FFFD),
                (0x50000, 0x5FFFD),
                (0x60000, 0x6FFFD),
                (0x70000, 0x7FFFD),
                (0x80000, 0x8FFFD),
                (0x90000, 0x9FFFD),
                (0xA0000, 0xAFFFD),
                (0xB0000, 0xBFFFD),
                (0xC0000, 0xCFFFD),
                (0xD0000, 0xDFFFD),
                (0xE0000, 0xEFFFD),
            ),
        )
    )

    identifier_rest = (
        identifier_start
        + digits
        + "".join(
            _charify_inclusive_ranges(
                (0x0300, 0x036F),
                (0x1DC0, 0x1DFF),
                (0x20D0, 0x20FF),
                (0xFE20, 0xFE2F),
            )
        )
    )

    # TODO: Do we need all of these single ones?
    punctuation1 = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""
    punctuation2 = tuple(chars for chars in PUNCTUATION_TOKEN_MAP if len(chars) == 2)
    punctuation3 = tuple(chars for chars in PUNCTUATION_TOKEN_MAP if len(chars) == 3)
