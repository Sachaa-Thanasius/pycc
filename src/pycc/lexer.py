from __future__ import annotations

from collections.abc import Callable, Generator, Sequence

from ._compat import Optional
from .token import PUNCTUATION_TOKEN_MAP, CharSets, Token, TokenKind


def _seq_index(sequence: Sequence[object], value: object, start: int = 0, stop: Optional[int] = None) -> Generator[int]:
    """Return indices where a value occurs in a sequence.

    Notes
    -----
    This is based on the iter_index recipe in the CPython itertools docs.

    Examples
    -------
    >>> list(seq_index('AABCADEAF', 'A'))
    [0, 1, 4, 7]
    """

    indexer = sequence.index
    stop = len(sequence) if (stop is None) else stop
    i = start
    try:
        while True:
            yield (i := indexer(value, i, stop))
            i += 1
    except ValueError:
        pass


def _canonicalize_newlines(source: str, /) -> str:
    """Canonicalize newlines to "\\n" in the given text. Newlines include "\\r" and "\\r\\n"."""

    return source.replace("\r\n", "\n").replace("\r", "\n")


def _replace_line_continuations(source: str, /) -> str:
    """Remove line continuations while keeping logical and physical line numbers synced via extra newlines."""

    line_continuation_count = 0
    fixed_lines: list[str] = []

    for line in source.splitlines(keepends=True):
        if line.endswith("\\\n"):
            # Discard the line continuation characters.
            fixed_lines.append(line.removesuffix("\\\n"))
            line_continuation_count += 1

        else:
            fixed_lines.append(line)

            if line_continuation_count:
                # Pad with newlines to match the number of line continuations so far.
                fixed_lines.append("\n" * line_continuation_count)
                line_continuation_count = 0

    return "".join(fixed_lines)


class CSyntaxError(Exception):
    """Exception raised when attempting to lex invalid C syntax."""

    msg: str
    filename: str
    text: str
    lineno: int
    offset: int
    end_offset: int

    def __init__(self, msg: str, location: tuple[str, str, int, int, int]) -> None:
        super().__init__()
        self.msg = msg
        self.filename, self.text, self.lineno, self.offset, self.end_offset = location

    def __str__(self):
        offset = max(0, self.offset)
        length = self.end_offset - self.offset
        return (
            f"File {self.filename!r}, line {self.lineno}\n"
            f"  {self.text}\n"
            f'  {offset * " "}{length * "^"}\n'
            f"{self.__class__.__name__}: {self.msg}"
        )


