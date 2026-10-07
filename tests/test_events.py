"""Unit tests for the event bus (app/core/events.py).
"""

import pytest
from app.core.events import EventBus, Event, SystemEvent, VoiceEvent


def test_sync_event_subscription():
    """Verify synchronous event emission and reception."""
    bus = EventBus()
    received = []

    def handler(evt: Event):
        received.append(evt.data.get("msg"))

    bus.subscribe(SystemEvent.STARTUP, handler)
    bus.emit(SystemEvent.STARTUP, {"msg": "started"})

    assert len(received) == 1
    assert received[0] == "started"


def test_unsubscribe():
    """Verify unsubscription from events."""
    bus = EventBus()
    received = []

    def handler(evt: Event):
        received.append(evt.name)

    bus.subscribe("custom.event", handler)
    bus.emit("custom.event", {})
    assert len(received) == 1

    bus.unsubscribe("custom.event", handler)
    bus.emit("custom.event", {})
    assert len(received) == 1


def test_subscribe_all():
    """Verify universal listener catches all events."""
    bus = EventBus()
    events_caught = []

    bus.subscribe_all(lambda evt: events_caught.append(evt.name))

    bus.emit(SystemEvent.STARTUP)
    bus.emit(VoiceEvent.LISTENING_STARTED)

    assert len(events_caught) == 2
    assert SystemEvent.STARTUP.value in events_caught
    assert VoiceEvent.LISTENING_STARTED.value in events_caught


def test_error_isolation():
    """Verify handler exceptions are caught and do not prevent other handlers."""
    bus = EventBus()
    order = []

    def failing_handler(evt: Event):
        raise RuntimeError("Handler failure")

    def good_handler(evt: Event):
        order.append("success")

    bus.subscribe("test.err", failing_handler)
    bus.subscribe("test.err", good_handler)

    # Should not raise exception
    bus.emit("test.err")
    assert order == ["success"]


@pytest.mark.asyncio
async def test_async_event_emission():
    """Verify async event emission and handler execution."""
    bus = EventBus()
    results = []

    async def async_handler(evt: Event):
        results.append(evt.data.get("val"))

    bus.subscribe("async.test", async_handler)
    await bus.emit_async("async.test", {"val": 42})

    assert results == [42]
