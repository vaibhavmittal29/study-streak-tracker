"""CSV generation service with formula injection mitigation."""

import csv
import io

from app.models import StudySession


def sanitize_csv_cell(value: str | None) -> str:
    """Sanitize text to prevent CSV/formula injection in spreadsheet software.

    If a string starts with '=', '+', '-', or '@', prefix it with a single
    quote so Excel and Google Sheets treat it as literal text rather than executable formula.
    """
    if value is None:
        return ""
    if value and value[0] in ("=", "+", "-", "@"):
        return f"'{value}"
    return value


def generate_sessions_csv(sessions: list[StudySession]) -> str:
    """Generate RFC 4180 compliant CSV string from study sessions."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Header row
    writer.writerow(["id", "date", "subject", "duration_minutes", "notes", "created_at"])

    for s in sessions:
        writer.writerow(
            [
                s.id,
                s.date.isoformat(),
                sanitize_csv_cell(s.subject),
                s.duration_minutes,
                sanitize_csv_cell(s.notes),
                s.created_at.isoformat() if s.created_at else "",
            ]
        )

    return output.getvalue()
