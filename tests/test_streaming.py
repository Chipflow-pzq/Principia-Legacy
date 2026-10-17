"""Provider bounds apply separately to SSE overhead and decoded content."""

import json
import pytest
from principia_legacy.providers import streamed_body, Provider


def event(text="", finish=None, padding=""):
    return (
        "data: "
        + json.dumps(
            {
                "choices": [{"delta": {"content": text}, "finish_reason": finish}],
                "padding": padding,
            }
        )
        + "\n"
    ).encode()


def test_streaming_envelopes_do_not_truncate_valid_long_outputs():
    # A token-level transport may carry many megabytes of repeated metadata.
    chunk = event("x", padding="." * 900)
    response = iter([chunk] * 5000 + [event(finish="stop"), b"data: [DONE]\n"])
    result = streamed_body(response, {})
    assert result["choices"][0]["message"]["content"] == "x" * 5000
    assert result["choices"][0]["finish_reason"] == "stop"


def test_decoded_output_and_transport_have_independent_caps():
    with pytest.raises(ValueError, match="decoded output"):
        streamed_body(iter([event("x" * 2_000_001)]), {})
    with pytest.raises(ValueError, match="transport"):
        streamed_body(iter([b"comment " + b"." * 9_000_000] * 4), {})


def test_missing_completion_marker_is_never_accepted():
    with pytest.raises(TimeoutError, match="completion marker"):
        streamed_body(iter([event("{}", finish="stop")]), {})


def test_attempt_is_recorded_before_transmission(tmp_path, monkeypatch):
    monkeypatch.setenv("SILICONFLOW_API_KEY", "test-only-placeholder")
    monkeypatch.setattr("principia_legacy.providers.time.sleep", lambda _: None)
    seen = []

    def fail(*args, **kwargs):
        receipts = list((tmp_path / ".work/receipts").glob("*.json"))
        running = [
            json.loads(p.read_text())
            for p in receipts
            if json.loads(p.read_text())["state"] == "running"
        ]
        assert len(running) == 1
        seen.append(running[0]["trace_id"])
        raise TimeoutError("synthetic interruption")

    monkeypatch.setattr("principia_legacy.providers.urllib.request.urlopen", fail)
    with pytest.raises(RuntimeError, match="Provider job failed"):
        Provider(tmp_path).complete("fixture", {}, "fixture", 10)
    assert len(set(seen)) == 1
    assert all(
        json.loads(p.read_text())["state"] == "unknown_possible_charge"
        for p in (tmp_path / ".work/receipts").glob("*.json")
    )
    with pytest.raises(RuntimeError, match="unresolved submitted request"):
        Provider(tmp_path).complete("fixture", {}, "fixture", 10)
    assert len(seen) == 1
