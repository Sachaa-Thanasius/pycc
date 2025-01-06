# TODO: Make the warnings more ergonomic to use and receive. Can they be made opt-in?

from __future__ import annotations

import os
import warnings
from collections.abc import Callable, Generator, Iterable, Iterator
from itertools import chain, takewhile, tee

from . import _typing_compat as _t
from .errors import PycpPreprocessorWarning, PycpSyntaxError, PycpSyntaxWarning
from .token import Token, TokenKind
from .tokenizer import Tokenizer


_MatcherFunc: _t.TypeAlias = Callable[["Preprocessor", Token], bool]

__all__ = ("Preprocessor", "Macro")


def _is_not_space(tok: Token, /) -> bool:
    """Determine if the given token is non-newline whitespace."""

    return tok.kind not in {TokenKind.WS, TokenKind.COMMENT}


def _is_pp_directive_hash(curr_tok: Token, prev_tok: _t.Optional[Token], /) -> bool:
    return (curr_tok.kind is TokenKind.PP_OCTO) and (prev_tok is None or prev_tok.kind is TokenKind.NL)


class Macro:
    pass


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
        The iterator of tokens being preprocessed.
    local_dir: str
        The directory to consider as the current working directory for the purpose of include path searching.
    include_search_dirs: list[str]
        A list of directories to search for include paths.
    ignore_missing_includes: bool
        Whether to ignore includes directives that point at files that cannot be found by the preprocessor.
    macros: dict[str, Macro]
        The macros defined during preprocessing.
    """

    raw_tokens: Iterator[Token]
    local_dir: str
    include_search_dirs: list[str]
    ignore_missing_includes: bool
    macros: dict[str, Macro]

    _directive_matchers: _t.ClassVar[dict[_MatcherFunc, str]] = {}

    def __init__(self, tokens: Iterable[Token], local_dir: str = ""):
        self.raw_tokens = iter(tokens)
        self.local_dir = local_dir
        self.include_search_dirs = []
        self.ignore_missing_includes = False
        self.macros = {}

        #: The last seen token before the current one.
        self._prev_tok: _t.Optional[Token] = None
        #: A set of files that guard inclusion via "#pragma once".
        self._pragma_once_paths: set[str] = set()
        #: A set of files that guard inclusion via the common "#ifndef" pattern.
        self._include_guarded_paths: set[str] = set()
        #: The index within include_search_dirs that the "#include_next" directive will start searching from.
        self._include_next_index: int = 0

    def __iter__(self) -> _t.Self:
        return self

    def __next__(self) -> Token:  # noqa: PLR0912
        # Loop until a token is found that isn't a macro, a preprocessor directive, or whitespace. Return that.
        for self.curr_tok in self.raw_tokens:  # noqa: B020 # False positive.
            if self._is_macro(self.curr_tok):
                self._expand_macro()

            elif _is_pp_directive_hash(self.curr_tok, self._prev_tok):
                # Invariant: Only the first token of a directive name is fully consumed here. Handlers can internally
                # forward as much as they wish, e.g. pragma once.
                pp_start_tok = next(filter(_is_not_space, self.raw_tokens), None)

                if pp_start_tok is None:
                    msg = "Missing preprocessor directive."
                    raise PycpSyntaxError.from_token(msg, self.curr_tok)

                pp_start_value = pp_start_tok.value

                if pp_start_tok.kind is TokenKind.NL:
                    pass  # Null directive.
                elif pp_start_value == "include":
                    self.pp_include()
                elif pp_start_value == "include_next":
                    self.pp_include_next()
                elif (
                    pp_start_value == "pragma"
                    and (peek := self._peek(skip_spaces=True)) is not None
                    and peek.value == "once"
                ):
                    self.pp_pragma_once()
                elif pp_start_value == "pragma":
                    self.pp_pragma()
                elif pp_start_value == "error":
                    self.pp_error()
                elif pp_start_value == "warning":
                    self.pp_warning()
                else:
                    msg = "Invalid preprocessor directive."
                    raise PycpSyntaxError.from_token(msg, pp_start_tok)

                self._prev_tok = self.curr_tok

            elif self.curr_tok.kind in {TokenKind.NL, TokenKind.WS, TokenKind.COMMENT}:
                self._prev_tok = self.curr_tok

            else:
                self._prev_tok = self.curr_tok
                return self.curr_tok

        # Signal that the preprocessor is done after the end of the token stream.
        raise StopIteration

    # region ---- Internal helpers ----

    def _peek(self, *, skip_spaces: bool = True) -> _t.Optional[Token]:
        """Peek at the next token without consuming it.

        Optionally specify whether to find the next non-whitespace token. Newlines are not skipped.
        """

        self.raw_tokens, forked_tokens = tee(self.raw_tokens)
        if skip_spaces:
            return next(filter(_is_not_space, forked_tokens), None)
        else:
            return next(forked_tokens, None)

    def _prepend(self, other_tokens: Iterable[Token], /) -> None:
        self.raw_tokens = chain(other_tokens, self.raw_tokens)

    def _skip_rest_of_line(self) -> None:
        """Skip tokens until the next newline is found. Warn if any tokens are found.

        This is for directives that technically allow extra tokens after they are done but before the newline.
        """

        next_tok = next(self.raw_tokens, None)
        if (next_tok is None) or (next_tok.kind is TokenKind.NL):
            return

        warnings.warn_explicit("Extra tokens.", PycpSyntaxWarning, next_tok.filename, next_tok.lineno)

        next_line_start = next((t for t in self.raw_tokens if t.kind is TokenKind.NL), None)
        if next_line_start is not None:
            self._prepend([next_line_start])

    def _is_macro(self, tok: Token, /) -> bool:
        """Determine if a token corresponds to a defined macro."""

        return (tok.kind is TokenKind.ID) and (tok.value in self.macros)

    def _expand_macro(self) -> None:
        raise NotImplementedError

    def _read_include_name(self, name_start_tok: Token, /) -> tuple[str, bool]:
        # Case 1: #include "foo.h"
        if name_start_tok.kind is TokenKind.STRING_LITERAL:
            parsed_include_name = name_start_tok.value[1:-1]
            is_quoted = True

            self._skip_rest_of_line()

        # Case 2: #include <foo.h>
        elif name_start_tok.kind is TokenKind.LT:
            # Find the closing ">" before a newline.
            _include_path_toks = list(takewhile(lambda t: t.kind is not TokenKind.NL, self.raw_tokens))

            # We could consume all the remaining tokens without finding ">", possibly without even hitting a newline.
            if not _include_path_toks or (_include_path_toks[-1].kind is not TokenKind.GT):
                msg = "Expected closing '>' for #include."
                raise PycpSyntaxError.from_token(msg, name_start_tok)

            # Remove the ">".
            del _include_path_toks[-1]

            parsed_include_name = "".join(t.value for t in _include_path_toks)
            is_quoted = False

        # Case 3: #include FOO
        elif self._is_macro(name_start_tok):
            # TODO: Perform macro expansion, i.e. run through preprocessor and prepend to self.tokens. Then recurse?
            self._expand_macro()
            raise NotImplementedError

        else:
            msg = "Expected filename after #include."
            raise PycpSyntaxError.from_token(msg, name_start_tok)

        return parsed_include_name, is_quoted

    def _find_include_path(self, include_name: str, /, *, is_quoted: bool = False) -> str:
        """Find an include path based on its name within the known include directories.

        Parameters
        ----------
        include_name: str
            The name or local path of the file to be included.
        is_quoted: bool, default=False
            Whether the include name is quoted. If True, the local directory is searched first. Defaults to False.

        Returns
        -------
        str
            If found, the resolved include path. If not found, the original name.
        """

        if is_quoted:
            search_dirs = (self.local_dir, *self.include_search_dirs)
        else:
            search_dirs = self.include_search_dirs

        for i, include_dir in enumerate(search_dirs):
            candidate = os.path.normpath(os.path.join(include_dir, include_name))
            if os.path.exists(candidate):
                self._include_next_index = i + 1
                return candidate

        return include_name

    def _find_include_next_path(self, include_name: str, /) -> str:
        for include_dir in self.include_search_dirs[self._include_next_index :]:
            candidate = os.path.normpath(os.path.join(include_dir, include_name))
            if os.path.exists(candidate):
                return candidate

        return include_name

    def _tokens_with_temp_local_dir(self, include_path: str, include_source: str, /) -> Generator[Token]:
        # TODO: There's no hook to replace the Tokenizer class with another one. Can one be provided? Should one?

        _orig_local_dir = self.local_dir
        self.local_dir = os.path.dirname(include_path)
        try:
            yield from Tokenizer(include_source, include_path)
        finally:
            self.local_dir = _orig_local_dir

    def _include_file(self, include_path: str, start_tok: Token, /) -> None:
        if not (include_path in self._pragma_once_paths or include_path in self._include_guarded_paths):
            try:
                # TODO: Cache successfully read include paths to avoid future searches with tons of stat calls.
                with open(include_path) as fp:
                    include_source = fp.read()
            except OSError as exc:
                if not self.ignore_missing_includes:
                    msg = f"Cannot open included file: {include_path!r}"
                    raise PycpSyntaxError.from_token(msg, start_tok) from exc
            else:
                self._prepend(self._tokens_with_temp_local_dir(include_source, include_path))

    # endregion ----

    # region ---- Directive handlers ----

    def pp_include(self) -> None:
        """#include directive: Find the included file and prepend its preprocessed tokens to our tokens."""

        include_name_start_tok = next(filter(_is_not_space, self.raw_tokens))
        include_name, is_quoted = self._read_include_name(include_name_start_tok)
        include_path = self._find_include_path(include_name, is_quoted=is_quoted)
        self._include_file(include_path, include_name_start_tok)

    def pp_include_next(self) -> None:
        """#include_next directive: Find the included file and prepend its preprocessed tokens to our tokens.

        Notes
        -----
        This is a *non-standard* directive.
        """

        include_name_start_tok = next(filter(_is_not_space, self.raw_tokens))
        include_name, _ = self._read_include_name(include_name_start_tok)
        include_path = self._find_include_next_path(include_name)
        self._include_file(include_path, include_name_start_tok)

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
        """#pragma once directive: Skip to the next line, but remember the current file as having been preprocessed
        already.

        Notes
        -----
        This is a common but *non-standard* directive that is used as an alternative to standard #ifndef include guards.
        """

        # Forward to "once" since its presence is confirmed.
        self.curr_tok = next(filter(_is_not_space, self.raw_tokens))

        self._pragma_once_paths.add(self.curr_tok.filename)
        self._skip_rest_of_line()

    def pp_pragma(self) -> None:
        """#pragma directive: Ignore and skip to the next line."""

        # FIXME: Actually capture pragmas.

        self.curr_tok = next(t for t in self.raw_tokens if t.kind is TokenKind.NL)

    def pp_error(self) -> None:
        """#error directive: Raise an error."""

        msg = "Preprocessing error."
        raise PycpSyntaxError.from_token(msg, next(self.raw_tokens))

    def pp_warning(self) -> None:
        """#warning directive: Send a warning."""

        if (peek := self._peek(skip_spaces=True)) is not None and (peek.kind is TokenKind.STRING_LITERAL):
            warnings.warn_explicit(peek.value, PycpPreprocessorWarning, peek.filename, peek.lineno)

        self._skip_rest_of_line()

    # endregion ----
