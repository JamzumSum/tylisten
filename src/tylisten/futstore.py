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
        self._errors: list[tuple[asyncio.Future, BaseException]] = []
        self.loop = loop
        """Event loop for running futures. Must be given when using ``thread_safe`` keyword."""

    def _record(self, fut: asyncio.Future) -> None:
        if fut.cancelled():
            return
        exc = fut.exception()
        if exc is not None:
            self._errors.append((fut, exc))

    def _on_done(self, fut: asyncio.Future) -> None:
        self._futs.discard(fut)
        self._record(fut)

    @staticmethod
    def _raise_or_log(
        errors: list[tuple[asyncio.Future, BaseException]],
        *,
        raise_exceptions: bool,
    ) -> None:
        seen: set[asyncio.Future] = set()
        unique: list[tuple[asyncio.Future, BaseException]] = []
        for fut, exc in errors:
            if fut in seen:
                continue
            seen.add(fut)
            unique.append((fut, exc))

        normal = [(fut, exc) for fut, exc in unique if isinstance(exc, Exception)]
        process_exit = next((exc for _, exc in unique if not isinstance(exc, Exception)), None)

        # Log ordinary failures before raising a process-level one, so a
        # concurrent BaseException does not hide them.
        if normal and (process_exit is not None or not raise_exceptions):
            for fut, exc in normal:
                log.exception("future %r failed", fut, exc_info=exc)

        if process_exit is not None:
            raise process_exit

        if normal and raise_exceptions:
            raise ExceptionGroup("future(s) failed", [exc for _, exc in normal])

    def _drain(
        self,
        collected: list[tuple[asyncio.Future, BaseException]],
        *,
        raise_exceptions: bool,
    ) -> None:
        batch = self._errors
        self._errors = []
        if not batch:
            return

        if raise_exceptions:
            collected.extend(batch)
            if any(not isinstance(exc, Exception) for _, exc in batch):
                self._raise_or_log(collected, raise_exceptions=True)
        else:
            self._raise_or_log(batch, raise_exceptions=False)

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
        if func.done():
            self._record(func)
        else:
            self._futs.add(func)
            func.add_done_callback(self._on_done)
        return func

    __call__ = add_awaitable

    async def wait(self, wait_new: bool = True, *, raise_exceptions: bool = False):
        """Wait for all tasks in the specific group(s).

        :param wait_new: also wait for new-added futures during waiting for existing futures.
        :param raise_exceptions: if true, raise an :exc:`ExceptionGroup` if any waited
            task failed. Otherwise task failures are retrieved and logged.
        :raise ExceptionGroup: If ``raise_exceptions`` is true and any waited task failed.

        Failures of tasks which completed before ``wait`` was called are reported too.
        They are retained until ``wait`` drains them; :meth:`clear` also discards them.

        .. note:: In a long-lived store, call ``wait`` periodically so recorded
            failures do not accumulate.

        .. note:: Even if `wait_new` is False, newly added tasks may still be scheduled.
        """
        errors: list[tuple[asyncio.Future, BaseException]] = []

        while True:
            # Report already-completed failures before blocking on the next batch.
            self._drain(errors, raise_exceptions=raise_exceptions)
            if not self._futs:
                break

            try:
                await asyncio.wait(self._futs)
            except BaseException:
                # Do not lose failures collected from earlier batches when the
                # wait itself is cancelled.
                if errors:
                    self._errors = errors + self._errors
                raise

            if not wait_new:
                break

        self._drain(errors, raise_exceptions=raise_exceptions)
        if raise_exceptions and errors:
            self._raise_or_log(errors, raise_exceptions=True)

    def clear(self):
        """Clear current future store, cancel all saved tasks, and discard recorded
        failures. If you do not want a task to be cancelled, wrap it in a
        `~asyncio.shield`.
        """
        for task in self._futs:
            task.cancel()
        self._errors.clear()

    def __bool__(self):
        return bool(self._futs)
