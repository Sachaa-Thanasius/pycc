"""C token enum, mappings, and container."""

from __future__ import annotations


TYPE_CHECKING = False

if TYPE_CHECKING:
    from enum import Enum, auto
else:
    from ._enum import Enum, auto


__all__ = ("TokenKind", "Token")


class TokenKind(Enum):
    """C token kinds."""

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"

    # fmt: off

    # Meta
    NL                  = auto()
    COMMENT             = auto()
    WS                  = auto()

    # Keywords (see KEYWORD_TOKEN_MAP)
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

    # New keywords
    ALIGNAS_            = auto()
    ALIGNOF_            = auto()
    ATOMIC_             = auto()
    BOOL_               = auto()
    COMPLEX_            = auto()
    GENERIC_            = auto()
    IMAGINARY_          = auto()
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

    # Operators (see PUNCTUATION_TOKEN_MAP)
    PLUS                = auto()
    MINUS               = auto()
    TIMES               = auto()
    DIVIDE              = auto()
    MOD                 = auto()
    OR                  = auto()
    AND                 = auto()
    NOT                 = auto()
    XOR                 = auto()
    LSHIFT              = auto()
    RSHIFT              = auto()
    LOR                 = auto()
    LAND                = auto()
    LNOT                = auto()
    LT                  = auto()
    GT                  = auto()
    LE                  = auto()
    GE                  = auto()
    EQ                  = auto()
    NE                  = auto()

    # Assignment operators
    EQUALS              = auto()
    TIMESEQUAL          = auto()
    DIVEQUAL            = auto()
    MODEQUAL            = auto()
    PLUSEQUAL           = auto()
    MINUSEQUAL          = auto()
    LSHIFTEQUAL         = auto()
    RSHIFTEQUAL         = auto()
    ANDEQUAL            = auto()
    OREQUAL             = auto()
    XOREQUAL            = auto()

    # Increment/decrement
    PLUSPLUS            = auto()
    MINUSMINUS          = auto()

    # Structure dereference
    ARROW               = auto()

    # Conditional operator
    CONDOP              = auto()

    # Delimiters
    LPAREN              = auto()
    RPAREN              = auto()
    LBRACKET            = auto()
    RBRACKET            = auto()
    COMMA               = auto()
    PERIOD              = auto()
    SEMICOLON           = auto()
    COLON               = auto()

    # Scope delimiters
    LBRACE              = auto()
    RBRACE              = auto()

    # Variadic parameter specifier
    ELLIPSIS            = auto()

    # Preprocessor
    PP_NUM              = auto()
    PP_OCTO             = auto()
    PP_OCTOOCTO         = auto()

    PP_PRAGMA           = auto()
    PP_PRAGMASTR        = auto()

    # fmt: on

    @classmethod
    def from_keyword(cls, name: str) -> TokenKind:
        try:
            return _KEYWORD_TOKEN_MAP[name]
        except KeyError:
            raise ValueError(name) from None

    @classmethod
    def from_punctuator(cls, punctuator: str) -> TokenKind:
        try:
            return _PUNCTUATION_TOKEN_MAP[punctuator]
        except KeyError:
            raise ValueError(punctuator) from None


_KEYWORD_TOKEN_MAP = {
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
    "_Generic":         TokenKind.GENERIC_,
    "_Imaginary":       TokenKind.IMAGINARY_,
    "_Noreturn":        TokenKind.NORETURN_,
    "_Pragma":          TokenKind.PRAGMA_,
    "_Static_assert":   TokenKind.STATIC_ASSERT_,
    "_Thread_local":    TokenKind.THREAD_LOCAL_,
}  # fmt: skip


_PUNCTUATION_TOKEN_MAP = {
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

    # Preprocessor
    "#":    TokenKind.PP_OCTO,
    "##":   TokenKind.PP_OCTOOCTO,
}  # fmt: skip


