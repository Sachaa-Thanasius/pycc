"""The lexing logic for transforming a source written in C into a stream of tokens."""

from __future__ import annotations

from collections.abc import Callable, Generator, Sequence

from ._compat import Optional
from .errors import CSyntaxError
from .token import PUNCTUATION_TOKEN_MAP, CharSets, Token, TokenKind


__all__ = ("Lexer",)


def _seq_indices(
    sequence: Sequence[object],
    value: object,
    start: int = 0,
    stop: Optional[int] = None,
) -> Generator[int]:
    """Return indices where a value occurs in a sequence.

    Notes
    -----
    This is based on the iter_index itertools recipe.

    Examples
    -------
    >>> list(_seq_indices('AABCADEAF', 'A'))
    [0, 1, 4, 7]
    """

    indexer = sequence.index
    if stop is None:
        stop = len(sequence)
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
    current: int
        The index of the current character in the given source.
    end: int
        The length of the entire source.
    lineno: int
        The line number currently being parsed of the source. Starts at 1.
    at_bol: bool
        Whether the token being processed is at the beginning of a line.
    has_space: bool
        Whether the token being processed has whitespace preceding it.
    """

    source: str
    filename: str
    previous: int
    current: int
    end: int
    lineno: int
    at_bol: bool
    has_space: bool

    def __init__(self, source: str, filename: str):
        self.source = _replace_line_continuations(_canonicalize_newlines(source))
        self.filename = filename
        self.previous = 0
        self.current = 0
        self.end = len(self.source)
        self.lineno = 1
        self.at_bol = True
        self.has_space = False

    # region ---- Lexing helpers ----

    @property
    def curr_char(self) -> str:
        """The character at the current index in the text."""

        return self.source[self.current]

    def peek(self, *, predicate: Optional[Callable[[str], bool]] = None) -> bool:
        """Check if the next character in the source exists and optionally meets some condition."""

        return (self.current + 1) < self.end and ((predicate is None) or predicate(self.source[self.current + 1]))

    def reset(self) -> None:
        """Discard the current potential token span."""

        self.previous = self.current

    def emit(self, tok_kind: TokenKind, /) -> Token:
        """Emit the current token."""

        _last_cr = max(self.source.rfind("\n", 0, self.previous), 0)
        col_offset = self.previous - _last_cr - 1

        tok = Token(
            tok_kind,
            self.source[self.previous : self.current],
            self.lineno,
            col_offset,
            self.filename,
            self.at_bol,
            self.has_space,
        )
        self.reset()
        self.has_space = self.at_bol = False
        return tok

    def get_current_location(self) -> tuple[str, str, int, int, int]:
        """Give location information about the current potential token."""

        line_text = self.source.splitlines()[self.lineno - 1]
        return (self.filename, line_text, self.lineno, self.previous, self.current)

    # endregion

    # region ---- Lexing loop and rules ----

    def lex(self) -> Generator[Token]:
        while self.current < self.end:
            curr_char = self.curr_char

            # Discard line comments.
            if self.source.startswith("//", self.current):
                self.lex_line_comment()

            # Discard block comments.
            elif self.source.startswith("/*"):
                self.lex_block_comment()

            # Discard newlines.
            elif curr_char == "\n":
                self.lex_newline()

            # Discard whitespace.
            elif curr_char.isspace():
                self.lex_whitespace()

            # Capture numeric literals.
            elif curr_char.isdecimal() or (curr_char == "." and self.peek(predicate=str.isdecimal)):
                self.lex_numeric_literal()
                yield self.emit(TokenKind.PP_NUM)

            # Capture string literals.
            elif self.source.startswith(('"', 'u8"', 'u"', 'L"', 'W"'), self.current):
                self.lex_string_literal()
                yield self.emit(TokenKind.STRING_LITERAL)

            # Capture character constants.
            elif self.source.startswith(("'", "u'", "L'", "U'"), self.current):
                self.lex_char_const()
                yield self.emit(TokenKind.CHAR_CONST)

            # Capture identifiers.
            elif CharSets.can_start_identifier(curr_char):
                # This is technically a valid identifier already. Try to see if it's longer.
                self.lex_identifier()
                yield self.emit(TokenKind.ID)

            # Capture punctuators.
            elif curr_char in CharSets.punctuation1:
                # Some punctuators overlap with different lengths, so verify the exact one.
                self.lex_punctuation()
                yield self.emit(PUNCTUATION_TOKEN_MAP[self.source[self.previous : self.current]])

            # Panic for unknowns.
            else:
                msg = "Invalid token."
                raise CSyntaxError(msg, self.get_current_location())

    def lex_line_comment(self) -> None:
        """Lex a line comment, which starts with "//"."""

        self.current += 2

        try:
            self.current = self.source.index("\n", self.current)
        except ValueError:
            self.current = self.end

        self.reset()
        self.has_space = True

    def lex_block_comment(self) -> None:
        """Lex a block comment, which starts with "/*", ends with "*/", and can span multiple lines."""

        self.current += 2

        try:
            comment_end = self.source.index("*/", self.current)
        except ValueError as exc:
            msg = "Unclosed block comment."
            raise CSyntaxError(msg, self.get_current_location()) from exc
        else:
            self.current = comment_end + 2

        self.reset()
        self.has_space = True

    def lex_newline(self) -> None:
        """Lex a newline."""

        self.current += 1
        self.reset()
        self.lineno += 1
        self.at_bol = True
        self.has_space = False

    def lex_whitespace(self) -> None:
        """Lex unimportant whitespace."""

        self.current += 1
        self.reset()
        self.has_space = True

    def lex_numeric_literal(self) -> None:
        """Lex a somewhat relaxed numeric literal. These will be replaced during preprocessing."""

        self.current += 1

        while self.current < self.end:
            if self.curr_char in "eEpP" and self.peek(predicate="+-".__contains__):
                self.current += 2
            elif self.curr_char in CharSets.alphanumeric or self.curr_char == ".":
                self.current += 1
            else:
                break

    def lex_identifier(self) -> None:
        """Lex an identifier/keyword."""

        self.current += 1
        self.current = next(
            (i for i in range(self.current, self.end) if not CharSets.can_end_identifier(self.source[i])),
            self.current,
        )

    def lex_punctuation(self) -> None:
        """Lex a punctuator."""

        # We have to increment by the exact length of the identifier, so we check the longest ones first.
        if self.source.startswith(CharSets.punctuation3, self.current):
            self.current += 3
        elif self.source.startswith(CharSets.punctuation2, self.current):
            self.current += 2
        else:
            self.current += 1

        if self.source[self.previous : self.current] not in PUNCTUATION_TOKEN_MAP:
            msg = "Invalid punctuation."
            raise CSyntaxError(msg, self.get_current_location())

    def lex_string_literal(self) -> None:
        """Lex a string literal, which can be utf-8, utf-16, wide, or utf-32."""

        # Move past the prefix so that the quote starter is the current character.
        if self.source.startswith("u8", self.current):
            self.current += 2
        elif self.curr_char in "uLW":
            self.current += 1

        self.find_quote_end()

    def lex_char_const(self) -> None:
        """Lex a character constant, which can be utf-8, utf-16, wide, or utf-32."""

        # Move past the prefix so that the quote starter is the current character.
        if self.curr_char in "uLU":
            self.current += 1

        self.find_quote_end()

    def find_quote_end(self) -> None:
        """Find the end of a quote-bounded section and set the index to it."""

        # Precondition: The index points to the starting quote character.
        quote_char = self.curr_char
        quote_start = self.current
        quote_type = "char const" if (quote_char == "'") else "string literal"

        # Find the end of the quote. Escaped quote characters are ignored.
        quote_indices = _seq_indices(self.source, quote_char, self.current, self.end)
        try:
            self.current = next(i for i in quote_indices if self.source[i - 1] != "\\") + 1
        except StopIteration:
            msg = f"Unclosed {quote_type}."
            raise CSyntaxError(msg, self.get_current_location()) from None

        # The quote must be entirely on one logical line. Unescaped newlines break it.
        if any((self.source[i - 1] != "\\") for i in _seq_indices(self.source, "\n", quote_start, self.current)):
            msg = f"Unclosed {quote_type}."
            raise CSyntaxError(msg, self.get_current_location())

    # endregion
