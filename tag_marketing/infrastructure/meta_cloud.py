"""Typed, version-pinned Meta WhatsApp Cloud API adapter.

This module is deliberately independent of Frappe documents and business policy.
It accepts credentials/configuration from an authorised application service and
returns redacted outcomes that the outbox can persist.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeGuard
from urllib.parse import urlparse

from tag_marketing.application.ports import ProviderTransport, TransportResponse

SUPPORTED_GRAPH_VERSIONS = frozenset({"v26.0"})
GRAPH_HOST = "graph.facebook.com"
MEDIA_HOSTS = frozenset({"lookaside.fbsbx.com"})
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_MEDIA_BYTES = 16 * 1024 * 1024
SUPPORTED_MEDIA_TYPES = frozenset(
	{
		"image/jpeg",
		"image/png",
		"video/mp4",
		"video/3gpp",
		"audio/aac",
		"audio/amr",
		"audio/mpeg",
		"audio/mp4",
		"audio/ogg",
		"application/pdf",
		"application/vnd.ms-powerpoint",
		"application/msword",
		"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
		"application/vnd.openxmlformats-officedocument.presentationml.presentation",
		"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
		"text/plain",
		"application/vnd.ms-excel",
	}
)
PROVIDER_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
CURSOR = re.compile(r"^[A-Za-z0-9_-]{1,2048}$")


class FailureKind(StrEnum):
	INVALID_CREDENTIAL = "Invalid Credential"
	UNSUPPORTED_VERSION = "Unsupported Version"
	WRONG_ACCOUNT = "Wrong Account"
	UNSUPPORTED_MEDIA = "Unsupported Media"
	RATE_LIMITED = "Rate Limited"
	REJECTED = "Rejected"
	UNAVAILABLE = "Unavailable"
	UNKNOWN_OUTCOME = "Unknown Outcome"
	INVALID_RESPONSE = "Invalid Response"


class ProviderFailure(Exception):
	"""Safe provider failure; raw bodies, tokens and URLs are never retained."""

	def __init__(self, kind: FailureKind, *, provider_code: int | None = None) -> None:
		self.kind = kind
		self.provider_code = provider_code if isinstance(provider_code, int) else None
		super().__init__(kind.value)


@dataclass(frozen=True)
class MetaCredentials:
	access_token: str
	app_secret: str


@dataclass(frozen=True)
class MetaConfig:
	api_version: str
	waba_id: str
	timeout_seconds: float = 15


@dataclass(frozen=True)
class ProviderNumber:
	provider_phone_id: str
	display_phone: str
	display_name: str
	quality_rating: str | None


@dataclass(frozen=True)
class ProviderPage[T]:
	items: tuple[T, ...]
	next_cursor: str | None


@dataclass(frozen=True)
class ProviderTemplate:
	provider_template_id: str
	name: str
	language: str
	category: str
	status: str
	components: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class MessageAcceptance:
	provider_message_id: str
	accepted: bool = True


@dataclass(frozen=True)
class TemplateSubmission:
	provider_template_id: str
	status: str


@dataclass(frozen=True)
class MediaAsset:
	mime_type: str
	sha256: str
	content: bytes


class MetaCloudAPI:
	"""Synchronous provider port. Call from background jobs, never CRM hooks."""

	def __init__(
		self,
		config: MetaConfig,
		credentials: MetaCredentials,
		transport: ProviderTransport,
	) -> None:
		if config.api_version not in SUPPORTED_GRAPH_VERSIONS:
			raise ProviderFailure(FailureKind.UNSUPPORTED_VERSION)
		if not PROVIDER_ID.fullmatch(config.waba_id):
			raise ProviderFailure(FailureKind.WRONG_ACCOUNT)
		if not credentials.access_token or not credentials.app_secret:
			raise ProviderFailure(FailureKind.INVALID_CREDENTIAL)
		if not 1 <= config.timeout_seconds <= 30:
			raise ValueError("Provider timeout must be between 1 and 30 seconds")
		self.config = config
		self.credentials = credentials
		self.transport = transport

	def validate_connection(self) -> Mapping[str, Any]:
		result = self._get(self._path(self.config.waba_id), params={"fields": "id,name"})
		if result.get("id") != self.config.waba_id:
			raise ProviderFailure(FailureKind.WRONG_ACCOUNT)
		return {"id": result["id"], "name": _safe_text(result.get("name"), 128)}

	def list_numbers(self, *, cursor: str | None = None, limit: int = 100) -> ProviderPage[ProviderNumber]:
		if not 1 <= limit <= 100 or (cursor is not None and not CURSOR.fullmatch(cursor)):
			raise ValueError("Invalid number page request")
		result = self._get(
			self._path(self.config.waba_id, "phone_numbers"),
			params=_page_params(
				{"fields": "id,display_phone_number,verified_name,quality_rating", "limit": str(limit)},
				cursor,
			),
		)
		data = result.get("data")
		if not isinstance(data, list):
			raise ProviderFailure(FailureKind.INVALID_RESPONSE)
		numbers = []
		for item in data:
			if not isinstance(item, dict) or not _valid_id(item.get("id")):
				raise ProviderFailure(FailureKind.INVALID_RESPONSE)
			numbers.append(
				ProviderNumber(
					provider_phone_id=item["id"],
					display_phone=_safe_text(item.get("display_phone_number"), 64),
					display_name=_safe_text(item.get("verified_name"), 128),
					quality_rating=_optional_text(item.get("quality_rating"), 32),
				)
			)
		return ProviderPage(items=tuple(numbers), next_cursor=_next_cursor(result))

	def list_templates(
		self, *, cursor: str | None = None, limit: int = 100
	) -> ProviderPage[ProviderTemplate]:
		if not 1 <= limit <= 500:
			raise ValueError("Template page limit must be between 1 and 500")
		if cursor is not None and not CURSOR.fullmatch(cursor):
			raise ValueError("Invalid template page cursor")
		result = self._get(
			self._path(self.config.waba_id, "message_templates"),
			params=_page_params(
				{"fields": "id,name,language,category,status,components", "limit": str(limit)}, cursor
			),
		)
		data = result.get("data")
		if not isinstance(data, list):
			raise ProviderFailure(FailureKind.INVALID_RESPONSE)
		templates = []
		for item in data:
			if not isinstance(item, dict) or not _valid_id(item.get("id")):
				raise ProviderFailure(FailureKind.INVALID_RESPONSE)
			components = item.get("components", [])
			name = _safe_text(item.get("name"), 512)
			language = _safe_text(item.get("language"), 64)
			category = _safe_text(item.get("category"), 32)
			status = _safe_text(item.get("status"), 32)
			if (
				not isinstance(components, list)
				or not all(isinstance(c, dict) for c in components)
				or not name
				or not language
				or not category
				or not status
			):
				raise ProviderFailure(FailureKind.INVALID_RESPONSE)
			templates.append(
				ProviderTemplate(
					provider_template_id=item["id"],
					name=name,
					language=language,
					category=category,
					status=status,
					components=tuple(components),
				)
			)
		return ProviderPage(items=tuple(templates), next_cursor=_next_cursor(result))

	def create_template(
		self,
		*,
		name: str,
		language: str,
		category: str,
		components: tuple[Mapping[str, Any], ...],
	) -> TemplateSubmission:
		if (
			not re.fullmatch(r"[a-z0-9_]{1,512}", name)
			or not re.fullmatch(r"[a-z]{2,3}(?:_[A-Z]{2})?", language)
			or category not in {"MARKETING", "UTILITY"}
			or not components
			or len(components) > 10
			or any(not isinstance(component, Mapping) for component in components)
		):
			raise ValueError("Invalid WhatsApp template definition")
		payload = {
			"name": name,
			"language": language,
			"category": category,
			"components": [dict(component) for component in components],
		}
		try:
			response = self._request(
				"POST",
				self._path(self.config.waba_id, "message_templates"),
				body=_json_bytes(payload),
			)
		except ProviderFailure as exc:
			if exc.kind in {FailureKind.RATE_LIMITED, FailureKind.REJECTED, FailureKind.INVALID_CREDENTIAL}:
				raise
			raise ProviderFailure(FailureKind.UNKNOWN_OUTCOME, provider_code=exc.provider_code) from None
		try:
			result = self._decode(response)
		except ProviderFailure:
			raise ProviderFailure(FailureKind.UNKNOWN_OUTCOME) from None
		if response.status == 429:
			raise ProviderFailure(FailureKind.RATE_LIMITED, provider_code=_error_code(result))
		if response.status >= 500:
			raise ProviderFailure(FailureKind.UNKNOWN_OUTCOME, provider_code=_error_code(result))
		if response.status < 200 or response.status >= 300:
			self._raise_response_error(response, result)
		provider_id = result.get("id")
		status = result.get("status")
		if not _valid_id(provider_id) or not isinstance(status, str):
			raise ProviderFailure(FailureKind.UNKNOWN_OUTCOME)
		return TemplateSubmission(provider_template_id=provider_id, status=_safe_text(status, 32))

	def submit_message(self, provider_phone_id: str, payload: Mapping[str, Any]) -> MessageAcceptance:
		self._require_id(provider_phone_id)
		if not isinstance(payload, Mapping) or payload.get("messaging_product") != "whatsapp":
			raise ValueError("Invalid WhatsApp message payload")
		body = _json_bytes(dict(payload))
		try:
			response = self._request("POST", self._path(provider_phone_id, "messages"), body=body)
		except ProviderFailure as exc:
			if exc.kind in {FailureKind.RATE_LIMITED, FailureKind.REJECTED, FailureKind.INVALID_CREDENTIAL}:
				raise
			raise ProviderFailure(FailureKind.UNKNOWN_OUTCOME, provider_code=exc.provider_code) from None
		try:
			result = self._decode(response)
		except ProviderFailure:
			raise ProviderFailure(FailureKind.UNKNOWN_OUTCOME) from None
		if response.status == 429:
			raise ProviderFailure(FailureKind.RATE_LIMITED, provider_code=_error_code(result))
		if response.status >= 500:
			raise ProviderFailure(FailureKind.UNKNOWN_OUTCOME, provider_code=_error_code(result))
		if response.status < 200 or response.status >= 300:
			self._raise_response_error(response, result)
		messages = result.get("messages")
		if not isinstance(messages, list) or not messages or not isinstance(messages[0], dict):
			raise ProviderFailure(FailureKind.UNKNOWN_OUTCOME)
		message_id = messages[0].get("id")
		if not _valid_id(message_id):
			raise ProviderFailure(FailureKind.UNKNOWN_OUTCOME)
		return MessageAcceptance(provider_message_id=message_id)

	def retrieve_media(self, media_id: str) -> MediaAsset:
		self._require_id(media_id)
		metadata = self._get(self._path(media_id), params={"fields": "url,mime_type,sha256,file_size"})
		url = metadata.get("url")
		mime_type = metadata.get("mime_type")
		digest = metadata.get("sha256")
		if (
			not isinstance(url, str)
			or not isinstance(mime_type, str)
			or mime_type.lower() not in SUPPORTED_MEDIA_TYPES
		):
			raise ProviderFailure(FailureKind.UNSUPPORTED_MEDIA)
		parsed = urlparse(url)
		if (
			parsed.scheme != "https"
			or parsed.hostname not in MEDIA_HOSTS
			or parsed.username
			or parsed.password
		):
			raise ProviderFailure(FailureKind.INVALID_RESPONSE)
		declared_size = metadata.get("file_size")
		if isinstance(declared_size, int) and (declared_size < 0 or declared_size > MAX_MEDIA_BYTES):
			raise ProviderFailure(FailureKind.UNSUPPORTED_MEDIA)
		response = self._request("GET", url, body=b"", max_bytes=MAX_MEDIA_BYTES)
		if not 200 <= response.status < 300 or len(response.body) > MAX_MEDIA_BYTES:
			raise ProviderFailure(
				FailureKind.UNAVAILABLE if response.status >= 500 else FailureKind.INVALID_RESPONSE
			)
		if not isinstance(digest, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
			raise ProviderFailure(FailureKind.INVALID_RESPONSE)
		import hashlib

		actual_digest = hashlib.sha256(response.body).hexdigest()
		if actual_digest.lower() != digest.lower():
			raise ProviderFailure(FailureKind.INVALID_RESPONSE)
		return MediaAsset(mime_type=mime_type.lower(), sha256=actual_digest, content=response.body)

	def _get(self, path: str, *, params: Mapping[str, str] | None = None) -> dict[str, Any]:
		if params:
			from urllib.parse import urlencode

			path = f"{path}?{urlencode(params)}"
		response = self._request("GET", path, body=b"")
		result = self._decode(response)
		if not 200 <= response.status < 300:
			self._raise_response_error(response, result)
		return result

	def _request(
		self, method: str, path: str, *, body: bytes, max_bytes: int = MAX_RESPONSE_BYTES
	) -> TransportResponse:
		url = (
			path
			if path.startswith("https://")
			else f"https://{GRAPH_HOST}/{self.config.api_version}/{path.lstrip('/')}"
		)
		parsed = urlparse(url)
		allowed_hosts = MEDIA_HOSTS if parsed.hostname in MEDIA_HOSTS else frozenset({GRAPH_HOST})
		if parsed.scheme != "https" or parsed.hostname not in allowed_hosts or parsed.port not in (None, 443):
			raise ProviderFailure(FailureKind.INVALID_RESPONSE)
		headers = {
			"Authorization": f"Bearer {self.credentials.access_token}",
			"Accept": "application/json",
			"Content-Type": "application/json",
		}
		try:
			response = self.transport.request(
				method,
				url,
				body=body,
				headers=headers,
				timeout_seconds=self.config.timeout_seconds,
				max_response_bytes=max_bytes,
			)
		except Exception:
			raise ProviderFailure(
				FailureKind.UNKNOWN_OUTCOME if method == "POST" else FailureKind.UNAVAILABLE
			) from None
		if len(response.body) > max_bytes:
			raise ProviderFailure(FailureKind.INVALID_RESPONSE)
		return response

	def _decode(self, response: TransportResponse) -> dict[str, Any]:
		try:
			value = json.loads(response.body)
		except (json.JSONDecodeError, UnicodeDecodeError):
			if response.status >= 500:
				return {}
			raise ProviderFailure(FailureKind.INVALID_RESPONSE) from None
		if not isinstance(value, dict):
			raise ProviderFailure(FailureKind.INVALID_RESPONSE)
		return value

	def _raise_response_error(self, response: TransportResponse, value: Mapping[str, Any]) -> None:
		code = _error_code(value)
		if code == 190:
			kind = FailureKind.INVALID_CREDENTIAL
		elif response.status == 429:
			kind = FailureKind.RATE_LIMITED
		elif response.status >= 500:
			kind = FailureKind.UNAVAILABLE
		else:
			kind = FailureKind.REJECTED
		raise ProviderFailure(kind, provider_code=code)

	def _path(self, *parts: str) -> str:
		for part in parts:
			self._require_id(part)
		return "/".join(parts)

	@staticmethod
	def _require_id(value: str) -> None:
		if not isinstance(value, str) or not PROVIDER_ID.fullmatch(value):
			raise ValueError("Invalid provider identifier")


def _valid_id(value: Any) -> TypeGuard[str]:
	return isinstance(value, str) and bool(PROVIDER_ID.fullmatch(value))


def _error_code(value: Mapping[str, Any]) -> int | None:
	error = value.get("error")
	code = error.get("code") if isinstance(error, dict) else None
	return code if isinstance(code, int) else None


def _page_params(params: Mapping[str, str], cursor: str | None) -> dict[str, str]:
	result = dict(params)
	if cursor is not None:
		result["after"] = cursor
	return result


def _next_cursor(value: Mapping[str, Any]) -> str | None:
	paging = value.get("paging")
	if not isinstance(paging, dict) or not isinstance(paging.get("next"), str):
		return None
	cursors = paging.get("cursors")
	after = cursors.get("after") if isinstance(cursors, dict) else None
	return after if isinstance(after, str) and CURSOR.fullmatch(after) else None


def _safe_text(value: Any, max_length: int) -> str:
	if not isinstance(value, str):
		return ""
	return " ".join(value.split())[:max_length]


def _optional_text(value: Any, max_length: int) -> str | None:
	text = _safe_text(value, max_length)
	return text or None


def _json_bytes(value: Mapping[str, Any]) -> bytes:
	try:
		return json.dumps(value, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
	except (TypeError, ValueError):
		raise ValueError("Invalid provider request payload") from None
