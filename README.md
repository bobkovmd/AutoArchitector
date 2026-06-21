# AutoArchitector

Ежедневный pipeline, который собирает сетевые правила из трёх источников и строит из них единую интерактивную архитектурную схему.

**Источники → единый граф → `diagram.html`**

```
Kubernetes NetworkPolicy  ──┐
GitLab ACL rules          ──┼──▶  InfraGraph  ──▶  diagram.html
Yandex Cloud Security Groups ──┘                    graph.json
                                                    diagram.mmd
```

Результат — самодостаточный HTML-файл с интерактивной Mermaid-схемой, фильтрами по источнику/окружению/тегу и кнопкой скачать `graph.json`.

---

## Как это устроено

### Архитектура pipeline

```
config/sources.yaml
  │
  ├── collectors/
  │     ├── gitlab_networkpolicy.py   читает NetworkPolicy YAML из GitLab API
  │     ├── gitlab_acl.py             читает ACL-файлы из GitLab API
  │     └── ycloud_sg.py              запрашивает Security Groups + VM attachments через yc CLI
  │
  ├── normalizers/
  │     ├── networkpolicy.py          K8s NetworkPolicy  ──┐
  │     ├── acl.py                    ACL rules          ──┼──▶  List[Node] + List[Edge]
  │     └── security_groups.py        YC Security Groups ──┘
  │
  ├── graph/
  │     └── model.py                  Node, Edge, InfraGraph  (canonical model)
  │
  └── src/autoarchitector/
        ├── app.py                    оркестратор: collect → normalize → merge → render
        └── generators/
              ├── mermaid.py          InfraGraph → Mermaid DSL
              └── html_renderer.py   Mermaid + фильтры + dark mode → diagram.html
```

### Канонические модели

Все источники сходятся к двум структурам:

**Node** — узел графа (сервис, VM, БД, очередь, внешняя система):
```python
Node(id="svc:payments", label="payments-service", node_type="service",
     metadata={"environment": "prod", "tags": ["internal"]})
```

**Edge** — направленный поток данных со стрелкой:
```python
Edge(from_id="svc:api-gateway", to_id="svc:payments",
     protocol="TCP", ports=["8080"],
     description="Payment initiation requests",
     source_type="acl", tags=["internal"])
```

`node_type` определяет форму узла на схеме:

| node_type | Форма | Примеры |
|-----------|-------|---------|
| `service` | прямоугольник | microservice, workload |
| `vm` | стадион | YC compute instance |
| `db` | цилиндр | postgres, redis, mongo |
| `queue` | асимметрия | kafka, rabbitmq, sns |
| `external` | шестиугольник | payment gateway, SMTP relay |
| `observability` | стадион | prometheus, grafana |
| `cidr` | прямоугольник | IP-диапазоны из SG |

### Цветовое кодирование стрелок

| Цвет | Источник |
|------|---------|
| 🟦 Teal `#4f98a3` | Kubernetes NetworkPolicy |
| 🟩 Green `#6daa45` | ACL rules |
| 🟨 Gold `#e8af34` | Yandex Cloud Security Groups |

---

## Быстрый старт

### 1. Клонировать и установить зависимости

```bash
git clone https://github.com/bobkovmd/AutoArchitector.git
cd AutoArchitector
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Подготовить конфиг

```bash
cp config/sources.yaml my-sources.yaml
```

Заполни `my-sources.yaml` — пример со всеми полями и комментариями уже есть в `config/sources.yaml`. Минимальный вариант только с ACL:

```yaml
acl:
  gitlab:
    url: https://gitlab.example.com
    token_env: GITLAB_TOKEN        # export GITLAB_TOKEN=glpat-xxxxx
    project_id: 456
    folder: acl/rules
    file_extensions: [.yaml, .yml]
  ref: main

output:
  directory: output/
  formats: [html, json]
  title: "My Infrastructure"
```

### 3. Запустить

```bash
export GITLAB_TOKEN=glpat-xxxxx
python main.py --config my-sources.yaml --output output/
```

Вывод:
```
[OK] ACL: 8 nodes, 10 edges
[INFO] Final graph: {'total_nodes': 8, 'total_edges': 10, ...}
[OK] HTML diagram → output/diagram.html
[OK] Graph JSON   → output/graph.json
```

### 4. Открыть схему

Открой `output/diagram.html` в браузере — схема готова.

---

## Что умеет diagram.html

- **Фильтры** — Source, Environment, Tag, NodeType: выбери любой и граф перестроится
- **Light / Dark mode** — кнопка ☀️/🌙 в хедере
- **Скачать JSON** — кнопка экспортирует полный `graph.json` со всеми узлами и рёбрами
- **Stats bar** — счётчики узлов и рёбер по типам
- **«No match»** — если фильтры дали пустой граф, показывается внятное сообщение

---

## Форматы ACL

ACL-нормализатор поддерживает YAML и JSON. Канонический формат (`examples/acl/rules.yaml`):

```yaml
rules:
  - from: api-gateway
    to: payments-service
    protocol: TCP
    ports: [8080]
    description: "Payment initiation requests"
    environment: prod
    tags: [internal]

  - from: payments-service
    to: billing-db
    protocol: TCP
    ports: [5432]
    description: "Payments write to billing Postgres"
    environment: prod
    tags: [internal, db]
