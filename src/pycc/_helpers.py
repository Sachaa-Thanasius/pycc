from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from typing import Generic, TypeVar

from ._compat import Self


_T = TypeVar("_T")


__all__ = ("PeekableIterator",)


class PeekableIterator(Generic[_T]):
    """Wrap an iterable to allow lookahead during iteration.

    Notes
    -----
    This is a modified version of more_itertools.peekable.
    """

    def __init__(self, iterable: Iterable[_T]) -> None:
        self._it = iter(iterable)
        self._cache: deque[_T] = deque()

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> _T:
        if self._cache:
            return self._cache.popleft()
        else:
            return next(self._it)

    def peek(self) -> _T:
        """Peek at the upcoming value."""

        if not self._cache:
            self._cache.append(next(self._it))
        return self._cache[0]

    def has_more(self) -> bool:
        """Check if anything is left in the iterator."""

        try:
            self.peek()
        except StopIteration:
            return False
        else:
            return True
