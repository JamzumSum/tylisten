import asyncio
import logging
from collections import deque
from inspect import isawaitable
from typing import Any, Awaitable, Callable, Deque, Generic, List, Optional, Type, TypeVar, Union
from weakref import ref

from .message import BaseMessage

_M = TypeVar("_M", bound=BaseMessage)
TyListener = Callable[[_M], Union[Awaitable[Any], Any]]

log = logging.getLogger(__name__)


def discard(q: Deque, v):
    if v in q:
        q.remove(v)


class Emitter(Generic[_M]):
    """An emitter which could be listened on or waited for."""

    listeners: List[TyListener[_M]]
    _waiters: Deque[asyncio.Future]

    def __init__(self, ty: Type[_M]) -> None:
        self._ty = ty
        self.listeners = []
        """You can access to this list to add/remove/clear_all listeners."""
        self._waiters = deque()

    async def wait(self) -> _M:
        fut = asyncio.get_event_loop().create_future()
        self._waiters.append(fut)
        try:
            return await fut
        finally:
            discard(self._waiters, fut)

    async def emit(self, **kw):
        clist: List[Awaitable[Any]] = []
        inst_msg = self._ty(**kw)
        for listener in self.listeners:
            try:
                c = listener(inst_msg)
            except:
                log.error("sync listener error!", exc_info=True)
                continue
            if isawaitable(c):
                clist.append(asyncio.ensure_future(c))

        if clist:
            try:
                await asyncio.wait(clist)
            except asyncio.CancelledError:
                raise
            except:
                log.error("async listener error!", exc_info=True)

        for fut in self._waiters:
            if not fut.done():
                fut.set_result(inst_msg)

    def abort(self, exc: Union[BaseException, Type[BaseException], None] = None):
        for fut in self._waiters:
            if exc is None:
                fut.cancel()
            else:
                fut.set_exception(exc)
        self._waiters.clear()


class VirtualEmitter(Generic[_M]):
    __slots__ = ("_conn_point", "connect_listeners")
    connect_listeners: List[Callable[["VirtualEmitter[_M]", Emitter[_M]], Any]]

    def __init__(self) -> None:
        super().__init__()
        self.connect_listeners = []

    def connect(self, connect_emitter: Emitter[_M]):
        self._conn_point = ref(connect_emitter)  # type: ref[Emitter[_M]]
        for listener in self.connect_listeners:
            try:
                listener(self, connect_emitter)
            except:
                log.error("sync connect_listener error!", exc_info=True)

    @property
    def connected(self):
        return hasattr(self, "_conn_point")

    async def wait(self) -> Optional[_M]:
        if not self.connected or (emitter := self._conn_point()) is None:
            return
        return await emitter.wait()

    @property
    def listeners(self) -> Optional[List[TyListener[_M]]]:
        if not self.connected or (emitter := self._conn_point()) is None:
            return
        return emitter.listeners
