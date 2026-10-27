from collections import deque
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta

from tag_marketing.application.ports import TransportResponse


class FakeClock:
	def __init__(self, instant: datetime) -> None:
		if instant.tzinfo is None or instant.utcoffset() is None:
			raise ValueError("Fake time must be timezone-aware")
		self._instant = instant.astimezone(UTC)

	def now(self) -> datetime:
		return self._instant

	def advance(self, duration: timedelta) -> None:
		if duration < timedelta():
			raise ValueError("Clock cannot move backwards")
		self._instant += duration


class FakeProvider:
	"""Scripted byte transport, not a substitute for Meta contract qualification."""

	def __init__(self, outcomes: Iterable[TransportResponse | Exception]) -> None:
		self._outcomes = deque(outcomes)
		self.calls: list[tuple[str, str, bytes, dict[str, str]]] = []

	def request(self, method: str, url: str, *, body: bytes, headers: Mapping[str, str]) -> TransportResponse:
		self.calls.append((method, url, body, dict(headers)))
		if not self._outcomes:
			raise AssertionError("Unexpected provider request: no scripted outcome")
		outcome = self._outcomes.popleft()
		if isinstance(outcome, Exception):
			raise outcome
		return outcome

	def assert_consumed(self) -> None:
		if self._outcomes:
			raise AssertionError("Scripted provider outcomes were not consumed")
