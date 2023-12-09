import asyncio
import typing as t
from functools import wraps

from ._type import _P, _T
from .base import HookSpec

if t.TYPE_CHECKING:
    from .static import StaticHookSpec


__all__ = ["TimeoutHookSpec"]


class TimeoutHookSpec(HookSpec[_P, _T]):
    """A HookSpec with a pre-defined timeout.

    Internally, :meth:`.gather` and :meth:`.first` is wrapped with :external+python:obj:`asyncio.wait_for`.
    Thus a :exc:`asyncio.TimeoutError` will be raised if timeout.

    .. seealso::

        :meth:`StaticHookSpec.with_timeout`
        :external+python:obj:`asyncio.wait_for`
    """

    def __init__(self, hookdef: "StaticHookSpec[_P, _T]", *, timeout: float) -> None:
        super().__init__(hookdef)
        self._timeout = timeout

        timeout_meths = [self.gather, self.first]
        for meth in timeout_meths:
            self._with_timeout(meth.__name__)

    def _with_timeout(self, name: str):
        meth = getattr(self, name)

        @wraps(meth)
        async def wrapper(*args, **kwds):
            return await asyncio.wait_for(meth(*args, **kwds), timeout=self._timeout)

        setattr(self, name, wrapper)
        return meth
