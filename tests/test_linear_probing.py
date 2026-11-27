import unittest

from src.linear_probing import LinearProbingTable


class LinearProbingTableTests(unittest.TestCase):
    def test_empty_table(self):
        table = LinearProbingTable()

        self.assertIsNone(table.get("a"))
        self.assertEqual(table.find("a"), (None, 1))
        self.assertNotIn("a", table)
        self.assertEqual(len(table), 0)
        self.assertEqual(table.load_factor, 0)
        self.assertFalse(table.delete("a"))

    def test_put_updates_existing_key(self):
        table = LinearProbingTable()

        table.put("a", 1)
        table.put("a", 2)

        self.assertEqual(table.get("a"), 2)
        self.assertEqual(len(table), 1)
        self.assertIn("a", table)

    def test_collisions_and_unsuccessful_searches_count_probed_slots(self):
        table = LinearProbingTable()
        for key in ("a", "i", "q"):
            table.put(key, key.upper())

        for key in ("a", "i", "q"):
            with self.subTest(key=key):
                self.assertEqual(table.get(key), key.upper())
                self.assertIn(key, table)

        self.assertEqual(
            [table.find(key)[1] for key in ("a", "i", "q")],
            [1, 2, 3],
        )
        self.assertEqual(table.find("y"), (None, 4))
        self.assertEqual(table.find("b"), (None, 3))

    def test_horner_hash_and_find_return_value(self):
        table = LinearProbingTable()
        table.put("a", 1)

        self.assertEqual(table.find("a"), (1, 1))
        self.assertEqual(table.find("ab"), (None, 2))
        self.assertEqual(table.find("ba"), (None, 1))

    def test_deleting_middle_of_cluster_reinserts_following_entries(self):
        table = LinearProbingTable()
        for key in ("a", "i", "q"):
            table.put(key, key.upper())

        self.assertTrue(table.delete("i"))
        self.assertIsNone(table.get("i"))
        self.assertEqual(table.get("a"), "A")
        self.assertEqual(table.get("q"), "Q")
        self.assertEqual(table.find("q"), ("Q", 2))
        self.assertEqual(len(table), 2)
        self.assertFalse(table.delete("i"))

    def test_deletion_at_each_position_preserves_other_cluster_entries(self):
        keys = ("a", "i", "q")
        for victim in keys:
            with self.subTest(victim=victim):
                table = LinearProbingTable()
                for key in keys:
                    table.put(key, key.upper())

                self.assertTrue(table.delete(victim))
                self.assertIsNone(table.get(victim))
                self.assertEqual(len(table), 2)
                for key in keys:
                    if key != victim:
                        self.assertEqual(table.get(key), key.upper())

    def test_cluster_wraps_around_and_reinserts_after_deletion(self):
        table = LinearProbingTable()
        for key in ("g", "o", "w"):
            table.put(key, key.upper())

        self.assertEqual(
            [table.find(key)[1] for key in ("g", "o", "w")],
            [1, 2, 3],
        )

        self.assertTrue(table.delete("g"))
        self.assertEqual(table.get("o"), "O")
        self.assertEqual(table.get("w"), "W")
        self.assertEqual(table.find("o"), ("O", 1))
        self.assertEqual(table.find("w"), ("W", 2))

    def test_resizes_after_load_factor_exceeds_limit(self):
        table = LinearProbingTable()
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

    def test_repeatedly_resizes_until_custom_max_load_is_met(self):
        table = LinearProbingTable(bucket_count=1, max_load=0.1)

        table.put("a", 1)
        table.put("b", 2)

        self.assertEqual(table.load_factor, 2 / 32)
        self.assertEqual(table.get("a"), 1)
        self.assertEqual(table.get("b"), 2)

    def test_full_table_overflow_and_reuse_after_deletion(self):
        table = LinearProbingTable(max_load=None)
        keys = ("a", "i", "q", "y", "g", "o", "w", "b")
        for key in keys:
            table.put(key, key.upper())

        self.assertEqual(table.load_factor, 1.0)
        for key in keys:
            with self.subTest(key=key):
                self.assertEqual(table.get(key), key.upper())

        with self.assertRaises(OverflowError):
            table.put("c", "C")
        self.assertEqual(len(table), 8)
        self.assertEqual(table.find("c"), (None, 8))
        for key in keys:
            with self.subTest(key=key):
                self.assertEqual(table.get(key), key.upper())

        table.put("i", "updated")
        self.assertEqual(table.get("i"), "updated")
        self.assertEqual(len(table), 8)

        self.assertTrue(table.delete("a"))
        for key in keys[1:]:
            with self.subTest(key=key):
                self.assertEqual(
                    table.get(key),
                    "updated" if key == "i" else key.upper(),
                )
        table.put("c", "C")
        self.assertEqual(table.get("c"), "C")
        self.assertEqual(len(table), 8)

    def test_max_load_validation(self):
        for max_load in (0, 1, 1.5, -0.1, True):
            with self.subTest(max_load=max_load):
                with self.assertRaises(ValueError):
                    LinearProbingTable(max_load=max_load)

    def test_bucket_count_validation_and_custom_initial_size(self):
        table = LinearProbingTable(bucket_count=4093, max_load=None)
        table.put("a", 1)
        self.assertEqual(table.load_factor, 1 / 4093)

        for bucket_count in (0, -1, 1.5, True):
            with self.subTest(bucket_count=bucket_count):
                with self.assertRaises(ValueError):
                    LinearProbingTable(bucket_count=bucket_count)

    def test_non_string_keys_follow_hash_table_behavior(self):
        table = LinearProbingTable()

        with self.assertRaises(TypeError):
            table.put(1, "value")
        self.assertNotIn(1, table)
        self.assertFalse(table.delete(1))


if __name__ == "__main__":
    unittest.main()
