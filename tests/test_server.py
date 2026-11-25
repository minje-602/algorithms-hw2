import http.client
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
SERVER_SCRIPT = ROOT / "src" / "server.py"


class ServerHTTPTests(unittest.TestCase):
    def setUp(self):
        self.process = None
        self.port = None
        self._start_server()

    def tearDown(self):
        self._stop_server()

    def _find_empty_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            return listener.getsockname()[1]

    def _start_server(self):
        self.port = self._find_empty_port()
        self.process = subprocess.Popen(
            [
                sys.executable,
                str(SERVER_SCRIPT),
                "--port",
                str(self.port),
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                error = self.process.stderr.read()
                self.process.stderr.close()
                raise RuntimeError(
                    f"server exited before accepting requests: {error.strip()}"
                )
            try:
                with socket.create_connection(
                    ("127.0.0.1", self.port), timeout=0.1
                ):
                    return
            except OSError:
                time.sleep(0.05)

        self._stop_server()
        self.fail("server did not start listening within 5 seconds")

    def _stop_server(self):
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
            self.process.stderr.close()
            self.process = None

    def _request(self, method, path, body=None, headers=None):
        request_headers = {"Host": f"localhost:{self.port}"}
        if headers:
            request_headers.update(headers)
        if body is not None:
            request_headers.setdefault(
                "Content-Type", "application/x-www-form-urlencoded"
            )

        connection = http.client.HTTPConnection(
            "127.0.0.1", self.port, timeout=5
        )
        try:
            connection.request(
                method, path, body=body, headers=request_headers
            )
            response = connection.getresponse()
            return (
                response.status,
                dict(response.getheaders()),
                response.read().decode("utf-8"),
            )
        finally:
            connection.close()

    def _post_url(self, url, headers=None):
        return self._request(
            "POST",
            "/shorten",
            body=urlencode({"url": url}),
            headers=headers,
        )

    def test_home_page_has_url_form_and_shorten_button(self):
        status, _, body = self._request("GET", "/")

        self.assertEqual(status, 200)
        self.assertIn('name="url"', body)
        self.assertIn('action="/shorten"', body)
        self.assertIn('method="post"', body.lower())
        self.assertIn("줄이기", body)
        self.assertRegex(body.lower(), r"<button|type=[\"']submit")

    def test_post_shortens_url_and_reuses_link_for_duplicate(self):
        url = "http://a.com"

        first_status, _, first_body = self._post_url(url)
        second_status, _, second_body = self._post_url(url)

        self.assertEqual(first_status, 200)
        self.assertEqual(second_status, 200)
        self.assertIn(f"http://localhost:{self.port}/1", first_body)
        self.assertEqual(first_body, second_body)

    def test_post_without_url_returns_bad_request_and_error_form(self):
        status, _, body = self._request(
            "POST", "/shorten", body="", headers={}
        )

        self.assertEqual(status, 400)
        self.assertIn('name="url"', body)
        self.assertRegex(body.lower(), r"error|오류|url")

    def test_post_invalid_url_returns_bad_request_and_error(self):
        status, _, body = self._post_url("ftp://a.com")

        self.assertEqual(status, 400)
        self.assertRegex(body.lower(), r"error|오류|invalid|url")

    def test_registered_code_and_leading_zero_code_redirect(self):
        url = "http://a.com"
        self._post_url(url)

        for code in ("1", "01"):
            with self.subTest(code=code):
                status, headers, _ = self._request("GET", f"/{code}")
                self.assertEqual(status, 302)
                self.assertEqual(headers.get("Location"), url)

    def test_unknown_code_returns_not_found(self):
        status, _, _ = self._request("GET", "/zzz")

        self.assertEqual(status, 404)

    def test_table_shows_url_code_link_chain_and_hash_calculation(self):
        url = "http://a.com"
        self._post_url(url)

        status, _, body = self._request("GET", "/table")
        lowered = body.lower()

        self.assertEqual(status, 200)
        self.assertIn(url, body)
        self.assertIn("1", body)
        self.assertIn(f"http://localhost:{self.port}/1", body)
        self.assertTrue(any(arrow in body for arrow in ("→", "&rarr;", "&#8594;")))
        self.assertRegex(lowered, r"horner|호너|hash")
        self.assertIn("<details", lowered)

    def test_forwarded_host_and_proto_build_short_link(self):
        status, _, body = self._post_url(
            "http://a.com",
            headers={
                "X-Forwarded-Host": "example.test",
                "X-Forwarded-Proto": "https",
            },
        )

        self.assertEqual(status, 200)
        self.assertIn("https://example.test/1", body)

    def test_forwarded_host_without_proto_defaults_to_http(self):
        status, _, body = self._post_url(
            "http://a.com",
            headers={"X-Forwarded-Host": "example.test"},
        )

        self.assertEqual(status, 200)
        self.assertIn("http://example.test/1", body)

    def test_forwarded_proto_without_host_uses_host_header(self):
        status, _, body = self._post_url(
            "http://a.com",
            headers={
                "X-Forwarded-Proto": "https",
                "Host": "localhost:8000",
            },
        )

        self.assertEqual(status, 200)
        self.assertIn("https://localhost:8000/1", body)

    def test_missing_forwarded_headers_use_http_and_host_header(self):
        status, _, body = self._post_url(
            "http://a.com", headers={"Host": "localhost:8000"}
        )

        self.assertEqual(status, 200)
        self.assertIn("http://localhost:8000/1", body)

    def test_non_ascii_redirect_is_percent_encoded_and_table_keeps_url(self):
        url = "http://a.com/한글"
        self._post_url(url)

        status, headers, _ = self._request("GET", "/1")
        self.assertEqual(status, 302)
        self.assertEqual(
            headers.get("Location"),
            "http://a.com/%ED%95%9C%EA%B8%80",
        )

        table_status, _, table_body = self._request("GET", "/table")
        self.assertEqual(table_status, 200)
        self.assertIn(url, table_body)

    def test_table_escapes_script_in_url(self):
        url = "http://a.com/<script>alert(1)</script>"
        self._post_url(url)

        status, _, body = self._request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", body)
        self.assertNotIn("<script>alert(1)</script>", body)

    def test_fixed_shorten_path_is_not_treated_as_a_code(self):
        self._post_url("http://a.com")

        status, _, _ = self._request("GET", "/shorten")

        self.assertNotEqual(status, 302)

    def test_restart_clears_saved_urls_and_resets_next_code(self):
        self._post_url("http://a.com")
        self._stop_server()
        self._start_server()

        status, _, _ = self._request("GET", "/1")
        self.assertEqual(status, 404)

        new_status, _, new_body = self._post_url("http://b.com")
        self.assertEqual(new_status, 200)
        self.assertIn(f"http://localhost:{self.port}/1", new_body)


if __name__ == "__main__":
    unittest.main()
