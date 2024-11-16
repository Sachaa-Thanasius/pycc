from __future__ import annotations

from collections.abc import Callable, Generator
from typing import TYPE_CHECKING, Any, Optional, TypeVar, Union

from ._compat import TypeAlias
from ._enum import Enum, auto


if TYPE_CHECKING:
    from enum import Enum, auto
else:
    from pycc._enum import Enum, auto

_T = TypeVar("_T")

_LexGen: TypeAlias = Generator[Optional["Token"], Any, Optional["_SubLexer"]]
_SubLexer: TypeAlias = Callable[[], _LexGen]
_SetLike: TypeAlias = Union[set[_T], frozenset[_T]]


class CSyntaxError(Exception):
    pass


class StringSets:
    ignored_whitespace = frozenset(" \t")
    ascii_lowercase = frozenset("abcdefghijklmnopqrstuvwxyz")
    ascii_uppercase = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    ascii_letters = ascii_lowercase | ascii_uppercase
    digits = frozenset("0123456789")
    hex_digits = digits.union("abcdef", "ABCDEF")
    oct_digits = frozenset("01234567")
    bin_digits = frozenset("01")

    alpha_numeric = ascii_letters | digits

    identifier_start = ascii_letters.union("_$")
    identifier_rest = alpha_numeric.union("_$")


class TokenType(Enum):
    NEWLINE = auto()

    # Keywords
    AUTO = auto()
    BREAK = auto()
    CASE = auto()
    CHAR = auto()
    CONST = auto()
    CONTINUE = auto()
    DEFAULT = auto()
    DO = auto()
    DOUBLE = auto()
    ELSE = auto()
    ENUM = auto()
    EXTERN = auto()
    FLOAT = auto()
    FOR = auto()
    GOTO = auto()
    IF = auto()
    INLINE = auto()
    INT = auto()
    LONG = auto()
    REGISTER = auto()
    OFFSETOF = auto()
    RESTRICT = auto()
    RETURN = auto()
    SHORT = auto()
    SIGNED = auto()
    SIZEOF = auto()
    STATIC = auto()
    STRUCT = auto()
    SWITCH = auto()
    TYPEDEF = auto()
    UNION = auto()
    UNSIGNED = auto()
    VOID = auto()
    VOLATILE = auto()
    WHILE = auto()
    _INT128 = auto()

    # New keywords
    _BOOL = auto()
    _COMPLEX = auto()
    _NORETURN = auto()
    _THREAD_LOCAL = auto()
    _STATIC_ASSERT = auto()
    _ATOMIC = auto()
    _ALIGNOF = auto()
    _ALIGNAS = auto()
    _PRAGMA = auto()

    # Identifier
    ID = auto()

    # Constants
    INT_CONST_DEC = auto()
    INT_CONST_OCT = auto()
    INT_CONST_HEX = auto()
    INT_CONST_BIN = auto()
    INT_CONST_CHAR = auto()
    FLOAT_CONST = auto()
    HEX_FLOAT_CONST = auto()
    CHAR_CONST = auto()
    WCHAR_CONST = auto()
    U8CHAR_CONST = auto()
    U16CHAR_CONST = auto()
    U32CHAR_CONST = auto()

    # String literals
    STRING_LITERAL = auto()
    WSTRING_LITERAL = auto()
    U8STRING_LITERAL = auto()
    U16STRING_LITERAL = auto()
    U32STRING_LITERAL = auto()

    # Operators
    PLUS = auto()
    MINUS = auto()
    TIMES = auto()
    DIVIDE = auto()
    MOD = auto()
    OR = auto()
    AND = auto()
    NOT = auto()
    XOR = auto()
    LSHIFT = auto()
    RSHIFT = auto()
    LOR = auto()
    LAND = auto()
    LNOT = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    EQ = auto()
    NE = auto()

    # Assignment operators
    EQUALS = auto()
    TIMESEQUAL = auto()
    DIVEQUAL = auto()
    MODEQUAL = auto()
    PLUSEQUAL = auto()
    MINUSEQUAL = auto()
    LSHIFTEQUAL = auto()
    RSHIFTEQUAL = auto()
    ANDEQUAL = auto()
    OREQUAL = auto()
    XOREQUAL = auto()

    # Increment/decrement
    PLUSPLUS = auto()
    MINUSMINUS = auto()

    # Structure dereference (->)
    ARROW = auto()

    # Conditional operator (?)
    CONDOP = auto()

    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    PERIOD = auto()
    SEMICOLON = auto()
    COLON = auto()

    # Scope delimiters
    LBRACE = auto()
    RBRACE = auto()

    # Ellipsis (...)
    ELLIPSIS = auto()

    # Pre-processor
    PP_OCTO = auto()
    PP_PRAGMA = auto()
    PP_PRAGMASTR = auto()


