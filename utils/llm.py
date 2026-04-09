from __future__ import annotations

import json
import os
from typing import Any

import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "qwen/qwen3.6-plus:free"
DEFAULT_TIMEOUT_SECONDS = 60


class LLMRequestError(Exception):
    """Raised when an LLM request fails or returns an invalid payload."""


class LLMConfigurationError(Exception):
    """Raised when required LLM configuration is missing."""


def _resolve_api_key() -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise LLMConfigurationError("Missing OPENROUTER_API_KEY")
    return api_key


def _resolve_model(model: str | None) -> str:
    resolved_model = (model or os.getenv("OPENROUTER_MODEL") or DEFAULT_MODEL).strip()
    if not resolved_model:
        raise LLMConfigurationError("Missing OpenRouter model configuration")
    return resolved_model


def _resolve_prompt(prompt: str | None, user_prompt: str | None) -> str:
    final_prompt = (user_prompt if user_prompt is not None else prompt) or ""
    final_prompt = final_prompt.strip()
    if not final_prompt:
        raise LLMConfigurationError("No prompt provided")
    return final_prompt


def _extract_text_content(message_content: Any) -> str:
    if isinstance(message_content, str):
        return message_content.strip()

    if isinstance(message_content, list):
        text_parts = []
        for part in message_content:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    text_parts.append(text.strip())
        return "\n".join(text_parts).strip()

    return str(message_content).strip()


def _extract_json_payload(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise LLMRequestError("LLM response did not contain a valid JSON object.") from None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMRequestError("Failed to parse JSON content from LLM response.") from exc

    if not isinstance(parsed, dict):
        raise LLMRequestError("LLM response JSON must be an object.")
    return parsed


def chat_completion(
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 1200,
    model: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    response_format: dict[str, str] | None = None,
) -> str:
    """Call OpenRouter chat completions and return the assistant text content."""

    headers = {
        "Authorization": f"Bearer {_resolve_api_key()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "StockSense India",
    }
    payload: dict[str, Any] = {
        "model": _resolve_model(model),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format is not None:
        payload["response_format"] = response_format

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise LLMRequestError(f"OpenRouter request failed: {exc}") from exc

    try:
        body = response.json()
    except ValueError as exc:
        raise LLMRequestError("OpenRouter returned a non-JSON response.") from exc

    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LLMRequestError("Invalid response format from OpenRouter: missing choices.")

    content = choices[0].get("message", {}).get("content", "")
    extracted_content = _extract_text_content(content)
    if not extracted_content:
        raise LLMRequestError("OpenRouter response did not include any message content.")
    return extracted_content


def complete_json(
    prompt: str | None = None,
    user_prompt: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1200,
    model: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Request a JSON response from OpenRouter.

    Backward compatibility:
    - `prompt` continues to work as the legacy user message input.
    - `user_prompt` takes precedence when both are provided.
    - callers may now also pass `system_prompt`, `temperature`, `max_tokens`, and `model`.
    """

    final_prompt = _resolve_prompt(prompt=prompt, user_prompt=user_prompt)
    messages: list[dict[str, str]] = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt.strip()})

    messages.append({"role": "user", "content": final_prompt})

    content = chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
        timeout=timeout,
        response_format={"type": "json_object"},
    )

    try:
        return _extract_json_payload(content)
    except LLMRequestError:
        return {"response": content}
