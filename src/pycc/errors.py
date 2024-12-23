"""Custom exceptions and warnings related to the parser."""

from ._compat import Self
from .token import Token


__all__ = (
    "PyCCError",
    "CSyntaxError",
    "PyCCWarning",
    "CSyntaxWarning",
    "CPreprocessorWarning",
)


class PyCCError(Exception):
    """Base exception class for pycc."""


class CSyntaxError(PyCCError):
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
    def from_token(cls, msg: str, token: Token, /) -> Self:
        with open(token.filename, encoding="utf-8") as fp:
            line_text = next(line for i, line in enumerate(fp, start=1) if i == token.lineno)
        return cls(msg, (token.filename, line_text, token.lineno, token.col_offset, token.end_col_offset))


class PyCCWarning(Warning):
    """Base warning class for pycc."""


class CSyntaxWarning(PyCCWarning):
    """Warnings related to issues encountered while parsing C."""


class CPreprocessorWarning(PyCCWarning):
    """Warnings raised during preprocessing by the #warning directive."""
