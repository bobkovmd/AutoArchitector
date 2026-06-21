"""
collectors/gitlab_networkpolicy.py

Collects k8s NetworkPolicy YAML from a GitLab repository.
Supports multiple folders, recursive traversal, and multi-environment setups.

Config section in config/sources.yaml:

    kubernetes:
      gitlab:
        url: https://gitlab.example.com
        token_env: GITLAB_TOKEN        # env var name holding the token
        project_id: 123                # or project_path: org/repo
        network_policy_folders:
          - k8s/network-policies/prod
          - k8s/network-policies/staging
          - k8s/network-policies/test
      ref: main
"""
import os
import yaml
from typing import List, Dict, Any, Optional

try:
    import gitlab
except ImportError:
    raise ImportError("Install with: pip install python-gitlab")


class GitLabNetworkPolicyCollector:
    """
    Reads Kubernetes NetworkPolicy manifests from GitLab via API.

    Returns raw policy dicts enriched with source metadata:
        {
            'source_ref': str,    # e.g. gitlab:org/infra/k8s/np/prod/payments.yaml
            'environment': str,   # prod | staging | test | None
            'raw': dict           # the full NetworkPolicy manifest
        }
    """

    def __init__(self, config: Dict[str, Any]):
        gl_cfg = config.get("kubernetes", {}).get("gitlab", {})
        token = os.environ.get(gl_cfg.get("token_env", "GITLAB_TOKEN"), "")
        self.gl = gitlab.Gitlab(
            gl_cfg.get("url", "https://gitlab.com"),
            private_token=token,
        )
        project_id = gl_cfg.get("project_id") or gl_cfg.get("project_path")
        self.project = self.gl.projects.get(project_id)
        self.folders: List[str] = gl_cfg.get("network_policy_folders", [])
        self.ref: str = config.get("kubernetes", {}).get("ref", "main")

    def collect(self) -> List[Dict[str, Any]]:
        policies: List[Dict[str, Any]] = []
        for folder in self.folders:
            env = self._detect_env(folder)
            items = self.project.repository_tree(
                path=folder,
                recursive=True,
                ref=self.ref,
                all=True,
            )
            for item in items:
                if item["type"] != "blob":
                    continue
                if not item["name"].endswith((".yaml", ".yml")):
                    continue
                try:
                    raw_bytes = self.project.files.get(
                        item["path"], ref=self.ref
                    ).decode()
                    for doc in yaml.safe_load_all(raw_bytes):
                        if doc and doc.get("kind") == "NetworkPolicy":
                            policies.append({
                                "source_ref": (
                                    f"gitlab:{self.project.path_with_namespace}"
                                    f"/{item['path']}"
                                ),
                                "environment": env,
                                "raw": doc,
                            })
                except Exception as exc:  # noqa: BLE001
                    print(f"[WARN] Could not read {item['path']}: {exc}")
        return policies

    @staticmethod
    def _detect_env(folder_path: str) -> Optional[str]:
        for env in ("prod", "production", "staging", "stage", "test", "dev", "demo"):
            if env in folder_path.lower().split("/"):
                return env
        return None
