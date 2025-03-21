# Мониторинг остатков товаров на маркетплейсе с использованием Apache Airflow и ClickHouse
📊 Автоматизированный мониторинг остатков товаров на маркетплейсе.
Проект собирает, анализирует и визуализирует данные о динамике продаж, используя Apache Airflow и ClickHouse

## Основные функции проекта:
- Автоматический сбор данных об остатках товаров по 10 артикулам с маркетплейса посредством Python-скриптов
- Автоматический запуск DAG'а в Apache Airflow каждый день в 23:00 МСК
- Сохранение остатков товаров в базе данных (ClickHouse)
- Построение витрины динамики продаж на основе изменения остатков

## Технологии
- **Apache Airflow** – управление DAG'ами для автоматического сбора данных.  
- **ClickHouse** – высокопроизводительное хранилище данных для аналитики.  
- **Postgres 13** – база для хранения метаданных Apache Airflow.  
- **Redis** – брокер сообщений для CeleryExecutor в Airflow.  
- **Docker, Docker Compose** – контейнеризация всех сервисов.  
- **Python, SQL** – парсинг данных и аналитика.  
- **DBeaver** – управление ClickHouse через SQL-запросы.  
- **Git и GitHub** – контроль версий.

# Технические детали
 Основным процессом данного проекта является корректный deploying необходимых сервисов. Ниже приведены ключевые моменты (конфигурацинный файл docker-compose.yml доступен для просмотора в репозитории)
- ##  Airflow: 
Вместо SequentialExecutor используется CeleryExecutor, который требует PostgreSQL (хранение метаданных) и Redis (брокер очередей)
### Основные сервисы Airflow:
- **airflow-init** – настройка БД и миграция данных
- **airflow-scheduler** – обработка DAG'ов
- **airflow-triggerer** – обработка асинхронных триггеров
- **airflow-webserver** – веб-интерфейс (8080:8080)
- **airflow-worker** – воркеры, выполняющие задачи


![Reference Image](/images/основные_сервисы_airflow.png)

📌Важно: 

Airflow использует:

- AIRFLOW__CORE__EXECUTOR=CeleryExecutor – для параллельного выполнения задач
- AIRFLOW__DATABASE__SQL_ALCHEMY_CONN – подключение к PostgreSQL
- AIRFLOW__CELERY__BROKER_URL=redis://:@redis:6379/0 – брокер сообщений Redis

### Основные настройки Airflow:
- Массовое использование переменных через **x-airflow-common** (шаблон с переменными окружения, которые переиспользуются в сервисах).
- build: . → Собственная сборка Docker-образа вместо стандартного apache/airflow:2.10.5
- **PostgreSQL** + **Redis** в качестве бэкенда для CeleryExecutor.
Автоматическое создание БД, миграции и админ-юзера в **airflow-init**

![Reference Image](/images/x-airflow-common.png)

- ## ClickHouse с оптимизированными параметрами:
    ClickHouse развернут с оптимизированными ресурсами для стабильной работы.
### Ключевые настройки:
#### Ограничение памяти
``` yaml
deploy:
  resources:
    limits:
      memory: 10G  
    reservations:
      memory: 2G  
```
- Ограничивает максимальную потребляемую память 10 ГБ
- Гарантирует резерв 2 ГБ для стабильности работы

#### Настройки кеша и потоков:
``` yaml
environment:
  MAX_MEMORY_USAGE: 8589934592  # 8 ГБ
  MAX_BYTES_BEFORE_EXTERNAL_SORT: 4294967296  # 4 ГБ
  MAX_BYTES_BEFORE_EXTERNAL_GROUP_BY: 4294967296  # 4 ГБ
  MAX_THREADS: 4  # 4 потока на запрос
  MARK_CACHE_SIZE: 536870912  # 512 МБ кэш индексов
  UNCOMPRESSED_CACHE_SIZE: 536870912  # 512 МБ кэш нежатых данных
```
- Ограничивает использование памяти (8 ГБ)
- Уменьшает нагрузку на дисковый ввод-вывод за счет кеширования
- Разрешает до 4 потоков на запрос для многопоточной обработки данных
#### Подключенные тома:
``` yaml
volumes:
  - clickhouse_data:/var/lib/clickhouse
  - ./clickhouse_tmp:/var/lib/clickhouse/tmp
```
📌Важно: 
- **ClickHouse** не требует брокера сообщений и может работать автономно
- **MAX_THREADS=4** важно для серверов с ограниченным количеством ядер
 - **PostgreSQL** + **Redis** в качестве бэкенда для Airflow

 - ##  PostgreSQL (Postgres 13):
