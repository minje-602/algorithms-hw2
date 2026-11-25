import unittest

from src.shortener import Shortener


class ShortenerTests(unittest.TestCase):
    def test_sequential_codes_and_duplicate_url(self):
        shortener = Shortener()

        self.assertEqual(shortener.shorten("http://a.com"), "1")
        self.assertEqual(shortener.shorten("http://a.com"), "1")
        self.assertEqual(shortener.shorten("http://b.com"), "2")

    def test_distinct_url_strings_get_distinct_codes(self):
        shortener = Shortener()

        self.assertEqual(shortener.shorten("http://a.com"), "1")
        self.assertEqual(shortener.shorten("http://a.com/"), "2")

    def test_base62_code_boundaries(self):
        shortener = Shortener()
        codes = []

        for index in range(1, 63):
            codes.append(shortener.shorten(f"http://example.com/{index}"))

        self.assertEqual(codes[60], "Z")
        self.assertEqual(codes[61], "10")

    def test_expand_accepts_leading_zeroes(self):
        shortener = Shortener()
        url = "http://a.com"
        shortener.shorten(url)

        for code in ("1", "01", "001"):
            with self.subTest(code=code):
                self.assertEqual(shortener.expand(code), url)

    def test_expand_returns_none_for_unknown_or_invalid_codes(self):
        shortener = Shortener()
        shortener.shorten("http://a.com")

        for code in ("0", "zzz", "", "ab!"):
            with self.subTest(code=code):
                self.assertIsNone(shortener.expand(code))

    def test_accepts_and_preserves_url_boundaries(self):
        shortener = Shortener()
        urls = (
            "http://a",
            f"http://a.com/{'x' * 10_000}",
            "http://a.com/한글",
        )

        for url in urls:
            with self.subTest(url=url[:40]):
                code = shortener.shorten(url)
                self.assertEqual(shortener.expand(code), url)

    def test_rejects_invalid_urls(self):
        shortener = Shortener()
        invalid_urls = (
            "ftp://a.com",
            "a.com",
            "http://",
            "http://a.com/with space",
            "http://a.com/with\nnewline",
        )

        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    shortener.shorten(url)


if __name__ == "__main__":
    unittest.main()
