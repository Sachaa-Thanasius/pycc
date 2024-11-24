# ruff: noqa: PLW2901

from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Any, Optional, TypeVar, Union

from ._compat import TypeAlias
from .token import KEYWORD_TOKEN_MAP, Token, TokenKind


_T = TypeVar("_T")

_LexGen: TypeAlias = Generator[Optional["Token"], Any, Optional["_SubLexer"]]
_SubLexer: TypeAlias = Callable[[], _LexGen]
_SetLike: TypeAlias = Union[set[_T], frozenset[_T]]


class CSyntaxError(Exception):
    pass


class CharSets:
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


class Lexer:
    """A lexer Initialize with the input string, and then call lex() which generates tokens.
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
    previous: int
        An integer pointing to the start of the currently processed token.
    state: SubLexer | None
        One of the state functions. Each such function yields the tokens it finds and then returns the next state
        function. When EOF is encountered, None is returned as the new state.
    """

    text: str
    index: int
    previous: int
    end: int
    state: Optional[_SubLexer]

    def __init__(self, text: str) -> None:
        self.text = self.replace_line_continuations(self.canonicalize_newlines(text))
        self.previous = 0
        self.index = 0
        self.end = len(self.text)
        self.state = self.file

    @staticmethod
    def canonicalize_newlines(text: str) -> str:
        """Canonicalize newlines to "\\n" in the given text."""

        return text.replace("\r\n", "\n").replace("\r", "\n")

    @staticmethod
    def replace_line_continuations(text: str) -> str:
        """Remove line continuations while keeping logical and physical line numbers synced via extra newlines."""

        fixed_lines: list[str] = []
        line_continuation_count = 0

        for line in text.splitlines(keepends=True):
            if line.endswith("\\\n"):
                line_continuation_count += 1
                fixed_lines.append(line.removesuffix("\\\n"))

            elif line_continuation_count:
                # Pad with as many newlines as have been removed from the continuation merging.
                fixed_lines.append(line + "\n" * line_continuation_count)
                line_continuation_count = 0

            else:
                fixed_lines.append(line)

        return "".join(fixed_lines)

    def lex(self) -> _LexGen:
        while self.state is not None:
            self.state = yield from self.state()

    # region ---- Helpers ----

    @property
    def is_eof(self) -> bool:
        return self.index >= self.end

    @property
    def has_advanced(self) -> bool:
        return self.index > self.previous

    @property
    def current(self) -> Optional[str]:
        """Get the char at self.index, or None if we're at EOF."""

        return self.text[self.index] if not self.is_eof else None

    @property
    def current_group(self) -> Optional[str]:
        return self.text[self.previous : self.index] if not self.is_eof else None

    def reset(self) -> None:
        """Ignore the current token."""

        self.previous = self.index

    def skip(self, num: int) -> None:
        self.previous = self.index = self.index + num

    def accept(self, validset: _SetLike[str]) -> bool:
        """Consume current char if it's in validset, and return True.

        Otherwise don't consume it, and return False.
        """

        if self.current in validset:
            self.index += 1
            return True
        else:
            return False

    def accept_run(self, validset: _SetLike[str]) -> None:
        """Consume chars as long as they're in validset (or until EOF)."""

        while self.accept(validset):
            pass

    def emit(self, toktype: TokenKind) -> Token:
        """Emit the current token."""

        tok = Token(toktype, self.text[self.previous : self.index])
        self.previous = self.index
        return tok

    # endregion

    # region ---- Rules ----

    def file(self) -> _LexGen:
        current = self.text[self.index]

        if current == "\n":
            self.index += 1
            has_space = False
            return self.file

        elif current.isspace():
            self.index += 1
            has_space = True
            return self.file

        elif self.text.startswith("//", self.index):
            return self.line_comment

        elif self.text.startswith("/*", self.index):
            return self.block_comment

        elif current.isdigit() or (current == "." and self.text[self.index + 1].isdigit()):
            return self.numeric_literal

        elif current == '"':
            return self.string_literal

        elif self.text.startswith('u8"', self.index):
            return self.utf8_string_literal

        elif self.text.startswith('u"', self.index):
            return self.utf16_string_literal

        elif self.text.startswith('L"', self.index):
            return self.wide_string_literal

        elif self.text.startswith('W"', self.index):
            return self.utf32_string_literal

        elif current == "'":
            return self.char_literal

        elif self.text.startswith("u'", self.index):
            return self.utf16_char_literal

        elif self.text.startswith("L'", self.index):
            return self.wide_char_literal

        elif self.text.startswith("U'", self.index):
            return self.utf32_char_literal

        elif self.is_identifier():
            return self.identifier

        elif self.is_punctuation():
            return self.punctuation

        yield None  # Signal the end of the tokens.
        return None  # Stop the lexing loop.

    def line_comment(self) -> _LexGen:
        # Skip the comment starter.
        self.skip(2)

        try:
            self.index = self.text.index("\n", self.index)
        except ValueError:
            self.index = self.end
            yield self.emit(TokenKind.LINE_COMMENT)
        else:
            yield self.emit(TokenKind.LINE_COMMENT)

            # Skip the comment ender if found.
            self.skip(1)

        return self.file

    def block_comment(self) -> _LexGen:
        # Skip the comment starter.
        self.skip(2)

        # Skip the comment-ending if found.
        try:
            self.index = self.text.index("*/", self.index)
        except ValueError as exc:
            msg = "Unclosed block comment"
            raise CSyntaxError(msg) from exc

        yield self.emit(TokenKind.BLOCK_COMMENT)

        return self.file

    def numeric_literal(self): ...

    def string_literal(self) -> _LexGen:
        # Skip the quote start.
        self.skip(1)

        try:
            self.index = self.text.index('"', self.index)
        except ValueError as exc:
            msg = "Unclosed string literal"
            raise CSyntaxError(msg) from exc

        yield self.emit(TokenKind.STRING_LITERAL)

        return self.file

    def utf8_string_literal(self): ...

    def utf16_string_literal(self): ...

    def wide_string_literal(self): ...

    def utf32_string_literal(self): ...

    def char_literal(self): ...

    def utf16_char_literal(self): ...

    def wide_char_literal(self): ...

    def utf32_char_literal(self): ...

    def identifier(self) -> _LexGen:
        self.accept(CharSets.identifier_start)
        self.accept_run(CharSets.identifier_rest)

        try:
            tok_type = KEYWORD_TOKEN_MAP[self.current_group]  # pyright: ignore [reportArgumentType]
        except KeyError:
            tok_type = TokenKind.ID

        yield self.emit(tok_type)

    def punctuation(self): ...

    # endregion
