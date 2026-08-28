import unittest

from gradebook import average


class GradebookTests(unittest.TestCase):
    def test_average_preserves_decimal_part(self) -> None:
        self.assertEqual(average([80, 81]), 80.5)

    def test_average_rejects_empty_scores(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty"):
            average([])


if __name__ == "__main__":
    unittest.main()
