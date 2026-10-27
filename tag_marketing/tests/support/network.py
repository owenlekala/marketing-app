"""Process-local fail-closed socket guard, used only by automated tests.

Not a production firewall: subprocesses/background workers require their own
guard. Integration tests run synchronously; worker tests must install this there.
"""

import socket
from contextlib import ExitStack
from types import TracebackType
from typing import Any
from unittest.mock import patch

LOCAL_INFRASTRUCTURE = (("mariadb", 3306), ("redis-cache", 6379), ("redis-queue", 6379))


class UnexpectedNetwork(AssertionError):
	pass


class NetworkGuard:
	def __init__(self, allowed: tuple[tuple[str, int], ...] = ()) -> None:
		self.allowed = set(allowed)
		self.attempts: list[str] = []
		self._stack = ExitStack()

	def __enter__(self) -> "NetworkGuard":
		resolve = socket.getaddrinfo
		for host, port in tuple(self.allowed):
			for item in resolve(host, port, type=socket.SOCK_STREAM):
				self.allowed.add((str(item[4][0]), port))
		connect, connect_ex, sendto = socket.socket.connect, socket.socket.connect_ex, socket.socket.sendto

		def check(address: Any) -> None:
			try:
				destination = (
					(str(address[0]), int(address[1]))
					if isinstance(address, tuple) and len(address) > 1
					else None
				)
			except (TypeError, ValueError):
				destination = None
			if destination not in self.allowed:
				# Do not include URLs, request bodies, credentials or arbitrary data.
				self.attempts.append("Unexpected network destination")
				raise UnexpectedNetwork("Automated test attempted an unapproved network destination")

		def guarded_resolve(host: Any, port: Any, *args: Any, **kwargs: Any) -> Any:
			check((host, port))
			return resolve(host, port, *args, **kwargs)

		def guarded_connect(sock: socket.socket, address: Any) -> Any:
			check(address)
			return connect(sock, address)

		def guarded_connect_ex(sock: socket.socket, address: Any) -> Any:
			check(address)
			return connect_ex(sock, address)

		def guarded_sendto(sock: socket.socket, data: Any, *args: Any) -> Any:
			check(args[-1])
			return sendto(sock, data, *args)

		for target, replacement in [
			("socket.getaddrinfo", guarded_resolve),
			("socket.socket.connect", guarded_connect),
			("socket.socket.connect_ex", guarded_connect_ex),
			("socket.socket.sendto", guarded_sendto),
		]:
			self._stack.enter_context(patch(target, replacement))
		return self

	def __exit__(
		self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
	) -> None:
		self._stack.close()

	def assert_clean(self) -> None:
		if self.attempts:
			raise UnexpectedNetwork("Unexpected network attempt occurred, even if its exception was caught")
