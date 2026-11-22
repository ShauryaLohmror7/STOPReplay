"""Shared runtime adapter tests: the Anushree-contract bridge in src/runtime.

Fully mocked; no network, no key. Covers the parsed-dict return, the error
taxonomy (refusal / timeout-as-TimeoutError / provider / invalid output), and
the PromptedAdapter metadata Cem needs.
"""

import io
import json
import os
import socket
import sys
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.runtime import adapter as rt
from src.runtime.adapter import (
    DEFAULT_ANALYSIS_MODEL,
    InvalidModelOutput,
    ModelAdapter,
    ModelRefusal,
    ModelTimeout,
    ProviderError,
    build_analysis_adapter,
)
from stopreplay_analysis import Analyzer, AnalysisError
from stopreplay_analysis.models import AnalysisRequest, Event
from stopreplay_analysis.prompting import build_prompt

VALID_FINDING = {
    "outcome": "new",
    "finding": {
        "statement": "The agenda says the demo is in Room A.",
        "kind": "observation",
        "evidence": [{"event_id": "e1", "source_ref": "agenda-v1",
                      "quote": "The demo is in Room A."}],
        "revises": None,
        "uncertainty": None,
    },
    "reason": "The source directly states the room.",
}


def _request():
    event = Event("demo", "e1", 1, "agenda-v1", "The demo is in Room A.")
    return AnalysisRequest("a1", event, (), ())


class _Resp:
    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


def _envelope(content: str, finish_reason: str = "stop") -> bytes:
    return json.dumps({
        "choices": [{"finish_reason": finish_reason,
                     "message": {"role": "assistant", "content": content}}],
    }).encode("utf-8")


def _patch(side_effect=None, return_value=None):
    target = "src.runtime.adapter.urllib.request.urlopen"
    if side_effect is not None:
        return mock.patch(target, side_effect=side_effect)
    return mock.patch(target, return_value=return_value)


class BridgeTests(unittest.TestCase):

    def setUp(self):
        # Real (non-mock) adapter so calls hit the patched network path.
        self.adapter = build_analysis_adapter(
            ModelAdapter(api_key="test-key", model="qwen/qwen-2.5-72b-instruct"))

    def test_generate_returns_parsed_dict(self):
        with _patch(return_value=_Resp(_envelope(json.dumps(VALID_FINDING)))):
            result = self.adapter.generate(_request())
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result), {"outcome", "finding", "reason"})
        self.assertEqual(result["outcome"], "new")

    def test_content_filter_is_refusal(self):
        with _patch(return_value=_Resp(_envelope("", finish_reason="content_filter"))):
            with self.assertRaises(ModelRefusal):
                self.adapter.generate(_request())

    def test_timeout_maps_to_model_timeout(self):
        with _patch(side_effect=socket.timeout("slow")):
            with self.assertRaises(ModelTimeout):
                self.adapter.generate(_request())

    def test_model_timeout_is_builtin_timeout_error(self):
        # The fix Anushree asked for: her `except TimeoutError` must catch it.
        with _patch(side_effect=socket.timeout("slow")):
            with self.assertRaises(TimeoutError):
                self.adapter.generate(_request())

    def test_http_500_is_provider_error(self):
        err = urllib.error.HTTPError("u", 500, "boom", None, io.BytesIO(b'{"error":"x"}'))
        with _patch(side_effect=err):
            with self.assertRaises(ProviderError) as ctx:
                self.adapter.generate(_request())
        self.assertEqual(ctx.exception.status, 500)

    def test_non_json_is_invalid_output(self):
        with _patch(return_value=_Resp(_envelope("not json at all"))):
            with self.assertRaises(InvalidModelOutput):
                self.adapter.generate(_request())

    def test_json_non_object_is_invalid_output(self):
        with _patch(return_value=_Resp(_envelope("[1, 2, 3]"))):
            with self.assertRaises(InvalidModelOutput):
                self.adapter.generate(_request())


class MetadataTests(unittest.TestCase):

    def test_metadata_matches_cem_requirements(self):
        adapter = build_analysis_adapter(
            ModelAdapter(api_key="k", model="qwen/qwen-2.5-72b-instruct"))
        meta = adapter.metadata
        self.assertEqual(meta.provider, "openrouter")
        self.assertEqual(meta.model_version, "qwen/qwen-2.5-72b-instruct")
        self.assertIn(meta.prompt_version, ("evidence-analysis-v1", "evidence-analysis-v2"))
        self.assertEqual(json.loads(meta.parameters_json),
                         {"temperature": 0.2, "top_p": 1.0})

    def test_default_model_slug(self):
        self.assertEqual(DEFAULT_ANALYSIS_MODEL, "qwen/qwen3-next-80b-a3b-instruct:free")
        self.assertEqual(build_analysis_adapter().metadata.model_version,
                         DEFAULT_ANALYSIS_MODEL)

    def test_explicit_model_param(self):
        meta = build_analysis_adapter(model="some/other-model").metadata
        self.assertEqual(meta.model_version, "some/other-model")

    def test_mock_mode_reports_deterministic_provider(self):
        mocked = ModelAdapter(mock_mode=True)
        mocked.set_mock_response("evidence", json.dumps(VALID_FINDING))
        adapter = build_analysis_adapter(mocked)
        self.assertEqual(adapter.metadata.provider, "deterministic_mock")
        result = adapter.generate(_request())  # offline, no network
        self.assertEqual(result["outcome"], "new")


class EndToEndMappingTests(unittest.TestCase):
    """Route the adapter's real errors through Anushree's Analyzer and assert the
    engine surfaces distinct codes, with no provider body leaking."""

    def setUp(self):
        self.analyzer = Analyzer(build_analysis_adapter(
            ModelAdapter(api_key="k", model="qwen/qwen-2.5-72b-instruct")))

    def _run(self):
        event = Event("demo", "e1", 1, "agenda-v1", "The demo is in Room A.")
        return self.analyzer.analyze_incremental(event, analysis_id="v1")

    def test_refusal_surfaces_as_refusal(self):
        with _patch(return_value=_Resp(_envelope("", finish_reason="content_filter"))):
            with self.assertRaises(AnalysisError) as c:
                self._run()
        self.assertEqual(c.exception.code, "refusal")
        self.assertIsNone(c.exception.__cause__)

    def test_timeout_surfaces_as_timeout(self):
        with _patch(side_effect=socket.timeout("slow")):
            with self.assertRaises(AnalysisError) as c:
                self._run()
        self.assertEqual(c.exception.code, "timeout")

    def test_http_error_surfaces_as_provider_failure_without_body(self):
        err = urllib.error.HTTPError("u", 500, "boom", None, io.BytesIO(b'{"secret":"boom-body"}'))
        with _patch(side_effect=err):
            with self.assertRaises(AnalysisError) as c:
                self._run()
        self.assertEqual(c.exception.code, "provider_failure")
        self.assertNotIn("boom-body", str(c.exception))  # provider body never leaks

    def test_invalid_output_surfaces_as_provider_failure(self):
        with _patch(return_value=_Resp(_envelope("not json at all"))):
            with self.assertRaises(AnalysisError) as c:
                self._run()
        self.assertEqual(c.exception.code, "provider_failure")


if __name__ == "__main__":
    unittest.main()