- Используется для хранения метаданных **Airflow**
- Автоматически инициализируется с **airflow:airflow** в качестве логина и пароля
``` yaml
services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    volumes:
      - postgres-db-volume:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "airflow"]
      interval: 10s
      retries: 5
      start_period: 5s
    restart: always
```
✅ Добавлен healthcheck – Airflow не стартует, пока Postgres не готов

 - ## Redis (7.2-bookworm):
- Брокер сообщений для Celery
``` yaml
services:
  redis:
    image: redis:7.2-bookworm
    expose:
      - 6379
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 30s
      retries: 50
      start_period: 30s
    restart: always
```
✅ Добавлен healthcheck – Airflow не стартует, пока Redis не готов

 - ## Airflow Init – автоматическая инициализация
    При первом запуске:
- Создает каталоги /sources/logs, /sources/dags, /sources/plugins/, /sources/projects
- Настраивает права доступа
- Запускает миграции и создает админ-аккаунт Airflow
``` yaml
airflow-init:
  <<: *airflow-common
  entrypoint: /bin/bash
  command:
    - -c
    - |
      projects/wildberries
      chown -R "${AIRFLOW_UID}:0" /sources/{logs,dags,plugins,projects}
      exec /entrypoint airflow version
```
- ## Healthchecks – автоматическая проверка состояния сервисов
    Все критически важные сервисы (Postgres, Redis, Airflow) имеют healthcheck, чтобы гарантировать, что они стартуют в правильном порядке.
- ### Airflow Webserver:
``` yaml
healthcheck:
  test: ["CMD", "curl", "--fail", "http://localhost:8080/health"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 30s
```
- ### Airflow Scheduler:
``` yaml
healthcheck:
  test: ["CMD", "curl", "--fail", "http://localhost:8974/health"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 30s
```
✅  Гарантирует, что сервисы Airflow не стартуют, пока зависимости не готовы

- ## Flower – мониторинг Celery
Flower (port 5555) добавлен как опциональный сервис:
``` yaml
flower:
  <<: *airflow-common
  command: celery flower
  profiles:
    - flower
  ports:
    - "5555:5555"
  healthcheck:
    test: ["CMD", "curl", "--fail", "http://localhost:5555/"]
    interval: 30s
    timeout: 10s
    retries: 5
    start_period: 30s
  restart: always
```
✅Позволяет отслеживать статус воркеров Celery.

## 💾 Как PostgreSQL используется в этом проекте?  

PostgreSQL не используется для хранения самих остатков товаров — эти данные сохраняются в ClickHouse.  
Однако, он играет ключевую роль в работе Airflow:  

📌 **Что хранится в PostgreSQL?**  
-  **Метаданные Airflow** (DAG'и, статусы задач, логи выполнения). 
-  **Параметры запусков DAG'ов** (execution_date, параметры конфигурации)
-  **История выполнения задач** (успешные, упавшие и ретраи)
-  **Пользователи и доступы** (если используется Airflow UI) 

📌 **Почему PostgreSQL?**  
- Позволяет хранить историю выполнения DAG'ов  
- Нужен для работы CeleryExecutor (управление задачами между воркерами)
- Обеспечивает отказоустойчивость (даже если Airflow перезапустится, метаданные сохраняются)

➡ **Вывод:** PostgreSQL — это "мозг" Apache Airflow, а ClickHouse используется для аналитики.  

## Данная конфигурация сборки сервисов обеспечивает: 
- ✅ Оптимизированный деплой Apache Airflow с Celery.
- ✅ ClickHouse с ограничением ресурсов и кешированием.
- ✅ PostgreSQL + Redis для хранения метаданных и работы Celery.
- ✅ Healthchecks для сервисов → Airflow не стартует, пока Postgres и Redis не готовы.
- ✅ Автоматическая инициализация (airflow-init) → минимальная ручная настройка.

Это готовое решение для продакшн-инфраструктуры, которое легко адаптировать под свои нужды.

## 📌 Итог
✔ **Полностью автоматизированный сбор данных**  
✔ **ClickHouse с оптимизированным кешем и потоками**  
✔ **Airflow + Celery для параллельных вычислений**  
✔ **Healthchecks — сервисы стартуют в нужном порядке**  
✔ **Минимальная ручная настройка — всё работает "из коробки"** 