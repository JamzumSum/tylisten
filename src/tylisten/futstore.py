import asyncio
import typing as t

T = t.TypeVar("T")


class FutureStore:
    """
    A store for keeping references of running futures,
    in order to keep them from being garbage collected.
    """

    _futs: t.Set[asyncio.Future]

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
        """
        if thread_safe:
            assert self.loop, "`thread_safe` mode needs specify loop when creating FutureStore."
            assert asyncio.iscoroutine(func), "`thread_safe` mode needs coroutine as input."
            func = asyncio.wrap_future(
                asyncio.run_coroutine_threadsafe(func, loop=self.loop), loop=self.loop
            )
        else:
            func = asyncio.ensure_future(func, loop=self.loop)
        if not func.done():
            self._futs.add(func)
            func.add_done_callback(self._futs.discard)
        return func

    __call__ = add_awaitable

    async def wait(self, wait_new: bool = True):
        """Wait for all tasks in the specific group(s).

        :param wait_new: also wait for new-added futures during waiting for existing futures.

        .. note:: Even if `wait_new` is False, newly added tasks may still be scheduled.
        """
        if not self._futs:
            return
        await asyncio.wait(self._futs)
        if wait_new and self._futs:
            # await potential new tasks in this store
            await self.wait()

    def clear(self):
        """Clear current future store, cancel all saved tasks. If you do not want a task to be cancelled,
        wrap it in a `~asyncio.shield`.

        :param exc: if not given, all futures will be cancelled; else they will be set with this exception.
        """
        for task in self._futs:
            task.cancel()

    def __bool__(self):
        return bool(self._futs)
