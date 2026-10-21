"""Academic year constants for procurement runs."""

DEFAULT_ACADEMIC_YEAR = 2026
# Prior closed year (2024) plus open years through the next five after default
ACADEMIC_YEARS = tuple(range(2024, DEFAULT_ACADEMIC_YEAR + 6))
SESSION_KEY = "academic_year"

# Seed: full procurement archive vs empty open years (lots + shared students only)
SEED_ARCHIVE_YEAR = 2024
SEED_OPEN_YEARS = (2025, 2026)
SEED_CURRENT_YEAR = DEFAULT_ACADEMIC_YEAR
