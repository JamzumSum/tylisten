import asyncio
import logging
import typing as t
from contextlib import aclosing
from inspect import isawaitable
from typing import Self

from ._type import _P, _T, TyImpl

log = logging.getLogger(__name__)

if t.TYPE_CHECKING:
    from .static import StaticHookSpec

__all__ = ["HookSpec"]


class _ProcessExit(Exception):
    """Internal carrier for KeyboardInterrupt/SystemExit escaping a listener task."""

    def __init__(self, exc: BaseException) -> None:
        super().__init__(str(exc))
        self.exc = exc


async def _guard(awaitable: t.Awaitable[_T]) -> _T:
    """Keep process-level exceptions inside the listener task.

    :class:`asyncio.Task` re-raises :exc:`KeyboardInterrupt` and :exc:`SystemExit`
    into the event loop, so the caller of ``await task`` cannot log them or clean up.
    Catching them here and raising an ordinary exception keeps control flow inside
    the task.
    """
    try:
        return await awaitable
    except (KeyboardInterrupt, SystemExit) as exc:
        raise _ProcessExit(exc) from exc


def _log_listener_error(impl: TyImpl[_P, _T], exc: BaseException) -> None:
    """Log a listener failure, unwrapping the internal process-exit carrier."""
    if isinstance(exc, _ProcessExit):
        log.exception(
            "listener %r interrupted by %s",
            impl,
            type(exc.exc).__name__,
            exc_info=exc.exc,
        )
    elif isinstance(exc, (KeyboardInterrupt, SystemExit)):
        log.exception(
            "listener %r interrupted by %s",
            impl,
            type(exc).__name__,
            exc_info=exc,
        )
    else:
        log.exception("listener %r error", impl, exc_info=exc)


def _handle_listener_error(impl: TyImpl[_P, _T], exc: BaseException) -> None:
    """Log ordinary listener errors; re-raise cancellation and process-level ones."""
    if isinstance(exc, asyncio.CancelledError):
        raise exc
    _log_listener_error(impl, exc)
    if isinstance(exc, _ProcessExit):
        raise exc.exc from None
    if not isinstance(exc, Exception):
        raise exc


async def call_impls(
    impls: t.Iterable[TyImpl[_P, _T]], *args: _P.args, **kwds: _P.kwargs
) -> t.AsyncGenerator[_T, t.Any]:
    """A uniform interface to call a batch of hook implements.

    Listener exceptions are logged and skipped, so one broken implementation does not
    stop the others. :exc:`asyncio.CancelledError`, :exc:`KeyboardInterrupt` and
    :exc:`SystemExit` are always re-raised. The last two are logged with the failing
    listener, and outstanding listener tasks are cancelled first for a graceful
    shutdown.
    """
    rfuts: list[tuple[TyImpl[_P, _T], asyncio.Future[_T] | _T]] = []
    handled: set[asyncio.Future] = set()

    try:
        for impl in impls:
            try:
                c = impl(*args, **kwds)
            except BaseException as exc:  # noqa: BLE001
                _handle_listener_error(impl, exc)
                continue

            rfuts.append((impl, asyncio.ensure_future(_guard(c)) if isawaitable(c) else c))

        for impl, rfut in rfuts:
            if asyncio.isfuture(rfut):
                try:
                    result = await rfut
                except BaseException as exc:  # noqa: BLE001
                    handled.add(rfut)
                    _handle_listener_error(impl, exc)
                    continue
                yield result
            else:
                yield rfut  # type: ignore
    finally:
        # The consumer may stop early (for example, on timeout). Never leave
        # listener tasks running unobserved in the background. Gathering every
        # future also retrieves exceptions from tasks the consumer never reached;
        # failures that were not handled in the loop above are logged here so
        # they are not lost silently.
        futs = [(impl, fut) for impl, fut in rfuts if asyncio.isfuture(fut)]
        for _, fut in futs:
            if not fut.done():
                fut.cancel()
        if futs:
            results = await asyncio.gather(*(fut for _, fut in futs), return_exceptions=True)
            process_exit: BaseException | None = None
            for (impl, fut), result in zip(futs, results):
                if fut in handled or isinstance(result, asyncio.CancelledError):
                    continue
                if isinstance(result, _ProcessExit):
                    _log_listener_error(impl, result)
                    if process_exit is None:
                        process_exit = result.exc
                elif isinstance(result, BaseException):
                    _log_listener_error(impl, result)
                    if not isinstance(result, Exception) and process_exit is None:
                        process_exit = result

            # A process-level exception must not be reduced to a log entry, even
            # when the consumer is already unwinding (e.g. on timeout).
            if process_exit is not None:
                raise process_exit


