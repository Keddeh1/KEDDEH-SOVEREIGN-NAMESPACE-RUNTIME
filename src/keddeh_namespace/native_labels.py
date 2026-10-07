"""REV-002 research adapter; native labels do not alter protocol integers."""


def displacement(label: int) -> int:
    """Map occupied labels ..., -3, -2, 1, 2, 3, ... to integer displacement."""
    if type(label) is not int or label in (0, -1):
        raise ValueError('native label must be an integer other than 0 or -1')
    return label - 1 if label > 0 else label + 1


def native_label(offset: int) -> int:
    """Map measurement displacement back to an occupied native label."""
    if type(offset) is not int:
        raise ValueError('displacement must be an integer')
    return offset + 1 if offset >= 0 else offset - 1


def add_labels(left: int, right: int) -> int:
    return native_label(displacement(left) + displacement(right))
