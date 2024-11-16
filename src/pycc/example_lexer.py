# ruff: noqa: T201, RUF012
# -------------------------------------------------------------------------------
# templatelexer.py
#
# A lexer based on sub-generators. Requires Python 3.3+ to run.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
# -------------------------------------------------------------------------------

from __future__ import annotations

import string
from collections.abc import Callable, Generator
from typing import TYPE_CHECKING, Any, Optional

from ._compat import TypeAlias


if TYPE_CHECKING:
    from enum import Enum, auto
else:
    from pycc._enum import Enum, auto


LexGen: TypeAlias = Generator[Optional["Token"], Any, Optional["SubLexer"]]
SubLexer: TypeAlias = Callable[[], LexGen]


class TokenType(Enum):
    TEXT = auto()
    LEFT_META = auto()
    RIGHT_META = auto()
    PIPE = auto()
    NUMBER = auto()
    ID = auto()


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

    def __init__(self, type: TokenType, value: str):  # noqa: A002
        self.type = type
        self.value = value

    def __repr__(self) -> str:
        return f"{type(self).__name__}(type={self.type!r}, value={self.value!r})"


class LexerError(Exception):
    pass


class TemplateLexer:
    """A lexer for the template language. Initialize with the input string, and then call lex() which generates tokens.
    None is generated at EOF (and the generator expires).

    Parameters
    ----------
    text: str
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
        self.text: str = text
        self.index: int = 0
        self.tokstart: int = 0
        self.state: SubLexer | None = self._lex_text

    def lex(self) -> LexGen:
        while self.state:
            self.state = yield from self.state()

    # --------- Internal --------- #

    _LEFT_META = "{{"
    _RIGHT_META = "}}"
    _PIPE = "|"
    _DOTS = set(".")
    _SIGNS = set("+-")
    _DEC_DIGITS = set(string.digits)
    _NUM_STARTERS = _SIGNS | _DEC_DIGITS
    _HEX_DIGITS = set(string.hexdigits)
    _ALPHANUM = _DEC_DIGITS | set(string.ascii_letters) | set("_")
    _EXP = set("eE")

    @property
    def current(self) -> str | None:
        """Get the char at self.index, or None if we're at EOF."""

        return self.text[self.index] if self.index < len(self.text) else None

    def _accept(self, validset: set[str]) -> bool:
        """Consume current char if it's in validset, and return True.

        Otherwise don't consume it, and return False.
        """

        consumed = self.current in validset
        if consumed:
            self.index += 1
        return consumed

    def _accept_run(self, validset: set[str]) -> None:
        """Consume chars as long as they're in validset (or until EOF)."""

        while self._accept(validset):
            pass

    def _ignore_tok(self) -> None:
        """Ignore the current token."""

        self.tokstart = self.index

    def _emit(self, toktype: TokenType) -> Token:
        """Emit the current token."""

        tok = Token(toktype, self.text[self.tokstart : self.index])
        self.tokstart = self.index
        return tok

    def _lex_text(self) -> LexGen:
        # Look for the beginning of LEFT_META
        meta_start = self.text.find(self._LEFT_META, self.index)
        if meta_start > 0:
            # Found. Emit all text until then (if any) and move to the lex_left_meta state.
            self.index = meta_start
            if self.index > self.tokstart:
                yield self._emit(TokenType.TEXT)
            return self._lex_left_meta
        else:
            # Not found. This means we're done. There may be some text left until EOF, so emit it if there is.
            self.index = len(self.text)
            if self.index > self.tokstart:
                yield self._emit(TokenType.TEXT)

            # Yield None to mark "no more tokens --> EOF"
            # Return None to stop the main lexing loop since there is no next state.
            yield None
            return None

    def _lex_left_meta(self) -> LexGen:
        self.index += len(self._LEFT_META)
        yield self._emit(TokenType.LEFT_META)
        return self._lex_inside_action

    def _lex_right_meta(self) -> LexGen:
        self.index += len(self._RIGHT_META)
        yield self._emit(TokenType.RIGHT_META)
        return self._lex_text

    def _lex_inside_action(self) -> LexGen:
        while True:
            # Check for RIGHT_META here before the next char is consumed,
            # to handle empty actions - {{}} - correctly.
            if self.text.startswith(self._RIGHT_META, self.index):
                return self._lex_right_meta

            c = self.current
            # Here a switch statement could be really useful...
            if c is None or c == "\n":
                msg = "Unterminated action"
                raise LexerError(msg)
            elif c.isspace():
                self.index += 1
                self._ignore_tok()
            elif c == self._PIPE:
                self.index += 1
                yield self._emit(TokenType.PIPE)
            elif c in self._NUM_STARTERS:
                return self._lex_number
            elif c.isalpha() or c == "_":
                return self._lex_identifier
            else:
                msg = "Invalid char '%s' inside action"
                raise LexerError(msg)

        # Reached EOF
        msg = "Unterminated action"
        raise LexerError(msg)
        return None

    def _lex_number(self) -> LexGen:
        # Optional sign before the number
        self._accept(self._SIGNS)

        # Figure out if we'll have a decimal or hex number
        digits = self._DEC_DIGITS
        if self.text.startswith("0x", self.index):
            self.index += 2
            digits = self._HEX_DIGITS

        # Grab the number
        self._accept_run(digits)

        # It may be a float, followed by a dot and optionally more numbers
        if self._accept(self._DOTS):
            self._accept_run(digits)

        # It may be followed by an exponent
        if self._accept(self._EXP):
            self._accept(self._SIGNS)
            self._accept_run(self._DEC_DIGITS)

        yield self._emit(TokenType.NUMBER)
        return self._lex_inside_action

    def _lex_identifier(self) -> LexGen:
        self._accept_run(self._ALPHANUM)
        yield self._emit(TokenType.ID)
        return self._lex_inside_action


# -------------------------------------------------------------------
if __name__ == "__main__":
    text = r"""
    sdfsdf
    Some t {{+45.e-12 0x23905.32 | }}{{ printf 2  |  |_2}}"""

    print("Lexing text:", "--------", text, "--------", sep="\n")
    print()

    tlex = TemplateLexer(text)
    for t in tlex.lex():
        print(t)
