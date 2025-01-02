# TODO: Consider operating on bytes?
# - Could be faster and/or more memory efficient.
#   - e.g. Token construction could avoid the overhead of string slicing by receiving memoryview instead.
# - Might make inspection worse, which we don't want.

from __future__ import annotations

from itertools import islice

from ._typing_compat import Optional, Self
from .errors import PyCCSyntaxError
from .token import PUNCTUATION_TOKEN_MAP, CharSets, Token, TokenKind


__all__ = ("Tokenizer",)


def _replace_line_continuations(source: str, /) -> str:
    """Remove line continuations while keeping logical and physical line numbers synced via extra newlines."""

    line_cont_count = 0
    fixed_lines: list[str] = []

    for line in source.splitlines(keepends=True):
        if line.endswith(("\\\n", "\\\r\n", "\\\r")):
            # Discard the line continuation characters.
            fixed_lines.append(line.rstrip("\r\n").removesuffix("\\"))
            line_cont_count += 1

        elif line_cont_count:
            # Splice together consecutive lines that were originally joined by line continuations.
            fixed_lines[-line_cont_count:] = ["".join((*fixed_lines[-line_cont_count:], line))]

            # Pad with newlines to match the number of line continuations so far.
            fixed_lines.append("\n" * line_cont_count)
            line_cont_count = 0

        else:
            fixed_lines.append(line)

    if line_cont_count:
        fixed_lines.append("\n" * line_cont_count)
        line_cont_count = 0

    return "".join(fixed_lines)


