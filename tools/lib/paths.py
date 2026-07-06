# Repo-relative paths, replacing the per-script os.path.abspath(...) boilerplate.
import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def public_path(*parts: str) -> str:
    """Path under public/ (the committed site data)."""
    return os.path.join(REPO_ROOT, "public", *parts)


def pipeline_data_path(*parts: str) -> str:
    """Path under pipeline/data/ (pipeline inputs/snapshots)."""
    return os.path.join(REPO_ROOT, "pipeline", "data", *parts)
