from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
QUERY_DIR = DATA_DIR / "queries"

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
INDEX_DIR = ARTIFACTS_DIR / "indexes"
DIAGNOSTICS_DIR = ARTIFACTS_DIR / "diagnostics"
ARCHIVE_DIR = ARTIFACTS_DIR / "archives"

RESULTS_DIR = PROJECT_ROOT / "results"
DEFAULT_RESULTS_DIR = RESULTS_DIR / "default"
ONE_W_RESULTS_DIR = RESULTS_DIR / "1wItems"


def resolve_project_path(path: str | Path) -> Path:
    """Resolve relative paths from the project root."""
    path = Path(path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path
