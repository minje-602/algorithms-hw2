"""A string-keyed hash table using linear probing."""


class _Entry:
    __slots__ = ("key", "value")

    def __init__(self, key: str, value: object) -> None:
        self.key = key
        self.value = value


class LinearProbingTable:
    def __init__(
        self, bucket_count: int = 8, max_load: float | None = 0.75
    ) -> None:
        if type(bucket_count) is not int or bucket_count <= 0:
            raise ValueError("bucket_count must be a positive integer")
        if max_load is not None and (
            isinstance(max_load, bool)
            or not isinstance(max_load, (int, float))
            or not 0 < max_load < 1
        ):
            raise ValueError("max_load must be between 0 and 1 or None")

        self._slots: list[_Entry | None] = [None] * bucket_count
        self._max_load = max_load
        self._size = 0

    @property
    def load_factor(self) -> float:
        return self._size / len(self._slots)

    def __len__(self) -> int:
        return self._size

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        index, _ = self._find_slot(key)
        return index is not None and self._slots[index] is not None

    @staticmethod
    def _bucket_index(key: str, bucket_count: int) -> int:
        value = 0
        for character in key:
            value = (31 * value + ord(character)) % bucket_count
        return value

    def _find_slot(self, key: str) -> tuple[int | None, int]:
        slot_count = len(self._slots)
        index = self._bucket_index(key, slot_count)
        for probes in range(1, slot_count + 1):
            entry = self._slots[index]
            if entry is None or entry.key == key:
                return index, probes
            index = (index + 1) % slot_count
        return None, slot_count

    def find(self, key: str) -> tuple[object | None, int]:
        index, probes = self._find_slot(key)
        if index is None:
            return None, probes
        entry = self._slots[index]
        if entry is None:
            return None, probes
        return entry.value, probes

    def get(self, key: str) -> object | None:
        value, _ = self.find(key)
        return value

    def put(self, key: str, value: object) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be a string")

        index, _ = self._find_slot(key)
        if index is None:
            raise OverflowError("hash table is full")

        entry = self._slots[index]
        if entry is not None:
            entry.value = value
            return

        self._slots[index] = _Entry(key, value)
        self._size += 1
        while self._max_load is not None and self.load_factor > self._max_load:
            self._resize()

    def delete(self, key: str) -> bool:
        if not isinstance(key, str):
            return False

        index, _ = self._find_slot(key)
        if index is None or self._slots[index] is None:
            return False

        self._slots[index] = None
        self._size -= 1

        entries: list[_Entry] = []
        slot_count = len(self._slots)
        next_index = (index + 1) % slot_count
        while self._slots[next_index] is not None:
            entry = self._slots[next_index]
            if entry is not None:
                entries.append(entry)
                self._slots[next_index] = None
                self._size -= 1
            next_index = (next_index + 1) % slot_count

        for entry in entries:
            self._insert_without_resize(entry)
        return True

    def _insert_without_resize(self, entry: _Entry) -> None:
        index, _ = self._find_slot(entry.key)
        if index is None:
            raise OverflowError("hash table is full")
        self._slots[index] = entry
        self._size += 1

    def _resize(self) -> None:
        old_slots = self._slots
        self._slots = [None] * (len(old_slots) * 2)
        self._size = 0
        for entry in old_slots:
            if entry is not None:
                self._insert_without_resize(entry)
