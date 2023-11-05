import asyncio
import typing as t

T = t.TypeVar("T")


class FutureStore:
    """
    A store for keeping references of running futures,
    in order to keep them from being garbage collected.
    """

    _futs: t.Set[asyncio.Future]

    def __init__(self) -> None:
        super().__init__()
        self._futs = set()

    def add_awaitable(self, func: t.Awaitable[T]) -> "asyncio.Future[T]":
        """Add an awaitable into this store.

        :param func: the awaitable
        :return: the wrapped task
        """
        if not (func := asyncio.ensure_future(func)).done():
            self._futs.add(func)
            func.add_done_callback(self._futs.discard)
        return func

    __call__ = add_awaitable

    async def wait(self, wait_new=True):
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
        for t in self._futs:
            t.cancel()

    def __bool__(self):
        return bool(self._futs)