```

Поддерживаются также bare-list и ключи `acl:` / `policies:` вместо `rules:`.

---

## Полный конфиг

```yaml
# Kubernetes NetworkPolicy из GitLab
kubernetes:
  gitlab:
    url: https://gitlab.example.com
    token_env: GITLAB_TOKEN
    project_id: 123                         # или project_path: org/infra-repo
    network_policy_folders:
      - k8s/network-policies/prod
      - k8s/network-policies/staging
  ref: main

# ACL из GitLab
acl:
  gitlab:
    url: https://gitlab.example.com
    token_env: GITLAB_TOKEN
    project_id: 456
    folder: acl/rules
    file_extensions: [.yaml, .yml, .json]
  ref: main

# Yandex Cloud Security Groups
cloud:
  provider: yandex_cloud
  folder_id: b1gxxxxxxxxxxxxxx
  token_env: YC_IAM_TOKEN

# Вывод
output:
  directory: output/
  formats: [html, json, mmd]               # html | json | mmd | svg
  environment_filter: prod                 # null = все окружения
  title: "Infrastructure & Security Diagram"
```

### Переменные окружения

| Переменная | Источник | Описание |
|------------|---------|----------|
| `GITLAB_TOKEN` | GitLab | Personal Access Token, scope: `read_api` |
| `YC_IAM_TOKEN` | Yandex Cloud | IAM-токен (`yc iam create-token`) |

---

## Ежедневный запуск через GitLab CI

Файл `.gitlab-ci.yml` уже готов в репозитории. Запускается каждый день в 06:00 UTC, публикует `diagram.html` в GitLab Pages.

```yaml
# .gitlab-ci.yml (уже в репо)
stages: [collect, publish]

generate-diagram:
  stage: collect
  schedule: "0 6 * * *"
  script:
    - pip install -r requirements.txt
    - python main.py --config config/sources.yaml --output output/
  artifacts:
    paths: [output/]

pages:
  stage: publish
  script: [mv output public]
  artifacts:
    paths: [public]
```

Чтобы включить:
1. В GitLab: `Settings → CI/CD → Variables` — добавь `GITLAB_TOKEN` и `YC_IAM_TOKEN`
2. `Settings → CI/CD → Schedules` — создай расписание `0 6 * * *`
3. Запуши — первый run создаст `diagram.html` в GitLab Pages

---

## Запуск через Docker

```bash
cp config/sources.yaml my-sources.yaml
docker compose up
```

Артефакты появятся в `output/`.

---

## Структура репозитория

```text
AutoArchitector/
├── collectors/
│   ├── gitlab_networkpolicy.py   GitLab API → raw NetworkPolicy files
│   ├── gitlab_acl.py             GitLab API → raw ACL files
│   └── ycloud_sg.py              yc CLI/API → security groups + VM attachments
│
├── normalizers/
│   ├── networkpolicy.py          K8s NetworkPolicy → Node + Edge
│   ├── acl.py                    ACL rules → Node + Edge
│   └── security_groups.py        YC SG rules → Node + Edge
│
├── graph/
│   ├── __init__.py
│   └── model.py                  Node, Edge, InfraGraph (canonical types)
│
├── src/autoarchitector/
│   ├── app.py                    Pipeline orchestrator
│   ├── generators/
│   │   ├── mermaid.py            InfraGraph → Mermaid DSL
│   │   └── html_renderer.py     → diagram.html (self-contained)
│   ├── parsers/
│   │   └── network_policy.py    Legacy K8s parser
│   └── loaders/
│       ├── config_loader.py
│       └── repo_cloner.py
│
├── examples/
│   └── acl/rules.yaml           Canonical ACL format example
│
├── config/
│   └── sources.yaml             Config example (copy → fill → use)
│
├── output/                      Generated artifacts (gitignored)
├── main.py
├── requirements.txt
├── .gitlab-ci.yml               Scheduled daily CI pipeline
└── docker-compose.yml
```

---

## Текущее состояние

**Готово:**
- Collectors: GitLab NetworkPolicy, GitLab ACL, Yandex Cloud SG
- Normalizers: все три источника → canonical Node + Edge
- InfraGraph: merge, filter_by_env, stats
- Renderers: HTML (с фильтрами, dark mode, JSON export), Mermaid DSL, JSON
- Pipeline orchestrator (`app.py`) с graceful degradation
- GitLab CI scheduled pipeline

**Запланировано:**
- AST-извлечение для Java (JavaParser) и TypeScript (ts-morph)
- Sequence diagram по цепочкам controller → service → repository
- Схема БД из Liquibase / Flyway / DDL
- Экспорт в Structurizr / C4
- SVG-рендеринг через mermaid-cli

---

## Принципы

- **Детерминированный**: одинаковый input → одинаковый output, diff-able артефакты в git
- **Graceful degradation**: падение одного источника не ломает остальные
- **Local-first**: запускается на ноутбуке без CI, CI — опционально
- **Источник истины — код**: схема живёт рядом с инфраструктурой, не в Confluence
