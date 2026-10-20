"""Academic year constants for procurement runs."""

DEFAULT_ACADEMIC_YEAR = 2025
# Default year plus the next five years (2025–2030)
ACADEMIC_YEARS = tuple(range(DEFAULT_ACADEMIC_YEAR, DEFAULT_ACADEMIC_YEAR + 6))
SESSION_KEY = "academic_year"