class HookSpec(t.Generic[_P, _T]):
    """An instance of a :class:`StaticHookSpec`.

    .. seealso:: :meth:`StaticHookSpec.__call__`
    """

    __slots__ = ("__def__", "impls")

    impls: list[TyImpl[_P, _T]]
    """You can access this list to add/remove/clear_all implements."""

    def __init__(self, hookdef: "StaticHookSpec[_P, _T]") -> None:
        super().__init__()
        self.impls = []
        self.__def__ = hookdef.__def__

    def add_impl(self, impl: TyImpl[_P, _T]) -> Self:
        """A shortcut to :obj:`.impls`.append."""
        self.impls.append(impl)
        return self

    @t.overload
    def replace_impl(
        self, index_or_impl: int | TyImpl[_P, _T]
    ) -> t.Callable[[TyImpl[_P, _T]], None]: ...

    @t.overload
    def replace_impl(
        self, index_or_impl: int | TyImpl[_P, _T], new_impl: TyImpl[_P, _T]
    ) -> None: ...

    def replace_impl(
        self,
        index_or_impl: int | TyImpl[_P, _T],
        new_impl: TyImpl[_P, _T] | None = None,
    ) -> None | t.Callable[[TyImpl[_P, _T]], None]:
        """Replace an implementation according to the given index or function.

        :param index_or_impl: The index or the function.
            The function will be transformed to index by :obj:`.impls`.index.
        :param new_impl: If not given, this method could be used as a decorator.

        :raise ValueError: If :obj:`index_or_impl` is a function AND not present in :obj:`.impls`.
        :raise IndexError: If :obj:`index_or_impl` is an integer out of range.
        """
        if not isinstance(index_or_impl, int):
            index_or_impl = self.impls.index(index_or_impl)

        if new_impl is None:
            return lambda f: self.impls.__setitem__(index_or_impl, f)

        self.impls[index_or_impl] = new_impl

    async def gather(self, *args: _P.args, **kwds: _P.kwargs) -> list[_T]:
        """Gather all results, results respect the corresponding order in :obj:`.impls`.

        Listener exceptions are logged and skipped. :exc:`asyncio.CancelledError`,
        :exc:`KeyboardInterrupt` and :exc:`SystemExit` are re-raised, and any still
        running listener tasks are cancelled.

        :return: All results corresponding the order in :obj:`.impls`
        """
        async with aclosing(call_impls(self.impls, *args, **kwds)) as agen:
            return [i async for i in agen]

    async def results(self, *args: _P.args, **kwds: _P.kwargs) -> list[_T]:
        """An alias to :meth:`.gather`."""
        return await self.gather(*args, **kwds)

    async def emit(self, *args: _P.args, **kwds: _P.kwargs) -> None:
        """Like :meth:`.gather`, but returns `None`.

        Listener exceptions are handled in the same way as :meth:`.gather`.
        """
        await self.gather(*args, **kwds)

    async def first(self, *args: _P.args, **kwds: _P.kwargs) -> _T:
        """
        Get the first valid result.

        Listener exceptions are logged and skipped. :exc:`asyncio.CancelledError`,
        :exc:`KeyboardInterrupt` and :exc:`SystemExit` are re-raised.

        If all results are invalid, raises :exc:`StopAsyncIteration`.

        .. note:: A listener raising :exc:`StopAsyncIteration` is treated as a normal
            listener error and skipped; it is not confused with "no valid result".

        :raise StopAsyncIteration: If all results are invalid.

        :return: The first valid result.
        """
        for impl in self.impls:
            try:
                c = impl(*args, **kwds)
                if isawaitable(c):
                    return await c
                return c  # type: ignore
            except BaseException as exc:  # noqa: BLE001
                _handle_listener_error(impl, exc)
                continue

        raise StopAsyncIteration

    async def __call__(self, *args: _P.args, **kwds: _P.kwargs) -> _T:
        """
        Get the first valid result.
        If all results are invalid, call the defination and return its result.

        Exceptions raised by the defination propagate unchanged.

        :return: The first valid result. If all results are invalid, returns the result of the defination.
        """
        try:
            result = await self.first(*args, **kwds)
        except StopAsyncIteration:
            pass
        else:
            return result

        # Call the definition outside the ``except`` block so its errors do not
        # get the internal StopAsyncIteration as ``__context__``.
        c = self.__def__(*args, **kwds)
        return await c if isawaitable(c) else c  # type: ignore

    @property
    def has_impl(self) -> bool:
        """Return if a hook is implemented.

        :return: If this hook is implemented.
        """
        return bool(self.impls)
