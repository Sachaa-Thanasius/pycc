import sys
from collections import deque
from collections.abc import Generator, Iterable, Iterator
from itertools import islice, tee
from typing import Any, TypeVar, Union


_S = TypeVar("_S")
_T = TypeVar("_T")

_missing: Any = object()

__all__ = ("sliding_window", "make_iterator_peekable", "lookahead")


def sliding_window(iterable: Iterable[_T], n: int) -> Generator[tuple[_T, ...]]:
    """Collect data into overlapping fixed-length chunks or blocks.

    Notes
    -----
    This is a recipe from the Python itertools docs.

    Examples
    --------
    >>> ["".join(window) for window in sliding_window("ABCDEFG", 4)]
    ['ABCD', 'BCDE', 'CDEF', 'DEFG']
    """

    iterator = iter(iterable)
    window = deque(islice(iterator, n - 1), maxlen=n)
    for x in iterator:
        window.append(x)
        yield tuple(window)


def make_iterator_peekable(iterator: Iterator[_T]) -> Iterator[_T]:
    """Make an iterator peekable via tee.

    Use the returned iterator instead of the original.
    """

    # This workaround is needed due to changes in 3.14.
    # ref: https://github.com/python/cpython/issues/126701

    if sys.version_info >= (3, 14):
        [iterator] = tee(iterator, 1)
    else:
        [_, iterator] = tee(iterator, 2)

    return iterator


def lookahead(tee_iterator: Iterator[_T], default: _S = _missing) -> Union[_T, _S]:
    """Return the next value without moving the input forward.

    The given iterator must have been created using itertools.tee().

    Notes
    -----
    This is a modified version of a recipe from the Python itertools docs.

    Examples
    --------
    >>> iterator = iter('abcdef')
    >>> iterator = make_iterator_peekable(iterator)
    >>> next(iterator)                  # Move the iterator forward
    'a'
    >>> lookahead(iterator)             # Check next value
    'b'
    >>> next(iterator)                  # Continue moving forward
    'b'
    """

    # This workaround is needed due to changes in 3.14.
    # ref: https://github.com/python/cpython/issues/126701

    if sys.version_info >= (3, 14):
        [forked_iterator] = tee(tee_iterator, 1)
    else:
        [_, forked_iterator] = tee(tee_iterator, 2)

    if default is _missing:
        return next(forked_iterator)
    else:
        return next(forked_iterator, default)
