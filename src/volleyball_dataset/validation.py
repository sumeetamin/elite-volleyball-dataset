from collections.abc import Iterable


def validate_counts(row: dict, attempts: str, successes: str, errors: str | None = None) -> list[str]:
    problems = []
    n, k = row.get(attempts), row.get(successes)
    e = row.get(errors) if errors else None
    if n is not None and k is not None and k > n:
        problems.append(f"{successes} exceeds {attempts}")
    if n is not None and e is not None and e > n:
        problems.append(f"{errors} exceeds {attempts}")
    for key, value in row.items():
        if key.endswith(("_attempts", "_aces", "_errors", "_kills", "_points")) and value is not None and value < 0:
            problems.append(f"{key} is negative")
    return problems


def unique_keys(rows: Iterable[dict], keys: tuple[str, ...]) -> list[str]:
    seen, problems = set(), []
    for row in rows:
        key = tuple(row.get(k) for k in keys)
        if key in seen:
            problems.append(f"duplicate key {key}")
        seen.add(key)
    return problems
