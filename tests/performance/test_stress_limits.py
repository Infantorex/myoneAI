"""Stress Limits & Resource Bounding Tests."""

import pytest

from app.ai.manager import ConversationManager
from app.ai.models import ChatMessage
from app.ai.provider import MockAIProvider
from app.cloud.protocol import CloudMessage, MessageType
from app.cloud.queue import OfflineEventQueue


def test_conversation_context_stress_bounding():
    """Verify history FIFO strictly bounds context to configured max limit under 200 turns."""
    mgr = ConversationManager(
        provider=MockAIProvider(),
        max_history_messages=15,
    )

    for i in range(100):
        mgr._history.append(ChatMessage(role="user", content=f"Stress user turn {i}"))
        mgr._history.append(ChatMessage(role="assistant", content=f"Stress asst turn {i}"))
        mgr._trim_history()

    assert mgr.history_length == 15
    assert len(mgr.get_history()) == 15


def test_offline_queue_capacity_under_stress():
    """Verify offline event queue never exceeds maximum capacity."""
    q = OfflineEventQueue(max_size=20)
    for i in range(100):
        q.enqueue(CloudMessage(
            type=MessageType.STATUS.value,
            device_id="dev_001",
            payload={"count": i},
        ))
    assert q.size == 20
    assert len(q) == 20
