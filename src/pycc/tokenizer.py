"""The lexing logic for transforming a source written in C into a stream of tokens."""

from __future__ import annotations

from collections.abc import Callable, Generator

from ._compat import Optional, Self
from .errors import CSyntaxError
from .token import PUNCTUATION_TOKEN_MAP, CharSets, Token, TokenKind


__all__ = ("Tokenizer",)


def _str_indices(text: str, value: str, start: int = 0, stop: Optional[int] = None) -> Generator[int]:
    """Yield indices where a value occurs in a string, from left to right.

    Notes
    -----
    This is based on the iter_index itertools recipe.

    Examples
    -------
    >>> list(_str_indices('AABCADEAF', 'A'))
    [0, 1, 4, 7]
    """

    indexer = text.index
    if stop is None:
        stop = len(text)
    idx = start
    try:
        while True:
            yield (idx := indexer(value, idx, stop))
            idx += 1
    except ValueError:
        pass


def _str_rindices(text: str, value: str, start: int = 0, stop: Optional[int] = None) -> Generator[int]:
    """Yield indices where a value occurs in a string, from right to left.

    Notes
    -----
    This is based on the iter_index itertools recipe.

    Examples
    -------
    >>> list(_str_rindices('AABCADEAF', 'A'))
    [7, 4, 1, 0]
    """

    rindexer = text.rindex
    if stop is None:
        stop = len(text)
    idx = stop
    try:
        while True:
            yield (idx := rindexer(value, start, idx))
            idx -= 1
    except ValueError:
        pass


def _canonicalize_newlines(source: str, /) -> str:
    """Canonicalize newlines to linefeed ("\\n") in the given source. Newlines include "\\r" and "\\r\\n"."""

    return source.replace("\r\n", "\n").replace("\r", "\n")


def _replace_line_continuations(source: str, /) -> str:
    """Remove line continuations while keeping logical and physical line numbers synced via extra newlines.

    This assumes newlines in the given source have already been canonicalized to linefeed ("\\n").
    """

    line_cont_count = 0
    fixed_lines: list[str] = []

    for line in source.splitlines(keepends=True):
        if line.endswith("\\\n"):
            # Discard the line continuation characters.
            fixed_lines.append(line.removesuffix("\\\n"))
            line_cont_count += 1

        elif line_cont_count:
            # Splice together consecutive lines that originally ended with line continuations.
            fixed_lines[-line_cont_count:] = ["".join((*fixed_lines[-line_cont_count:], line))]

            # Pad with newlines to match the number of line continuations so far.
            fixed_lines.extend("\n" * line_cont_count)
            line_cont_count = 0

        else:
            fixed_lines.append(line)

    if line_cont_count:
        fixed_lines.extend("\n" * line_cont_count)
        line_cont_count = 0

    return "".join(fixed_lines)


