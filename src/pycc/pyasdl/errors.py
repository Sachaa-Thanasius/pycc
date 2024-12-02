from __future__ import annotations

from typing import Optional


__all__ = ("ASDLSyntaxError",)


class ASDLSyntaxError(Exception):
    def __init__(self, msg: str, lineno: Optional[int] = None):
        self.msg = msg
        self.lineno = lineno or "<unknown>"

    def __str__(self):
        return f"Syntax error on line {self.lineno}: {self.msg}"
