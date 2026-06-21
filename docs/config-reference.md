# Справочник по конфигурации sources.yaml

`config/sources.yaml` — **единая точка правды** для всех источников данных AutoArchitector.  
Все репозитории, NetworkPolicy, ACL и Yandex Cloud описываются здесь.

---

## Разделы конфига

### `repositories[]` — сервисные репозитории

| Поле | Обязательно | Описание |
|---|---|---|
| `name` | ✅ | Произвольное имя сервиса |
| `type` | ✅ | `java` или `typescript` |
| `origin` | ✅ | URL оригинального репозитория (GitHub/GitLab) |
| `branch` | — | Ветка (по умолчанию `main`) |
| `path` | ✅ | Локальный путь для checkout |
| `enabled` | — | `true`/`false` (по умолчанию `true`) |

---

### `kubernetes` — K8s-манифесты и NetworkPolicy

| Поле | Описание |
|---|---|
| `manifests_path` | Директория с общими K8s-манифестами |
| `network_policy_repos[]` | Отдельные репо с NetworkPolicy — структура как у `repositories[]` |
| `network_policies.test/demo/prod` | Списки директорий с NetworkPolicy по окружениям |

---

### `access_control` — GitLab ACL / RBAC

| Поле | Описание |
|---|---|
| `repos[]` | Репозитории с ACL-манифестами — структура как у `repositories[]` |
| `policies.test/demo/prod` | Директории с политиками по окружениям |

---

### `cloud` — Yandex Cloud

| Поле | Описание |
|---|---|
| `provider` | Провайдер: `yandex_cloud` |
| `topology_file` | JSON-экспорт всех ресурсов фолдера |
| `network_groups_file` | JSON-экспорт security groups |
| `networks_file` | JSON-экспорт VPC и подсетей |
| `terraform_state_file` | Terraform state (опционально) |

---

### `output` — параметры генерации

| Поле | Описание |
|---|---|
| `render_svg` | `true` — рендерить SVG через mermaid-cli |
| `formats` | Список форматов: `mermaid`, `json` |

---

## Как получить данные из Yandex Cloud

```bash
# Топология всех ресурсов
yc resource-manager folder list-resources --folder-id <FOLDER_ID> --format json > inputs/yandex-cloud-topology.json

# Security groups (network groups)
yc vpc security-group list --folder-id <FOLDER_ID> --format json > inputs/yandex-cloud-security-groups.json

# VPC и подсети
yc vpc network list --folder-id <FOLDER_ID> --format json > inputs/yandex-cloud-networks.json
yc vpc subnet list --folder-id <FOLDER_ID> --format json >> inputs/yandex-cloud-networks.json
```

---

## CLI-команды

```bash
# Склонировать / обновить все репозитории из конфига
python main.py --config config/sources.yaml --clone-repos

# Только генерация артефактов (репо уже склонированы)
python main.py --config config/sources.yaml --output output/

# Полный прогон: клонировать + сгенерировать
python main.py --config config/sources.yaml --clone-repos --output output/
```

---

## Принцип работы с несколькими репо

1. Все репо описаны в `repositories[]`, `kubernetes.network_policy_repos[]`, `access_control.repos[]`.
2. `--clone-repos` обходит **все три секции** и клонирует/обновляет каждый репо.
3. Основной `run` использует уже локальные `path` для парсинга.
4. Каждое окружение (`test`, `demo`, `prod`) получает свой набор диаграмм в `output/<env>/`.
