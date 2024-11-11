from collections.abc import Callable, Generator

from ._enum import Enum, auto
from ._typing_compat import Any, TypeAlias


LexGen: TypeAlias = Generator["Token | None", Any, "SubLexer | None"]
SubLexer: TypeAlias = Callable[[], LexGen]


class TokenType(Enum):
    thing = auto()


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
    input: str
        The string being lexed.
    pos: int
        An integer pointing at the current character in the input string.
    tokstart: int
        An integer pointing to the start of the currently processed token.
    state: SubLexer | None
        One of the _lex_* state functions. Each such function yields the tokens it finds and then returns the next
        state function. When EOF is encountered, None is returned as the new state.
    """

    def __init__(self, input: str) -> None:
        self.input = input
        self.pos = 0
        self.tokstart = 0
        self.state: SubLexer | None = self._lex_text

    def lex(self) -> LexGen:
        while self.state:
            self.state = yield from self.state()

    @property
    def _curchar(self) -> str | None:
        """Get the char at self.pos, or None if we're at EOF."""

        return self.input[self.pos] if self.pos < len(self.input) else None

    def _accept(self, validset: set[str]) -> bool:
        """Consume current char if it's in validset, and return True.
        Otherwise don't consume it, and return False.
        """

        consumed = self._curchar in validset
        if consumed:
            self.pos += 1
        return consumed

    def _accept_run(self, validset: set[str]) -> None:
        """Consume chars as long as they're in validset (or until EOF)."""

        while self._accept(validset):
            pass

    def _ignore_tok(self) -> None:
        """Ignore the current token."""

        self.tokstart = self.pos

    def _emit(self, toktype: TokenType) -> Token:
        """Emit the current token."""

        tok = Token(toktype, self.input[self.tokstart : self.pos])
        self.tokstart = self.pos
        return tok
