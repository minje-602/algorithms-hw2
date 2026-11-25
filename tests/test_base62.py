import unittest

from src.base62 import decode, encode


class Base62Tests(unittest.TestCase):
    def test_encode_zero(self):
        self.assertEqual(encode(0), "0")

    def test_encode_alphabet_boundaries(self):
        self.assertEqual(encode(9), "9")
        self.assertEqual(encode(10), "a")
        self.assertEqual(encode(35), "z")
        self.assertEqual(encode(36), "A")
        self.assertEqual(encode(61), "Z")
        self.assertEqual(encode(62), "10")

    def test_decode_alphabet_boundaries(self):
        self.assertEqual(decode("0"), 0)
        self.assertEqual(decode("9"), 9)
        self.assertEqual(decode("a"), 10)
        self.assertEqual(decode("z"), 35)
        self.assertEqual(decode("A"), 36)
        self.assertEqual(decode("Z"), 61)
        self.assertEqual(decode("10"), 62)
        self.assertEqual(decode("01"), 1)
        self.assertEqual(decode("001"), 1)

    def test_round_trip_large_values(self):
        for value in (0, 1, 61, 62, 3844, 2**128):
            with self.subTest(value=value):
                self.assertEqual(decode(encode(value)), value)

    def test_encode_rejects_invalid_values(self):
        with self.assertRaises(ValueError):
            encode(-1)
        with self.assertRaises(TypeError):
            encode(1.5)

    def test_decode_rejects_invalid_strings(self):
        with self.assertRaises(ValueError):
            decode("")
        with self.assertRaises(ValueError):
            decode("ab!")
        with self.assertRaises(TypeError):
            decode(123)


if __name__ == "__main__":
    unittest.main()
