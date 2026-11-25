"""In-memory URL shortening backed by custom hash tables."""

import unicodedata
from urllib.parse import urlsplit

from src.base62 import encode
from src.hash_table import HashTable

_BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


class Shortener:
    def __init__(self) -> None:
        self._url_to_code = HashTable()
        self._code_to_url = HashTable()
        self._next_id = 1

    def shorten(self, url: str) -> str:
        self._validate_url(url)

        existing_code = self._url_to_code.get(url)
        if existing_code is not None:
            return existing_code

        code = encode(self._next_id)
        self._next_id += 1
        self._url_to_code.put(url, code)
        self._code_to_url.put(code, url)
        return code

    def expand(self, code: str) -> str | None:
        if not isinstance(code, str):
            return None
        if not code or any(character not in _BASE62_ALPHABET for character in code):
            return None
        normalized_code = code.lstrip("0") or "0"
        return self._code_to_url.get(normalized_code)

    @staticmethod
    def _validate_url(url: str) -> None:
        if not isinstance(url, str):
            raise ValueError("url must be a string")
        if any(
            character.isspace() or unicodedata.category(character) == "Cc"
            for character in url
        ):
            raise ValueError("url must not contain whitespace or control characters")

        try:
            parsed = urlsplit(url)
            hostname = parsed.hostname
            parsed.port
        except ValueError as error:
            raise ValueError(f"invalid URL: {error}") from error

        if parsed.scheme not in ("http", "https") or not hostname:
            raise ValueError("url must have an http or https scheme and a host")
