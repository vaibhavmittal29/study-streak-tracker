"""NLP and string similarity helpers for subject normalization (Phase 9.3b)."""

import difflib
import re

COMMON_ACRONYMS: dict[str, str] = {
    "dsa": "Data Structures & Algorithms",
    "os": "Operating Systems",
    "dbms": "Database Management Systems",
    "cn": "Computer Networks",
    "ml": "Machine Learning",
    "ai": "Artificial Intelligence",
    "toc": "Theory of Computation",
    "oop": "Object Oriented Programming",
}


def suggest_normalized_subject(query: str, existing_subjects: list[str]) -> str | None:
    """Given a user's typed subject and existing subjects, suggest an existing subject.

    Returns None if:
    - query is empty or whitespace
    - query is already an exact case-insensitive match
    - no close match is found
    """
    q = query.strip()
    if not q:
        return None

    q_lower = q.lower()

    # 1. Exact case-insensitive match check: if identical, no need to suggest
    for s in existing_subjects:
        if s.strip().lower() == q_lower:
            return None

    # 2. Check acronym / abbreviation dictionary
    if q_lower in COMMON_ACRONYMS:
        target = COMMON_ACRONYMS[q_lower]
        for s in existing_subjects:
            if s.lower() == target.lower() or (
                difflib.SequenceMatcher(None, s.lower(), target.lower()).ratio() >= 0.7
            ):
                return s
        for s in existing_subjects:
            initials = "".join(w[0] for w in re.split(r"[\s&_/-]+", s) if w).lower()
            if initials == q_lower:
                return s

    # 3. Check initials of multi-word subjects (e.g. DSA -> Data Structures)
    for s in existing_subjects:
        words = [w for w in re.split(r"[\s&_/-]+", s) if w]
        if len(words) >= 2:
            initials = "".join(w[0] for w in words).lower()
            if initials == q_lower:
                return s

    # 4. Fuzzy match using difflib.get_close_matches
    lower_map = {s.strip().lower(): s.strip() for s in existing_subjects if s.strip()}
    close_keys = difflib.get_close_matches(q_lower, list(lower_map.keys()), n=1, cutoff=0.7)
    if close_keys:
        match = lower_map[close_keys[0]]
        if match.lower() != q_lower:
            return match

    return None
