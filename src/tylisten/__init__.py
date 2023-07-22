"""A fully typed async emitter-listener library."""
from .emitter import Emitter, VirtualEmitter
from .message import BaseMessage
from typing import Any

__all__ = ["BaseMessage", "Emitter", "VirtualEmitter", "null_emitter"]


class __null_message(BaseMessage):
    def __init__(self, *args, **kwds) -> None:
        super().__init__()


null_emitter: Emitter[Any] = Emitter(__null_message)
null_vemitter: VirtualEmitter[Any] = VirtualEmitter()
