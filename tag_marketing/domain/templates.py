"""Pure WhatsApp template definition rules and rendering."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

NAME = re.compile(r"^[a-z0-9_]{1,512}$")
LANGUAGE = re.compile(r"^[a-z]{2,3}(?:_[A-Z]{2})?$")
PLACEHOLDER = re.compile(r"\{\{([1-9][0-9]{0,2})\}\}")
PLACEHOLDER_LIKE = re.compile(r"\{\{|\}\}")
SUPPORTED_CATEGORIES = frozenset({"Marketing", "Utility"})
MAX_COMPONENTS = 5
MAX_BODY_LENGTH = 1024
MAX_VARIABLES = 100
MAX_BUTTONS = 3


def canonical_components(value: Any) -> list[dict[str, Any]]:
	"""Validate the editable v1 subset; unknown provider components remain read-only."""
	if isinstance(value, str):
		try:
			value = json.loads(value)
		except (ValueError, TypeError):
			raise ValueError("invalid_components") from None
	if not isinstance(value, list) or not 1 <= len(value) <= MAX_COMPONENTS:
		raise ValueError("invalid_components")
	result: list[dict[str, Any]] = []
	seen: set[str] = set()
	for component in value:
		if not isinstance(component, Mapping) or not isinstance(component.get("type"), str):
			raise ValueError("invalid_component")
		kind = component["type"].upper()
		if kind in seen:
			raise ValueError("duplicate_component")
		seen.add(kind)
		if kind == "HEADER":
			format_ = component.get("format", "TEXT")
			if format_ != "TEXT" or not _keys(component, {"type", "format", "text", "example"}):
				raise ValueError("unsupported_component")
			text = component.get("text", "")
			if not isinstance(text, str) or len(text) > 60 or PLACEHOLDER.search(text):
				raise ValueError("invalid_header")
			clean = {"type": "HEADER", "format": "TEXT"}
			if text:
				clean["text"] = text
			result.append(clean)
		elif kind == "BODY":
			if not _keys(component, {"type", "text", "example"}):
				raise ValueError("invalid_body")
			text = component.get("text")
			if not isinstance(text, str) or not 1 <= len(text) <= MAX_BODY_LENGTH:
				raise ValueError("invalid_body")
			matches = list(PLACEHOLDER.finditer(text))
			indices = [int(match.group(1)) for match in matches]
			unmatched = PLACEHOLDER.sub("", text)
			if PLACEHOLDER_LIKE.search(unmatched):
				raise ValueError("invalid_placeholders")
			if len(indices) > MAX_VARIABLES or sorted(set(indices)) != list(
				range(1, max(indices, default=0) + 1)
			):
				raise ValueError("invalid_placeholders")
			body_component: dict[str, Any] = {"type": "BODY", "text": text}
			if matches:
				body_component["example"] = {
					"body_text": [[f"Example {index}" for index in range(1, max(indices) + 1)]]
				}
			result.append(body_component)
		elif kind == "FOOTER":
			text = component.get("text")
			if not isinstance(text, str) or len(text) > 60 or PLACEHOLDER.search(text):
				raise ValueError("invalid_footer")
			result.append({"type": "FOOTER", "text": text})
		elif kind == "BUTTONS":
			buttons = component.get("buttons")
			if not isinstance(buttons, list) or not 1 <= len(buttons) <= MAX_BUTTONS:
				raise ValueError("invalid_buttons")
			clean_buttons = []
			for button in buttons:
				if not isinstance(button, Mapping) or not isinstance(button.get("type"), str):
					raise ValueError("invalid_button")
				type_ = button["type"].upper()
				text = button.get("text")
				if not isinstance(text, str) or not 1 <= len(text) <= 25:
					raise ValueError("invalid_button")
				if type_ == "QUICK_REPLY" and _keys(button, {"type", "text"}):
					clean_buttons.append({"type": type_, "text": text})
				elif type_ == "URL" and _keys(button, {"type", "text", "url"}):
					url = button.get("url")
					if not isinstance(url, str) or not url.startswith("https://") or len(url) > 2000:
						raise ValueError("invalid_button_url")
					clean_buttons.append({"type": type_, "text": text, "url": url})
				else:
					raise ValueError("unsupported_button")
			result.append({"type": "BUTTONS", "buttons": clean_buttons})
		else:
			raise ValueError("unsupported_component")
	if "BODY" not in seen:
		raise ValueError("body_required")
	return result


def validate_definition(name: Any, language: Any, category: Any, components: Any) -> list[dict[str, Any]]:
	if not isinstance(name, str) or not NAME.fullmatch(name):
		raise ValueError("invalid_name")
	if not isinstance(language, str) or not LANGUAGE.fullmatch(language):
		raise ValueError("invalid_language")
	if category not in SUPPORTED_CATEGORIES:
		raise ValueError("unsupported_category")
	return canonical_components(components)


def content_hash(
	name: str, language: str, category: str, components: Any, media_sha256: str | None = None
) -> str:
	canonical = validate_definition(name, language, category, components)
	serialized = json.dumps(
		{
			"name": name,
			"language": language,
			"category": category,
			"components": canonical,
			"media_sha256": media_sha256,
		},
		ensure_ascii=False,
		sort_keys=True,
		separators=(",", ":"),
		allow_nan=False,
	)
	return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def render_preview(components: Any, sample_values: Any = None) -> dict[str, Any]:
	canonical = canonical_components(components)
	values = sample_values if sample_values is not None else []
	if (
		not isinstance(values, list)
		or len(values) > MAX_VARIABLES
		or any(not isinstance(item, str) or len(item) > 256 for item in values)
	):
		raise ValueError("invalid_sample_values")
	body = next(part["text"] for part in canonical if part["type"] == "BODY")
	body = PLACEHOLDER.sub(
		lambda match: values[int(match.group(1)) - 1]
		if len(values) >= int(match.group(1))
		else match.group(0),
		body,
	)
	return {"body": body, "components": canonical}


def _keys(value: Mapping[str, Any], allowed: set[str]) -> bool:
	return set(value).issubset(allowed)
