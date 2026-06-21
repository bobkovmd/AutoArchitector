"""
normalizers/acl.py

ACL normalizer skeleton.

This file is intentionally minimal because the ACL format is
proprietary / project-specific. The interface is fixed; only
the parsing logic inside `normalize()` needs to be filled in
once the actual format is known.

Expected ACL entry structure (YAML example):

    - name: allow-api-to-db
      from: payments-api
      to: billing-db
      protocol: TCP
      ports:
        - 5432
      description: "API writes to billing postgres"
      environment: prod

If the format differs, update only `_parse_acl_entries()` below.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import yaml

from ..graph.model import Edge, Node


def normalize(raw_files: List[Dict[str, Any]]) -> Tuple[List[Node], List[Edge]]:
    """
    Normalize ACL files from GitLabACLCollector into canonical graph primitives.

    Args:
        raw_files: List of dicts from GitLabACLCollector.collect()
                   Each dict has keys: source_ref, filename, extension, raw_text

    Returns:
        (nodes, edges) ready to be merged into InfraGraph
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
            from_id = f"acl:{entry['from']}"
            to_id = f"acl:{entry['to']}"
            _ensure_node(Node(
                id=from_id,
                label=entry["from"],
                node_type="service",
                metadata={"environment": entry.get("environment")},
            ))
            _ensure_node(Node(
                id=to_id,
                label=entry["to"],
                node_type="service",
                metadata={"environment": entry.get("environment")},
            ))
            ports = [
                str(p) for p in entry.get("ports", [])
            ]
            edges.append(Edge(
                from_id=from_id,
                to_id=to_id,
                direction="egress",
                protocol=entry.get("protocol", "TCP"),
                ports=ports,
                description=entry.get("description", ""),
                source_type="acl",
                source_ref=file_data["source_ref"],
            ))

    return nodes, edges


def _parse_acl_entries(
    raw_text: str,
    extension: str,
    source_ref: str,
) -> List[Dict[str, Any]]:
    """
    Parse raw ACL file content into a list of entry dicts.

    TODO: Adjust this function to match the actual ACL format.
    Current implementation assumes a YAML list of rule objects.
    """
    if extension in (".yaml", ".yml"):
        try:
            data = yaml.safe_load(raw_text)
            if isinstance(data, list):
                return [e for e in data if _is_valid_entry(e)]
            if isinstance(data, dict) and "rules" in data:
                return [e for e in data["rules"] if _is_valid_entry(e)]
        except yaml.YAMLError as exc:
            print(f"[WARN] YAML parse error in {source_ref}: {exc}")
    # For other formats: implement JSON / HCL / proprietary parsing here
    return []


def _is_valid_entry(entry: Any) -> bool:
    """Check that a dict has the minimum required fields."""
    return (
        isinstance(entry, dict)
        and "from" in entry
        and "to" in entry
    )
