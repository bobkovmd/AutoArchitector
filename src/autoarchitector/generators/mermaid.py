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
