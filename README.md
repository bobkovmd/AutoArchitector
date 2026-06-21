# AutoArchitector

Локальный pipeline для преобразования исходного кода сервисов, Kubernetes NetworkPolicy и метаданных облачной инфраструктуры в архитектурные артефакты:

- sequence flow диаграммы
- архитектурные диаграммы
- модель/схема БД
- сервисно-ресурсная модель / сетевая топология

Репозиторий спроектирован для **локального запуска** — клонируй, настрой и проверь на своей машине, до подключения CI.

---

## Что делает AutoArchitector

Строит детерминированную промежуточную модель из исходных данных и генерирует текстовые артефакты диаграмм.

### Входные данные

- Java-репозитории
- TypeScript-репозитории
- Kubernetes-манифесты: `NetworkPolicy`, `Service`, `Deployment`, `Ingress`
- Директории с миграциями БД (Liquibase, Flyway, DDL) — опционально
- Экспорт инфраструктуры Yandex Cloud или вручную подготовленные данные топологии — опционально

### Результаты

- Mermaid-диаграммы (`.mmd`)
- Нормализованные JSON-индексы
- SVG/PNG — опционально, если установлен mermaid-cli

---

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/bobkovmd/AutoArchitector.git
cd AutoArchitector
```

### 2. Подготовить конфиг

Скопировать пример и заполнить своими данными:

```bash
cp config/sources.example.yaml config/sources.yaml
```

Указать в `config/sources.yaml`:
- ссылки или локальные пути к оригинальным репозиториям сервисов
- репозиторий или директорию с Kubernetes-манифестами
- конкретные файлы или директории с `NetworkPolicy`
- файл экспорта топологии Yandex Cloud

### 3. Запустить локально через Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --config config/sources.yaml --output output/
```

### 4. Опциональный рендеринг SVG

Если установлен Node.js:

```bash
npm install
npm run render
```

### 5. Запуск через Docker Compose

Если Python не настроен локально:

```bash
cp config/sources.example.yaml config/sources.yaml
# отредактировать config/sources.yaml
docker compose up
```

---

## Структура репозитория

```text
AutoArchitector/
  config/
    sources.example.yaml        # пример конфига — скопировать в sources.yaml
  docs/
    architecture.md             # описание архитектуры pipeline
  examples/
    sample-networkpolicy.yaml   # пример NetworkPolicy
    sample-topology.json        # пример топологии Yandex Cloud
  output/                       # сюда попадают сгенерированные артефакты
  src/
    autoarchitector/
      loaders/                  # загрузка конфига
      parsers/                  # парсинг репозиториев и NetworkPolicy
      generators/               # генерация Mermaid
  main.py
  requirements.txt
  package.json
  docker-compose.yml
```

---

## Пример конфига

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
    - ../platform/k8s/network-policies/test
    - ../platform/k8s/network-policies/demo
    - ../platform/k8s/network-policies/prod
cloud:
  provider: yandex_cloud
  topology_file: ./examples/sample-topology.json
output:
  render_svg: false
```

### Поля конфига

| Поле | Описание |
|---|---|
| `repositories[].name` | Произвольное имя сервиса |
| `repositories[].type` | `java` или `typescript` |
| `repositories[].path` | Локальный путь к checkout |
| `repositories[].origin` | URL оригинального репозитория (для документации) |
| `kubernetes.manifests_path` | Директория с Kubernetes-манифестами |
| `kubernetes.network_policies` | Список директорий или файлов с NetworkPolicy |
| `cloud.provider` | Провайдер: `yandex_cloud` |
| `cloud.topology_file` | Путь к JSON/YAML экспорту топологии |
| `output.render_svg` | `true` — генерировать SVG через mermaid-cli |

---

## Как подготовить оригинальные данные

AutoArchitector ожидает, что ты укажешь ссылки/пути к исходным данным в `config/sources.yaml`.

**Рекомендуемый подход:**

1. Склонируй все оригинальные репозитории сервисов рядом с AutoArchitector
2. Укажи в конфиге локальные пути (`../service-a`, `../platform/k8s` и т.д.)
3. Запусти парсер локально
4. Проверь артефакты в `output/`
5. После проверки — подключи к CI

**Для NetworkPolicy:**
- укажи директории по окружениям: `test`, `demo`, `prod` — каждую отдельной строкой
- файлы могут быть вложены произвольно — парсер обходит рекурсивно

**Для Yandex Cloud:**
- экспортируй инвентарь ресурсов (VM, ALB, VPC, PostgreSQL и т.д.) в JSON или YAML
- положи файл рядом с репозиторием и укажи путь в `cloud.topology_file`
- пример структуры — в `examples/sample-topology.json`

---

## Текущее состояние

MVP-scaffold, работает локально.

**Реализовано:**
- загрузка конфига
- инвентаризация Java/TypeScript-репозиториев
- парсер Kubernetes NetworkPolicy
- объединённая промежуточная модель
- генерация Mermaid: граф сервисов и сетевая топология

**Запланировано:**
- AST-извлечение для Java (JavaParser) и TypeScript (ts-morph)
- sequence diagram по цепочкам вызовов controller → service → repository
- извлечение схемы БД из Liquibase / Flyway / DDL
- загрузчик Yandex Cloud API / Terraform state
- экспорт в формат Structurizr / C4

---

## Заметки

- Репозиторий намеренно local-first и детерминированный: одинаковый код всегда даёт одинаковые байты в выходных файлах.
- Текстовые артефакты генерируются всегда; рендеринг изображений — опционально.
- Оригинальные репозитории могут оставаться приватными — AutoArchitector работает с локальными checkout.
