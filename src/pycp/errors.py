"""Custom exceptions and warnings related to the parser."""

from __future__ import annotations

from . import _typing_compat as _t
from .token import Token


__all__ = (
    "PycpError",
    "PycpSyntaxError",
    "PycpWarning",
    "PycpSyntaxWarning",
    "PycpPreprocessorWarning",
)


class PycpError(Exception):
    """Base exception class for pycp."""


class PycpSyntaxError(PycpError):
    """Exception raised when a fatal issue is encountered while parsing C.

    Parameters
    ----------
    msg: str
        The exception message.
    location: tuple[str, str, int, int, int]
        Details about the text for which the error occured, including the filename, line text, line number, column
        offset, and column ending offset.

    Attributes
    ----------
    msg: str
        The exception message.
    filename: str
        The name of the file the error occured in.
    text: str
        The source code involved with the error.
    lineno: int
        The line number in the file that the error occurred at. This is 1-indexed.
    offset: int
        The column in the line where the error occurred.
    end_offset: int
        The relevant end column in the line of the error.

    Notes
    -----
    The implementation and documentation of this exception is based off of Python's builtin SyntaxError.
    """

    msg: str
    filename: str
    text: str
    lineno: int
    offset: int
    end_offset: int

    def __init__(self, msg: str, location: tuple[str, str, int, int, int]):
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

    @classmethod
    def from_token(cls, msg: str, token: Token, /) -> _t.Self:
        with open(token.filename) as fp:
            line_text = next(line for i, line in enumerate(fp, start=1) if i == token.lineno)
        return cls(msg, (token.filename, line_text, token.lineno, token.col_offset, token.end_col_offset))


class PycpWarning(Warning):
    """Base warning class for pycp."""


class PycpSyntaxWarning(PycpWarning):
    """Warning emitted while parsing C when a noncritical issue is encountered."""


class PycpPreprocessorWarning(PycpWarning):
    """Warning emitted by the "#warning" directive during preprocessing."""
