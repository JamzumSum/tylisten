import typing as t

from typing_extensions import ParamSpec

_T = t.TypeVar("_T")
_P = ParamSpec("_P")
TyImpl = t.Callable[_P, t.Union[t.Awaitable[_T], _T]]
