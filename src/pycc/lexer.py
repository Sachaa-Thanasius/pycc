from __future__ import annotations

from collections.abc import Callable, Generator

from .token import PUNCTUATION_TOKEN_MAP, CharSets, Token, TokenKind


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
        start = max(0, self.offset - 1)
        length = self.end_offset - self.offset
        return (
            f"File {self.filename!r}, line {self.lineno}\n"
            f"  {self.text}\n"
            f'  {start * " "}{length * "^"}\n'
            f"{self.__class__.__name__}: {self.msg}"
        )


def canonicalize_newlines(text: str) -> str:
    """Canonicalize newlines to "\\n" in the given text. Newlines include "\\r" and "\\r\\n"."""

    return text.replace("\r\n", "\n").replace("\r", "\n")


def replace_line_continuations(text: str) -> str:
    """Remove line continuations while keeping logical and physical line numbers synced via extra newlines."""

    line_continuation_count = 0
    fixed_lines: list[str] = []

    for line in text.splitlines(keepends=True):
        if line.endswith("\\\n"):
            # Discard the line continuation characters.
            fixed_lines.append(line.removesuffix("\\\n"))

        else:
            fixed_lines.append(line)

            if line_continuation_count:
                # Pad with newlines to match the number of line continuations so far.
                fixed_lines.append("\n" * line_continuation_count)

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
    index: int
        The index of the current character in the given text.
    end: int
        The length of the entire text.
    lineno: int
        The current line number, based on newlines. Starts at 1.
    at_bol: bool
        Whether the token being processed is at the beginning of a line.
    has_space: bool
        Whether the token being processed has whitespace preceding it.
    """

    source: str
    filename: str
    index: int
    previous: int
    end: int
    lineno: int
    at_bol: bool
    has_space: bool

    def __init__(self, source: str, filename: str) -> None:
        self.source = replace_line_continuations(canonicalize_newlines(source))
        self.filename = filename

        self.previous = 0
        self.index = 0
        self.end = len(self.source)
        self.lineno = 1
        self.at_bol = True
        self.has_space = False

    # region ---- Meta helpers ----

    @property
    def current(self) -> str:
        """The character at the current index in the text."""

        return self.source[self.index]

    def peek_with_condition(self, predicate: Callable[[str], bool]) -> bool:
        """Check if the next character in the text meets some condition.

        If there is no next character, return False.
        """

        return (self.index + 1) < self.end and predicate(self.source[self.index + 1])

    def reset(self) -> None:
        """Discard the current potential token."""

        self.previous = self.index

    def emit(self, toktype: TokenKind) -> Token:
        """Emit the current token."""

        tok = Token(
            toktype,
            self.source[self.previous : self.index],
            self.previous,
            self.end,
            self.filename,
            self.at_bol,
            self.has_space,
        )
        self.previous = self.index
        return tok

    def get_current_location(self) -> tuple[str, str, int, int, int]:
        return (self.filename, self.source.splitlines()[self.lineno - 1], self.lineno, self.previous, self.index)

    # endregion

    # region ---- Lexing loop and rules ----

    def lex(self) -> Generator[Token]:  # noqa: PLR0912
        while self.index < self.end:
            current = self.current

            if self.source.startswith("//", self.index):
                # Discard the comment.
                self.lex_line_comment()

            elif self.source.startswith("/*"):
                # Discoard the comment.
                self.lex_block_comment()

            elif current == "\n":
                # Discard the newline.
                self.lex_newline()

            elif current.isspace():
                # Discard the whitespace.
                self.lex_whitespace()

            elif current.isdecimal() or (current == "." and self.peek_with_condition(str.isdecimal)):
                self.lex_numeric_literal()
                yield self.emit(TokenKind.PP_NUM)

            elif current == '"':
                self.lex_string_literal()
                yield self.emit(TokenKind.STRING_LITERAL)

            elif self.source.startswith('u8"', self.index):
                # We don't need the first two characters; we just need to know where the string starts and ends.
                self.index += 2
                self.lex_string_literal()
                yield self.emit(TokenKind.STRING_LITERAL)

            elif self.source.startswith(('u"', 'L"', 'W"'), self.index):
                # We don't need the first character; we just need to know where the string starts and ends.
                self.index += 1
                self.lex_string_literal()
                yield self.emit(TokenKind.STRING_LITERAL)

            elif current == "'":
                self.lex_char_const()
                yield self.emit(TokenKind.CHAR_CONST)

            elif self.source.startswith(("u'", "L'", "U'"), self.index):
                # We don't need the first character; we just need to know where the characters start and end.
                self.index += 1
                self.lex_char_const()
                yield self.emit(TokenKind.CHAR_CONST)

            elif current in CharSets.identifier_start:
                # This is a valid identifier already, but try to see if it's longer.
                self.lex_identifier()
                yield self.emit(TokenKind.ID)

            elif current in CharSets.punctuation1:
                # Puncuation can have different lengths, so verify the exact one.
                self.lex_punctuation()
                yield self.emit(PUNCTUATION_TOKEN_MAP[self.source[self.previous : self.index]])

            else:
                # We have no idea what this is.
                msg = "Invalid token"
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
        """Lex a block comment, which starts with "/*", ends with "*/", and can stretch across multiple lines."""

        self.index += 2

        try:
            comment_end = self.source.index("*/", self.index)
        except ValueError as exc:
            msg = "Unclosed block comment."
            raise CSyntaxError(msg, self.get_current_location()) from exc
        else:
            self.lineno += self.source.count("\n", self.index, comment_end)
            self.index = comment_end + 2

        self.reset()
        self.has_space = True

    def lex_newline(self) -> None:
        """Lex a newline."""

        self.index += 1
        self.lineno += 1
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
            if self.current in "eEpP" and self.peek_with_condition("+-".__contains__):
                self.index += 2
            elif self.current in CharSets.alphanumeric or self.current == ".":
                self.index += 1
            else:
                break

    def lex_identifier(self) -> None:
        """Lex an identifier/keyword."""

        self.index += 1

        while self.index < self.end:
            if self.source[self.index] not in CharSets.identifier_rest:
                break
            self.index += 1

    def lex_punctuation(self) -> None:
        """Lex a punctuater."""

        # We have to increment by the exact length of the identifier, so we check the longest ones first.
        if self.source.startswith(CharSets.punctuation3, self.index):
            self.index += 3
        elif self.source.startswith(CharSets.punctuation2, self.index):
            self.index += 2
        else:
            self.index += 1

        if self.source[self.previous : self.index] not in PUNCTUATION_TOKEN_MAP:
            msg = "Invalid punctuation"
            raise CSyntaxError(msg, self.get_current_location())

    def lex_string_literal(self) -> None:
        """Lex a string literal, which can be utf-8, utf-16, wide, or utf-32."""

        self.index += 1
        self.reset()
        self.find_quoted_literal_end('"')

    def lex_char_const(self) -> None:
        """Lex a character constant, which can be utf-8, utf-16, wide, or utf-32."""

        self.index += 1
        self.reset()
        self.find_quoted_literal_end("'")

    def find_quoted_literal_end(self, quote_char: str) -> None:
        """Find the other end of a quoted literal based on a given quote character."""

        quote_start = self.index
        quote_end = self.end

        while self.index < self.end:
            quote_end = self.source.find(quote_char, self.index)

            if quote_end == -1:
                msg = "Unclosed string literal."
                raise CSyntaxError(msg, self.get_current_location())

            if self.source[quote_end - 1] != "\\":
                # If the quote wasn't escaped, only then does it count as the end of the quoted literal.
                break

            self.index = quote_end

        # Newlines break the literal. It must be entirely on one logical line.
        if self.source.find("\n", quote_start, quote_end) != -1:
            msg = "Unclosed string literal."
            raise CSyntaxError(msg, self.get_current_location())

    # endregion