class Lexer:
    """A lexer for the C language. The main entrypoint is the lex() method.

    Parameters
    ----------
    source: str
        The string to lex.
    filename: str
        The name of the file the string came from.

    Attributes
    ----------
    source: str
        The string being lexed.
    filename: str
        The name of the file the string came from.
    previous: int
        The index of the start of the token currently being processed.
    index: int
        The index of the current character in the given source.
    end: int
        The length of the entire source.
    at_bol: bool
        Whether the token being processed is at the beginning of a line.
    has_space: bool
        Whether the token being processed has whitespace preceding it.
    """

    source: str
    filename: str
    previous: int
    index: int
    end: int
    at_bol: bool
    has_space: bool

    def __init__(self, source: str, filename: str) -> None:
        self.source = _replace_line_continuations(_canonicalize_newlines(source))
        self.filename = filename
        self.previous = 0
        self.index = 0
        self.end = len(self.source)
        self.at_bol = True
        self.has_space = False

    # region ---- Lexing helpers ----

    @property
    def current(self) -> str:
        """The character at the current index in the text."""

        return self.source[self.index]

    def peek(self, *, predicate: Optional[Callable[[str], bool]] = None) -> bool:
        """Check if the next character in the source exists and optionally meets some condition."""

        return (self.index + 1) < self.end and (
            predicate(self.source[self.index + 1]) if (predicate is not None) else True
        )

    def reset(self) -> None:
        """Discard the current potential token span."""

        self.previous = self.index

    def emit(self, tok_kind: TokenKind) -> Token:
        """Emit the current token."""

        tok = Token(
            tok_kind,
            self.source[self.previous : self.index],
            self.previous,
            self.end,
            self.filename,
            self.at_bol,
            self.has_space,
        )
        self.reset()
        return tok

    def get_current_location(self) -> tuple[str, str, int, int, int]:
        lineno = self.source.count("\n", 0, self.previous)
        line = self.source.splitlines()[lineno]
        return (self.filename, line, lineno, self.previous, self.index)

    # endregion

    # region ---- Lexing loop and rules ----

    def lex(self) -> Generator[Token]:
        while self.index < self.end:
            current = self.current

            # Discard line comments.
            if self.source.startswith("//", self.index):
                self.lex_line_comment()

            # Discard block comments.
            elif self.source.startswith("/*"):
                self.lex_block_comment()

            # Discard newlines.
            elif current == "\n":
                self.lex_newline()

            # Discard whitespace.
            elif current.isspace():
                self.lex_whitespace()

            # Capture numeric literals.
            elif current.isdecimal() or (current == "." and self.peek(predicate=str.isdecimal)):
                self.lex_numeric_literal()
                yield self.emit(TokenKind.PP_NUM)

            # Capture string literals.
            elif self.source.startswith(('"', 'u8"', 'u"', 'L"', 'W"'), self.index):
                self.lex_string_literal()
                yield self.emit(TokenKind.STRING_LITERAL)

            # Capture character constants.
            elif self.source.startswith(("'", "u'", "L'", "U'"), self.index):
                self.lex_char_const()
                yield self.emit(TokenKind.CHAR_CONST)

            # Capture identifiers.
            elif current in CharSets.identifier_start:
                # This is technically a valid identifier already, but try to see if it's longer.
                self.lex_identifier()
                yield self.emit(TokenKind.ID)

            # Capture punctuators.
            elif current in CharSets.punctuation1:
                # Some punctuators overlap with different lengths, so verify the exact one.
                self.lex_punctuation()
                yield self.emit(PUNCTUATION_TOKEN_MAP[self.source[self.previous : self.index]])

            # Panic for unknowns.
            else:
                msg = "Invalid token."
                raise CSyntaxError(msg, self.get_current_location())

    def lex_line_comment(self) -> None:
        """Lex a line comment, which starts with "//"."""

        self.index += 2

        try:
            self.index = self.source.index("\n", self.index)
        except ValueError:
            self.index = self.end

        self.reset()
        self.has_space = True

    def lex_block_comment(self) -> None:
        """Lex a block comment, which starts with "/*", ends with "*/", and can span multiple lines."""

        self.index += 2

        try:
            comment_end = self.source.index("*/", self.index)
        except ValueError as exc:
            msg = "Unclosed block comment."
            raise CSyntaxError(msg, self.get_current_location()) from exc
        else:
            self.index = comment_end + 2

        self.reset()
        self.has_space = True

    def lex_newline(self) -> None:
        """Lex a newline."""

        self.index += 1
        self.reset()
        self.at_bol = True
        self.has_space = False

    def lex_whitespace(self) -> None:
        """Lex unimportant whitespace."""

        self.index += 1
        self.reset()
        self.has_space = True

    def lex_numeric_literal(self) -> None:
        """Lex a somewhat relaxed numeric literal. These will be more specified after preprocessing."""

        self.index += 1

        while self.index < self.end:
            if self.current in "eEpP" and self.peek(predicate="+-".__contains__):
                self.index += 2
            elif self.current in CharSets.alphanumeric or self.current == ".":
                self.index += 1
            else:
                break

    def lex_identifier(self) -> None:
        """Lex an identifier/keyword."""

        self.index += 1
        while (self.index < self.end) and (self.current in CharSets.identifier_rest):
            self.index += 1

    def lex_punctuation(self) -> None:
        """Lex a punctuator."""

        # We have to increment by the exact length of the identifier, so we check the longest ones first.
        if self.source.startswith(CharSets.punctuation3, self.index):
            self.index += 3
        elif self.source.startswith(CharSets.punctuation2, self.index):
            self.index += 2
        else:
            self.index += 1

        if self.source[self.previous : self.index] not in PUNCTUATION_TOKEN_MAP:
            msg = "Invalid punctuation."
            raise CSyntaxError(msg, self.get_current_location())

    def lex_string_literal(self) -> None:
        """Lex a string literal, which can be utf-8, utf-16, wide, or utf-32."""

        # Move past the prefix so that the current character is the quote starter.
        if self.source.startswith("u8"):
            self.index += 2
        elif self.current in "uLW":
            self.index += 1

        self.find_quote_end()

    def lex_char_const(self) -> None:
        """Lex a character constant, which can be utf-8, utf-16, wide, or utf-32."""

        # Move past the prefix so that the current character is the quote starter.
        if self.current in "uLU":
            self.index += 1

        self.find_quote_end()

    def find_quote_end(self) -> None:
        """Find the end of a quote-bounded section and set the index to it."""

        # Precondition: The index points to the starting quote character.
        quote_char = self.current
        quote_start = self.index
        quote_type = "char const" if (quote_char == "'") else "string literal"

        # Find the end. Escaped quote characters are ignored.
        for quote_idx in _seq_index(self.source, quote_char, self.index, self.end):
            if self.source[quote_idx - 1] != "\\":
                self.index = quote_idx + 1
                break
        else:
            msg = f"Unclosed {quote_type}."
            raise CSyntaxError(msg, self.get_current_location())

        # Unescaped newlines break the quote. It must be entirely on one logical line.
        if any(
            self.source[newline_idx - 1] != "\\"
            for newline_idx in _seq_index(self.source, "\n", quote_start, self.index)
        ):
            msg = f"Unclosed {quote_type}."
            raise CSyntaxError(msg, self.get_current_location())

    # endregion
