"""Bounded HTTPS transport for the Meta adapter; redirects never forward tokens."""

from collections.abc import Mapping
from time import monotonic

import requests  # type: ignore[import-untyped]

from tag_marketing.application.ports import TransportResponse


class RequestsProviderTransport:
	"""Perform one bounded request without retries or automatic redirects."""

	def request(
		self,
		method: str,
		url: str,
		*,
		body: bytes,
		headers: Mapping[str, str],
		timeout_seconds: float = 15,
		max_response_bytes: int = 8 * 1024 * 1024,
	) -> TransportResponse:
		if not 1 <= timeout_seconds <= 30 or not 1 <= max_response_bytes <= 16 * 1024 * 1024:
			raise ValueError("Provider request bounds are invalid")
		deadline = monotonic() + timeout_seconds
		with requests.request(
			method,
			url,
			data=body if body else None,
			headers=dict(headers),
			timeout=(min(timeout_seconds, 5), min(timeout_seconds, 5)),
			allow_redirects=False,
			stream=True,
		) as response:
			chunks: list[bytes] = []
			total = 0
			for chunk in response.iter_content(chunk_size=64 * 1024):
				if monotonic() >= deadline:
					raise requests.Timeout("Provider request exceeded its total deadline")
				if not chunk:
					continue
				total += len(chunk)
				if total > max_response_bytes:
					raise ValueError("Provider response exceeds configured limit")
				chunks.append(chunk)
			return TransportResponse(status=response.status_code, body=b"".join(chunks))
