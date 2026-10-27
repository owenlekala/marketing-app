import io
import socket
import unittest
import urllib.request
from datetime import UTC, datetime, timedelta

from tag_marketing.application.ports import Clock, ProviderTransport, TransportResponse
from tag_marketing.tests.support.cases import OfflineTestCase
from tag_marketing.tests.support.fakes import FakeClock, FakeProvider
from tag_marketing.tests.support.network import NetworkGuard, UnexpectedNetwork


class TestDeterministicAdapters(OfflineTestCase):
	def test_clock_has_explicit_utc_boundaries(self) -> None:
		clock: Clock = FakeClock(datetime(2026, 1, 1, tzinfo=UTC))
		self.assertEqual(clock.now(), clock.now())
		assert isinstance(clock, FakeClock)
		clock.advance(timedelta(hours=24))
		self.assertEqual(clock.now(), datetime(2026, 1, 2, tzinfo=UTC))
		with self.assertRaises(ValueError):
			clock.advance(timedelta(seconds=-1))
		with self.assertRaises(ValueError):
			FakeClock(datetime(2026, 1, 1))

	def test_provider_scripts_responses_and_uncertain_outcomes(self) -> None:
		fake = FakeProvider([TransportResponse(429, b'{"synthetic":true}'), TimeoutError("synthetic")])
		provider: ProviderTransport = fake
		headers = {"Authorization": "synthetic-token"}
		self.assertEqual(
			provider.request("POST", "https://provider.invalid", body=b"{}", headers=headers).status, 429
		)
		headers.clear()
		self.assertEqual(fake.calls[0][3]["Authorization"], "synthetic-token")
		with self.assertRaises(TimeoutError):
			provider.request("POST", "https://provider.invalid", body=b"{}", headers={})
		fake.assert_consumed()
		with self.assertRaises(AssertionError):
			provider.request("POST", "https://provider.invalid", body=b"{}", headers={})
		with self.assertRaises(AssertionError):
			FakeProvider([TransportResponse(200, b"{}")]).assert_consumed()

	def test_http_dns_and_direct_ip_udp_are_blocked(self) -> None:
		with NetworkGuard() as guard:
			with self.assertRaises(UnexpectedNetwork):
				urllib.request.urlopen("https://graph.facebook.com/never-send", timeout=1)
			with socket.socket() as sock, self.assertRaises(UnexpectedNetwork):
				sock.connect_ex(("1.1.1.1", 443))
			with socket.socket(type=socket.SOCK_DGRAM) as sock, self.assertRaises(UnexpectedNetwork):
				sock.sendto(b"synthetic", ("1.1.1.1", 53))
			with socket.socket() as sock, self.assertRaises(UnexpectedNetwork):
				sock.connect(("1.1.1.1", 443))
			with socket.socket(socket.AF_INET6) as sock, self.assertRaises(UnexpectedNetwork):
				sock.connect(("2606:4700:4700::1111", 443, 0, 0))
			with self.assertRaises(UnexpectedNetwork):
				socket.getaddrinfo("provider.invalid", None)
			self.assertEqual(len(guard.attempts), 6)

	def test_caught_network_exception_still_fails_ordinary_test(self) -> None:
		class LeakingTest(OfflineTestCase):
			def runTest(self) -> None:
				try:
					socket.getaddrinfo("provider.invalid", 443)
				except UnexpectedNetwork:
					pass

		result = unittest.TextTestRunner(stream=io.StringIO()).run(LeakingTest())
		self.assertFalse(result.wasSuccessful())
		self.assertEqual(len(result.failures), 1)
