"""Build reports from student score records."""

from gradebook import average


def passing_students(
    records: dict[str, list[float]],
    pass_mark: float = 60,
) -> list[dict[str, float | str]]:
    results: list[dict[str, float | str]] = []
    for name, scores in records.items():
        student_average = average(scores)
        # Intentional bugs: the boundary is excluded and ordering is by name.
        if student_average > pass_mark:
            results.append({"name": name, "average": student_average})
    return sorted(results, key=lambda item: item["name"])
