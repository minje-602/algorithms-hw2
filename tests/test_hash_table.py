import unittest

from src.hash_table import HashTable


class HashTableTests(unittest.TestCase):
    def test_empty_table(self):
        table = HashTable()

        self.assertIsNone(table.get("a"))
        self.assertEqual(table.find("a"), (None, 0))
        self.assertNotIn("a", table)
        self.assertEqual(len(table), 0)
        self.assertEqual(table.load_factor, 0)
        self.assertFalse(table.delete("a"))

    def test_put_updates_existing_key(self):
        table = HashTable()

        table.put("a", 1)
        table.put("a", 2)

        self.assertEqual(table.get("a"), 2)
        self.assertEqual(len(table), 1)
        self.assertIn("a", table)

    def test_collisions_are_searched_and_counted(self):
        table = HashTable()
        for key in ("a", "i", "q"):
            table.put(key, key.upper())

        for key in ("a", "i", "q"):
            with self.subTest(key=key):
                self.assertEqual(table.get(key), key.upper())
                self.assertIn(key, table)

        comparisons = [table.find(key)[1] for key in ("a", "i", "q")]
        self.assertEqual(sorted(comparisons), [1, 2, 3])
        self.assertEqual(table.find("y"), (None, 3))
        self.assertEqual(table.find("b"), (None, 0))

    def test_delete_from_collision_chain(self):
        table = HashTable()
        for key in ("a", "i", "q"):
            table.put(key, key.upper())

        self.assertTrue(table.delete("i"))
        self.assertIsNone(table.get("i"))
        self.assertIn("a", table)
        self.assertIn("q", table)
        self.assertEqual(len(table), 2)
        self.assertFalse(table.delete("i"))

    def test_resizes_after_load_factor_exceeds_limit(self):
        table = HashTable()
        keys = ("a", "b", "c", "d", "e", "f")

        for key in keys:
            table.put(key, key.upper())
        self.assertEqual(table.load_factor, 0.75)

        table.put("g", "G")

        self.assertEqual(table.load_factor, 7 / 16)
        self.assertEqual(len(table), 7)
        for key in keys + ("g",):
            with self.subTest(key=key):
                self.assertEqual(table.get(key), key.upper())

    def test_none_max_load_disables_resizing(self):
        table = HashTable(max_load=None)

        for index in range(20):
            key = f"key-{index}"
            table.put(key, index)

        self.assertEqual(len(table), 20)
        self.assertEqual(table.load_factor, 2.5)
        for index in range(20):
            key = f"key-{index}"
            with self.subTest(key=key):
                self.assertEqual(table.get(key), index)

    def test_hash_uses_horner_multiplier(self):
        table = HashTable()
        table.put("a", 1)

        self.assertEqual(table.find("ab"), (None, 1))
        self.assertEqual(table.find("ba"), (None, 0))

    def test_find_returns_stored_value(self):
        table = HashTable()
        table.put("a", 1)

        self.assertEqual(table.find("a"), (1, 1))

    def test_bucket_count_sets_initial_size(self):
        table = HashTable(bucket_count=4093, max_load=None)
        table.put("a", 1)

        self.assertEqual(table.load_factor, 1 / 4093)

    def test_delete_each_position_in_chain(self):
        keys = ("a", "i", "q")
        for victim in keys:
            with self.subTest(victim=victim):
                table = HashTable()
                for key in keys:
                    table.put(key, key.upper())

                self.assertTrue(table.delete(victim))
                self.assertIsNone(table.get(victim))
                self.assertEqual(len(table), 2)
                for key in keys:
                    if key != victim:
                        self.assertEqual(table.get(key), key.upper())


if __name__ == "__main__":
    unittest.main()
