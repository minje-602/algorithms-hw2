"""HTTP server for the in-memory URL shortener."""

import argparse
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import sys
from urllib.parse import parse_qsl, quote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.shortener import Shortener


def _escape(value: str, *, quote_attribute: bool = False) -> str:
    return html.escape(value, quote=quote_attribute)


def _page(content: str, title: str = "URL 단축기") -> str:
    return (
        "<!doctype html>"
        '<html lang="ko"><head><meta charset="utf-8">'
        f"<title>{_escape(title)}</title></head><body>"
        f"<h1>{_escape(title)}</h1>{content}</body></html>"
    )


def _url_form(url: str = "", error: str | None = None) -> str:
    error_html = ""
    if error is not None:
        error_html = f'<p role="alert">오류: {_escape(error)}</p>'
    escaped_url = _escape(url, quote_attribute=True)
    return (
        f"{error_html}<form action='/shorten' method='post'>"
        f'<label for="url">URL</label> '
        f'<input id="url" name="url" type="url" value="{escaped_url}" required> '
        "<button type='submit'>줄이기</button></form>"
    )


class ShorteningHTTPServer(HTTPServer):
    def __init__(self, address: tuple[str, int]) -> None:
        self.shortener = Shortener()
        super().__init__(address, ShorteningRequestHandler)


class ShorteningRequestHandler(BaseHTTPRequestHandler):
    server: ShorteningHTTPServer

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/":
            content = _url_form() + '<p><a href="/table">해시 테이블 보기</a></p>'
            self._send_html(200, _page(content))
            return

        if path == "/table":
            self._send_html(200, self._table_page())
            return

        if path == "/shorten":
            self._send_html(404, _page("<p>페이지를 찾을 수 없습니다.</p>", "404"))
            return

        if not path.startswith("/") or "/" in path[1:]:
            self._send_html(404, _page("<p>페이지를 찾을 수 없습니다.</p>", "404"))
            return

        code = path[1:]
        url = self.server.shortener.expand(code)
        if url is None:
            self._send_html(404, _page("<p>단축 URL을 찾을 수 없습니다.</p>", "404"))
            return

        location = quote(url, safe=":/?#[]@!$&'()*+,;=%")
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/shorten":
            self._send_html(404, _page("<p>페이지를 찾을 수 없습니다.</p>", "404"))
            return

        url = ""
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length < 0:
                raise ValueError("요청 본문 길이가 올바르지 않습니다.")
            body = self.rfile.read(content_length).decode("utf-8")
            form_values = parse_qsl(body, keep_blank_values=True)
            url = next(
                (value for name, value in form_values if name == "url"),
                None,
            )
            if url is None or not url:
                raise ValueError("URL을 입력해 주세요.")
            code = self.server.shortener.shorten(url)
            short_link = self._short_link(code)
        except (UnicodeDecodeError, ValueError) as error:
            self._send_html(400, _page(_url_form(url or "", str(error))))
            return

        escaped_link = _escape(short_link, quote_attribute=True)
        content = (
            '<p>짧은 링크:</p>'
            f'<p><a href="{escaped_link}">{_escape(short_link)}</a></p>'
            + _url_form()
        )
        self._send_html(200, _page(content, "단축 결과"))

    def _short_link(self, code: str) -> str:
        host = self.headers.get("X-Forwarded-Host")
        if host is None:
            host = self.headers.get("Host")
        if not host:
            host = f"localhost:{self.server.server_port}"

        scheme = self.headers.get("X-Forwarded-Proto")
        if scheme is None:
            scheme = "http"
        return f"{scheme}://{host}/{code}"

    def _table_page(self) -> str:
        table = self.server.shortener._url_to_code
        bucket_count = len(table._buckets)
        host = self.headers.get("X-Forwarded-Host")
        if host is None:
            host = self.headers.get("Host")
        if not host:
            host = f"localhost:{self.server.server_port}"
        scheme = self.headers.get("X-Forwarded-Proto")
        if scheme is None:
            scheme = "http"
        sections = []

        for bucket_index, head in enumerate(table._buckets):
            nodes = []
            node = head
            while node is not None:
                code = node.value
                short_link = f"{scheme}://{host}/{code}"
                node_html = (
                    '<article><p>URL 키: '
                    f"{_escape(node.key)}</p><p>짧은 코드: "
                    f"{_escape(code)}</p><p>짧은 링크: "
                    f'<a href="{_escape(short_link, quote_attribute=True)}">'
                    f"{_escape(short_link)}</a></p>"
                    f"{self._hash_calculation(node.key, bucket_count)}"
                    "</article>"
                )
                nodes.append(node_html)
                node = node.next

            chain = " → ".join(nodes) if nodes else "<p>비어 있음</p>"
            sections.append(
                f"<section><h2>버킷 {bucket_index}</h2>{chain}</section>"
            )

        content = "".join(sections)
        return _page(content, "URL → 코드 해시 테이블")

    @staticmethod
    def _hash_calculation(key: str, bucket_count: int) -> str:
        steps = []
        value = 0
        for character in key:
            character_code = ord(character)
            remainder = (31 * value + character_code) % bucket_count
            steps.append(
                "<li>"
                f"h = (31 * {value} + ord('{_escape(character)}')) % "
                f"{bucket_count} = ("
                f"{31 * value} + {character_code}) % {bucket_count} "
                f"= {remainder}</li>"
            )
            value = remainder
        return (
            "<details><summary>호너 해시 계산 과정</summary>"
            f"<ol>{''.join(steps)}</ol></details>"
        )

    def _send_html(self, status: int, document: str) -> None:
        body = document.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the URL shortener web server.")
    parser.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args()
    if not 0 <= arguments.port <= 65535:
        parser.error("--port must be between 0 and 65535")

    with ShorteningHTTPServer(("", arguments.port)) as server:
        print(
            f"URL shortener listening on port {server.server_port}",
            flush=True,
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
