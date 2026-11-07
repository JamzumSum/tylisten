import asyncio
import logging
import typing as t

T = t.TypeVar("T")

log = logging.getLogger(__name__)


class FutureStore:
    """
    A store for keeping references of running futures,
    in order to keep them from being garbage collected.
    """

    _futs: set[asyncio.Future]

    def __init__(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Create a :class:`FutureStore`.

        :param loop: Event loop for running futures. Must be given when using ``thread_safe`` keyword.
        """
        super().__init__()
        self._futs = set()
        self.loop = loop
        """Event loop for running futures. Must be given when using ``thread_safe`` keyword."""

    @t.overload
    def add_awaitable(
        self, func: t.Coroutine[t.Any, t.Any, T], thread_safe: t.Literal[True]
    ) -> "asyncio.Future[T]": ...

    @t.overload
    def add_awaitable(
        self, func: t.Awaitable[T], thread_safe: bool = False
    ) -> "asyncio.Future[T]": ...

    def add_awaitable(
        self, func: t.Awaitable[T], thread_safe: bool = False
    ) -> "asyncio.Future[T]":
        """Add an awaitable into this store.

        :param func: the awaitable
        :param thread_safe: whether to use :meth:`asyncio.run_coroutine_threadsafe`. If true, must specify :obj:`.loop`, and `func` must be a coroutine.
        :return: the wrapped future
        :raise ValueError: If ``thread_safe`` is true but :obj:`.loop` is not set.
        :raise TypeError: If ``thread_safe`` is true but ``func`` is not a coroutine.
        """
        if thread_safe:
            if self.loop is None:
                if asyncio.iscoroutine(func):
                    func.close()
                raise ValueError(
                    "`thread_safe` mode needs specify loop when creating FutureStore."
                )
            if not asyncio.iscoroutine(func):
                raise TypeError("`thread_safe` mode needs coroutine as input.")
            try:
                cfut = asyncio.run_coroutine_threadsafe(func, loop=self.loop)
            except BaseException:
                func.close()
                raise
            func = asyncio.wrap_future(cfut, loop=self.loop)
        else:
            func = asyncio.ensure_future(func, loop=self.loop)
        if not func.done():
            self._futs.add(func)
            func.add_done_callback(self._futs.discard)
        return func

    __call__ = add_awaitable

    async def wait(self, wait_new: bool = True, *, raise_exceptions: bool = False):
        """Wait for all tasks in the specific group(s).

        :param wait_new: also wait for new-added futures during waiting for existing futures.
        :param raise_exceptions: if true, raise an :exc:`ExceptionGroup` if any waited
            task failed. Otherwise task failures are retrieved and logged.
        :raise ExceptionGroup: If ``raise_exceptions`` is true and any waited task failed.

        .. note:: Even if `wait_new` is False, newly added tasks may still be scheduled.
        """
        while self._futs:
            done, _ = await asyncio.wait(self._futs)
            errors: list[tuple[asyncio.Future, Exception]] = []

            for fut in done:
                self._futs.discard(fut)
                if fut.cancelled():
                    continue

                exc = fut.exception()
                if exc is None:
                    continue
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    raise exc
                if isinstance(exc, Exception):
                    errors.append((fut, exc))

            if errors:
                if raise_exceptions:
                    raise ExceptionGroup("future(s) failed", [exc for _, exc in errors])
                for fut, exc in errors:
                    log.exception("future %r failed", fut, exc_info=exc)

            if not wait_new:
                break

    def clear(self):
        """Clear current future store, cancel all saved tasks. If you do not want a task to be cancelled,
        wrap it in a `~asyncio.shield`.
        """
        for task in self._futs:
            task.cancel()

    def __bool__(self):
        return bool(self._futs)
