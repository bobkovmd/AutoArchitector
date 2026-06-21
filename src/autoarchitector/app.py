"""
src/autoarchitector/app.py

Main pipeline orchestrator for AutoArchitector.

Flow:
  config.yaml
    └─ collectors:  GitLab NetworkPolicy, GitLab ACL, Yandex Cloud SG
    └─ normalizers: per-source → List[Node] + List[Edge]
    └─ InfraGraph:  merge + optional env filter
    └─ renderers:   diagram.html, graph.json, diagram.mmd
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

# Graph model — try package path first, then root-level fallback
try:
    from graph.model import InfraGraph
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from graph.model import InfraGraph  # type: ignore

from src.autoarchitector.generators.html_renderer import render_html
from src.autoarchitector.generators.mermaid import generate_from_graph


def run(config_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(config_path) as f:
        config: Dict[str, Any] = yaml.safe_load(f)

    title = config.get("output", {}).get("title", "Infrastructure Diagram")
    env_filter = config.get("output", {}).get("environment_filter")
    formats = config.get("output", {}).get("formats", ["html", "json"])

    graph = InfraGraph()

    # ── 1. Kubernetes NetworkPolicy ─────────────────────────────────────────
    if "kubernetes" in config:
        try:
            from collectors.gitlab_networkpolicy import GitLabNetworkPolicyCollector
            from normalizers.networkpolicy import normalize as np_normalize

            k8s_cfg = config["kubernetes"]["gitlab"]
            collector = GitLabNetworkPolicyCollector(
                gitlab_url=k8s_cfg["url"],
                token_env=k8s_cfg["token_env"],
                project_id=k8s_cfg.get("project_id"),
                project_path=k8s_cfg.get("project_path"),
                folders=k8s_cfg["network_policy_folders"],
                ref=config["kubernetes"].get("ref", "main"),
            )
            raw = collector.collect()
            nodes, edges = np_normalize(raw)
            graph.merge(nodes, edges)
            print(f"[OK] NetworkPolicy: {len(nodes)} nodes, {len(edges)} edges")
        except Exception as exc:
            print(f"[WARN] NetworkPolicy collector failed: {exc}")

    # ── 2. ACL ─────────────────────────────────────────────────────────────────
    if "acl" in config:
        try:
            from collectors.gitlab_acl import GitLabACLCollector
            from normalizers.acl import normalize as acl_normalize

            acl_cfg = config["acl"]["gitlab"]
            collector = GitLabACLCollector(
                gitlab_url=acl_cfg["url"],
                token_env=acl_cfg["token_env"],
                project_id=acl_cfg.get("project_id"),
                project_path=acl_cfg.get("project_path"),
                folder=acl_cfg["folder"],
                file_extensions=acl_cfg.get("file_extensions", [".yaml", ".yml"]),
                ref=config["acl"].get("ref", "main"),
            )
            raw = collector.collect()
            nodes, edges = acl_normalize(raw)
            graph.merge(nodes, edges)
            print(f"[OK] ACL: {len(nodes)} nodes, {len(edges)} edges")
        except Exception as exc:
            print(f"[WARN] ACL collector failed: {exc}")

    # ── 3. Yandex Cloud Security Groups ───────────────────────────────────────
    if "cloud" in config:
        try:
            from collectors.ycloud_sg import YandexCloudSGCollector
            from normalizers.security_groups import normalize as sg_normalize

            cloud_cfg = config["cloud"]
            collector = YandexCloudSGCollector(
                folder_id=cloud_cfg["folder_id"],
                token_env=cloud_cfg["token_env"],
            )
            raw = collector.collect()
            nodes, edges = sg_normalize(raw)
            graph.merge(nodes, edges)
            print(f"[OK] YC SecurityGroups: {len(nodes)} nodes, {len(edges)} edges")
        except Exception as exc:
            print(f"[WARN] YC SG collector failed: {exc}")

    # ── 4. Apply environment filter ───────────────────────────────────────────
    if env_filter:
        graph = graph.filter_by_env(env_filter)
        print(f"[INFO] Filtered to env='{env_filter}': {len(graph.nodes)} nodes, {len(graph.edges)} edges")

    stats = graph.stats()
    print(f"[INFO] Final graph: {stats}")

    # ── 5. Render outputs ────────────────────────────────────────────────────────
    if "html" in formats:
        html = render_html(graph, title=title)
        out_path = output_dir / "diagram.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"[OK] HTML diagram → {out_path}")

    if "json" in formats:
        from src.autoarchitector.generators.html_renderer import _graph_to_json
        json_path = output_dir / "graph.json"
        json_path.write_text(_graph_to_json(graph), encoding="utf-8")
        print(f"[OK] Graph JSON   → {json_path}")

    if "svg" in formats or "mmd" in formats:
        mmd = generate_from_graph(graph, title=title)
        mmd_path = output_dir / "diagram.mmd"
        mmd_path.write_text(mmd, encoding="utf-8")
        print(f"[OK] Mermaid file → {mmd_path}")