KEYWORD_MAP = {
    # Keywords
    "auto": TokenType.AUTO,
    "break": TokenType.BREAK,
    "case": TokenType.CASE,
    "char": TokenType.CHAR,
    "const": TokenType.CONST,
    "continue": TokenType.CONTINUE,
    "default": TokenType.DEFAULT,
    "do": TokenType.DO,
    "double": TokenType.DOUBLE,
    "else": TokenType.ELSE,
    "enum": TokenType.ENUM,
    "extern": TokenType.EXTERN,
    "float": TokenType.FLOAT,
    "for": TokenType.FOR,
    "goto": TokenType.GOTO,
    "if": TokenType.IF,
    "inline": TokenType.INLINE,
    "int": TokenType.INT,
    "long": TokenType.LONG,
    "register": TokenType.REGISTER,
    "offsetof": TokenType.OFFSETOF,
    "restrict": TokenType.RESTRICT,
    "return": TokenType.RETURN,
    "short": TokenType.SHORT,
    "signed": TokenType.SIGNED,
    "sizeof": TokenType.SIZEOF,
    "static": TokenType.STATIC,
    "struct": TokenType.STRUCT,
    "switch": TokenType.SWITCH,
    "typedef": TokenType.TYPEDEF,
    "union": TokenType.UNION,
    "unsigned": TokenType.UNSIGNED,
    "void": TokenType.VOID,
    "volatile": TokenType.VOLATILE,
    "while": TokenType.WHILE,
    "__int128": TokenType._INT128,
    # New keywords
    "_Bool": TokenType._BOOL,
    "_Complex": TokenType._COMPLEX,
    "_Noreturn": TokenType._NORETURN,
    "_Thread_local": TokenType._THREAD_LOCAL,
    "_Static_assert": TokenType._STATIC_ASSERT,
    "_Atomic": TokenType._ATOMIC,
    "_Alignof": TokenType._ALIGNOF,
    "_Alignas": TokenType._ALIGNAS,
    "_Pragma": TokenType._PRAGMA,
}


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

    def __init__(self, type: TokenType, value: str):
        self.type = type
        self.value = value

    def __repr__(self) -> str:
        return f"{type(self).__name__}(type={self.type!r}, value={self.value!r})"


class Lexer:
    """A lexer Initialize with the input string, and then call lex() which generates tokens.
    None is generated at EOF (and the generator expires).

    Parameters
    ----------
    input: str
        The string to lex.

    Attributes
    ----------
    text: str
        The string being lexed.
    index: int
        An integer pointing at the current character in the given text.
    tokstart: int
        An integer pointing to the start of the currently processed token.
    state: SubLexer | None
        One of the _lex_* state functions. Each such function yields the tokens it finds and then returns the next
        state function. When EOF is encountered, None is returned as the new state.
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self.index = 0
        self.tokstart = 0
        self.state: _SubLexer | None = self._lex_text

    def lex(self) -> _LexGen:
        while self.state:
            self.state = yield from self.state()

    # region ---- Internals ----

    @property
    def end(self) -> int:
        return len(self.text)

    @property
    def current(self) -> str | None:
        """Get the char at self.index, or None if we're at EOF."""

        return self.text[self.index] if self.index < self.end else None

    @property
    def current_group(self) -> Optional[str]:
        return self.text[self.tokstart : self.index] if self.index < self.end else None

    def _ignore_tok(self) -> None:
        """Ignore the current token."""

        self.tokstart = self.index

    def _accept(self, validset: _SetLike[str]) -> bool:
        """Consume current char if it's in validset, and return True.

        Otherwise don't consume it, and return False.
        """

        consumed = self.current in validset
        if consumed:
            self.index += 1
        return consumed

    def _accept_run(self, validset: _SetLike[str]) -> None:
        """Consume chars as long as they're in validset (or until EOF)."""

        # An alternative to the while loop: deque(iter(partial(self._accept, validset), False), maxlen=0)
        while self._accept(validset):
            pass

    def _emit(self, toktype: TokenType) -> Token:
        """Emit the current token."""

        tok = Token(toktype, self.text[self.tokstart : self.index])
        self.tokstart = self.index
        return tok

    # endregion

    # region ---- Rules ----

    def base(self) -> _LexGen:
        while True:
            if self._accept(StringSets.ignored_whitespace):
                self._ignore_tok()
            elif self.current in StringSets.identifier_start:
                return self.identifier

    def identifier(self) -> _LexGen:
        self._accept(StringSets.identifier_start)
        self._accept_run(StringSets.identifier_rest)

        try:
            tok_type = KEYWORD_MAP[self.current_group]  # pyright: ignore [reportArgumentType]
        except KeyError:
            tok_type = TokenType.ID

        yield self._emit(tok_type)

    # endregion
