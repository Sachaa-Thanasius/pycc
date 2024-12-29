# TODO: Switch to using a logger for warnings; that might be more configurable.

from __future__ import annotations

import os
import warnings
from collections.abc import Generator, Iterable, Iterator
from itertools import chain, takewhile, tee

from ._compat import Optional, Self
from .errors import CPreprocessorWarning, CSyntaxError, CSyntaxWarning
from .token import Token, TokenKind
from .tokenizer import Tokenizer


__all__ = ("Preprocessor",)


def _is_not_ws(tok: Token, /) -> bool:
    """Determine if the given token is non-newline whitespace."""

    return tok.kind not in {TokenKind.WS, TokenKind.COMMENT}


def _is_pp_directive_hash(curr_tok: Token, prev_tok: Optional[Token], /) -> bool:
    return curr_tok.kind is TokenKind.PP_OCTO and (prev_tok is None or prev_tok.kind is TokenKind.NL)


class Preprocessor:
    """A preprocessor for the C language, loosely based on the C11 standard.

    Iterate over it to get a stream of preprocessed tokens.

    Parameters
    ----------
    tokens: Iterable[Token]
        An iterable of unpreprocessed tokens.
    local_dir: str, default=""
        The directory to consider as the current working directory for the purpose of include path searching. Defaults
        to the empty string.

    Attributes
    ----------
    raw_tokens: Iterator[Token]
        An iterator of unpreprocessed tokens.
    local_dir: str
        The directory to consider as the current working directory for the purpose of include path searching.
    include_search_dirs: list[str]
        A list of directories to search for include paths.
    ignore_missing_includes: bool
        Whether to ignore includes directives that point at files that cannot be found by the preprocessor.
    curr_tok: Token
        The token currently being preprocessed. Does not exist until iteration begins.
    """

    raw_tokens: Iterator[Token]
    local_dir: str
    include_search_dirs: list[str]
    ignore_missing_includes: bool
    curr_tok: Token

    def __init__(self, tokens: Iterable[Token], local_dir: str = ""):
        self.raw_tokens = iter(tokens)
        self.local_dir = local_dir
        self.include_search_dirs = []
        self.ignore_missing_includes = False

        #: The last seen token before the current one.
        self._prev_tok: Optional[Token] = None

        #: A set of files that use "#pragma once" and thus should only be included once, i.e. only be preprocessed once.
        self._pragma_once_paths: set[str] = set()

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> Token:
        for self.curr_tok in self.raw_tokens:  # noqa: B020
            # -- Expand macros.
            if (self.curr_tok.kind is TokenKind.ID) and self._is_macro(self.curr_tok):
                self._expand_macro()

            # -- Process preprocessor directives.
            elif _is_pp_directive_hash(self.curr_tok, self._prev_tok):
                directive_name_tok = next(filter(_is_not_ws, self.raw_tokens), None)

                if directive_name_tok is None:
                    msg = "Missing preprocessor directive."
                    raise CSyntaxError.from_token(msg, self.curr_tok)

                if directive_name_tok.kind is TokenKind.NL:
                    # Null directive.
                    pass

                elif directive_name_tok.value == "include":
                    self.pp_include()

                # NOTE: "#pragma once" is a common but non-standard alternative to "#include" guards.
                elif (
                    directive_name_tok.value == "pragma"
                    and (peek := self._peek(skip_ws=True)) is not None
                    and peek.value == "once"
                ):
                    # Land on the "once" since its presence is confirmed.
                    self.curr_tok = next(filter(_is_not_ws, self.raw_tokens))  # noqa: PLW2901
                    self.pp_pragma_once()

                elif directive_name_tok.value == "pragma":
                    self.pp_pragma()

                elif directive_name_tok.value == "error":
                    self.pp_error()

                elif directive_name_tok.value == "warning":
                    self.pp_warning()

                else:
                    msg = "Invalid preprocessor directive."
                    raise CSyntaxError.from_token(msg, directive_name_tok)

                self._prev_tok = self.curr_tok

            # -- No more preprocessing needed for the current token. Exit the loop and return that token.
            else:
                break

        else:
            # -- Broadcast that the preprocessor is done after the end of the token stream.
            raise StopIteration

        self._prev_tok = self.curr_tok

        return self.curr_tok

    # region ---- Helpers ----

    def _peek(self, *, skip_ws: bool = True) -> Optional[Token]:
        self.raw_tokens, forked_tokens = tee(self.raw_tokens)
        if skip_ws:
            return next(filter(_is_not_ws, forked_tokens), None)
        else:
            return next(forked_tokens, None)

    def _prepend(self, other_tokens: Iterable[Token], /) -> None:
        self.raw_tokens = chain(other_tokens, self.raw_tokens)

    def _skip_line(self) -> None:
        """Skip tokens until the next newline is found.

        This is for directives where extra tokens are technically allowed before the newline ends them.
        """

        next_tok = next(self.raw_tokens, None)
        if (next_tok is None) or (next_tok.kind is TokenKind.NL):
            return

        warnings.warn_explicit("Extra tokens.", CSyntaxWarning, next_tok.filename, next_tok.lineno)

        next_line_start = next((t for t in self.raw_tokens if t.kind is TokenKind.NL), None)
        if next_line_start is not None:
            self._prepend([next_line_start])

    def _find_include_path(self, potential_path: str, *, is_quoted: bool = False) -> str:
        if is_quoted:
            search_dirs = (self.local_dir, *self.include_search_dirs)
        else:
            search_dirs = self.include_search_dirs

        for include_dir in search_dirs:
            candidate = os.path.normpath(os.path.join(include_dir, potential_path))
            if os.path.exists(candidate):
                return candidate

        # Use the original path as a last resort.
        return potential_path

    def _is_macro(self, tok: Token, /) -> bool:
        raise NotImplementedError

    def _expand_macro(self) -> None:
        raise NotImplementedError

    # endregion ----

    # region ---- Directive handlers ----

    def pp_include(self) -> None:
        """#include directive: Find the included file and prepend its preprocessed tokens to our tokens."""

        path_start_tok = next(filter(_is_not_ws, self.raw_tokens))

        # Case 1: #include "foo.h"
        if path_start_tok.kind is TokenKind.STRING_LITERAL:
            parsed_include_path = path_start_tok.value[1:-1]
            self._skip_line()
            is_quoted = True

        # Case 2: #include <foo.h>
        elif path_start_tok.kind is TokenKind.LE:
            # Find the closing ">" before a newline.
            _include_path_toks = list(takewhile(lambda t: t.kind is not TokenKind.NL, self.raw_tokens))

            # We could consume all the remaining tokens without finding ">", possibly without even hitting a newline.
            if not _include_path_toks or (_include_path_toks[-1].kind is not TokenKind.GE):
                msg = "Expected closing '>' for #include."
                raise CSyntaxError.from_token(msg, path_start_tok)

            # Remove the ">".
            del _include_path_toks[-1]

            parsed_include_path = "".join(t.value for t in _include_path_toks)
            is_quoted = False

        # Case 3: #include FOO
        else:
            # TODO: Perform macro expansion, i.e. run through preprocessor and prepend to self.tokens.
            raise NotImplementedError

        include_path = self._find_include_path(parsed_include_path, is_quoted=is_quoted)

        if include_path not in self._pragma_once_paths:
            try:
                with open(include_path) as fp:
                    include_source = fp.read()
            except OSError as exc:
                if not self.ignore_missing_includes:
                    msg = f"Cannot open included file: {include_path!r}"
                    raise CSyntaxError.from_token(msg, path_start_tok) from exc
            else:
                tokenizer = Tokenizer(include_source, include_path)

                def _pp_with_new_local_dir() -> Generator[Token]:
                    _orig_local_dir = self.local_dir
                    self.local_dir = os.path.dirname(include_path)

                    try:
                        yield from tokenizer
                    finally:
                        self.local_dir = _orig_local_dir

                self._prepend(_pp_with_new_local_dir())

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
        """#pragma once directive: Skip to the next line, but count the current file as having been preprocessed already."""

        self._pragma_once_paths.add(self.curr_tok.filename)
        self._skip_line()

    def pp_pragma(self) -> None:
        """#pragma directive: Ignore and skip to the next line."""

        # NOTE: Capturing pragmas might be useful for certain kinds of analysis? Something to consider.

        self.curr_tok = next(t for t in self.raw_tokens if t.kind is TokenKind.NL)

    def pp_error(self) -> None:
        """#error directive: Raise an error."""

        msg = "Preprocessing error."
        raise CSyntaxError.from_token(msg, next(self.raw_tokens))

    def pp_warning(self) -> None:
        """#warning directive: Send a warning."""

        if (peek := self._peek(skip_ws=True)) is not None and (peek.kind is TokenKind.STRING_LITERAL):
            warnings.warn_explicit(peek.value, CPreprocessorWarning, peek.filename, peek.lineno)

        self._skip_line()

    # endregion ----
