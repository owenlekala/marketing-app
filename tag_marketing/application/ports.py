"""Injectable time and byte transport, independent of Frappe and Meta payloads."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class Clock(Protocol):
	def now(self) -> datetime:
		"""Return an aware UTC instant."""
		...


@dataclass(frozen=True)
class TransportResponse:
	status: int
	body: bytes


class ProviderTransport(Protocol):
	def request(self, method: str, url: str, *, body: bytes, headers: Mapping[str, str]) -> TransportResponse:
		"""Perform one HTTP attempt; provider interpretation belongs to its adapter."""
		...
