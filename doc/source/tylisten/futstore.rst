Future Store
=======================

.. currentmodule:: tylisten

.. autoclass:: FutureStore
    :members:

Error Handling
-----------------------

:meth:`FutureStore.wait` always retrieves task exceptions, including failures of
tasks which completed before ``wait`` was called. Ordinary exceptions are logged
by default; pass ``raise_exceptions=True`` to receive an :exc:`ExceptionGroup`.
Non-``Exception`` failures are always re-raised. Call ``wait`` periodically in a
long-lived store, or use :meth:`FutureStore.clear` to discard recorded failures.

:meth:`FutureStore.add_awaitable` raises :exc:`ValueError` when ``thread_safe``
is requested without a loop, and :exc:`TypeError` when the input is not a
coroutine.
