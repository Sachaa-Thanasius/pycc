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

from pycc._compat import TypeAlias


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


class CharSets:
    LEFT_META = "{{"
    RIGHT_META = "}}"
    PIPE = "|"
    DOTS = set(".")
    SIGNS = set("+-")
    DEC_DIGITS = set(string.digits)
    NUM_STARTERS = SIGNS | DEC_DIGITS
    HEX_DIGITS = set(string.hexdigits)
    ALPHANUM = DEC_DIGITS | set(string.ascii_letters) | set("_")
    EXP = set("eE")


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

    text: str
    index: int
    previous: int
    end: int
    state: Optional[SubLexer]

    def __init__(self, text: str) -> None:
        self.text = text

        self.index = 0
        self.previous = 0
        self.end = len(text)
        self.state = self.program

    def lex(self) -> LexGen:
        while self.state:
            self.state = yield from self.state()

    # region ----- Helpers -----

    @property
    def is_eof(self) -> bool:
        return self.index >= self.end

    @property
    def has_advanced(self) -> bool:
        return self.index > self.previous

    @property
    def current(self) -> str | None:
        """Get the char at self.index, or None if we're at EOF."""

        return self.text[self.index] if self.index < len(self.text) else None


    def reset(self) -> None:
        """Ignore the current token."""

        self.previous = self.index

    def accept(self, validset: set[str]) -> bool:
        """Consume current char if it's in validset, and return True.

        Otherwise don't consume it, and return False.
        """

        if self.current in validset:
            self.index += 1
            return True
        else:
            return False

    def accept_run(self, validset: set[str]) -> None:
        """Consume chars as long as they're in validset (or until EOF)."""

        while self.accept(validset):
            pass

    def emit(self, toktype: TokenType) -> Token:
        """Emit the current token."""

        tok = Token(toktype, self.text[self.previous : self.index])
        self.previous = self.index
        return tok

    # endregion

    # region ---- Rules ----

    def program(self) -> LexGen:
        # Look for the beginning of LEFT_META
        meta_start = self.text.find(CharSets.LEFT_META, self.index)
        if meta_start > 0:
            # Found. Emit all text until then (if any) and move to the left_meta state.
            self.index = meta_start
            if self.has_advanced:
                yield self.emit(TokenType.TEXT)
            return self.left_meta
        else:
            # Not found. This means we're done. There may be some text left until EOF, so emit it if there is.
            self.index = len(self.text)
            if self.has_advanced:
                yield self.emit(TokenType.TEXT)

            # Yield None to mark "no more tokens --> EOF"
            # Return None to stop the main lexing loop since there is no next state.
            yield None
            return None

    def left_meta(self) -> LexGen:
        self.index += len(CharSets.LEFT_META)
        yield self.emit(TokenType.LEFT_META)
        return self.inside_action

    def right_meta(self) -> LexGen:
        self.index += len(CharSets.RIGHT_META)
        yield self.emit(TokenType.RIGHT_META)
        return self.program

    def inside_action(self) -> LexGen:
        while True:
            # Check for RIGHT_META here before the next char is consumed,
            # to handle empty actions - {{}} - correctly.
            if self.text.startswith(CharSets.RIGHT_META, self.index):
                return self.right_meta

            c = self.current
            # Here a switch statement could be really useful...

            if c is None or c == "\n":
                msg = "Unterminated action"
                raise LexerError(msg)
            elif c.isspace():
                self.index += 1
                self.reset()
            elif c == CharSets.PIPE:
                self.index += 1
                yield self.emit(TokenType.PIPE)
            elif c in CharSets.NUM_STARTERS:
                return self.number
            elif c.isalpha() or c == "_":
                return self.identifier
            else:
                msg = "Invalid char '%s' inside action"
                raise LexerError(msg)

        # Reached EOF
        msg = "Unterminated action"
        raise LexerError(msg)

    def number(self) -> LexGen:
        # Optional sign before the number
        self.accept(CharSets.SIGNS)

        # Figure out if we'll have a decimal or hex number
        digits = CharSets.DEC_DIGITS
        if self.text.startswith("0x", self.index):
            self.index += 2
            digits = CharSets.HEX_DIGITS

        # Grab the number
        self.accept_run(digits)

        # It may be a float, followed by a dot and optionally more numbers
        if self.accept(CharSets.DOTS):
            self.accept_run(digits)

        # It may be followed by an exponent
        if self.accept(CharSets.EXP):
            self.accept(CharSets.SIGNS)
            self.accept_run(CharSets.DEC_DIGITS)

        yield self.emit(TokenType.NUMBER)
        return self.inside_action

    def identifier(self) -> LexGen:
        self.accept_run(CharSets.ALPHANUM)
        yield self.emit(TokenType.ID)
        return self.inside_action

    # endregion


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
