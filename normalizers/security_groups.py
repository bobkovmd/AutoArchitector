"""
normalizers/security_groups.py

Normalizes Yandex Cloud Security Group rules into the canonical
InfraGraph Node + Edge model.

Input: output of YandexCloudSGCollector.collect()
Output: Tuple[List[Node], List[Edge]]
"""
from typing import Any, Dict, List, Optional, Tuple

from ..graph.model import Edge, Node

_PROTOCOL_MAP: Dict[str, str] = {
    "TCP": "TCP",
    "UDP": "UDP",
    "ICMP": "ICMP",
    "ANY": "ANY",
    "": "ANY",
}


def normalize_security_groups(
    sg_data: Dict[str, Any],
) -> Tuple[List[Node], List[Edge]]:
    """
    Convert raw Yandex Cloud SG data into canonical graph primitives.

    Args:
        sg_data: Dict returned by YandexCloudSGCollector.collect()

    Returns:
        (nodes, edges) ready to be merged into InfraGraph
    """
    sgs = sg_data.get("security_groups", [])
    vm_attachments = sg_data.get("vm_attachments", {})

    sg_index: Dict[str, Dict] = {sg["id"]: sg for sg in sgs}

    # Build reverse index: sg_id -> [vm_name, ...]
    sg_to_vms: Dict[str, List[str]] = {}
    for vm_name, vm_meta in vm_attachments.items():
        for sg_id in vm_meta.get("security_group_ids", []):
            sg_to_vms.setdefault(sg_id, []).append(vm_name)

    nodes: List[Node] = []
    edges: List[Edge] = []
    seen_nodes: set = set()

    def _ensure_node(node: Node) -> None:
        if node.id not in seen_nodes:
            nodes.append(node)
            seen_nodes.add(node.id)

    for sg_id, sg in sg_index.items():
        attached_vms = sg_to_vms.get(sg_id, [])

        for vm_name in attached_vms:
            vm_id = f"vm:{vm_name}"
            vm_meta = vm_attachments.get(vm_name, {})
            _ensure_node(Node(
                id=vm_id,
                label=vm_name,
                node_type="vm",
                metadata={
                    "zone": vm_meta.get("zone", ""),
                    "labels": vm_meta.get("labels", {}),
                    "security_group": sg.get("name", sg_id),
                    "source_ref": vm_meta.get("source_ref", ""),
                },
            ))

        for rule in sg.get("rules", []):
            direction = rule.get("direction", "INGRESS").lower()  # ingress | egress
            protocol = _PROTOCOL_MAP.get(
                rule.get("protocol_name", "").upper(), "ANY"
            )
            ports = _extract_ports(rule)
            cidr_list: List[str] = (
                rule.get("cidr_blocks", {}).get("v4_cidr_blocks", [])
            )
            description = _build_label(sg["name"], direction, protocol, ports, cidr_list)

            for vm_name in attached_vms:
                vm_id = f"vm:{vm_name}"

                if cidr_list:
                    for cidr in cidr_list:
                        cidr_id = f"cidr:{cidr}"
                        _ensure_node(Node(
                            id=cidr_id,
                            label=cidr,
                            node_type="external",
                            metadata={"cidr": cidr},
                        ))
                        from_id, to_id = (
                            (cidr_id, vm_id)
                            if direction == "ingress"
                            else (vm_id, cidr_id)
                        )
                        edges.append(Edge(
                            from_id=from_id,
                            to_id=to_id,
                            direction=direction,
                            protocol=protocol,
                            ports=ports,
                            description=description,
                            source_type="security_group",
                            source_ref=f"yc:sg:{sg_id}",
                        ))
                else:
                    any_id = "any"
                    _ensure_node(Node(id=any_id, label="Any", node_type="external"))
                    from_id, to_id = (
                        (any_id, vm_id)
                        if direction == "ingress"
                        else (vm_id, any_id)
                    )
                    edges.append(Edge(
                        from_id=from_id,
                        to_id=to_id,
                        direction=direction,
                        protocol=protocol,
                        ports=ports,
                        description=description,
                        source_type="security_group",
                        source_ref=f"yc:sg:{sg_id}",
                    ))

    return nodes, edges


def _extract_ports(rule: Dict[str, Any]) -> List[str]:
    port_range = rule.get("ports", {})
    if not port_range:
        return []
    from_port = port_range.get("from_port")
    to_port = port_range.get("to_port")
    if from_port is None:
        return []
    return (
        [str(from_port)]
        if from_port == to_port
        else [f"{from_port}-{to_port}"]
    )


def _build_label(
    sg_name: str,
    direction: str,
    protocol: str,
    ports: List[str],
    cidr_list: List[str],
) -> str:
    port_str = ",".join(ports) if ports else "any"
    cidr_str = ",".join(cidr_list) if cidr_list else "any"
    return f"SG:{sg_name} {direction.upper()} {protocol} :{port_str} ← {cidr_str}"
