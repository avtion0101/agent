"""Intentional bug and a corrected version; both have type annotations."""


def broken(value: str, items: list[str] = []) -> list[str]:
    items.append(value)
    return items


def fixed(value: str, items: list[str] | None = None) -> list[str]:
    if items is None:
        items = []
    items.append(value)
    return items


if __name__ == "__main__":
    first = broken("first")
    second = broken("second")
    print("broken:", first, second, "same object:", first is second)
    a, b = fixed("first"), fixed("second")
    print("fixed: ", a, b, "same object:", a is b)
