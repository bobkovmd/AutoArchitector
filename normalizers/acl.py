"""
normalizers/acl.py

Full ACL normalizer for AutoArchitector.

Expected input format: examples/acl/rules.yaml
Parses rule files collected by collectors/gitlab_acl.py and converts them
into canonical Node + Edge graph primitives.

Supported file formats:
  - YAML with top-level "rules" list  (primary format, see examples/acl/rules.yaml)
  - YAML with bare list at root
  - JSON with same structure
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

import yaml

# ---------------------------------------------------------------------------
# Canonical graph model — inline to avoid import path issues in both
# standalone and package usage.  If graph/model.py exists, import from there.
# ---------------------------------------------------------------------------
try:
    from graph.model import Edge, Node  # type: ignore
except ImportError:
    from dataclasses import dataclass, field

    @dataclass
    class Node:
        id: str
        label: str
        node_type: str = "service"   # service | vm | external | cluster | db
        metadata: Dict[str, Any] = field(default_factory=dict)

    @dataclass
    class Edge:
        from_id: str
        to_id: str
        direction: str = "egress"
        protocol: str = "TCP"
        ports: List[str] = field(default_factory=list)
        description: str = ""
        source_type: str = "acl"
        source_ref: str = ""
        tags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize(raw_files: List[Dict[str, Any]]) -> Tuple[List[Node], List[Edge]]:
    """
    Normalize ACL files from GitLabACLCollector into canonical graph primitives.

    Args:
        raw_files: list of dicts, each with keys:
            source_ref  str  - e.g. "gitlab:org/repo/acl/rules.yaml"
            filename    str  - base filename
            extension   str  - .yaml | .yml | .json | ...
            raw_text    str  - raw file content

    Returns:
        (nodes, edges) ready to merge into InfraGraph
    """
    nodes: List[Node] = []
    edges: List[Edge] = []
    seen_nodes: set = set()

    def _ensure_node(n: Node) -> None:
        if n.id not in seen_nodes:
            nodes.append(n)
            seen_nodes.add(n.id)

    for file_data in raw_files:
        entries = _parse_acl_entries(
            file_data["raw_text"],
            file_data["extension"],
            file_data["source_ref"],
        )
        for entry in entries:
            from_name = entry["from"]
            to_name   = entry["to"]
            from_id   = f"svc:{from_name}"
            to_id     = f"svc:{to_name}"

            env = entry.get("environment")
            tags = entry.get("tags", [])

            _ensure_node(Node(
                id=from_id,
                label=from_name,
                node_type=_infer_node_type(from_name, tags),
                metadata={"environment": env, "tags": tags},
            ))
            _ensure_node(Node(
                id=to_id,
                label=to_name,
                node_type=_infer_node_type(to_name, tags),
                metadata={"environment": env, "tags": tags},
            ))

            ports = _normalise_ports(entry.get("ports", []))
            edges.append(Edge(
                from_id=from_id,
                to_id=to_id,
                direction="egress",
                protocol=entry.get("protocol", "TCP").upper(),
                ports=ports,
                description=entry.get("description", ""),
                source_type="acl",
                source_ref=file_data["source_ref"],
                tags=tags,
            ))

    return nodes, edges


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_acl_entries(
    raw_text: str,
    extension: str,
    source_ref: str,
) -> List[Dict[str, Any]]:
    """Parse raw file text into a list of rule dicts."""
    data: Any = None
    try:
        if extension in (".yaml", ".yml"):
            data = yaml.safe_load(raw_text)
        elif extension == ".json":
            data = json.loads(raw_text)
        else:
            print(f"[WARN] Unsupported ACL format '{extension}' in {source_ref} — skipping")
            return []
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] Parse error in {source_ref}: {exc}")
        return []

    # Accepted shapes:
    #   { rules: [...] }          ← primary canonical format
    #   [...]                     ← bare list
    if isinstance(data, dict):
        candidates = data.get("rules") or data.get("acl") or data.get("policies")
        if isinstance(candidates, list):
            raw_list = candidates
        else:
            print(f"[WARN] ACL file {source_ref}: dict has no 'rules' key — skipping")
            return []
    elif isinstance(data, list):
        raw_list = data
    else:
        print(f"[WARN] ACL file {source_ref}: unexpected top-level type {type(data)} — skipping")
        return []

    return [e for e in raw_list if _is_valid_entry(e, source_ref)]


def _is_valid_entry(entry: Any, source_ref: str = "") -> bool:
    if not isinstance(entry, dict):
        return False
    missing = [f for f in ("from", "to") if f not in entry]
    if missing:
        print(f"[WARN] ACL entry missing required fields {missing} in {source_ref}: {entry}")
        return False
    return True


def _normalise_ports(raw_ports: Any) -> List[str]:
    """Accept int, str, or list and return a normalised list of strings."""
    if raw_ports is None:
        return []
    if isinstance(raw_ports, (int, str)):
        return [str(raw_ports)]
    if isinstance(raw_ports, list):
        return [str(p) for p in raw_ports]
    return []


_DB_HINTS    = ("db", "database", "postgres", "mysql", "mongo", "redis", "elastic")
_EXT_HINTS   = ("external", "gateway", "relay", "smtp", "s3", "cdn")
_MQ_HINTS    = ("kafka", "rabbit", "rabbitmq", "sqs", "sns", "nats", "queue", "broker")
_OBS_HINTS   = ("prometheus", "grafana", "jaeger", "tempo", "loki", "elastic")


def _infer_node_type(name: str, tags: List[str]) -> str:
    """Best-effort node type from name patterns and tags."""
    lowered = name.lower()
    all_tags = [t.lower() for t in tags]

    if "external" in all_tags or any(h in lowered for h in _EXT_HINTS):
        return "external"
    if "db" in all_tags or any(h in lowered for h in _DB_HINTS):
        return "db"
    if any(h in lowered for h in _MQ_HINTS):
        return "queue"
    if any(h in lowered for h in _OBS_HINTS):
        return "observability"
    return "service"
