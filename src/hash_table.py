"""A string-keyed hash table using Horner hashing and separate chaining."""


class _Node:
    __slots__ = ("key", "value", "next")

    def __init__(self, key: str, value: object) -> None:
        self.key = key
        self.value = value
        self.next: _Node | None = None


class HashTable:
    def __init__(
        self, bucket_count: int = 8, max_load: float | None = 0.75
    ) -> None:
        if type(bucket_count) is not int or bucket_count <= 0:
            raise ValueError("bucket_count must be a positive integer")
        if max_load is not None and (
            isinstance(max_load, bool)
            or not isinstance(max_load, (int, float))
            or max_load <= 0
        ):
            raise ValueError("max_load must be a positive number or None")

        self._buckets: list[_Node | None] = [None] * bucket_count
        self._max_load = max_load
        self._size = 0

    @property
    def load_factor(self) -> float:
        return self._size / len(self._buckets)

    def __len__(self) -> int:
        return self._size

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        node, _ = self._find_node(key)
        return node is not None

    @staticmethod
    def _bucket_index(key: str, bucket_count: int) -> int:
        value = 0
        for character in key:
            value = (31 * value + ord(character)) % bucket_count
        return value

    def _find_node(self, key: str) -> tuple[_Node | None, int]:
        bucket = self._buckets[self._bucket_index(key, len(self._buckets))]
        comparisons = 0
        while bucket is not None:
            comparisons += 1
            if bucket.key == key:
                return bucket, comparisons
            bucket = bucket.next
        return None, comparisons

    def find(self, key: str) -> tuple[object | None, int]:
        node, comparisons = self._find_node(key)
        if node is None:
            return None, comparisons
        return node.value, comparisons

    def get(self, key: str) -> object | None:
        node, _ = self._find_node(key)
        if node is None:
            return None
        return node.value

    def put(self, key: str, value: object) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be a string")

        node, _ = self._find_node(key)
        if node is not None:
            node.value = value
            return

        self._append_node(_Node(key, value), self._buckets)
        self._size += 1
        while self._max_load is not None and self.load_factor > self._max_load:
            self._resize()

    def delete(self, key: str) -> bool:
        if not isinstance(key, str):
            return False

        index = self._bucket_index(key, len(self._buckets))
        current = self._buckets[index]
        previous: _Node | None = None
        while current is not None:
            if current.key == key:
                if previous is None:
                    self._buckets[index] = current.next
                else:
                    previous.next = current.next
                self._size -= 1
                return True
            previous = current
            current = current.next
        return False

    def _append_node(self, node: _Node, buckets: list[_Node | None]) -> None:
        index = self._bucket_index(node.key, len(buckets))
        if buckets[index] is None:
            buckets[index] = node
            return

        tail = buckets[index]
        while tail.next is not None:
            tail = tail.next
        tail.next = node

    def _resize(self) -> None:
        new_buckets: list[_Node | None] = [None] * (len(self._buckets) * 2)
        for head in self._buckets:
            node = head
            while node is not None:
                next_node = node.next
                node.next = None
                self._append_node(node, new_buckets)
                node = next_node
        self._buckets = new_buckets
