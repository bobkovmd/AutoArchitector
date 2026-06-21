from pathlib import Path


def build_repo_inventory(repositories: list[dict]) -> list[dict]:
    result = []
    for repo in repositories:
        path = Path(repo["path"])
        files = []
        if path.exists():
            for pattern in ("**/*.java", "**/*.ts", "**/*.tsx"):
                files.extend(sorted(str(p) for p in path.glob(pattern) if p.is_file()))
        result.append({
            "name": repo["name"],
            "type": repo["type"],
            "path": str(path),
            "origin": repo.get("origin"),
            "files_count": len(files),
            "sample_files": files[:20],
        })
    return result
