#!/usr/bin/env python3
"""Benchmark WebSocket latency for Gemini Live API.

Measures:
- Connection establishment time
- Time to ready message
- Round-trip time (RTT) for first response
- Total turn completion time

Target: <150ms RTT for real-time voice interaction
"""

import asyncio
import json
import statistics
import sys
import time
from typing import NamedTuple

import websockets


class LatencyMetrics(NamedTuple):
    """Latency measurements for a single request."""

    connection_time_ms: float
    ready_time_ms: float
    first_response_time_ms: float
    turn_complete_time_ms: float


async def measure_single_request(token: str, message: str) -> LatencyMetrics:
    """Measure latency for a single WebSocket request.

    Args:
        token: JWT access token
        message: Text message to send

    Returns:
        LatencyMetrics with timing measurements
    """
    uri = f"ws://localhost:8000/ws/gemini/live?token={token}"

    # Measure connection time
    connect_start = time.perf_counter()
    websocket = await websockets.connect(uri)
    connect_end = time.perf_counter()
    connection_time = (connect_end - connect_start) * 1000

    try:
        # Measure time to ready message
        ready_start = time.perf_counter()
        ready_msg = await websocket.recv()
        ready_end = time.perf_counter()
        ready_time = (ready_end - ready_start) * 1000

        # Send message and measure RTT
        request_payload = {"type": "text", "content": message}
        send_start = time.perf_counter()
        await websocket.send(json.dumps(request_payload))

        # Wait for first response (audio or text)
        first_response = None
        first_response_time = None

        turn_complete = False
        while not turn_complete:
            msg = await asyncio.wait_for(websocket.recv(), timeout=30.0)

            if first_response is None:
                first_response_end = time.perf_counter()
                first_response_time = (first_response_end - send_start) * 1000
                first_response = msg

            # Check for turn complete
            if isinstance(msg, str):
                data = json.loads(msg)
                if data.get("type") == "turn_complete":
                    turn_complete_end = time.perf_counter()
                    turn_complete_time = (turn_complete_end - send_start) * 1000
                    break

        return LatencyMetrics(
            connection_time_ms=connection_time,
            ready_time_ms=ready_time,
            first_response_time_ms=first_response_time,
            turn_complete_time_ms=turn_complete_time,
        )

    finally:
        await websocket.close()


async def run_benchmark(token: str, iterations: int = 5) -> None:
    """Run latency benchmark with multiple iterations.

    Args:
        token: JWT access token
        iterations: Number of test iterations
    """
    print("=" * 70)
    print("GEMINI LIVE API WEBSOCKET LATENCY BENCHMARK")
    print("=" * 70)
    print(f"\nRunning {iterations} iterations...\n")

    # Test messages of varying lengths
    test_messages = [
        "Hi!",
        "What's the weather like?",
        "Can you explain quantum computing in one sentence?",
    ]

    all_metrics = []

    for i in range(iterations):
        message = test_messages[i % len(test_messages)]
        print(f"[{i + 1}/{iterations}] Testing with: '{message}'")

        try:
            metrics = await measure_single_request(token, message)
            all_metrics.append(metrics)

            print(f"  ✓ Connection: {metrics.connection_time_ms:.1f}ms")
            print(f"  ✓ Ready: {metrics.ready_time_ms:.1f}ms")
            print(f"  ✓ First Response (RTT): {metrics.first_response_time_ms:.1f}ms")
            print(f"  ✓ Turn Complete: {metrics.turn_complete_time_ms:.1f}ms")

            # Brief pause between iterations
            if i < iterations - 1:
                await asyncio.sleep(0.5)

        except Exception as e:
            print(f"  ❌ Error: {e}")

    # Calculate statistics
    if not all_metrics:
        print("\n❌ No successful measurements")
        return

    print("\n" + "=" * 70)
    print("LATENCY STATISTICS (milliseconds)")
    print("=" * 70)

    metrics_fields = [
        ("Connection Time", "connection_time_ms"),
        ("Ready Time", "ready_time_ms"),
        ("First Response (RTT)", "first_response_time_ms"),
        ("Turn Complete", "turn_complete_time_ms"),
    ]

    for label, field in metrics_fields:
        values = [getattr(m, field) for m in all_metrics]
        print(f"\n{label}:")
        print(f"  Min:    {min(values):.1f}ms")
        print(f"  Max:    {max(values):.1f}ms")
        print(f"  Avg:    {statistics.mean(values):.1f}ms")
        print(f"  Median: {statistics.median(values):.1f}ms")
        if len(values) >= 2:
            print(f"  StdDev: {statistics.stdev(values):.1f}ms")

    # Check RTT target
    rtt_values = [m.first_response_time_ms for m in all_metrics]
    avg_rtt = statistics.mean(rtt_values)
    print("\n" + "=" * 70)
    print("PERFORMANCE ASSESSMENT")
    print("=" * 70)
    print(f"\nAverage RTT: {avg_rtt:.1f}ms")
    print("Target RTT:  <150ms")

    if avg_rtt < 150:
        print(f"✅ PASS - Average RTT is {150 - avg_rtt:.1f}ms below target")
    else:
        print(f"❌ FAIL - Average RTT is {avg_rtt - 150:.1f}ms above target")

    # Additional insights
    print(
        f"\nConnection overhead: {statistics.mean([m.connection_time_ms for m in all_metrics]):.1f}ms"
    )
    print(f"Ready overhead:      {statistics.mean([m.ready_time_ms for m in all_metrics]):.1f}ms")
    print(
        f"Total latency:       {statistics.mean([m.turn_complete_time_ms for m in all_metrics]):.1f}ms"
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python benchmark_websocket_latency.py <access_token> [iterations]")
        print("\nGet your access token from the /auth/callback response")
        print("Example: python benchmark_websocket_latency.py eyJhbGc... 10")
        sys.exit(1)

    token = sys.argv[1]
    iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    asyncio.run(run_benchmark(token, iterations))
