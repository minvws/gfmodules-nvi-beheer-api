def parse(value: str | None) -> set[str]:
    if not value:
        return set()
    return set(value.split())


def is_subset(child: str | None, parent: str | None) -> bool:
    return parse(child).issubset(parse(parent))
