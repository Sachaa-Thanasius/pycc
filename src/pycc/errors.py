"""Custom exceptions related to the parser."""

__all__ = ("CSyntaxError",)


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
