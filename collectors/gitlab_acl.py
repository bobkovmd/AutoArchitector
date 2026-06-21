"""
collectors/gitlab_acl.py

Generic ACL collector from a GitLab project.
Reads all files from a configured folder and passes raw content
to the normalizer. The format is intentionally opaque here —
the normalizer (normalizers/acl.py) owns the parsing logic.

Config section in config/sources.yaml:

    acl:
      gitlab:
        url: https://gitlab.example.com
        token_env: GITLAB_TOKEN
        project_id: 456          # or project_path: org/acl-repo
        folder: acl/rules        # root folder to scan
        file_extensions: [.yaml, .yml, .json, .conf, .hcl]
      ref: main
"""
import os
from typing import Any, Dict, List, Optional

try:
    import gitlab
except ImportError:
    raise ImportError("Install with: pip install python-gitlab")


class GitLabACLCollector:
    """
    Collects raw ACL rule files from a GitLab repository.

    Returns a list of dicts:
        {
            'source_ref': str,       # gitlab:org/repo/path/file.yaml
            'filename': str,
            'extension': str,        # .yaml | .json | .conf | ...
            'raw_text': str,         # raw file content as string
        }
    """

    DEFAULT_EXTENSIONS = (".yaml", ".yml", ".json", ".conf", ".hcl", ".toml")

    def __init__(self, config: Dict[str, Any]):
        acl_cfg = config.get("acl", {}).get("gitlab", {})
        token = os.environ.get(acl_cfg.get("token_env", "GITLAB_TOKEN"), "")
        self.gl = gitlab.Gitlab(
            acl_cfg.get("url", "https://gitlab.com"),
            private_token=token,
        )
        project_id = acl_cfg.get("project_id") or acl_cfg.get("project_path")
        self.project = self.gl.projects.get(project_id)
        self.folder: str = acl_cfg.get("folder", "")
        raw_exts = acl_cfg.get("file_extensions", list(self.DEFAULT_EXTENSIONS))
        self.extensions = tuple(raw_exts)
        self.ref: str = config.get("acl", {}).get("ref", "main")

    def collect(self) -> List[Dict[str, Any]]:
        items = self.project.repository_tree(
            path=self.folder,
            recursive=True,
            ref=self.ref,
            all=True,
        )
        results: List[Dict[str, Any]] = []
        for item in items:
            if item["type"] != "blob":
                continue
            ext = self._ext(item["name"])
            if ext not in self.extensions:
                continue
            try:
                raw_text = self.project.files.get(
                    item["path"], ref=self.ref
                ).decode().decode("utf-8", errors="replace")
                results.append({
                    "source_ref": (
                        f"gitlab:{self.project.path_with_namespace}/{item['path']}"
                    ),
                    "filename": item["name"],
                    "extension": ext,
                    "raw_text": raw_text,
                })
            except Exception as exc:  # noqa: BLE001
                print(f"[WARN] Could not read ACL file {item['path']}: {exc}")
        return results

    @staticmethod
    def _ext(filename: str) -> Optional[str]:
        idx = filename.rfind(".")
        return filename[idx:].lower() if idx != -1 else None
