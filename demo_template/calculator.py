"""A deliberately incomplete calculator used for the agent demo."""


def add(left: float, right: float) -> float:
    return left + right


def divide(left: float, right: float) -> float:
    # Intentional bug: this loses the decimal part and has no clear zero check.
    return left // right

