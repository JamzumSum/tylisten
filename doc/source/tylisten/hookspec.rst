Hook Specifications
===============================

.. currentmodule:: tylisten

Error Handling
---------------------------

Listeners are isolated from each other. If a listener raises a normal exception,
the exception is logged and that listener is skipped; the remaining listeners
still run.

Only the following exceptions are re-raised:

- :exc:`asyncio.CancelledError`
- :exc:`KeyboardInterrupt`
- :exc:`SystemExit`

:class:`TimeoutHookSpec` applies its timeout to :meth:`~HookSpec.gather`,
:meth:`~HookSpec.results`, :meth:`~HookSpec.emit`, :meth:`~HookSpec.first` and
calling the hook instance. When the timeout expires, :exc:`asyncio.TimeoutError`
is raised and any still-running listener tasks are cancelled.

Exceptions raised by the hook definition itself are propagated unchanged when
the hook instance is called.

Hook Defination
---------------------------

.. autoclass:: tylisten.StaticHookSpec
    :members:
    :special-members: __call__

.. automodule:: tylisten
    :members: hookdef, null_emitter

Basic Hook Instance
-------------------------------

.. autoclass:: tylisten.HookSpec
    :members:
    :special-members: __call__

Hook Instance with Timeout
----------------------------------

.. autoclass:: tylisten.TimeoutHookSpec
    :members:
