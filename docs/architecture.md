# AutoArchitector architecture

AutoArchitector is organized as a deterministic transformation pipeline.

## Stages

1. Load source configuration.
2. Inspect local repositories and build a normalized inventory.
3. Parse Kubernetes NetworkPolicy manifests.
4. Merge source data into one intermediate model.
5. Generate Mermaid diagrams.
6. Optionally render SVG with mermaid-cli.

## Intended next integrations

- JavaParser / ts-morph based AST extraction
- Liquibase / Flyway schema extraction
- Yandex Cloud inventory/API loader
- Structurizr exporter
