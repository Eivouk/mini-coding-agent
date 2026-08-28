"""Core calculations for a small student gradebook."""


def average(scores: list[float]) -> float:
    if not scores:
        raise ValueError("scores cannot be empty")
    # Intentional bug: floor division discards the decimal part.
    return round(sum(scores) // len(scores), 2)
