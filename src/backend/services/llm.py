"""Local LLM extraction service using Ollama and Qwen3.

Enforces:
- 100% offline local inference (http://127.0.0.1:11434)
- Extraction only, no hallucination or invention
- Returns null for missing/unclear fields
- Never predicts fraud or determines authenticity
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "60.0"))

EXTRACTION_FIELDS = [
    "document_type",
    "issuing_authority",
    "permit_number",
    "organization_name",
    "purpose",
    "issue_date",
    "expiration_date",
    "beneficiaries",
]


class ExtractedDocumentFields(BaseModel):
    """Schema for structured document extraction."""

    document_type: str | None = None
    issuing_authority: str | None = None
    permit_number: str | None = None
    organization_name: str | None = None
    purpose: str | None = None
    issue_date: str | None = None
    expiration_date: str | None = None
    beneficiaries: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    confidence_notes: str | None = None


SYSTEM_PROMPT = """You are a factual document text extractor assisting administrative verification of Philippine relief fundraisers.
Your sole job is to extract explicit factual fields from the provided document text into JSON.

Strict Rules:
1. Extract ONLY facts explicitly stated in the document text.
2. Return null for any field that is missing, unmentioned, ambiguous, or illegible. NEVER invent, guess, or extrapolate.
3. Dates must be formatted as YYYY-MM-DD if clearly identifiable, otherwise verbatim or null.
4. Do NOT judge authenticity, do NOT predict fraud, and do NOT make approval recommendations.
5. In 'missing_fields', list the names of any standard fields that were null or not found in the text.
6. Return ONLY a valid JSON object matching the requested schema. No surrounding commentary."""


def build_user_prompt(raw_text: str) -> str:
    return f"""Extract fields from the following document text into JSON.
Target fields:
- document_type (e.g. "Solicitation Permit", "SEC Certificate", "Bank Statement", "Post Screenshot", etc.)
- issuing_authority (e.g. "DSWD", "SEC", "City Government of Marikina", etc.)
- permit_number (e.g. "DSWD-SB-SP-00123-2026")
- organization_name
- purpose
- issue_date (YYYY-MM-DD)
- expiration_date (YYYY-MM-DD)
- beneficiaries
- missing_fields (array of strings)

DOCUMENT TEXT:
\"\"\"
{raw_text}
\"\"\""""


class OllamaServiceError(Exception):
    """Base exception for Ollama LLM errors."""


class OllamaUnavailableError(OllamaServiceError):
    """Raised when Ollama server cannot be reached."""


async def check_ollama_health(host: str = OLLAMA_HOST) -> bool:
    """Check if Ollama local service is reachable."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{host.rstrip('/')}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


def sanitize_extracted_data(data: dict[str, Any]) -> ExtractedDocumentFields:
    """Validate and clean extracted dictionary, ensuring missing_fields is accurate."""
    # Convert empty strings to None for string fields
    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            val_strip = value.strip()
            cleaned[key] = val_strip if val_strip and val_strip.lower() != "null" else None
        else:
            cleaned[key] = value

    missing: list[str] = []
    for field in EXTRACTION_FIELDS:
        if cleaned.get(field) is None:
            missing.append(field)

    cleaned["missing_fields"] = sorted(list(set(missing)))
    return ExtractedDocumentFields(**cleaned)


async def call_ollama_extraction(
    raw_text: str,
    *,
    host: str = OLLAMA_HOST,
    model: str = OLLAMA_MODEL,
    timeout: float = OLLAMA_TIMEOUT,
) -> tuple[ExtractedDocumentFields, str]:
    """Call Ollama local API and parse structured extraction.

    Returns:
        tuple[ExtractedDocumentFields, str]: (parsed_fields, raw_llm_json_response)
    """
    if not raw_text or not raw_text.strip():
        # Empty text yields empty extraction without calling LLM
        empty_data = sanitize_extracted_data({"missing_fields": EXTRACTION_FIELDS})
        return empty_data, "{}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(raw_text)},
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.0,
        },
    }

    url = f"{host.rstrip('/')}/api/chat"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
    except httpx.ConnectError as exc:
        logger.error("Failed to connect to Ollama at %s: %s", url, exc)
        raise OllamaUnavailableError(f"Cannot reach Ollama at {url}") from exc
    except httpx.TimeoutException as exc:
        logger.error("Ollama request timed out after %ss: %s", timeout, exc)
        raise OllamaServiceError(f"Ollama request timed out after {timeout}s") from exc
    except Exception as exc:
        logger.error("Unexpected error contacting Ollama: %s", exc)
        raise OllamaServiceError(f"Ollama call failed: {exc}") from exc

    if response.status_code != 200:
        logger.error("Ollama returned HTTP %d: %s", response.status_code, response.text)
        raise OllamaServiceError(
            f"Ollama returned HTTP {response.status_code}: {response.text[:200]}"
        )

    response_json = response.json()
    message_content = response_json.get("message", {}).get("content", "").strip()

    # Parse JSON from content
    try:
        parsed_dict = json.loads(message_content)
    except json.JSONDecodeError:
        # Fallback regex search for json block if model included extra text
        match = re.search(r"\{.*\}", message_content, re.DOTALL)
        if match:
            try:
                parsed_dict = json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise OllamaServiceError("Model did not return valid JSON") from exc
        else:
            raise OllamaServiceError("Model did not return valid JSON")

    validated = sanitize_extracted_data(parsed_dict)
    return validated, message_content
