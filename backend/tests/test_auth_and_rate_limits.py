import asyncio
import base64
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("APP_BASIC_AUTH_USERNAME", "test-user")
os.environ.setdefault("APP_BASIC_AUTH_PASSWORD", "test-pass")

from app.main import app, _clear_rate_limit_buckets
from app.schemas import AddressAutocompleteResponse


def make_basic_auth_header(
    username: str = "test-user",
    password: str = "test-pass",
) -> tuple[bytes, bytes]:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return (b"authorization", f"Basic {token}".encode("ascii"))


async def asgi_request(
    *,
    method: str,
    path: str,
    query_string: bytes = b"",
    body: bytes = b"",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    response_status = 500
    response_headers: dict[str, str] = {}
    body_chunks: list[bytes] = []
    request_headers = headers[:] if headers else []

    if not any(name.lower() == b"host" for name, _ in request_headers):
        request_headers.append((b"host", b"testserver"))
    if body and not any(name.lower() == b"content-length" for name, _ in request_headers):
        request_headers.append((b"content-length", str(len(body)).encode("ascii")))

    body_sent = False

    async def receive() -> dict[str, object]:
        nonlocal body_sent
        if body_sent:
            return {"type": "http.disconnect"}
        body_sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        nonlocal response_status
        if message["type"] == "http.response.start":
            response_status = int(message["status"])
            response_headers.update(
                {
                    key.decode("latin1"): value.decode("latin1")
                    for key, value in message["headers"]
                }
            )
            return

        if message["type"] == "http.response.body":
            body_chunks.append(message.get("body", b""))

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": query_string,
        "headers": request_headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    return response_status, response_headers, b"".join(body_chunks)


class AuthAndRateLimitTest(unittest.TestCase):
    def setUp(self) -> None:
        _clear_rate_limit_buckets()

    def test_health_is_open_without_auth(self):
        status_code, _, body = asyncio.run(asgi_request(method="GET", path="/health"))

        self.assertEqual(status_code, 200)
        self.assertEqual(json.loads(body), {"status": "ok"})

    def test_protected_route_without_auth_returns_basic_auth_challenge(self):
        status_code, headers, _ = asyncio.run(
            asgi_request(
                method="GET",
                path="/",
                headers=[(b"host", b"example.com")],
            )
        )

        self.assertEqual(status_code, 401)
        self.assertEqual(headers["www-authenticate"], 'Basic realm="Invoice Creator"')

    def test_wrong_credentials_return_401(self):
        status_code, headers, _ = asyncio.run(
            asgi_request(
                method="GET",
                path="/",
                headers=[
                    (b"host", b"example.com"),
                    make_basic_auth_header(password="wrong-pass"),
                ],
            )
        )

        self.assertEqual(status_code, 401)
        self.assertEqual(headers["www-authenticate"], 'Basic realm="Invoice Creator"')

    def test_correct_credentials_allow_protected_api_request(self):
        with patch("app.main.autocomplete_addresses") as autocomplete_mock:
            autocomplete_mock.return_value = AddressAutocompleteResponse(
                query="Domkl",
                suggestions=[],
            )
            status_code, _, body = asyncio.run(
                asgi_request(
                    method="GET",
                    path="/api/address/autocomplete",
                    query_string=b"q=Domkl",
                    headers=[(b"host", b"example.com"), make_basic_auth_header()],
                )
            )

        self.assertEqual(status_code, 200)
        self.assertEqual(json.loads(body)["query"], "Domkl")

    def test_generate_rate_limit_blocks_third_request_within_a_minute(self):
        payload = json.dumps({"filename": "rows.csv", "rows": []}).encode("utf-8")
        headers = [
            (b"host", b"example.com"),
            make_basic_auth_header(),
            (b"content-type", b"application/json"),
        ]

        with patch("app.main._current_time", side_effect=[0.0, 1.0, 2.0]):
            responses = [
                asyncio.run(
                    asgi_request(
                        method="POST",
                        path="/api/invoices/generate",
                        body=payload,
                        headers=headers,
                    )
                )[0]
                for _ in range(3)
            ]

        self.assertEqual(responses, [200, 200, 429])

    def test_validate_and_address_limits_use_separate_buckets(self):
        validate_payload = json.dumps({"filename": "rows.csv", "rows": []}).encode("utf-8")
        validate_headers = [
            (b"host", b"example.com"),
            make_basic_auth_header(),
            (b"content-type", b"application/json"),
        ]

        with patch("app.main._current_time", side_effect=[0.0] * 8 + [1.0]):
            validate_statuses = [
                asyncio.run(
                    asgi_request(
                        method="POST",
                        path="/api/invoices/validate-rows",
                        body=validate_payload,
                        headers=validate_headers,
                    )
                )[0]
                for _ in range(8)
            ]

            with patch("app.main.autocomplete_addresses") as autocomplete_mock:
                autocomplete_mock.return_value = AddressAutocompleteResponse(
                    query="Domkl",
                    suggestions=[],
                )
                address_status = asyncio.run(
                    asgi_request(
                        method="GET",
                        path="/api/address/autocomplete",
                        query_string=b"q=Domkl",
                        headers=[(b"host", b"example.com"), make_basic_auth_header()],
                    )
                )[0]

        self.assertTrue(all(status == 200 for status in validate_statuses))
        self.assertEqual(address_status, 200)

    def test_repeated_failed_auth_attempts_are_rate_limited(self):
        with patch("app.main._current_time", side_effect=[float(index) for index in range(11)]):
            statuses = [
                asyncio.run(
                    asgi_request(
                        method="GET",
                        path="/",
                        headers=[(b"host", b"example.com")],
                    )
                )[0]
                for _ in range(11)
            ]

        self.assertEqual(statuses[:10], [401] * 10)
        self.assertEqual(statuses[10], 429)

    def test_rate_limit_resets_after_window_passes(self):
        payload = json.dumps({"filename": "rows.csv", "rows": []}).encode("utf-8")
        headers = [
            (b"host", b"example.com"),
            make_basic_auth_header(),
            (b"content-type", b"application/json"),
        ]

        with patch("app.main._current_time", side_effect=[0.0, 1.0, 61.0]):
            statuses = [
                asyncio.run(
                    asgi_request(
                        method="POST",
                        path="/api/invoices/generate",
                        body=payload,
                        headers=headers,
                    )
                )[0]
                for _ in range(3)
            ]

        self.assertEqual(statuses, [200, 200, 200])

    def test_localhost_requests_bypass_basic_auth_in_local_development(self):
        status_code, headers, body = asyncio.run(
            asgi_request(
                method="GET",
                path="/",
                headers=[(b"host", b"localhost:8000")],
            )
        )

        self.assertEqual(status_code, 200)
        self.assertNotIn("www-authenticate", headers)
        self.assertIn(b"<!doctype html>", body.lower())


if __name__ == "__main__":
    unittest.main()
