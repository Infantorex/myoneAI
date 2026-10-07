"""Voice pipeline performance benchmark for myoneAI.

Measures VAD chunk processing latency, RMS energy calculation throughput,
audio encoding/decoding performance, and memory footprint.
"""

import asyncio
import io
import json
import os
import sys
import time
import tracemalloc
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import psutil

from app.voice.audio import AudioPlayer
from app.voice.audio_config import AudioConfig
from app.voice.microphone import pcm_to_wav_bytes
from app.voice.stt import MockSTTProvider
from app.voice.tts import MockTTSProvider
from app.voice.vad import VoiceActivityDetector, VADState


def run_benchmark():
    tracemalloc.start()
    process = psutil.Process(os.getpid())
    results = {}

    print("=" * 60)
    print("myoneAI — Voice Pipeline Performance Benchmark")
    print("=" * 60)

    # Prepare sample synthetic 16-bit 16kHz PCM audio
    sample_rate = 16000
    chunk_size = 1024
    num_samples = chunk_size * 100  # 100 chunks (~6.4 seconds of audio)
    # Generate speech-like waveform with quiet intervals
    t = np.linspace(0, 6.4, num_samples, dtype=np.float32)
    waveform = (np.sin(2 * np.pi * 440 * t) * 12000).astype(np.int16)
    audio_pcm = waveform.tobytes()
    chunks = [audio_pcm[i : i + chunk_size * 2] for i in range(0, len(audio_pcm), chunk_size * 2)]

    # 1. RMS Calculation Speed (10,000 chunks)
    vad = VoiceActivityDetector()
    test_chunk = chunks[0] if chunks else b"\x00" * (chunk_size * 2)

    t0 = time.perf_counter()
    for _ in range(5000):
        _ = vad.calculate_rms(test_chunk)
    t_rms_total = (time.perf_counter() - t0) * 1000
    us_per_chunk = (t_rms_total / 5000) * 1000
    results["rms_per_chunk_us"] = round(us_per_chunk, 3)
    results["rms_throughput_chunks_per_sec"] = round(5000 / (t_rms_total / 1000), 1)
    print(f"[*] RMS Energy Compute:         {us_per_chunk:7.3f} µs / chunk ({results['rms_throughput_chunks_per_sec']:.0f} chunks/sec)")

    # 2. VAD State Machine 100-chunk Simulation
    vad.reset()
    vad.calibrate_ambient_noise(chunks[:10])
    t0 = time.perf_counter()
    for chunk in chunks:
        _ = vad.process_chunk(chunk)
    t_vad_stream = (time.perf_counter() - t0) * 1000
    recorded = vad.get_recorded_audio()
    results["vad_100_chunks_ms"] = round(t_vad_stream, 2)
    results["vad_per_chunk_us"] = round((t_vad_stream / len(chunks)) * 1000, 3)
    print(f"[*] VAD 100 Chunks Processing:  {t_vad_stream:7.2f} ms ({results['vad_per_chunk_us']:.3f} µs/chunk)")

    # 3. PCM to WAV in-memory Conversion
    t0 = time.perf_counter()
    from app.voice.audio_config import DEFAULT_AUDIO_CONFIG
    wav_bytes = pcm_to_wav_bytes(audio_pcm, config=DEFAULT_AUDIO_CONFIG)
    t_wav_enc = (time.perf_counter() - t0) * 1000
    results["pcm_to_wav_ms"] = round(t_wav_enc, 3)
    print(f"[*] PCM to WAV Encoding:        {t_wav_enc:7.3f} ms ({len(wav_bytes) / 1024:.1f} KB)")

    # 4. Audio Player Decode WAV
    player = AudioPlayer()
    t0 = time.perf_counter()
    samples, sr = player.decode_audio_bytes(wav_bytes)
    t_decode = (time.perf_counter() - t0) * 1000
    results["audio_decode_ms"] = round(t_decode, 3)
    print(f"[*] Audio Player WAV Decode:    {t_decode:7.3f} ms ({len(samples)} samples @ {sr}Hz)")

    # 5. Mock STT Transcribe Latency (async)
    stt = MockSTTProvider(default_response="வணக்கம் ஜார்விஸ்")
    async def test_stt():
        t0 = time.perf_counter()
        res = await stt.transcribe(wav_bytes)
        return (time.perf_counter() - t0) * 1000, res

    t_stt, stt_res = asyncio.run(test_stt())
    results["stt_mock_latency_ms"] = round(t_stt, 3)
    print(f"[*] STT Engine Latency (Mock):  {t_stt:7.3f} ms -> '{stt_res.text}'")

    # 6. Mock TTS Synthesis Latency (async)
    tts = MockTTSProvider()
    async def test_tts():
        t0 = time.perf_counter()
        res = await tts.synthesize("வணக்கம் Infanto, நான் உங்களுக்கு உதவ தயாராக உள்ளேன்.")
        return (time.perf_counter() - t0) * 1000, res

    t_tts, tts_res = asyncio.run(test_tts())
    results["tts_mock_latency_ms"] = round(t_tts, 3)
    print(f"[*] TTS Engine Latency (Mock):  {t_tts:7.3f} ms -> {len(tts_res.audio_bytes)} bytes audio")

    # Resource Profile
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    mem_info = process.memory_info()

    results["rss_mb"] = round(mem_info.rss / (1024 * 1024), 2)
    results["traced_peak_kb"] = round(peak_mem / 1024, 2)
    print("-" * 60)
    print(f"[*] Voice Benchmark Peak Heap:  {results['traced_peak_kb']:7.2f} KB")
    print(f"[*] Process RSS Memory:          {results['rss_mb']:7.2f} MB")
    print("=" * 60)

    return results


if __name__ == "__main__":
    res = run_benchmark()
    if "--json" in sys.argv:
        print(json.dumps(res, indent=2))
