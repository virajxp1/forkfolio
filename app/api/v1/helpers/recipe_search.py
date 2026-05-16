WRAPPING_QUOTES = {'"', "'"}


def normalize_search_query(raw_query: str) -> str:
    normalized = " ".join(raw_query.strip().split())
    if (
        len(normalized) >= 2
        and normalized[0] == normalized[-1]
        and normalized[0] in WRAPPING_QUOTES
    ):
        normalized = " ".join(normalized[1:-1].strip().split())
    return normalized
