Future Store
=======================

.. currentmodule:: tylisten

.. autoclass:: FutureStore
    :members:

Error Handling
-----------------------

:meth:`FutureStore.wait` always retrieves task exceptions. By default they are
logged; pass ``raise_exceptions=True`` to receive an :exc:`ExceptionGroup`.

:meth:`FutureStore.add_awaitable` raises :exc:`ValueError` when ``thread_safe``
is requested without a loop, and :exc:`TypeError` when the input is not a
coroutine.
