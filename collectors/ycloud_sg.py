"""
collectors/ycloud_sg.py

Collects Yandex Cloud Security Group rules and VM-to-SG attachments.
Requires `yc` CLI to be installed and authenticated.

Config section in config/sources.yaml:

    cloud:
      provider: yandex_cloud
      folder_id: b1gxxxxxxxxxxxxxx
      token_env: YC_IAM_TOKEN    # env var name; set YC_FOLDER_ID too
"""
import json
import os
import subprocess
from typing import Any, Dict, List


class YandexCloudSGCollector:
    """
    Collects Security Groups and VM network interface attachments
    from Yandex Cloud via the `yc` CLI.

    Returns:
        {
            'security_groups': List[dict],    # raw SG objects with rules
            'vm_attachments': Dict[str, dict] # vm_name -> {vm_id, sg_ids, ...}
        }
    """

    def __init__(self, config: Dict[str, Any]):
        cloud_cfg = config.get("cloud", {})
        self.folder_id: str = cloud_cfg.get("folder_id", "")
        # IAM token can also be set via `yc init`; this env var is a CI-friendly override
        self._token: str = os.environ.get(
            cloud_cfg.get("token_env", "YC_IAM_TOKEN"), ""
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _yc(self, *args: str) -> Any:
        """Run a `yc` command and return the parsed JSON response."""
        cmd = ["yc", *args, "--format", "json"]
        if self.folder_id:
            cmd += ["--folder-id", self.folder_id]
        env = os.environ.copy()
        if self._token:
            env["YC_TOKEN"] = self._token
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, env=env
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"yc error ({' '.join(args)}): {result.stderr.strip()}"
            )
        return json.loads(result.stdout) if result.stdout.strip() else []

    # ------------------------------------------------------------------
    # Public collection methods
    # ------------------------------------------------------------------

    def collect_security_groups(self) -> List[Dict[str, Any]]:
        """Return all Security Groups with their rules."""
        groups = self._yc("vpc", "security-group", "list")
        enriched: List[Dict[str, Any]] = []
        for sg in groups:
            try:
                detail = self._yc("vpc", "security-group", "get", sg["id"])
                enriched.append(detail)
            except Exception as exc:  # noqa: BLE001
                print(f"[WARN] Could not fetch SG {sg['id']}: {exc}")
        return enriched

    def collect_vm_sg_attachments(self) -> Dict[str, Dict[str, Any]]:
        """
        Build a mapping: vm_name -> {vm_id, security_group_ids, labels, zone}.
        Security groups are attached at the network interface level.
        """
        vms = self._yc("compute", "instance", "list")
        mapping: Dict[str, Dict[str, Any]] = {}
        for vm in vms:
            sg_ids: List[str] = []
            for iface in vm.get("network_interfaces", []):
                sg_ids.extend(iface.get("security_group_ids", []))
            mapping[vm["name"]] = {
                "vm_id": vm["id"],
                "security_group_ids": sg_ids,
                "labels": vm.get("labels", {}),
                "zone": vm.get("zone_id", ""),
                "source_ref": f"yc:compute/instance:{vm['id']}",
            }
        return mapping

    def collect(self) -> Dict[str, Any]:
        """Main entry point — return combined SG + VM attachment data."""
        return {
            "security_groups": self.collect_security_groups(),
            "vm_attachments": self.collect_vm_sg_attachments(),
        }
