from pathlib import Path
import json
import yaml

from .loaders.config_loader import load_config
from .parsers.repo_inventory import build_repo_inventory
from .parsers.network_policy import parse_network_policies
from .generators.mermaid import generate_service_graph, generate_network_graph


def run(config_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(config_path)

    repo_inventory = build_repo_inventory(config.get("repositories", []))
    network_model = parse_network_policies(config.get("kubernetes", {}).get("network_policies", []))

    merged = {
        "project_name": config.get("project_name", "unknown-project"),
        "repositories": repo_inventory,
        "network": network_model,
        "cloud": config.get("cloud", {}),
    }

    (output_dir / "inventory.json").write_text(json.dumps(merged, indent=2, ensure_ascii=False))
    (output_dir / "service-architecture.mmd").write_text(generate_service_graph(merged), encoding="utf-8")
    (output_dir / "network-topology.mmd").write_text(generate_network_graph(merged), encoding="utf-8")