class Tokenizer:
    """A tokenizer for the C language based on the C11 standard.

    Parameters
    ----------
    source: str
        The string to tokenize.
    filename: str, default="<unknown>"
        The name of the file the string came from.

    Attributes
    ----------
    source: str
        The string being tokenized, after newline canonicalization and line continuation splicing.
    filename: str
        The name of the file the string came from.
    previous: int
        The index of the start of the token currently being processed.
    current: int
        The index of the current character in the given source.
    end: int
        The length of the entire source (after modification).
    lineno: int
        The line number currently being parsed of the source. Starts at 1.

    Notes
    -----
    The long-term goal is for a run of this tokenizer to be fully roundtrip-able, i.e. the result of combining the
    values of the tokens should match the original source code exactly. That means understanding the following without
    source modification:

        - Digraphs and trigraphs.
        - All valid newlines, e.g. "\\n", "\\r\\n", "\\r".
        - Line continuations.

    Unfortunately, these are currently either a) unhandled, or b) taken care of via source modification.
    """

    source: str
    filename: str
    previous: int
    current: int
    end: int
    lineno: int

    def __init__(self, source: str, filename: str = "<unknown>"):
        self.source = _canonicalize_newlines(_replace_line_continuations(source))
        self.filename = filename
        self.previous = 0
        self.current = 0
        self.end = len(self.source)
        self.lineno = 1

    @property
    def curr_char(self) -> str:
        """str: The character at the current index in the text."""

        return self.source[self.current]

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> Token:
        # -- Broadcast that the tokenizer is done past the end of the given source code.
        if self.current >= self.end:
            raise StopIteration

        # -- Get the kind and set the start and end positions of the next token.
        curr_char = self.curr_char

        if self.source.startswith("//", self.current):
            self.lex_line_comment()
            kind = TokenKind.COMMENT

        elif self.source.startswith("/*", self.current):
            self.lex_block_comment()
            kind = TokenKind.COMMENT

        elif curr_char == "\n":
            self.lex_newline()
            kind = TokenKind.NEWLINE

        elif curr_char.isspace():
            self.lex_whitespace()
            kind = TokenKind.WS

        elif curr_char.isdecimal() or (curr_char == "." and self._peek(predicate=str.isdecimal)):
            self.lex_numeric_literal()
            kind = TokenKind.PP_NUM

        elif self.source.startswith(('"', 'u8"', 'u"', 'L"', 'W"'), self.current):
            self.lex_string_literal()
            kind = TokenKind.STRING_LITERAL

        elif self.source.startswith(("'", "u'", "L'", "U'"), self.current):
            self.lex_char_const()
            kind = TokenKind.CHAR_CONST

        elif CharSets.can_start_identifier(curr_char):
            self.lex_identifier()
            kind = TokenKind.ID

        elif curr_char in CharSets.punctuation1:
            # Some punctuators overlap with different lengths. Verify the exact one.
            self.lex_punctuation()
            kind = PUNCTUATION_TOKEN_MAP[self.source[self.previous : self.current]]

        else:
            msg = "Invalid token."
            raise CSyntaxError(msg, self._get_current_location())

        # -- Construct the token.
        tok_value = self.source[self.previous : self.current]
        col_offset, end_col_offset = self._get_col_offsets()
        tok = Token(kind, tok_value, self.lineno, col_offset, end_col_offset, self.filename)

        # -- Reset the token position tracking.
        self.previous = self.current

        if kind is TokenKind.NEWLINE:
            self.lineno += 1

        # -- Return the token.
        return tok

    def _peek(self, *, predicate: Optional[Callable[[str], bool]] = None) -> bool:
        """Check if the next character in the source exists and optionally meets some condition."""

        return (self.current + 1) < self.end and ((predicate is None) or predicate(self.source[self.current + 1]))

    def _get_col_offsets(self) -> tuple[int, int]:
        """Get the column offsets for the start and end of the current potential token.

        These are relative to the nearest preceding unescaped newline.
        """

        _previous_newlines = _str_rindices(self.source, "\n", 0, self.previous)
        _last_unescaped_nl = next((i for i in _previous_newlines if self.source[i - 1] != "\\"), 0)

        col_offset = self.previous - _last_unescaped_nl - 1
        end_col_offset = col_offset + (self.current - self.previous)

        return (col_offset, end_col_offset)

    def _get_current_location(self) -> tuple[str, str, int, int, int]:
        """Give location information about the current potential token."""

        line_text = self.source.splitlines()[self.lineno - 1]
        col_offset, end_col_offset = self._get_col_offsets()
        return (self.filename, line_text, self.lineno, col_offset, end_col_offset)

    def _find_quote_end(self) -> None:
        """Find the end of a quote-bounded section and set the index to it."""

        # Precondition: The index points to the starting quote character.
        quote_start = self.current
        quote_char = self.curr_char
        quote_type = "char const" if (quote_char == "'") else "string literal"

        # Find the end of the quote. Escaped quote characters are ignored.
        quote_indices = _str_indices(self.source, quote_char, self.current + 1, self.end)
        try:
            self.current = next(i for i in quote_indices if self.source[i - 1] != "\\") + 1
        except StopIteration:
            msg = f"Unclosed {quote_type}."
            raise CSyntaxError(msg, self._get_current_location()) from None

        # The quote must be entirely on one logical line. Ensure it doesn't contain any unescaped newlines.
        if any((self.source[i - 1] != "\\") for i in _str_indices(self.source, "\n", quote_start, self.current)):
            msg = f"Unclosed {quote_type}."
            raise CSyntaxError(msg, self._get_current_location())

    def lex_line_comment(self) -> None:
        """Lex a line comment, which starts with "//"."""

        self.current += 2

        try:
            self.current = self.source.index("\n", self.current)
        except ValueError:
            self.current = self.end

    def lex_block_comment(self) -> None:
        """Lex a block comment, which starts with "/*", ends with "*/", and can span multiple lines."""

        self.current += 2

        try:
            comment_end = self.source.index("*/", self.current)
        except ValueError as exc:
            msg = "Unclosed block comment."
            raise CSyntaxError(msg, self._get_current_location()) from exc
        else:
            self.current = comment_end + 2

    def lex_newline(self) -> None:
        """Lex a newline."""

        # NOTE: This is currently sparse, but that'll change if we handle all newlines without canonicalization.

        self.current += 1

    def lex_whitespace(self) -> None:
        """Lex unimportant whitespace."""

        self.current += 1

        # Get the index of the next non-whitespace character.
        self.current = next((i for i in range(self.current, self.end) if not self.source[i].isspace()), self.current)

    def lex_numeric_literal(self) -> None:
        """Lex a somewhat relaxed numeric literal. These will be replaced during preprocessing."""

        self.current += 1

        while self.current < self.end:
            if self.curr_char in "eEpP" and self._peek(predicate="+-".__contains__):
                self.current += 2
            elif self.curr_char in CharSets.alphanumeric or self.curr_char == ".":
                self.current += 1
            else:
                break

    def lex_identifier(self) -> None:
        """Lex an identifier/keyword."""

        self.current += 1

        # Get the index of the next character that isn't valid as part of an identifier.
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
            raise CSyntaxError(msg, self._get_current_location())

    def lex_string_literal(self) -> None:
        """Lex a string literal, which can be utf-8, utf-16, wide, or utf-32."""

        # Move past the prefix so that the quote starter is the current character.
        if self.source.startswith("u8", self.current):
            self.current += 2
        elif self.curr_char in "uLW":
            self.current += 1

        self._find_quote_end()

    def lex_char_const(self) -> None:
        """Lex a character constant, which can be utf-8, utf-16, wide, or utf-32."""

        # Move past the prefix so that the quote starter is the current character.
        if self.curr_char in "uLU":
            self.current += 1

        self._find_quote_end()
