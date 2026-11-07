import asyncio
import typing as t
from contextlib import suppress

from ._type import _P, _T
from .base import HookSpec

if t.TYPE_CHECKING:
    from .static import StaticHookSpec


__all__ = ["TimeoutHookSpec"]


class TimeoutHookSpec(HookSpec[_P, _T]):
    """A HookSpec with a pre-defined timeout.

    :meth:`.gather`, :meth:`.results`, :meth:`.emit`, :meth:`.first` and
    :meth:`~tylisten.HookSpec.__call__` are wrapped with
    :external+python:obj:`asyncio.wait_for`.
    Thus a :exc:`asyncio.TimeoutError` will be raised if timeout, and any
    still-running listener tasks are cancelled.

    .. seealso::

        :meth:`tylisten.StaticHookSpec.with_timeout`
        :external+python:obj:`asyncio.wait_for`
    """

    __slots__ = ("_timeout",)

    def __init__(self, hookdef: "StaticHookSpec[_P, _T]", *, timeout: float) -> None:
        super().__init__(hookdef)
        self._timeout = timeout

    async def gather(self, *args: _P.args, **kwds: _P.kwargs) -> list[_T]:
        return await asyncio.wait_for(super().gather(*args, **kwds), timeout=self._timeout)

    async def first(self, *args: _P.args, **kwds: _P.kwargs) -> _T:
        return await asyncio.wait_for(super().first(*args, **kwds), timeout=self._timeout)

    async def emit_suppress_timeout(self, *args: _P.args, **kwds: _P.kwargs) -> None:
        """Call :meth:`.emit` and suppress :exc:`asyncio.TimeoutError`.

        Listener exceptions are handled as in :meth:`.emit`, and listener tasks still
        running when the timeout expires are cancelled.
        """
        with suppress(asyncio.TimeoutError):
            return await super().emit(*args, **kwds)
