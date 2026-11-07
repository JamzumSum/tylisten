import asyncio
import logging
import threading
from inspect import CORO_CLOSED, getcoroutinestate

import pytest

from tylisten.futstore import FutureStore

pytestmark = pytest.mark.asyncio


class _CustomBaseException(BaseException):
    pass


async def test_add_awaitable():
    pool = []
    fs = FutureStore()

    async def f1():
        pool.append(1)

    async def f2():
        pool.append(2)

    assert asyncio.isfuture(fs.add_awaitable(f1()))
    assert asyncio.isfuture(fs.add_awaitable(asyncio.create_task(f2())))

    await asyncio.sleep(0.4)
    assert 1 in pool
    assert 2 in pool
    assert not fs._futs


async def test_wait():
    pool = []
    fs = FutureStore()

    async def fr():
        pool.append(1)
        if len(pool) < 2:
            fs.add_awaitable(fr())

    fs.add_awaitable(fr())
    await fs.wait()
    assert len(pool) == 2
    assert not fs._futs


async def test_clear():
    fs = FutureStore()

    fut = fs.add_awaitable(asyncio.sleep(1))
    fs.clear()

    with pytest.raises(asyncio.CancelledError):
        await fut
    assert not fs._futs


async def test_thread_safe_requires_loop():
    fs = FutureStore()
    coro = asyncio.sleep(0)

    try:
        with pytest.raises(ValueError):
            fs.add_awaitable(coro, True)
        assert getcoroutinestate(coro) == CORO_CLOSED
    finally:
        coro.close()


async def test_thread_safe_requires_coroutine():
    fs = FutureStore(loop=asyncio.get_running_loop())

    with pytest.raises(TypeError):
        fs.add_awaitable(asyncio.Future(), True)


async def test_wait_logs_task_errors(caplog):
    fs = FutureStore()

    async def fail():
        raise RuntimeError("task failed")

    fs.add_awaitable(fail())

    with caplog.at_level(logging.ERROR, logger="tylisten.futstore"):
        await fs.wait()

    records = [record for record in caplog.records if record.name == "tylisten.futstore"]
    assert any(
        record.exc_info
        and isinstance(record.exc_info[1], RuntimeError)
        and "task failed" in str(record.exc_info[1])
        for record in records
    )


async def test_wait_raise_exceptions():
    fs = FutureStore()

    async def fail():
        raise RuntimeError("task failed")

    fs.add_awaitable(fail())

    with pytest.raises(ExceptionGroup) as excinfo:
        await fs.wait(raise_exceptions=True)

    assert any(isinstance(exc, RuntimeError) for exc in excinfo.value.exceptions)


async def test_wait_logs_error_completed_before_wait(caplog):
    fs = FutureStore()

    async def fail():
        raise RuntimeError("early failure")

    fs.add_awaitable(fail())
    while fs._futs:
        await asyncio.sleep(0)

    with caplog.at_level(logging.ERROR, logger="tylisten.futstore"):
        await fs.wait()

    records = [record for record in caplog.records if record.name == "tylisten.futstore"]
    assert any(
        record.exc_info
        and isinstance(record.exc_info[1], RuntimeError)
        and "early failure" in str(record.exc_info[1])
        for record in records
    )


async def test_wait_raise_exception_completed_before_wait():
    fs = FutureStore()

    async def fail():
        raise RuntimeError("early failure")

    fs.add_awaitable(fail())
    while fs._futs:
        await asyncio.sleep(0)

    with pytest.raises(ExceptionGroup) as excinfo:
        await fs.wait(raise_exceptions=True)

    assert any(isinstance(exc, RuntimeError) for exc in excinfo.value.exceptions)


async def test_wait_raises_base_exception_and_logs_normal(caplog):
    fs = FutureStore()

    async def fail_normal():
        raise RuntimeError("normal failure")

    async def fail_base():
        raise _CustomBaseException("base failure")

    fs.add_awaitable(fail_normal())
    fs.add_awaitable(fail_base())

    with (
        caplog.at_level(logging.ERROR, logger="tylisten.futstore"),
        pytest.raises(_CustomBaseException),
    ):
        await fs.wait()

    records = [record for record in caplog.records if record.name == "tylisten.futstore"]
    assert any(
        record.exc_info
        and isinstance(record.exc_info[1], RuntimeError)
        and "normal failure" in str(record.exc_info[1])
        for record in records
    )


async def test_wait_raise_exceptions_preserves_errors_on_cancel(monkeypatch):
    fs = FutureStore()
    loop = asyncio.get_running_loop()

    failed = loop.create_future()
    failed.set_exception(RuntimeError("batch failure"))
    fs.add_awaitable(failed)

    hang = loop.create_future()
    fs.add_awaitable(hang)

    calls = 0

    async def fake_wait(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return set(), set()
        raise asyncio.CancelledError

    monkeypatch.setattr(asyncio, "wait", fake_wait)

    with pytest.raises(asyncio.CancelledError):
        await fs.wait(raise_exceptions=True)

    assert any(isinstance(exc, RuntimeError) for _, exc in fs._errors)
    hang.cancel()


async def test_wait_raises_precompleted_base_exception_promptly():
    fs = FutureStore()
    loop = asyncio.get_running_loop()

    done = loop.create_future()
    done.set_exception(_CustomBaseException("pre-completed"))
    fs.add_awaitable(done)

    hang = loop.create_future()
    fs.add_awaitable(hang)

    with pytest.raises(_CustomBaseException):
        await asyncio.wait_for(fs.wait(), 0.1)

    hang.cancel()


async def test_clear_discards_recorded_errors():
    fs = FutureStore()

    async def fail():
        raise RuntimeError("cleared failure")

    fs.add_awaitable(fail())
    while fs._futs:
        await asyncio.sleep(0)

    assert fs._errors
    fs.clear()
    assert not fs._errors


async def test_add_awaitable_thread_safe():
    def new_loop_thread(loop: asyncio.AbstractEventLoop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    loop_in_thread = asyncio.new_event_loop()
    t = threading.Thread(target=new_loop_thread, args=(loop_in_thread,), daemon=True)
    t.start()

    pool = []
    fs = FutureStore(loop=loop_in_thread)

    async def f1():
        pool.append(threading.current_thread().native_id)

    async def f2():
        pool.count(threading.current_thread().name)

    assert asyncio.isfuture(fs.add_awaitable(f1(), True))
    with pytest.raises(TypeError):
        fs.add_awaitable(loop_in_thread.create_task(f2()), True)
    with pytest.raises(TypeError):
        fs.add_awaitable(asyncio.ensure_future(f2(), loop=loop_in_thread), True)

    await asyncio.sleep(0.4)
    assert len(pool) == 1
    assert pool[0] == t.native_id
    assert not fs._futs
