"""Base62 encoding and decoding."""

_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_BASE = len(_ALPHABET)


def encode(n: int) -> str:
    """Encode a non-negative integer as a base62 string."""
    if type(n) is not int:
        raise TypeError("n must be an integer")
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return _ALPHABET[0]

    digits = []
    while n:
        n, remainder = divmod(n, _BASE)
        digits.append(_ALPHABET[remainder])
    return "".join(reversed(digits))


def decode(s: str) -> int:
    """Decode a base62 string into a non-negative integer."""
    if not isinstance(s, str):
        raise TypeError("s must be a string")
    if not s:
        raise ValueError("s must not be empty")

    value = 0
    for character in s:
        try:
            digit = _ALPHABET.index(character)
        except ValueError:
            raise ValueError(f"invalid base62 character: {character!r}") from None
        value = value * _BASE + digit
    return value
