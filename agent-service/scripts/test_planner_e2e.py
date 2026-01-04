#!/usr/bin/env python3
"""
End-to-end test for Planner Agent via API.

Run: python scripts/test_planner_e2e.py

Requires server running:
    cd agent-service
    source ../.venv/bin/activate
    USE_MOCK_LLM=true uvicorn app.main:app --reload
"""

import json
import sys

import requests


def parse_sse_events(response) -> list[dict]:
    """Parse SSE events from streaming response."""
    events = []
    for line in response.iter_lines():
        if line:
            line = line.decode("utf-8")
            if line.startswith("data:"):
                try:
                    event = json.loads(line[5:].strip())
                    events.append(event)
                except json.JSONDecodeError as e:
                    print(f"  Warning: Failed to parse SSE: {e}")
    return events


def test_simple_task():
    """Test simple task that skips LLM planning."""
    print("=== Test 1: Simple Task ===")
    url = "http://localhost:8000/tasks"

    response = requests.post(
        url,
        json={"description": "Sort a list"},
        stream=True,
        timeout=30,
    )

    events = parse_sse_events(response)

    # Print events
    for event in events:
        event_type = event.get("event", "unknown")
        print(f"  {event_type}: {str(event)[:80]}...")

    # Verify plan events
    assert any(
        e.get("event") == "plan_start" for e in events
    ), "Missing plan_start event"
    assert any(
        e.get("event") == "plan_complete" for e in events
    ), "Missing plan_complete event"

    # Verify simple task detection
    analysis_events = [e for e in events if e.get("event") == "plan_analysis"]
    assert len(analysis_events) == 1, "Should have exactly one plan_analysis event"
    assert analysis_events[0]["is_complex"] is False, "Simple task should be is_complex=False"

    # Verify single step
    complete_events = [e for e in events if e.get("event") == "plan_complete"]
    assert complete_events[0]["total_steps"] == 1, "Simple task should have 1 step"
    assert complete_events[0]["parallel_stages"] == 1, "Simple task should have 1 stage"

    # Verify code agent events followed
    assert any(e.get("event") == "result" for e in events), "Missing result event"

    print("  ✓ Simple task passed\n")


def test_complex_task():
    """Test complex task that uses LLM planning."""
    print("=== Test 2: Complex Task (Snake Game) ===")
    url = "http://localhost:8000/tasks"

    response = requests.post(
        url,
        json={"description": "Create a snake game"},
        stream=True,
        timeout=30,
    )

    events = parse_sse_events(response)
    plan_complete = None

    # Print events
    for event in events:
        event_type = event.get("event", "unknown")
        print(f"  {event_type}: {str(event)[:80]}...")
        if event_type == "plan_complete":
            plan_complete = event

    # Verify plan events
    assert any(
        e.get("event") == "plan_start" for e in events
    ), "Missing plan_start event"
    assert plan_complete is not None, "Missing plan_complete event"

    # Verify complex task detection
    analysis_events = [e for e in events if e.get("event") == "plan_analysis"]
    assert len(analysis_events) == 1, "Should have exactly one plan_analysis event"
    assert analysis_events[0]["is_complex"] is True, "Snake game should be is_complex=True"

    # Verify multiple steps
    assert plan_complete["total_steps"] > 1, "Complex task should have multiple steps"
    assert plan_complete["parallel_stages"] > 1, "Snake game should have parallel stages"

    # Verify Mermaid diagram
    assert "graph TD" in plan_complete["mermaid"], "Should have Mermaid diagram"
    assert "config" in plan_complete["mermaid"], "Diagram should include config step"

    # Count step_identified events
    step_events = [e for e in events if e.get("event") == "plan_step_identified"]
    assert len(step_events) == plan_complete["total_steps"], \
        f"Should have {plan_complete['total_steps']} step_identified events"

    # Verify code agent events followed
    assert any(e.get("event") == "result" for e in events), "Missing result event"

    print(f"  ✓ Complex task passed: {plan_complete['total_steps']} steps, "
          f"{plan_complete['parallel_stages']} stages\n")


def test_event_order():
    """Test that events arrive in correct order."""
    print("=== Test 3: Event Order ===")
    url = "http://localhost:8000/tasks"

    response = requests.post(
        url,
        json={"description": "Create a snake game"},
        stream=True,
        timeout=30,
    )

    events = parse_sse_events(response)
    event_types = [e.get("event") for e in events]

    # Plan events should come first
    plan_start_idx = event_types.index("plan_start")
    plan_complete_idx = event_types.index("plan_complete")
    result_idx = event_types.index("result")

    assert plan_start_idx == 0, "plan_start should be first event"
    assert plan_complete_idx < result_idx, "plan_complete should come before result"

    # All plan events should be contiguous and before code agent events
    plan_events = ["plan_start", "plan_analysis", "plan_step_identified", "plan_complete"]
    code_events = ["node_start", "node_complete", "result"]

    last_plan_idx = -1
    first_code_idx = len(events)

    for i, event_type in enumerate(event_types):
        if event_type in plan_events:
            last_plan_idx = max(last_plan_idx, i)
        if event_type in code_events:
            first_code_idx = min(first_code_idx, i)

    assert last_plan_idx < first_code_idx, "All plan events should come before code events"

    print(f"  Event order: {' -> '.join(event_types[:5])}... -> {event_types[-1]}")
    print("  ✓ Event order passed\n")


def main():
    print("\n🧪 Planner Agent E2E Tests\n")
    print("=" * 50)

    try:
        # Quick connectivity check
        requests.get("http://localhost:8000/", timeout=2)
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to server at localhost:8000")
        print("\nPlease start the server first:")
        print("  cd agent-service")
        print("  source ../.venv/bin/activate")
        print("  USE_MOCK_LLM=true uvicorn app.main:app")
        sys.exit(1)

    try:
        test_simple_task()
        test_complex_task()
        test_event_order()
        print("=" * 50)
        print("✅ All E2E Tests Passed!\n")
    except AssertionError as e:
        print(f"\n❌ Test Failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
