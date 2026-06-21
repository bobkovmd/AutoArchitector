# AutoArchitector

Local-first pipeline for transforming service source code, Kubernetes NetworkPolicy, and cloud/network metadata into architecture artifacts:

- sequence flows
- architecture diagrams
- DB model/schema views
- service-resource / network topology maps

The repo is designed to run **locally first** so you can clone it and try the flow on your workstation before wiring CI.

## What it does

AutoArchitector builds a deterministic intermediate model from input sources and renders text-based diagram artifacts.

### Inputs

- Java repositories
- TypeScript repositories
- Kubernetes manifests, especially `NetworkPolicy`, `Service`, `Deployment`, `Ingress`
- optional DB metadata / migration directories
- optional Yandex Cloud inventory exports or manually prepared topology data

### Outputs

- Mermaid diagrams (`.mmd`)
- normalized JSON index files
- optional SVG/PNG if mermaid-cli is installed

---

## Local quick start

### 1. Clone

```bash
git clone https://github.com/bobkovmd/AutoArchitector.git
cd AutoArchitector
```

### 2. Prepare source links

Edit `config/sources.example.yaml` and save your real config as `config/sources.yaml`.

Put there links or local paths to:
- original service repositories
- Kubernetes repo / manifests directory
- NetworkPolicy files
- Yandex Cloud exported inventory files

### 3. Run locally with Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --config config/sources.yaml --output output/
```

### 4. Optional SVG rendering

If Node.js is installed:

```bash
npm install
npm run render
```

---

## Repository layout

```text
AutoArchitector/
  config/
    sources.example.yaml
  docs/
    architecture.md
  examples/
    sample-networkpolicy.yaml
    sample-topology.json
  output/
  src/
    autoarchitector/
      loaders/
      parsers/
      generators/
      model/
  main.py
  requirements.txt
  package.json
  docker-compose.yml
```

---

## Configuration

Example config:

```yaml
project_name: my-landscape
repositories:
  - name: service-a
    type: java
    path: ../service-a
    origin: https://github.com/your-org/service-a
  - name: service-b
    type: typescript
    path: ../service-b
    origin: https://github.com/your-org/service-b
kubernetes:
  manifests_path: ../platform/k8s
  network_policies:
    - ../platform/k8s/network-policies/prod
    - ../platform/k8s/network-policies/demo
cloud:
  provider: yandex_cloud
  topology_file: ./examples/sample-topology.json
output:
  render_svg: false
```

---

## Original sources to provide

The project expects you to supply references to the original sources in `config/sources.yaml`:

- service repo URLs or local checkout paths
- repo or folder containing Kubernetes manifests
- exact directories/files with `NetworkPolicy`
- Yandex Cloud topology export, for example VM/network/load balancer inventory in JSON/YAML

Recommended approach:

1. clone all original repos locally side by side;
2. point AutoArchitector config to local paths;
3. run parser locally;
4. inspect `output/` artifacts;
5. then move to CI.

---

## Current status

This is a **local MVP scaffold**.

Implemented:
- config loading
- Java/TypeScript source inventory
- Kubernetes NetworkPolicy parser
- topology merge model
- Mermaid generation for service graph and network graph

Planned next:
- deeper AST extraction for Java and TS
- DB schema extraction from Liquibase/Flyway/DDL
- Yandex Cloud API loader
- Structurizr/C4 export
- sequence diagram generation from controller/service call chains

---

## Notes

- The repo is intentionally local-first and deterministic.
- Text artifacts are generated first; image rendering is optional.
- You can keep original repos private and only point to local paths.
