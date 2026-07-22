def parse(value: str | None) -> set[str]:
    if not value:
        return set()
    return set(value.split())


def is_subset(child: str | None, parent: str | None) -> bool:
    return parse(child).issubset(parse(parent))


def check_in_configured_scopes(allowed_scopes: set[str], requested: str | None) -> bool:
    if not requested:
        return True
    return parse(requested).issubset(allowed_scopes)
