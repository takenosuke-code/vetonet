"""
Unified JSON extraction utilities for LLM responses.

Handles markdown code fences, surrounding prose, and balanced-brace
extraction to safely parse JSON from any LLM backend.
"""

import json
import re


def _extract_single_json_object(text: str) -> dict | None:
    """
    Securely extract a single JSON object from text.
    Uses balanced brace counting to prevent injection attacks.
    """
    start_idx = text.find("{")
    if start_idx == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i, char in enumerate(text[start_idx:], start_idx):
        if escape_next:
            escape_next = False
            continue

        if char == "\\" and in_string:
            escape_next = True
            continue

        # escape_next is always False here — it was consumed by the continue above
        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                # Found complete object
                json_str = text[start_idx : i + 1]
                try:
                    obj = json.loads(json_str)
                    # Only accept JSON objects (dicts), not arrays or primitives
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    return None
                return None

    return None


def extract_json_from_llm_response(text: str) -> dict:
    """
    Extract a JSON object from an LLM response string.

    Handles common LLM output formats:
    1. Strips markdown code fences (```json ... ```)
    2. Tries direct json.loads (fast path for clean responses)
    3. Falls back to balanced-brace extraction for prose-wrapped JSON

    Args:
        text: Raw LLM response text.

    Returns:
        Parsed dict from the JSON object.

    Raises:
        ValueError: If no valid JSON object can be extracted.
    """
    if not isinstance(text, str):
        raise ValueError("Expected string input")

    cleaned = text.strip()

    # Strip markdown code fences if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # Fast path: direct parse
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: balanced-brace extraction for text with surrounding prose
    obj = _extract_single_json_object(cleaned)
    if obj is not None:
        return obj

    raise ValueError("No valid JSON object found in LLM response")
