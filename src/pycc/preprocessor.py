from __future__ import annotations

import os
import sys
import warnings
from collections.abc import Iterable, Iterator
from itertools import chain, tee

from ._compat import TYPE_CHECKING, Optional, Self
from .errors import CPreprocessorWarning, CSyntaxError, CSyntaxWarning
from .token import Token, TokenKind
from .tokenizer import Tokenizer


__all__ = ("Preprocessor",)

if sys.version_info >= (3, 10):
    from itertools import pairwise as _pairwise
elif TYPE_CHECKING:
    from collections.abc import Generator
    from typing import TypeVar

    _T = TypeVar("_T")

    def _pairwise(iterable: Iterable[_T], /) -> Generator[tuple[_T, _T]]: ...
else:

    def _pairwise(iterable: Iterable) -> tuple:
        iterator = iter(iterable)
        first = next(iterator, None)
        for second in iterator:
            yield (first, second)
            first = second


def _is_not_ws_token(tok: Token, /) -> bool:
    return tok.kind is not TokenKind.WS


class Preprocessor:
    """A preprocessor for the C language based on the C11 standard.

    Iterate over it to get a stream of tokens.

    Parameters
    ----------
    tokens: Iterable[Token]
        An iterable of unpreprocessed tokens.
    local_dir: str, default=""
        The directory to consider as the current working directory for the purpose of include path searching. Defaults
        to the empty string.
    include_dirs: list[str]
        A list of directories to search for include paths.
    ignore_missing_includes: bool
        Whether to ignore includes directives that point at files that cannot be found by the preprocessor.
    """

    tokens: Iterator[Token]
    local_dir: str
    include_dirs: list[str]
    ignore_missing_includes: bool

    def __init__(self, tokens: Iterable[Token], local_dir: str = ""):
        self.tokens = iter(tokens)
        self.local_dir = local_dir
        self.include_dirs = []
        self.ignore_missing_includes = False

        self._prev_tok: Optional[Token] = None

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> Token:
        # -- Broadcast that the preprocesser is done after the end of the token stream.
        try:
            curr_tok = next(self.tokens)
        except StopIteration as exc:
            raise StopIteration from exc

        # TODO: Check all identifiers to see if they are macros, and if so, expand them.

        # -- Process preprocessor directives.
        if curr_tok.kind is TokenKind.PP_OCTO and (self._prev_tok is None or self._prev_tok.kind is TokenKind.NEWLINE):
            directive_name_tok = next(filter(_is_not_ws_token, self.tokens), None)

            # null directive
            if directive_name_tok is not None and directive_name_tok.kind is TokenKind.NEWLINE:
                ...

            if directive_name_tok is None:
                pass

            elif directive_name_tok.value == "include":
                self.pp_include()

            elif directive_name_tok.value == "pragma":
                self.pp_pragma()

            elif directive_name_tok.value == "error":
                self.pp_error()

            elif directive_name_tok.value == "warning":
                self.pp_warning()

            else:
                msg = "Invalid preprocessor directive."
                raise CSyntaxError.from_token(msg, directive_name_tok)

        self._prev_tok = curr_tok

    def _peek(self) -> Optional[Token]:
        self.tokens, forked_tokens = tee(self.tokens)
        return next(forked_tokens, None)

    def _prepend(self, iterable: Iterable[Token], /) -> None:
        self.tokens = chain(iter(iterable), self.tokens)

    def _skip_line(self) -> None:
        """Skip tokens until the next newline is found.

        This is for directives where extra tokens are technically allowed before the newline ends them.
        """

        next_tok = next(self.tokens, None)
        if (next_tok is None) or (next_tok.kind is TokenKind.NEWLINE):
            return

        warnings.warn_explicit("Extra tokens.", CSyntaxWarning, next_tok.filename, next_tok.lineno)

        next_line_start = next((t for t in self.tokens if t.kind is TokenKind.NEWLINE), None)
        if next_line_start is not None:
            self._prepend([next_line_start])

    def _find_include_path(self, potential_path: str) -> str:
        for include_dir in chain([self.local_dir], self.include_dirs):
            candidate = os.path.normpath(os.path.join(include_dir, potential_path))
            if os.path.exists(candidate):
                return candidate

        # Default to the original path as a last resort.
        return potential_path

    def pp_include(self) -> None:
        """#include directive: Find the included file and prepend its preprocessed tokens to our tokens."""

        path_start_tok = next(self.tokens)

        # Pattern 1: #include "foo.h"
        if path_start_tok.kind is TokenKind.STRING_LITERAL:
            parsed_include_path = path_start_tok.value[1:-1]
            self._skip_line()

        # Pattern 2: #include <foo.h>
        elif path_start_tok.kind is TokenKind.LE:
            # Find the closing ">" before a newline.
            _include_name_toks: list[Token] = []

            for _tok in self.tokens:
                if _tok.kind is TokenKind.NEWLINE:
                    msg = "Expected '>'."
                    raise CSyntaxError.from_token(msg, _tok)

                if _tok.kind is TokenKind.GE:
                    break

                _include_name_toks.append(_tok)
            else:
                # Consumed all the remaining tokens without finding ">" *or* hitting a newline.
                msg = "Expected '>'."
                raise CSyntaxError.from_token(msg, path_start_tok)

            parsed_include_path = "".join(t.value for t in _include_name_toks)

        # Pattern 3: #include FOO
        else:
            # TODO: Perform macro expansion, i.e. run through preprocessor and prepend to self.tokens.
            raise NotImplementedError

        include_path = self._find_include_path(parsed_include_path)

        try:
            with open(include_path, encoding="utf-8") as fp:
                include_source = fp.read()
        except OSError as exc:
            if not self.ignore_missing_includes:
                msg = f"Cannot open included file: {include_path!r}"
                raise CSyntaxError.from_token(msg, path_start_tok) from exc
        else:
            tokenizer = Tokenizer(include_source, include_path)
            preprocessor = Preprocessor(tokenizer, os.path.dirname(include_path))
            self._prepend(preprocessor)

    def pp_include_next(self) -> None:
        raise NotImplementedError

    def pp_define(self) -> None:
        raise NotImplementedError

    def pp_undef(self) -> None:
        raise NotImplementedError

    def pp_if(self) -> None:
        raise NotImplementedError

    def pp_ifdef(self) -> None:
        raise NotImplementedError

    def pp_ifndef(self) -> None:
        raise NotImplementedError

    def pp_elif(self) -> None:
        raise NotImplementedError

    def pp_else(self) -> None:
        raise NotImplementedError

    def pp_endif(self) -> None:
        raise NotImplementedError

    def pp_line(self) -> None:
        raise NotImplementedError

    def pp_pragma_once(self) -> None:
        raise NotImplementedError

    def pp_pragma(self) -> None:
        """#pragma directive: Ignore and skip to the next line."""

        # NOTE: Capturing pragmas might be useful for certain kinds of analysis? Something to consider.

        self._skip_line()

    def pp_error(self) -> None:
        """#error directive: Raise an error."""

        msg = "Preprocessing error."
        raise CSyntaxError.from_token(msg, next(self.tokens))

    def pp_warning(self) -> None:
        """#warning directive: Send a warning."""

        if (peek := self._peek()) is not None and (peek.kind is TokenKind.STRING_LITERAL):
            warnings.warn_explicit(peek.value, CPreprocessorWarning, peek.filename, peek.lineno)

        self._skip_line()
