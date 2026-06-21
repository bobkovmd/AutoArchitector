"""
graph/model.py

Canonical graph model for AutoArchitector.

All collectors and normalizers converge to this model.
The graph builder merges Node + Edge lists from all sources,
deduplicates by id, and passes the result to the renderers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Node:
    """
    A single entity in the infrastructure graph.

    node_type values:
        service       — k8s workload / microservice
        vm            — Yandex Cloud compute instance
        db            — database (postgres, redis, mongo ...)
        queue         — message broker (kafka, rabbit, sns ...)
        external      — system outside the perimeter (payment gateway, SMTP ...)
        cluster       — k8s cluster or namespace group
        observability — prometheus, grafana, jaeger ...
        cidr          — IP range from security group rule
    """
    id: str                              # unique: "svc:payments", "vm:billing-db-01"
    label: str                           # display name on the diagram
    node_type: str = "service"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def merge(self, other: "Node") -> "Node":
        """Merge metadata from another Node with the same id."""
        merged_meta = {**other.metadata, **self.metadata}  # self wins on conflict
        return Node(
            id=self.id,
            label=self.label,
            node_type=self.node_type,
            metadata=merged_meta,
        )


@dataclass
class Edge:
    """
    A directed data-flow between two nodes.

    source_type values: networkpolicy | security_group | acl
    direction values:   ingress | egress
    """
    from_id: str
    to_id: str
    direction: str = "egress"            # ingress | egress
    protocol: str = "TCP"
    ports: List[str] = field(default_factory=list)     # ["443"], ["5432"], ["8080-8090"]
    description: str = ""
    source_type: str = ""                # networkpolicy | security_group | acl
    source_ref: str = ""                 # e.g. gitlab:org/repo/path/policy.yaml
    tags: List[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        """Arrow label shown on the diagram."""
        port_str = ",".join(self.ports) if self.ports else "any"
        proto = self.protocol if self.protocol != "ANY" else ""
        parts = [p for p in [proto, port_str] if p]
        suffix = f" [{':'.join(parts)}]" if parts else ""
        return f"{self.description}{suffix}" if self.description else suffix.strip()


@dataclass
class InfraGraph:
    """
    Merged infrastructure graph from all sources.
    """
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)

    def merge_nodes(self, new_nodes: List[Node]) -> None:
        index = {n.id: n for n in self.nodes}
        for n in new_nodes:
            if n.id in index:
                index[n.id] = index[n.id].merge(n)
            else:
                index[n.id] = n
        self.nodes = list(index.values())

    def merge_edges(self, new_edges: List[Edge]) -> None:
        self.edges.extend(new_edges)

    def merge(self, nodes: List[Node], edges: List[Edge]) -> None:
        self.merge_nodes(nodes)
        self.merge_edges(edges)

    def filter_by_env(self, environment: Optional[str]) -> "InfraGraph":
        """Return a subgraph matching the given environment tag."""
        if not environment:
            return self
        env_nodes = {
            n.id for n in self.nodes
            if n.metadata.get("environment") in (environment, None)
        }
        filtered_edges = [
            e for e in self.edges
            if e.from_id in env_nodes and e.to_id in env_nodes
        ]
        filtered_nodes = [
            n for n in self.nodes if n.id in env_nodes
        ]
        g = InfraGraph()
        g.nodes = filtered_nodes
        g.edges = filtered_edges
        return g

    def stats(self) -> Dict[str, int]:
        from collections import Counter
        type_counts = Counter(n.node_type for n in self.nodes)
        source_counts = Counter(e.source_type for e in self.edges)
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            **{f"node_{k}": v for k, v in type_counts.items()},
            **{f"edge_{k}": v for k, v in source_counts.items()},
        }
