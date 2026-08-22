# tests/test_code_quality.py
from pathlib import Path


def test_no_python_file_exceeds_250_lines():
    """Verifies that no single Python source file in src/ or tests/ exceeds 250 lines of code."""
    root_dir = Path(__file__).resolve().parent.parent
    over_limit = []

    for path in root_dir.rglob("*.py"):
        if any(
            part in path.parts
            for part in (".venv", ".git", "__pycache__", ".pytest_cache", ".ruff_cache", "migrations")
        ):
            continue

        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > 250:
            rel_path = path.relative_to(root_dir)
            over_limit.append(f"{rel_path} ({line_count} lines)")

    assert not over_limit, f"The following Python files exceed the 250-line limit: {', '.join(over_limit)}"
