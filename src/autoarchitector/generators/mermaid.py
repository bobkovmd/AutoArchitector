"""
src/autoarchitector/generators/mermaid.py

Mermaid diagram generators for AutoArchitector.

Two modes:
  1. Legacy dict-based (generate_service_graph / generate_network_graph) — kept for back-compat.
  2. InfraGraph-based (generate_from_graph) — primary path, uses canonical graph/model.py.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from graph.model import InfraGraph


# ---------------------------------------------------------------------------
# InfraGraph → Mermaid (primary)
# ---------------------------------------------------------------------------

NODE_SHAPES = {
    "service":       ('["{}")', '["{}"'),     # rounded rect: ["label"]
    "vm":            ('("{}")', '("{}"'),     # stadium
    "db":            ('[("{}")', '[("{}"'),   # cylinder
    "queue":         ('>"{}"', '>"{}"'),      # asymmetric
    "external":      ('{{"{}"}}', '{{"{}"}}'),# hexagon
    "observability": ('("{}")', '("{}"'),
    "cidr":          ('["{}")', '["{}"'),
    "cluster":       ('["{}")', '["{}"'),
}

SOURCE_COLORS = {
    "networkpolicy": "#4f98a3",   # teal
    "acl":           "#6daa45",   # green
    "security_group": "#e8af34",  # gold
}


def generate_from_graph(graph: "InfraGraph", title: str = "") -> str:
    """
    Convert InfraGraph to a Mermaid flowchart string.
    Returns the raw Mermaid DSL (no HTML wrapper).
    """
    lines = ["flowchart LR"]

    if title:
        lines.insert(0, f"---\ntitle: {title}\n---")

    # Nodes grouped by type for visual clustering
    type_groups: dict = {}
    for node in graph.nodes:
        type_groups.setdefault(node.node_type, []).append(node)

    for node_type, nodes in type_groups.items():
        lines.append(f"  subgraph {node_type}")
        for node in nodes:
            nid = _safe(node.id)
            label = node.label
            shape_open, shape_close = _node_shape(node_type)
            lines.append(f"    {nid}{shape_open}{label}{shape_close}")
        lines.append("  end")

    lines.append("")

    # Edges with labels
    for edge in graph.edges:
        src = _safe(edge.from_id)
        dst = _safe(edge.to_id)
        label = _edge_label(edge)
        color = SOURCE_COLORS.get(edge.source_type, "#aaaaaa")
        arrow = "-->" if edge.direction == "egress" else "<--"
        if label:
            lines.append(f"  {src} {arrow}|\"{label}\"| {dst}")
        else:
            lines.append(f"  {src} {arrow} {dst}")

    # Style edges by source
    for i, edge in enumerate(graph.edges):
        color = SOURCE_COLORS.get(edge.source_type, "#aaaaaa")
        lines.append(f"  linkStyle {i} stroke:{color},stroke-width:1.5px")

    return "\n".join(lines) + "\n"


def _node_shape(node_type: str) -> tuple:
    shapes = {
        "service":       ("[\"", "\"]"),
        "vm":            ("(\"", "\")"),
        "db":            ("[(\"", "\")]"),
        "queue":         (">\"" , "\"]"),
        "external":      ("{{\"", "\"}}"),
        "observability": ("(\"", "\")"),
        "cidr":          ("[\"", "\"]"),
        "cluster":       ("[\"", "\"]"),
    }
    return shapes.get(node_type, ("[\"", "\"]"))


def _edge_label(edge) -> str:
    port_str = ",".join(edge.ports) if edge.ports else ""
    proto = edge.protocol if edge.protocol not in ("ANY", "TCP") else ""
    tag = f"{proto}:{port_str}" if proto and port_str else (port_str or proto)
    desc = edge.description[:40] if edge.description else ""
    if desc and tag:
        return f"{desc} [{tag}]"
    return desc or (f"[{tag}]" if tag else "")


# ---------------------------------------------------------------------------
# Legacy dict-based generators (back-compat)
# ---------------------------------------------------------------------------

def generate_service_graph(model: dict) -> str:
    lines = ["flowchart LR"]
    for repo in model.get("repositories", []):
        node = _safe(repo["name"])
        label = f'{repo["name"]}\\n{repo["type"]}\\nfiles={repo["files_count"]}'
        lines.append(f'  {node}["{label}"]')
    return "\n".join(lines) + "\n"


def generate_network_graph(model: dict) -> str:
    lines = ["flowchart LR"]
    network = model.get("network", {})
    for service in network.get("services", []):
        lines.append(f'  {_safe(service)}(("{service}"))')
    for edge in network.get("edges", []):
        src = _safe(edge["from"])
        dst = _safe(edge["to"])
        label = f'{edge["direction"]} / {edge["policy"]}'
        lines.append(f'  {src} -->|"{label}"| {dst}')
    return "\n".join(lines) + "\n"


def _safe(name: str) -> str:
    return ''.join(ch if ch.isalnum() else '_' for ch in name)
