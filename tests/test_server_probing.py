import http.client
from html.parser import HTMLParser
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
SERVER_SCRIPT = ROOT / "src" / "server.py"


class _ProbingScreenParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sections = []
        self._section = None
        self._article = None
        self._details = None
        self._in_heading = False

    def handle_starttag(self, tag, attrs):
        if tag == "section":
            self._section = {
                "heading": [],
                "articles": [],
                "text": [],
            }
            self.sections.append(self._section)
        elif tag == "h2" and self._section is not None:
            self._in_heading = True
        elif tag == "article" and self._section is not None:
            self._article = {"text": [], "details": []}
            self._section["articles"].append(self._article)
        elif tag == "details" and self._article is not None:
            self._details = []

    def handle_endtag(self, tag):
        if tag == "details":
            if self._article is not None and self._details is not None:
                self._article["details"].extend(self._details)
            self._details = None
        elif tag == "article":
            self._article = None
        elif tag == "h2":
            self._in_heading = False
        elif tag == "section":
            self._section = None

    def handle_data(self, data):
        if self._section is None:
            return
        self._section["text"].append(data)
        if self._in_heading:
            self._section["heading"].append(data)
        if self._article is not None:
            self._article["text"].append(data)
        if self._details is not None:
            self._details.append(data)


def _bucket_index(key, bucket_count=8):
    value = 0
    for character in key:
        value = (31 * value + ord(character)) % bucket_count
    return value


def _horner_steps(key, bucket_count=8):
    value = 0
    steps = []
    for character in key:
        character_code = ord(character)
        remainder = (31 * value + character_code) % bucket_count
        steps.append(
            f"h = (31 * {value} + ord('{character}')) % {bucket_count} "
            f"= ({31 * value} + {character_code}) % {bucket_count} "
            f"= {remainder}"
        )
        value = remainder
    return steps


