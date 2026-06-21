from pathlib import Path
import yaml


def _read_yaml_documents(path: Path) -> list[dict]:
    docs = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
    return [d for d in docs if isinstance(d, dict)]


def parse_network_policies(paths: list[str]) -> dict:
    services = set()
    edges = []

    for raw in paths:
        root = Path(raw)
        if not root.exists():
            continue
        files = [root] if root.is_file() else sorted(root.rglob("*.y*ml"))
        for file in files:
            for doc in _read_yaml_documents(file):
                if doc.get("kind") != "NetworkPolicy":
                    continue
                name = doc.get("metadata", {}).get("name", "unknown-policy")
                spec = doc.get("spec", {})
                target = spec.get("podSelector", {}).get("matchLabels", {}).get("app", name)
                services.add(target)
                for ingress in spec.get("ingress", []):
                    for source in ingress.get("from", []):
                        src = source.get("podSelector", {}).get("matchLabels", {}).get("app", "external")
                        services.add(src)
                        edges.append({
                            "from": src,
                            "to": target,
                            "policy": name,
                            "direction": "ingress",
                        })
                for egress in spec.get("egress", []):
                    for dst in egress.get("to", []):
                        target_dst = dst.get("podSelector", {}).get("matchLabels", {}).get("app", "external")
                        services.add(target_dst)
                        edges.append({
                            "from": target,
                            "to": target_dst,
                            "policy": name,
                            "direction": "egress",
                        })

    return {
        "services": sorted(services),
        "edges": sorted(edges, key=lambda x: (x["from"], x["to"], x["policy"], x["direction"])),
    }
