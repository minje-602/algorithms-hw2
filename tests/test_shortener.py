import unittest

from src.linear_probing import LinearProbingTable
from src.shortener import Shortener


class ShortenerTests(unittest.TestCase):
    def make_shortener(self):
        return Shortener()

    def test_sequential_codes_and_duplicate_url(self):
        shortener = self.make_shortener()

        self.assertEqual(shortener.shorten("http://a.com"), "1")
        self.assertEqual(shortener.shorten("http://a.com"), "1")
        self.assertEqual(shortener.shorten("http://b.com"), "2")

    def test_distinct_url_strings_get_distinct_codes(self):
        shortener = self.make_shortener()

        self.assertEqual(shortener.shorten("http://a.com"), "1")
        self.assertEqual(shortener.shorten("http://a.com/"), "2")

    def test_base62_code_boundaries(self):
        shortener = self.make_shortener()
        codes = []

        for index in range(1, 63):
            codes.append(shortener.shorten(f"http://example.com/{index}"))

        self.assertEqual(codes[60], "Z")
        self.assertEqual(codes[61], "10")

    def test_expand_accepts_leading_zeroes(self):
        shortener = self.make_shortener()
        url = "http://a.com"
        shortener.shorten(url)

        for code in ("1", "01", "001"):
            with self.subTest(code=code):
                self.assertEqual(shortener.expand(code), url)

    def test_expand_returns_none_for_unknown_or_invalid_codes(self):
        shortener = self.make_shortener()
        shortener.shorten("http://a.com")

        for code in ("0", "zzz", "", "ab!"):
            with self.subTest(code=code):
                self.assertIsNone(shortener.expand(code))

    def test_accepts_and_preserves_url_boundaries(self):
        shortener = self.make_shortener()
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
        shortener = self.make_shortener()
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

    def test_preserves_all_parts_of_https_url(self):
        shortener = self.make_shortener()
        url = "https://user@a.com:8443/path?q=1#part"

        self.assertEqual(shortener.expand(shortener.shorten(url)), url)

    def test_rejects_non_whitespace_control_characters(self):
        shortener = self.make_shortener()

        for code_point in (0, 127):
            with self.subTest(code_point=code_point):
                with self.assertRaises(ValueError):
                    shortener.shorten("http://a.com/" + chr(code_point))


class LinearProbingShortenerTests(ShortenerTests):
    def make_shortener(self):
        return Shortener(table_class=LinearProbingTable)


class ShortenerTableClassTests(unittest.TestCase):
    def test_table_class_creates_and_uses_two_tables(self):
        tables = []

        def make_table():
            table = LinearProbingTable()
            tables.append(table)
            return table

        shortener = Shortener(table_class=make_table)
        shortener.shorten("http://a.com")

        self.assertEqual(len(tables), 2)
        self.assertEqual(len(tables[0]), 1)
        self.assertEqual(len(tables[1]), 1)


if __name__ == "__main__":
    unittest.main()
