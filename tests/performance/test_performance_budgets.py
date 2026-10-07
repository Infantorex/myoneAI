"""Performance Budget Verification Tests."""

import time
import pytest
import numpy as np

from app.cloud.authentication import compute_signature
from app.cloud.protocol import CloudMessage, MessageType
from app.voice.vad import VoiceActivityDetector


def test_vad_rms_latency_budget():
    """Verify RMS energy calculation throughput adheres to < 100 µs budget."""
    vad = VoiceActivityDetector()
    chunk = (np.ones(1024, dtype=np.int16) * 5000).tobytes()

    t0 = time.perf_counter()
    iterations = 1000
    for _ in range(iterations):
        _ = vad.calculate_rms(chunk)
    elapsed_us = ((time.perf_counter() - t0) * 1000000) / iterations

    assert elapsed_us < 100.0, f"RMS calculation took {elapsed_us:.2f} µs, exceeded 100 µs target."


def test_cloud_hmac_latency_budget():
    """Verify HMAC signature computation takes < 500 µs per payload."""
    secret = "perf_secret_budget_key"
    msg = CloudMessage(
        id="test_perf_msg",
        type=MessageType.HEARTBEAT.value,
        device_id="dev_001",
        payload={"cpu": 25.0, "memory": 50.0},
    )

    t0 = time.perf_counter()
    iterations = 500
    for _ in range(iterations):
        _ = compute_signature(secret, msg)
    elapsed_us = ((time.perf_counter() - t0) * 1000000) / iterations

    assert elapsed_us < 500.0, f"HMAC sign took {elapsed_us:.2f} µs, exceeded 500 µs target."
