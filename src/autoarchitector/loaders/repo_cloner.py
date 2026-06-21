import subprocess
from pathlib import Path


def clone_repos(repositories: list[dict]) -> None:
    """Clone or update all repositories listed in config."""
    for repo in repositories:
        origin = repo.get("origin")
        path = Path(repo["path"])
        name = repo["name"]

        if not origin:
            print(f"[{name}] skip: no 'origin' URL specified")
            continue

        if path.exists():
            print(f"[{name}] exists at {path}, pulling latest...")
            result = subprocess.run(
                ["git", "pull", "--ff-only"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            _print_result(name, result)
        else:
            print(f"[{name}] cloning {origin} → {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                ["git", "clone", origin, str(path)],
                capture_output=True,
                text=True,
            )
            _print_result(name, result)


def _print_result(name: str, result: subprocess.CompletedProcess) -> None:
    if result.returncode == 0:
        msg = (result.stdout or result.stderr or "ok").strip()
        print(f"[{name}] ✓ {msg}")
    else:
        print(f"[{name}] ✗ error (code {result.returncode}):")
        if result.stderr:
            print(result.stderr.strip())
