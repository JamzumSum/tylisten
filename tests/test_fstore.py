import asyncio

import pytest

from tylisten.futstore import FutureStore

pytestmark = pytest.mark.asyncio


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
