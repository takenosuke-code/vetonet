"""Tests for vetonet.llm.json_utils — unified JSON extraction from LLM responses."""

import pytest

from vetonet.llm.json_utils import (
    _extract_single_json_object,
    extract_json_from_llm_response,
)


# --- _extract_single_json_object tests ---


class TestExtractSingleJsonObject:
    def test_simple_object(self):
        assert _extract_single_json_object('{"key": "value"}') == {"key": "value"}

    def test_object_with_surrounding_text(self):
        text = 'Here is the result: {"score": 42} hope that helps!'
        assert _extract_single_json_object(text) == {"score": 42}

    def test_nested_object(self):
        text = '{"outer": {"inner": 1}}'
        assert _extract_single_json_object(text) == {"outer": {"inner": 1}}

    def test_escaped_braces_in_strings(self):
        text = '{"msg": "use \\"{}\\" for format"}'
        result = _extract_single_json_object(text)
        assert result is not None
        assert result["msg"] == 'use "{}" for format'

    def test_no_json(self):
        assert _extract_single_json_object("no json here") is None

    def test_incomplete_json(self):
        assert _extract_single_json_object('{"key": "value"') is None

    def test_returns_only_first_object(self):
        text = '{"a": 1} {"b": 2}'
        assert _extract_single_json_object(text) == {"a": 1}

    def test_array_not_returned(self):
        # Only dicts are returned, not arrays
        assert _extract_single_json_object("[1, 2, 3]") is None


# --- extract_json_from_llm_response tests ---


class TestExtractJsonFromLlmResponse:
    def test_clean_json(self):
        assert extract_json_from_llm_response('{"ok": true}') == {"ok": True}

    def test_json_with_whitespace(self):
        assert extract_json_from_llm_response('  \n{"ok": true}\n  ') == {"ok": True}

    def test_markdown_code_fence_json(self):
        text = '```json\n{"key": "val"}\n```'
        assert extract_json_from_llm_response(text) == {"key": "val"}

    def test_markdown_code_fence_no_language(self):
        text = '```\n{"key": "val"}\n```'
        assert extract_json_from_llm_response(text) == {"key": "val"}

    def test_prose_around_json(self):
        text = 'Sure! Here is the JSON:\n{"action": "buy"}\nLet me know if you need more.'
        assert extract_json_from_llm_response(text) == {"action": "buy"}

    def test_code_fence_with_prose(self):
        text = 'Here you go:\n```json\n{"x": 1}\n```\nDone.'
        assert extract_json_from_llm_response(text) == {"x": 1}

    def test_raises_on_no_json(self):
        with pytest.raises(ValueError, match="No valid JSON object found"):
            extract_json_from_llm_response("This has no JSON at all.")

    def test_raises_on_empty_string(self):
        with pytest.raises(ValueError, match="No valid JSON object found"):
            extract_json_from_llm_response("")

    def test_raises_on_array(self):
        # Arrays are not valid — we only accept dicts
        with pytest.raises(ValueError, match="No valid JSON object found"):
            extract_json_from_llm_response("[1, 2, 3]")

    def test_fast_path_preferred_over_extraction(self):
        """When text is valid JSON directly, fast path should handle it."""
        text = '{"fast": "path"}'
        assert extract_json_from_llm_response(text) == {"fast": "path"}
