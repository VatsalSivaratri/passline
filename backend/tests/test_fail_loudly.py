"""
Gemini failures must surface as AnalysisError, never as a fake default.

Before: classify_room returned 'entrance' and analyze_features returned
{"features": []} on any failure, which looked like real predictions
("this is an entrance with no violations"). These tests mock the Gemini
client, so they need no API key or network.
"""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import services.gemini_analysis as ga  # noqa: E402
from services.gemini_analysis import AnalysisError  # noqa: E402

FRAMES = ["a.jpg", "b.jpg"]


class FakeClient:
    """Stands in for genai.Client: returns `reply` as response text, or raises it."""

    def __init__(self, reply):
        self.calls = 0
        self.models = SimpleNamespace(generate_content=self._generate)
        self._reply = reply

    def _generate(self, **kwargs):
        self.calls += 1
        if isinstance(self._reply, Exception):
            raise self._reply
        return SimpleNamespace(text=self._reply)


@pytest.fixture
def gemini(monkeypatch):
    """Install a fake client and skip reading frames from disk."""
    monkeypatch.setattr(ga, "_load_frame_as_part", lambda p: b"jpeg")
    monkeypatch.setattr(ga.time, "sleep", lambda s: None)  # skip retry backoff in tests

    def install(reply):
        client = FakeClient(reply)
        monkeypatch.setattr(ga, "_get_client", lambda: client)
        return client

    return install


def run(coro):
    return asyncio.run(coro)


# ---- classify_room ----

def test_classify_valid(gemini):
    gemini('{"room_type": "restroom"}')
    assert run(ga.classify_room(FRAMES)) == "restroom"


def test_classify_api_error_raises(gemini):
    client = gemini(RuntimeError("quota exceeded"))
    with pytest.raises(AnalysisError, match="quota exceeded"):
        run(ga.classify_room(FRAMES))
    assert client.calls == 3  # retried, then gave up


def test_classify_unknown_type_raises(gemini):
    gemini('{"room_type": "spaceship"}')
    with pytest.raises(AnalysisError, match="spaceship"):
        run(ga.classify_room(FRAMES))


def test_classify_bad_json_raises(gemini):
    gemini("not json")
    with pytest.raises(AnalysisError, match="invalid JSON"):
        run(ga.classify_room(FRAMES))


def test_classify_no_frames_raises(gemini, monkeypatch):
    gemini('{"room_type": "restroom"}')

    def unreadable(p):
        raise FileNotFoundError(p)

    monkeypatch.setattr(ga, "_load_frame_as_part", unreadable)
    with pytest.raises(AnalysisError, match="no frames"):
        run(ga.classify_room(FRAMES))


# ---- analyze_features ----

def test_features_valid_and_fenced_json(gemini):
    gemini('```json\n{"features": [{"feature_type": "door"}, {"feature_type": "unicorn"}]}\n```')
    result = run(ga.analyze_features(FRAMES))
    assert [f["feature_type"] for f in result["features"]] == ["door"]  # unknown type dropped


def test_features_empty_list_is_a_real_answer(gemini):
    gemini('{"features": []}')
    assert run(ga.analyze_features(FRAMES)) == {"features": []}


def test_features_api_error_raises(gemini):
    gemini(RuntimeError("503"))
    with pytest.raises(AnalysisError):
        run(ga.analyze_features(FRAMES))


def test_features_missing_key_raises(gemini):
    gemini('{"objects": []}')
    with pytest.raises(AnalysisError, match="no 'features' list"):
        run(ga.analyze_features(FRAMES))