class Tokenizer:
    """A tokenizer for the C language, based loosely on the C11 standard.

    Iterate over an instance to get a stream of tokens.

    Parameters
    ----------
    source: str
        The string to tokenize.
    filename: str, default="<unknown>"
        The name of the file the string came from.

    Attributes
    ----------
    source: str
        The string being tokenized, after line continuation splicing.
    filename: str
        The name of the file the string came from.
    previous: int
        The index of the start of the token currently being processed.
    current: int
        The current index in the given source.
    end: int
        The length of the entire source (after modification).
    lineno: int
        The line number currently being parsed of the source. Starts at 1.

    Notes
    -----
    The long-term goal is for a run of this tokenizer to be fully roundtrip-able, i.e.::

        "".join(tok.value for tok in Tokenizer(source)) == source

    That means the tokenizer has to understand the following without source modification:
        - [x] All valid newlines.
            - [x] "\\n" (Unix)
            - [x] "\\r\\n" (Windows)
            - [x] "\\r" (older MacOS?)
        - [] Line continuations, i.e. line-ending escaped newlines.
        - [] Universal escape sequences (starting with \\u or \\U) in identifiers, char constants, and string literals.
        - [] Other escape sequences in char constants and string literals.
        - [] Missing ending newlines.
        - [] Digraphs and trigraphs (optional).
    """

    source: str
    filename: str
    previous: int
    current: int
    end: int
    lineno: int

    def __init__(self, source: str, filename: str = "<unknown>"):
        self.source = _replace_line_continuations(source)
        self.filename = filename
        self.previous = 0
        self.current = 0
        self.end = len(self.source)
        self.lineno = 1

        #: The index of the first character of the current line.
        self._current_line_start: int = 0

    @property
    def curr_char(self) -> str:
        """`str`: The character at the current index in the text."""

        return self.source[self.current]

    def __repr__(self):
        return f"{self.__class__.__name__}(filename={self.filename!r}, current={self.current!r})"

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> Token:
        # Signal that the tokenizer is done after the end of the source code.
        if self.current >= self.end:
            raise StopIteration

        # Get the token kind and set the start and end positions of the next token.
        curr_char = self.curr_char

        if self.source.startswith("//", self.current):
            self.line_comment()
            tok_kind = TokenKind.COMMENT

        elif self.source.startswith("/*", self.current):
            self.block_comment()
            tok_kind = TokenKind.COMMENT

        elif curr_char in "\r\n":
            self.newline()
            tok_kind = TokenKind.NL

        elif curr_char in CharSets.non_nl_whitespace:
            self.whitespace()
            tok_kind = TokenKind.WS

        elif curr_char.isdecimal() or (curr_char == "." and ((peek := self._peek()) is not None) and peek.isdecimal()):
            self.numeric_literal()
            tok_kind = TokenKind.PP_NUM

        elif self.source.startswith(('"', 'u8"', 'u"', 'L"', 'W"'), self.current):
            self.string_literal()
            tok_kind = TokenKind.STRING_LITERAL

        elif self.source.startswith(("'", "u'", "L'", "U'"), self.current):
            self.char_const()
            tok_kind = TokenKind.CHAR_CONST

        elif CharSets.can_start_identifier(curr_char):
            self.identifier()
            tok_kind = TokenKind.ID

        elif curr_char in CharSets.punctuation1:
            # Some punctuators overlap with different lengths. Verify the exact one.
            self.punctuation()
            tok_kind = PUNCTUATION_TOKEN_MAP[self.source[self.previous : self.current]]

        else:
            msg = "Invalid token."
            raise PyCCSyntaxError(msg, self._get_current_location())

        # Construct the token.
        tok_value = self.source[self.previous : self.current]
        col_offset, end_col_offset = self._get_current_offset()
        tok = Token(tok_kind, tok_value, self.lineno, col_offset, end_col_offset, self.filename)

        # Update position trackers.
        self.previous = self.current

        if tok_kind is TokenKind.NL:
            self.lineno += 1
            self._current_line_start = self.current

        # Return the token.
        return tok

    # region ---- Internal helpers ----

    def _peek(self) -> Optional[str]:
        """Return the next character in the source if it exists. Otherwise, return None."""

        if (self.current + 1) < self.end:
            return self.source[self.current + 1]
        else:
            return None

    def _get_current_offset(self) -> tuple[int, int]:
        """Get the start and end offset of the current potential token relative to start of the current line."""

        col_offset     = self.previous - self._current_line_start  # fmt: skip
        end_col_offset = self.current  - self._current_line_start  # fmt: skip
        return (col_offset, end_col_offset)

    def _get_current_location(self) -> tuple[str, str, int, int, int]:
        """Give location information about the current potential token.

        This is usually passed into CSyntaxError.

        Returns
        -------
        tuple[str, str, int, int, int]
            A tuple with the filename, line text, line number, column offset, and end column offset.
        """

        # TODO: Confirm that this is correct; I don't think it finds the relevant *unescaped* newline.
        line_text = self.source.splitlines()[self.lineno - 1]

        col_offset, end_col_offset = self._get_current_offset()
        return (self.filename, line_text, self.lineno, col_offset, end_col_offset)

    def _find_quote_end(self) -> None:
        """Find the end of a quote-bounded section and set the index to it."""

        # Precondition: The index points to the starting quote character.
        quote_start = self.current
        quote_char = self.curr_char
        quote_type = "char const" if (quote_char == "'") else "string literal"

        # Find the end of the quote. Ignore escaped quote characters.
        quote_end = self.current + 1
        try:
            while True:
                quote_end = self.source.index(quote_char, quote_end, self.end)
                if self.source[quote_end - 1] != "\\":
                    self.current = quote_end + 1
                    break
                quote_end += 1
        except ValueError:  # Raised by index when not found.
            msg = f"Unclosed {quote_type}."
            raise PyCCSyntaxError(msg, self._get_current_location()) from None

        # Ensure the quote is entirely on one logical line, i.e. that it doesn't contain any unescaped newlines.
        if any(
            (char == "\r" and self.source[i - 1] != "\\") or (char == "\n" and self.source[i - 1] not in "\\\r")
            for i, char in enumerate(islice(self.source, quote_start, self.current), start=quote_start)
        ):
            msg = f"Unclosed {quote_type}."
            raise PyCCSyntaxError(msg, self._get_current_location())

    # endregion ----

    # region ---- Token position handlers ----

    def line_comment(self) -> None:
        """Handle a line comment, which starts with "//"."""

        self.current += 2
        potential_ends = (self.source.find("\r", self.current), self.source.find("\n", self.current), self.end)
        self.current = min(i for i in potential_ends if i != -1)

    def block_comment(self) -> None:
        """Handle a block comment, which starts with "/*", ends with "*/", and can span multiple lines."""

        self.current += 2

        try:
            comment_end = self.source.index("*/", self.current)
        except ValueError as exc:
            msg = "Unclosed block comment."
            raise PyCCSyntaxError(msg, self._get_current_location()) from exc
        else:
            self.current = comment_end + 2

    def newline(self) -> None:
        """Handle a newline. A newline can be "\\n", "\\r\\n", or "\\r"."""

        # Account for DOS-style line endings.
        if self.curr_char == "\r":
            self.current += 1

        if self.curr_char == "\n":
            self.current += 1

    def whitespace(self) -> None:
        """Handle unimportant whitespace."""

        self.current += 1

        # Get the index of the next non-whitespace character.
        self.current = next(
            (i for i in range(self.current, self.end) if self.source[i] not in CharSets.non_nl_whitespace),
            self.current,
        )

    def numeric_literal(self) -> None:
        """Handle a somewhat relaxed numeric literal. These will be replaced during preprocessing."""

        self.current += 1

        while self.current < self.end:
            if self.curr_char in "eEpP" and ((peek := self._peek()) is not None) and peek in "+-":
                self.current += 2
            elif self.curr_char in CharSets.alphanumeric or self.curr_char == ".":
                self.current += 1
            else:
                break

    def identifier(self) -> None:
        """Handle an identifier/keyword."""

        self.current += 1

        # Get the index of the next character that isn't valid as part of an identifier.
        self.current = next(
            (i for i in range(self.current, self.end) if not CharSets.can_end_identifier(self.source[i])),
            self.current,
        )

    def punctuation(self) -> None:
        """Handle a punctuator."""

        # We have to increment by the exact length of the identifier, so we check the longest ones first.
        if self.source.startswith(CharSets.punctuation3, self.current):
            self.current += 3
        elif self.source.startswith(CharSets.punctuation2, self.current):
            self.current += 2
        else:
            self.current += 1

        if self.source[self.previous : self.current] not in PUNCTUATION_TOKEN_MAP:
            msg = "Invalid punctuation."
            raise PyCCSyntaxError(msg, self._get_current_location())

    def string_literal(self) -> None:
        """Handle a string literal, which can be utf-8, utf-16, wide, or utf-32."""

        # Move past the prefix so that the quote starter is the current character.
        if self.source.startswith("u8", self.current):
            self.current += 2
        elif self.curr_char in "uLW":
            self.current += 1

        self._find_quote_end()

    def char_const(self) -> None:
        """Handle a character constant, which can be utf-8, utf-16, wide, or utf-32."""

        # Move past the prefix so that the quote starter is the current character.
        if self.curr_char in "uLU":
            self.current += 1

        self._find_quote_end()

    # endregion ----
