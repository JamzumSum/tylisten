"""A fully typed async emitter-listener library."""
from typing import Any

from .futstore import FutureStore
from .hookspec import HookSpec

__all__ = ["HookSpec", "hookdef", "null_emitter", "FutureStore"]

hookdef = HookSpec
null_emitter: HookSpec[Any, Any] = HookSpec(lambda *args, **kwds: None)
