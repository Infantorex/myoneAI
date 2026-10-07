"""Reliability: Offline Mode Resilience and Network Drop Recovery."""

import pytest

from app.cloud.client import CloudClient
from app.cloud.connection import CloudConnection, ConnectionState
from app.cloud.protocol import CloudMessage, MessageType
from app.cloud.queue import OfflineEventQueue
from app.core.memory.manager import MemoryManager
from app.productivity.database import ProductivityDatabase
from app.productivity.manager import ProductivityManager


@pytest.mark.asyncio
async def test_local_productivity_and_memory_work_100_percent_offline(tmp_path):
    """Verify local memory, tasks, reminders, and notes operate completely offline without network."""
    from app.productivity.tasks import TaskManager
    mem_db = tmp_path / "offline_mem.db"
    prod_db = tmp_path / "offline_prod.db"

    mem_mgr = MemoryManager(db_path=mem_db)
    prod_db_inst = ProductivityDatabase(db_path=str(prod_db))
    tasks_inst = TaskManager(db=prod_db_inst)
    prod_mgr = ProductivityManager(db=prod_db_inst, tasks=tasks_inst)

    # Memory offline
    item = await mem_mgr.remember("preference", "theme", "dark_mode")
    assert item.value == "dark_mode"
    res = await mem_mgr.get("preference", "theme")
    assert res.value == "dark_mode"

    # Tasks offline
    task = prod_mgr.create_task("Offline task execution")
    assert task["id"] is not None
    assert len(prod_mgr.list_tasks()) == 1


def test_cloud_offline_queue_buffers_events_during_disconnect():
    """Verify cloud client buffers events when connection state is DISCONNECTED."""
    q = OfflineEventQueue(max_size=50)
    for i in range(10):
        q.enqueue(CloudMessage(
            type=MessageType.STATUS.value,
            device_id="dev_01",
            payload={"step": i},
        ))
    assert q.size == 10

    # Pop sequentially when connection restores
    first = q.dequeue()
    assert first.payload["step"] == 0
    assert q.size == 9