class Token:
    """The token container.

    Parameters
    ----------
    kind: TokenKind
        The kind of the token.
    value: str
        String value, as taken from the input.
    lineno: int
        The line number of the file that the token is on. 1-indexed.
    col_offset: int
        Where the token starts relative to the start of the line.
    end_col_offset: int
        Where the token ends relative to the start of the line.
    filename: str
        What file the token comes from.
    """

    __slots__ = ("kind", "value", "lineno", "col_offset", "end_col_offset", "filename")

    def __init__(  # noqa: PLR0913 # Tokens are dense currently.
        self,
        kind: TokenKind,
        value: str,
        lineno: int,
        col_offset: int,
        end_col_offset: int,
        filename: str,
    ) -> None:
        self.kind = kind
        self.value = value
        self.lineno = lineno
        self.col_offset = col_offset
        self.end_col_offset = end_col_offset
        self.filename = filename

    @property
    def end_lineno(self) -> int:
        # FIXME: This doesn't match how a few things are handled in the tokenizer, e.g. block comments, line endings.

        return self.lineno + self.value.count("\n")

    def __repr__(self):
        return "".join(
            (
                f"{self.__class__.__name__}(",
                ", ".join(
                    (
                        f"kind={self.kind!r}",
                        f"value={self.value!r}",
                        f"lineno={self.lineno!r}",
                        f"col_offset={self.col_offset!r}",
                        f"end_col_offset={self.end_col_offset!r}",
                    )
                ),
                ")",
            )
        )


class CharSets:
    non_nl_whitespace = frozenset(" \t")

    ascii_lowercase = frozenset("abcdefghijklmnopqrstuvwxyz")
    ascii_uppercase = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    ascii_letters = ascii_lowercase | ascii_uppercase

    digits = frozenset("0123456789")

    alphanumeric = ascii_letters | digits

    punctuation1 = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""
    punctuation2 = tuple(chars for chars in _PUNCTUATION_TOKEN_MAP if len(chars) == 2)
    punctuation3 = tuple(chars for chars in _PUNCTUATION_TOKEN_MAP if len(chars) == 3)

    _identifier_start_ranges = (
        ("\u00b2", "\u00b5"),
        ("\u00b7", "\u00ba"),
        ("\u00bc", "\u00be"),
        ("\u00c0", "\u00d6"),
        ("\u00d8", "\u00f6"),
        ("\u00f8", "\u00ff"),
        ("\u0100", "\u02ff"),
        ("\u0370", "\u167f"),
        ("\u1681", "\u180d"),
        ("\u180f", "\u1dbf"),
        ("\u1e00", "\u1fff"),
        ("\u200b", "\u200d"),
        ("\u202a", "\u202e"),
        ("\u203f", "\u2040"),
        ("\u2054", "\u2054"),
        ("\u2060", "\u206f"),
        ("\u2070", "\u20cf"),
        ("\u2100", "\u218f"),
        ("\u2460", "\u24ff"),
        ("\u2776", "\u2793"),
        ("\u2c00", "\u2dff"),
        ("\u2e80", "\u2fff"),
        ("\u3004", "\u3007"),
        ("\u3021", "\u302f"),
        ("\u3031", "\u303f"),
        ("\u3040", "\ud7ff"),
        ("\uf900", "\ufd3d"),
        ("\ufd40", "\ufdcf"),
        ("\ufdf0", "\ufe1f"),
        ("\ufe30", "\ufe44"),
        ("\ufe47", "\ufffd"),
        ("\U00010000", "\U0001fffd"),
        ("\U00020000", "\U0002fffd"),
        ("\U00030000", "\U0003fffd"),
        ("\U00040000", "\U0004fffd"),
        ("\U00050000", "\U0005fffd"),
        ("\U00060000", "\U0006fffd"),
        ("\U00070000", "\U0007fffd"),
        ("\U00080000", "\U0008fffd"),
        ("\U00090000", "\U0009fffd"),
        ("\U000a0000", "\U000afffd"),
        ("\U000b0000", "\U000bfffd"),
        ("\U000c0000", "\U000cfffd"),
        ("\U000d0000", "\U000dfffd"),
        ("\U000e0000", "\U000efffd"),
    )

    @classmethod
    def can_start_identifier(cls, char: str, /) -> bool:
        return (
            (char in cls.ascii_letters)
            or (char in {"_", "$", "\u00a8", "\u00aa", "\u00ad", "\u00af"})
            or any(lower <= char <= upper for lower, upper in cls._identifier_start_ranges)
        )

    _extra_identifier_end_ranges = (
        ("\u0300", "\u036f"),
        ("\u1dc0", "\u1dff"),
        ("\u20d0", "\u20ff"),
        ("\ufe20", "\ufe2f"),
    )

    @classmethod
    def can_end_identifier(cls, char: str, /) -> bool:
        return (
            cls.can_start_identifier(char)
            or char in cls.digits
            or any(lower <= char <= upper for lower, upper in cls._extra_identifier_end_ranges)
        )
