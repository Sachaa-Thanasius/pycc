# TODO: Consider operating on bytes?
# - Could be faster and/or more memory efficient.
#   - e.g. Token construction could avoid the overhead of string slicing by receiving memoryview instead.
# - Might make inspection worse, which we don't want.

from __future__ import annotations

from itertools import islice

from . import _typing_compat as _t
from .errors import PycpSyntaxError
from .token import CharSets, Token, TokenKind


__all__ = ("Tokenizer",)


class Tokenizer:
    """A tokenizer for the C language based on the C11 standard.

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

    That will make it a better foundation for tooling, e.g. code formatters and linter. Consequently, the tokenizer has
    to understand the following without source modification:
        - [x] All valid newlines.
            - [x] "\\n" (Unix)
            - [x] "\\r\\n" (Windows)
            - [x] "\\r" (older MacOS?)
        - [x] Line continuations, i.e. escaped newlines at the ends of lines.
        - [] Universal escape sequences (starting with \\u or \\U) in identifiers, char constants, and string literals.
        - [] Other escape sequences in char constants and string literals.
        - [] A missing newline at the end of a non-empty source (optional?).
        - [] Digraphs and trigraphs (optional).
    """

    source: str
    filename: str
    previous: int
    current: int
    end: int
    lineno: int

    def __init__(self, source: str, filename: str = "<unknown>"):
        self.source = source
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

    def __iter__(self) -> _t.Self:
        return self

    def __next__(self) -> Token:  # noqa: PLR0912
        # Signal that the tokenizer is done after the end of the source code.
        if self.current >= self.end:
            raise StopIteration

        # Get the token kind and set the start and end positions of the next token.
        curr_char = self.curr_char

        if self.source.startswith("//", self.current):
            tok_kind = self.line_comment()

        elif self.source.startswith("/*", self.current):
            tok_kind = self.block_comment()

        elif self.source.startswith(("\\\r", "\\\n"), self.current):
            tok_kind = self.escaped_newline()

        elif curr_char in "\r\n":
            tok_kind = self.newline()

        elif curr_char in CharSets.non_nl_whitespace:
            tok_kind = self.whitespace()

        elif curr_char.isdecimal() or (curr_char == "." and ((peek := self._peek()) is not None) and peek.isdecimal()):
            tok_kind = self.numeric_literal()

        elif self.source.startswith(('"', 'u8"', 'u"', 'L"', 'W"'), self.current):
            tok_kind = self.string_literal()

        elif self.source.startswith(("'", "u'", "L'", "U'"), self.current):
            tok_kind = self.char_const()

        elif CharSets.can_start_identifier(curr_char):
            tok_kind = self.identifier()

        elif curr_char in CharSets.punctuation1:
            # Some punctuators overlap with different lengths. Verify the exact one.
            tok_kind = self.punctuation()

        else:
            msg = "Invalid token."
            raise PycpSyntaxError(msg, self._get_current_location())

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

    def _peek(self) -> _t.Optional[str]:
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

        # TODO: This probably won't work if/when line continuations are kept around.
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
            raise PycpSyntaxError(msg, self._get_current_location()) from None

        # Ensure the quote is entirely on one logical line, i.e. that it doesn't contain any unescaped newlines.
        if any(
            (char == "\r" and self.source[i - 1] != "\\") or (char == "\n" and self.source[i - 1] not in "\\\r")
            for i, char in enumerate(islice(self.source, quote_start, self.current), start=quote_start)
        ):
            msg = f"Unclosed {quote_type}."
            raise PycpSyntaxError(msg, self._get_current_location())

    # endregion ----

    # region ---- Token position handlers ----

    def line_comment(self) -> _t.Literal[TokenKind.COMMENT]:
        """Handle a line comment, which starts with "//"."""

        self.current += 2
        potential_ends = (self.source.find("\r", self.current), self.source.find("\n", self.current), self.end)
        self.current = min(i for i in potential_ends if i != -1)
        return TokenKind.COMMENT

    def block_comment(self) -> _t.Literal[TokenKind.COMMENT]:
        """Handle a block comment, which starts with "/*", ends with "*/", and can span multiple lines."""

        self.current += 2

        try:
            comment_end = self.source.index("*/", self.current)
        except ValueError as exc:
            msg = "Unclosed block comment."
            raise PycpSyntaxError(msg, self._get_current_location()) from exc
        else:
            self.current = comment_end + 2

        return TokenKind.COMMENT

    def newline(self) -> _t.Literal[TokenKind.NL]:
        """Handle a newline. A newline can be "\\n", "\\r\\n", or "\\r"."""

        # Account for DOS-style line endings.
        if self.curr_char == "\r":
            self.current += 1

        if self.curr_char == "\n":
            self.current += 1

        return TokenKind.NL

    def escaped_newline(self) -> _t.Literal[TokenKind.ESCAPED_NL]:
        """Handle an escaped (i.e. preceded with a backslash) newline."""

        self.current += 1  # For the backslash.
        self.newline()
        return TokenKind.ESCAPED_NL

    def whitespace(self) -> _t.Literal[TokenKind.WS]:
        """Handle unimportant whitespace."""

        self.current += 1

        # Get the index of the next non-whitespace character.
        self.current = next(
            (i for i in range(self.current, self.end) if self.source[i] not in CharSets.non_nl_whitespace),
            self.current,
        )

        return TokenKind.WS

    def numeric_literal(self) -> _t.Literal[TokenKind.PP_NUM]:
        """Handle a somewhat relaxed numeric literal. These will be replaced during preprocessing."""

        self.current += 1

        while self.current < self.end:
            if self.curr_char in "eEpP" and ((peek := self._peek()) is not None) and peek in "+-":
                self.current += 2
            elif self.curr_char in CharSets.alphanumeric or self.curr_char == ".":
                self.current += 1
            else:
                break

        return TokenKind.PP_NUM

    def identifier(self) -> _t.Literal[TokenKind.ID]:
        """Handle an identifier/keyword."""

        self.current += 1

        # Get the index of the next character that isn't valid as part of an identifier.
        self.current = next(
            (i for i in range(self.current, self.end) if not CharSets.can_end_identifier(self.source[i])),
            self.current,
        )

        return TokenKind.ID

    def punctuation(self) -> TokenKind:
        """Handle a punctuator."""

        # We have to increment by the exact length of the identifier, so we check the longest ones first.
        if self.source.startswith(CharSets.punctuation3, self.current):
            self.current += 3
        elif self.source.startswith(CharSets.punctuation2, self.current):
            self.current += 2
        else:
            self.current += 1

        try:
            tok_kind = TokenKind.from_punctuator(self.source[self.previous : self.current])
        except ValueError:
            msg = "Invalid punctuation."
            raise PycpSyntaxError(msg, self._get_current_location()) from None
        else:
            return tok_kind

    def string_literal(self) -> _t.Literal[TokenKind.STRING_LITERAL]:
        """Handle a string literal, which can be utf-8, utf-16, wide, or utf-32."""

        # Move past the prefix so that the quote starter is the current character.
        if self.source.startswith("u8", self.current):
            self.current += 2
        elif self.curr_char in "uLW":
            self.current += 1

        self._find_quote_end()

        return TokenKind.STRING_LITERAL

    def char_const(self) -> _t.Literal[TokenKind.CHAR_CONST]:
        """Handle a character constant, which can be utf-8, utf-16, wide, or utf-32."""

        # Move past the prefix so that the quote starter is the current character.
        if self.curr_char in "uLU":
            self.current += 1

        self._find_quote_end()

        return TokenKind.CHAR_CONST

    # endregion ----
