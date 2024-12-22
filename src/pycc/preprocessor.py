"""A partial implementation of a C processor."""

from __future__ import annotations

import os
import warnings
from collections.abc import Iterable, Iterator
from itertools import chain, tee

from ._compat import Optional, Self
from .errors import CPreprocessorWarning, CSyntaxError, CSyntaxWarning
from .token import Token, TokenKind
from .tokenizer import Tokenizer


__all__ = ("Preprocessor",)


class Preprocessor:
    """A preprocessor for the C language based on the C11 standard.

    Parameters
    ----------
    tokens: Iterable[Token]
        An iterable of unpreprocessed tokens.
    local_dir: str, default=""
        The directory to consider as the current working directory for the purpose of include path searching. Defaults
        to the empty string.
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

        self._curr_tok: Optional[Token] = None
        self._prev_tok: Optional[Token] = None

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> Token:
        # We're done if we reach the end of the given tokens.
        try:
            self._curr_tok = next(self.tokens)
        except StopIteration as exc:
            raise StopIteration from exc

        # TODO: Handle macro expansions.

        # Let tokens unrelated to the preprocessor pass through.
        if not (
            self._curr_tok.kind is TokenKind.PP_OCTO
            and (self._prev_tok is None or self._prev_tok.kind is TokenKind.NEWLINE)
        ):
            self._prev_tok = self._curr_tok
            return self._curr_tok

        directive_tok = next(self.tokens, None)

        if directive_tok is None:
            pass

        elif directive_tok.value == "include":
            self.pp_include()

        elif directive_tok.value == "pragma":
            self.pp_pragma()

        elif directive_tok.value == "error":
            self.pp_error()

        elif directive_tok.value == "warning":
            self.pp_warning()

        else:
            msg = "Invalid preprocessor directive."
            raise CSyntaxError.from_token(msg, directive_tok)

        self._prev_tok = self._curr_tok

    def _peek(self) -> Optional[Token]:
        self.tokens, forked_tokens = tee(self.tokens)
        return next(forked_tokens, None)

    def _prepend(self, iterable: Iterable[Token], /) -> None:
        self.tokens = chain(iter(iterable), self.tokens)

    def _prepend_if_not_none(self, item: Optional[Token], /) -> None:
        if item is not None:
            self._prepend([item])

    def _skip_line(self) -> None:
        """Skip tokens until the next newline is found.

        This is for directives where extra tokens are technically allowed before the newline ends them.
        """

        next_tok = next(self.tokens, None)
        if (next_tok is None) or (next_tok.kind is TokenKind.NEWLINE):
            return

        warnings.warn_explicit("Extra tokens.", CSyntaxWarning, next_tok.filename, next_tok.lineno)

        next_line_start = next((t for t in self.tokens if t.kind is TokenKind.NEWLINE), None)
        self._prepend_if_not_none(next_line_start)

    def _find_include_path(self, potential_path: str) -> str:
        for include_dir in chain([self.local_dir], self.include_dirs):
            candidate = os.path.normpath(os.path.join(include_dir, potential_path))
            if os.path.exists(candidate):
                return candidate

        # Default to the original path as a last resort.
        return potential_path

    def pp_include(self) -> None:
        """#include directive: Find the included file and prepend its preprocessed tokens to our tokens."""

        directive_start = next(self.tokens)

        # Pattern 1: #include "foo.h"
        if directive_start.kind is TokenKind.STRING_LITERAL:
            parsed_include_path = directive_start.value[1:-1]
            self._skip_line()

        # Pattern 2: #include <foo.h>
        elif directive_start.kind is TokenKind.LE:
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
                raise CSyntaxError.from_token(msg, directive_start)

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
                raise CSyntaxError.from_token(msg, directive_start) from exc
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

    # endregion