class ProbingServerHTTPTests(unittest.TestCase):
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
                "--table",
                "probing",
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
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            if self.process.stderr is not None:
                self.process.stderr.close()
            self.process = None

    def _request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.port, timeout=5
        )
        try:
            request_headers = {"Host": f"localhost:{self.port}"}
            if headers:
                request_headers.update(headers)
            if body is not None:
                request_headers["Content-Type"] = (
                    "application/x-www-form-urlencoded"
                )
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            return response.status, response.read().decode("utf-8")
        finally:
            connection.close()

    def _post_url(self, url, headers=None):
        return self._request(
            "POST",
            "/shorten",
            body=urlencode({"url": url}),
            headers=headers,
        )

    def _get_sections(self, expected_count=8, headers=None):
        status, body = self._request("GET", "/table", headers=headers)
        self.assertEqual(status, 200)

        parser = _ProbingScreenParser()
        parser.feed(body)
        self.assertEqual(len(parser.sections), expected_count)
        for index, section in enumerate(parser.sections):
            with self.subTest(slot=index):
                self.assertEqual(
                    "".join(section["heading"]),
                    f"칸 {index}",
                )
                self.assertLessEqual(len(section["articles"]), 1)
        return body, parser.sections

    def _assert_slot_contents(self, sections, expected):
        for slot, section in enumerate(sections):
            with self.subTest(slot=slot):
                if slot in expected:
                    self.assertEqual(len(section["articles"]), 1)
                    article = section["articles"][0]
                    self.assertIn(expected[slot], "".join(article["text"]))
                else:
                    self.assertEqual(section["articles"], [])
                    self.assertIn("비어 있음", "".join(section["text"]))

    def _assert_article_fields(
        self,
        article,
        url,
        code,
        start,
        probe_count,
        path,
        bucket_count=8,
    ):
        text = "".join(article["text"])
        self.assertIn(f"URL 키: {url}", text)
        self.assertIn(f"짧은 코드: {code}", text)
        self.assertIn(
            f"짧은 링크: http://localhost:{self.port}/{code}",
            text,
        )
        self.assertIn(f"시작 칸: {start}", text)
        self.assertIn(f"들여다본 칸 수: {probe_count}", text)
        self.assertIn(f"지나온 칸: {path}", text)
        details = " ".join(article["details"])
        self.assertTrue(details)
        for step in _horner_steps(url, bucket_count=bucket_count):
            self.assertIn(step, details)

    def test_empty_probing_table_shows_eight_ordered_empty_slots(self):
        _, sections = self._get_sections()

        for section in sections:
            self.assertEqual(section["articles"], [])
            self.assertIn("비어 있음", "".join(section["text"]))

    def test_colliding_urls_use_next_slot_and_show_probe_count(self):
        first_url = "http://a.com/probe-5"
        second_url = "http://a.com/probe-12"
        third_url = "http://a.com/probe-23"
        self.assertEqual(_bucket_index(first_url), 3)
        self.assertEqual(_bucket_index(second_url), 3)
        self.assertEqual(_bucket_index(third_url), 3)

        self.assertEqual(self._post_url(first_url)[0], 200)
        self.assertEqual(self._post_url(second_url)[0], 200)
        self.assertEqual(self._post_url(third_url)[0], 200)
        _, sections = self._get_sections()

        self._assert_slot_contents(
            sections,
            {3: first_url, 4: second_url, 5: third_url},
        )
        self._assert_article_fields(
            sections[3]["articles"][0],
            first_url,
            "1",
            3,
            1,
            "3",
        )
        self._assert_article_fields(
            sections[4]["articles"][0],
            second_url,
            "2",
            3,
            2,
            "3 → 4",
        )
        self._assert_article_fields(
            sections[5]["articles"][0],
            third_url,
            "3",
            3,
            3,
            "3 → 4 → 5",
        )

    def test_collision_at_last_slot_wraps_to_zero(self):
        first_url = "http://a.com/probe-1"
        second_url = "http://a.com/probe-9"
        self.assertEqual(_bucket_index(first_url), 7)
        self.assertEqual(_bucket_index(second_url), 7)

        self.assertEqual(self._post_url(first_url)[0], 200)
        self.assertEqual(self._post_url(second_url)[0], 200)
        _, sections = self._get_sections()

        self._assert_slot_contents(
            sections,
            {7: first_url, 0: second_url},
        )
        self._assert_article_fields(
            sections[7]["articles"][0],
            first_url,
            "1",
            7,
            1,
            "7",
        )
        self._assert_article_fields(
            sections[0]["articles"][0],
            second_url,
            "2",
            7,
            2,
            "7 → 0",
        )

    def test_seven_distinct_hash_starts_are_shown_after_resize_to_sixteen(self):
        urls_and_starts = (
            ("http://a.com/probe-17", 0),
            ("http://a.com/probe-18", 1),
            ("http://a.com/probe-19", 2),
            ("http://a.com/probe-70", 3),
            ("http://a.com/probe-2", 8),
            ("http://a.com/probe-3", 9),
            ("http://a.com/probe-9", 15),
        )
        start_slots = [
            _bucket_index(url, bucket_count=16)
            for url, _ in urls_and_starts
        ]
        self.assertEqual(start_slots, [start for _, start in urls_and_starts])
        self.assertEqual(len(set(start_slots)), 7)
        self.assertTrue(any(start >= 8 for start in start_slots))

        for url, _ in urls_and_starts:
            self.assertEqual(self._post_url(url)[0], 200)

        _, sections = self._get_sections(expected_count=16)
        self._assert_slot_contents(
            sections,
            {start: url for url, start in urls_and_starts},
        )
        for index, (url, start) in enumerate(urls_and_starts, start=1):
            self._assert_article_fields(
                sections[start]["articles"][0],
                url,
                str(index),
                start,
                1,
                str(start),
                bucket_count=16,
            )

    def test_special_characters_in_url_are_html_escaped(self):
        url = "http://a.com/<script>alert(1)</script>&x=1"
        self.assertEqual(self._post_url(url)[0], 200)

        status, body = self._request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn(
            "&lt;script&gt;alert(1)&lt;/script&gt;&amp;x=1",
            body,
        )
        self.assertNotIn("<script>alert(1)</script>", body)

    def test_table_short_links_use_forwarded_headers_and_escape_host(self):
        self.assertEqual(self._post_url("http://a.com")[0], 200)

        status, body = self._request(
            "GET",
            "/table",
            headers={
                "X-Forwarded-Host": "example.test",
                "X-Forwarded-Proto": "https",
            },
        )
        self.assertEqual(status, 200)
        self.assertIn("https://example.test/1", body)

        status, body = self._request(
            "GET",
            "/table",
            headers={
                "X-Forwarded-Host": "example.test<script>alert(1)</script>",
                "X-Forwarded-Proto": "https",
            },
        )
        self.assertEqual(status, 200)
        self.assertIn(
            "https://example.test&lt;script&gt;alert(1)&lt;/script&gt;/1",
            body,
        )
        self.assertNotIn("<script>alert(1)</script>", body)


class ProbingServerArgumentTests(unittest.TestCase):
    def test_unknown_table_mode_exits_with_an_error(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SERVER_SCRIPT),
                "--port",
                "0",
                "--table",
                "invalid",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )

        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
