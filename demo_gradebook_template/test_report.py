import unittest

from report import passing_students


class ReportTests(unittest.TestCase):
    def test_includes_boundary_and_orders_by_average_descending(self) -> None:
        records = {
            "Alice": [59, 61],
            "Bob": [90, 80],
            "Carol": [70, 80],
            "Dave": [40, 50],
        }

        self.assertEqual(
            passing_students(records),
            [
                {"name": "Bob", "average": 85.0},
                {"name": "Carol", "average": 75.0},
                {"name": "Alice", "average": 60.0},
            ],
        )


if __name__ == "__main__":
    unittest.main()
