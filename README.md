# Система аренды и бронирования жилья

Back-end приложение на базе REST-архитектуры для управления объявлениями об аренде недвижимости в Германии, бронирования, сбора отзывов и автоматизированной аналитики тональности с использованием LLM.

---

## 1. Технологический стек

* **Язык и среда выполнения:** Python 3.14.3
* **Фреймворк:** Django 6.1, Django REST Framework 3.18
* **Пакетный менеджер:** `uv`
* **База данных:** SQLite 3 (проектирование в 3НФ с учетом особенностей планировщика запросов и регистронезависимого поиска)
* **Аутентификация и безопасность:** `djangorestframework-simplejwt` (JWT с ротацией токенов и `token_blacklist`), ролевая модель на базе стандартных групп Django (`Group`)
* **Документация API:** `drf-spectacular` (Swagger UI / ReDoc / OpenAPI 3.0)
* **ИИ-интеграция:** `langchain`, `langchain-core`, `langchain-google-genai` (с поддержкой резервного переключения провайдеров)
* **Тестирование и генерация данных:** `pytest` / Django `TestCase`, `Faker`

---

## 2. Настройка переменных окружения (`.env`)

Все конфиденциальные данные и параметры среды хранятся в файле `.env` в корне репозитория (файл исключен из системы контроля версий через `.gitignore`).

1. Создайте рабочий файл конфигурации на основе шаблона:
   ```bash
   cp .env_example .env
   ```
2. Заполните переменные в файле `.env`:

```env
# --- Базовые настройки Django ---
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# --- Настройки базы данных ---
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# --- Настройки JWT (SimpleJWT) ---
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=15
JWT_REFRESH_TOKEN_LIFETIME_DAYS=30

# --- Настройки почтового сервиса (Email) ---
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@example.com
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=noreply@example.com

# --- Настройки LLM-провайдеров (LangChain) ---
PRIMARY_LLM_PROVIDER=google
FALLBACK_LLM_PROVIDER=openai
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key
LLM_TIMEOUT_SECONDS=15
```

---

## 3. Локальный запуск проекта через `uv`

### Предварительные требования
Убедитесь, что менеджер пакетов `uv` установлен в системе (проверка: `uv --version`). При необходимости установите его:
```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Пошаговая инструкция

1. **Клонирование репозитория и переход в директорию проекта:**
   ```bash
   git clone <repository-url>
   cd rental_system
   ```

2. **Создание виртуального окружения с Python 3.14 и синхронизация зависимостей:**
   ```bash
   uv venv --python 3.14
   uv sync
   ```

3. **Активация виртуального окружения:**
   ```bash
   # Windows (CMD / PowerShell)
   .venv\Scripts\activate

   # Linux / macOS
   source .venv/bin/activate
   ```

4. **Применение миграций базы данных:**
   ```bash
   uv run python manage.py migrate
   ```

5. **Создание суперпользователя:**
   ```bash
   uv run python manage.py createsuperuser
   ```

6. **Заполнение базы тестовыми данными (опционально):**
   ```bash
   uv run python manage.py seed_rental
   uv run python manage.py seed_rental --clear
   ```

7. **Запуск сервера разработки:**
   ```bash
   uv run python manage.py runserver
   ```

8. **Доступ к документации API (после запуска сервера):**
   * Swagger UI: `http://127.0.0.1:8000/api/v1/docs/`
   * ReDoc: `http://127.0.0.1:8000/api/v1/schema/redoc/`
   * Схема OpenAPI: `http://127.0.0.1:8000/api/v1/schema/`

9. **Запуск тестов:**
   ```bash
   uv run python manage.py test
   ```

---

## 4. Структура репозитория

```text
rental_system/
├── config/                     # Конфигурация проекта (settings, urls, asgi, wsgi)
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/                       # Пакет всех прикладных модулей
│   ├── __init__.py
│   ├── urls.py                 # Единая точка маршрутизации API (/api/v1/...)
│   ├── core/                   # Базовые абстракции, константы, менеджеры, исключения
│   │   ├── __init__.py
│   │   ├── constants.py        # Бизнес-константы (горизонт 360 дней, дедлайны)
│   │   ├── exceptions.py       # Кастомные исключения и обработчик ошибок DRF
│   │   ├── managers.py         # Менеджеры для фильтрации Soft Delete
│   │   └── models.py           # Абстрактные модели (TimeStampedModel, SoftDeleteModel)
│   ├── accounts/               # Пользователи и JWT-аутентификация
│   │   ├── migrations/
│   │   ├── models/
│   │   ├── serializers/
│   │   ├── services/
│   │   ├── views/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   └── urls.py
│   ├── listings/               # Объявления, адреса, история просмотров и поиска
│   │   ├── migrations/
│   │   ├── models/
│   │   ├── serializers/
│   │   ├── filters/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── views/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   └── urls.py
│   ├── bookings/               # Бронирования и контроль пересечения дат
│   │   ├── migrations/
│   │   ├── models/
│   │   ├── serializers/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── views/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   └── urls.py
│   ├── reviews/                # Отзывы и рейтинги
│   │   ├── migrations/
│   │   ├── models/
│   │   ├── serializers/
│   │   ├── services/
│   │   ├── views/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   └── urls.py
│   └── analytics/              # Интеграция LangChain, анализ тональности и автоответы
│       ├── migrations/
│       ├── models/
│       ├── prompts/
│       ├── services/
│       ├── admin.py
│       └── apps.py
├── tests/                      # Модульные и интеграционные тесты
├── .env                        # Приватные переменные окружения (в .gitignore)
├── .env_example                # Шаблон переменных окружения
├── .gitignore
├── manage.py
├── pyproject.toml              # Конфигурация зависимостей для uv
└── uv.lock                     # Lock-файл зависимостей
```

---

## 5. Архитектура базы данных (3НФ)

Схема базы данных спроектирована в соответствии с требованиями **3-й нормальной формы (3НФ)**:

1. **Первая нормальная форма (1НФ — атомарность):**
   * Все поля таблиц содержат атомарные значения.
   * Почтовый адрес декомпозирован на отдельные атрибуты: федеральная земля (`federal_state`), город (`city`), район (`district`), почтовый индекс (`postal_code`), улица (`street`), номер дома (`house_number`) и номер квартиры (`apartment_number`).

2. **Вторая нормальная форма (2НФ — отсутствие частичных зависимостей):**
   * Все сущности используют суррогатные первичные ключи (`id`), от которых полностью зависят все неключевые атрибуты.

3. **Третья нормальная форма (3НФ — отсутствие транзитивных зависимостей):**
   * **Выделение сущности `Address` (`listings_addresses`):** Исключает дублирование связки «почтовый индекс — город — федеральная земля» и сохраняет привязку истории отзывов к физическому объекту недвижимости при пересоздании объявления (соблюдение требований по прозрачности истории объекта и GDPR).
   * **Отсутствие денормализованных агрегатов:** Средний рейтинг, количество просмотров и количество отзывов не хранятся в столбцах таблицы `listings_listings`, а вычисляются динамически через `Subquery` и `annotate()` в ORM.
   * **Разделение отзывов и ИИ-аналитики:** Результаты анализа тональности и генерации промокодов вынесены в отдельную таблицу `analytics_review_analyses` (связь `OneToOne` с `reviews_reviews`).

4. **Целостность исторических данных и Soft Delete:**
   * Для исторически значимых внешних ключей (`Booking.listing`, `Booking.tenant`, `Review.booking`, `Listing.landlord`) установлено ограничение `on_delete=models.PROTECT`.
   * Удаление пользователей, адресов, объявлений, бронирований и отзывов выполняется через механизм мягкого удаления (`is_deleted`, `deleted_at`) с переопределением менеджера по умолчанию (`objects`) и сохранением доступа ко всем записям через `all_objects`.

---

## 6. Особенности SQLite и стратегия индексации

### Учет ограничений SQLite
* **Регистронезависимый поиск (`icontains`):** Стандартный оператор `LIKE` в SQLite выполняет регистронезависимое сравнение только для символов ASCII. Для корректной фильтрации по немецким умлаутам (`ä, ö, ü, ß`) и кириллице на уровне подключения БД (сигнал `connection_created`) переопределяется SQL-функция `LOWER()` с использованием `str.lower()` Python, а поисковые запросы нормализуются перед сохранением в `listings_search_queries`.
* **Контроль пересечения дат без `ExclusionConstraint`:** Поскольку SQLite не поддерживает исключающие ограничения на диапазоны дат (`btree_gist`), защита от двойного бронирования (race condition) реализована на трех уровнях:
  1. Проверка валидатором сериализатора DRF.
  2. Выполнение операции создания/подтверждения бронирования внутри атомарной транзакции (`transaction.atomic()`) с блокировкой записи.
  3. Составной индекс по интервалам дат для быстрого поиска конфликтующих записей.

### Составные индексы и ограничения

| Таблица | Индекс / Ограничение | Поля | Назначение |
| :--- | :--- | :--- | :--- |
| `accounts_users` | `idx_user_email_active` | `(email, is_active)` | Ускорение аутентификации по email |
| `listings_addresses` | `uq_active_property_address` (`UniqueConstraint`) | `(postal_code, city, street, house_number, apartment_number)` при `is_deleted=False` | Запрет дублирования активных объектов недвижимости по одному адресу |
| `listings_addresses` | `idx_addr_city_state` | `(city, federal_state)` | Фильтрация по городу и федеральной земле |
| `listings_addresses` | `idx_addr_city_district` | `(city, district)` | Фильтрация по району города |
| `listings_listings` | `idx_lst_act_price` | `(is_active, is_deleted, price)` | Базовая выборка активных объявлений с фильтрацией и сортировкой по цене |
| `listings_listings` | `idx_lst_act_specs` | `(is_active, is_deleted, rooms_count, property_type)` | Фильтрация по количеству комнат и типу жилья |
| `listings_listings` | `idx_lst_act_created` | `(is_active, is_deleted, -created_at)` | Сортировка ленты объявлений по новизне |
| `listings_listings` | `idx_lst_landlord` | `(landlord_id, is_deleted)` | Выборка объектов конкретного арендодателя |
| `listings_search_queries` | `idx_search_norm_created` | `(normalized_query, -created_at)` | Агрегация популярных поисковых запросов |
| `listings_listing_views` | `idx_view_listing_time` | `(listing_id, -viewed_at)` | Подсчет просмотров объявления и сортировка по популярности |
| `bookings_bookings` | `chk_booking_checkout_after_checkin` (`CheckConstraint`) | `check_out > check_in` | Гарантия корректности интервала дат на уровне БД |
| `bookings_bookings` | `idx_bkg_overlap_lookup` | `(listing_id, status, check_in, check_out)` | Поиск пересечений дат бронирования |
| `bookings_bookings` | `idx_bkg_tenant_status` | `(tenant_id, status, -check_in)` | Просмотр активных и завершенных бронирований арендатора |
| `reviews_reviews` | `idx_rev_listing_created` | `(listing_id, is_deleted, -created_at)` | Выборка отзывов по объявлению |
| `analytics_review_analyses` | `idx_sent_label_status` | `(sentiment, action_status)` | Мониторинг статусов ИИ-обработки и отправки писем |

---

## 7. Поиск, фильтрация и сортировка в DRF

| Параметр запроса | Реализация на уровне DRF / ORM | Используемый индекс БД |
| :--- | :--- | :--- |
| `?search=<текст>` | Фильтрация по `Q(title__icontains=q) \| Q(description__icontains=q)` с записью нормализованного запроса в `SearchQueryHistory` | `idx_lst_act_created` (предварительная фильтрация активных записей) |
| `?min_price=&max_price=` | `NumberFilter` (`price__gte`, `price__lte`) | `idx_lst_act_price` |
| `?city=&district=&federal_state=` | `CharFilter` (`icontains` по полям `address`) / `ChoiceFilter` | `idx_addr_city_state`, `idx_addr_city_district` |
| `?min_rooms=&max_rooms=` | `NumberFilter` (`rooms_count__gte`, `rooms_count__lte`) | `idx_lst_act_specs` |
| `?property_type=` | `ChoiceFilter` по `PropertyType.choices` | `idx_lst_act_specs` |
| `?ordering=price` / `-price` | `OrderingFilter` | `idx_lst_act_price` |
| `?ordering=created_at` / `-created_at` | `OrderingFilter` | `idx_lst_act_created` |
| `?ordering=popularity_views` | Аннотация через `Subquery` по `ListingViewHistory` (исключает дублирование строк при join) | `idx_view_listing_time` |
| `?ordering=popularity_reviews` | Аннотация через `Subquery` по `Review` (`is_deleted=False`) | `idx_rev_listing_created` |

---

## 8. Бизнес-константы (`apps/core/constants.py`)

* `MAX_BOOKING_HORIZON_DAYS = 360` — максимальный горизонт бронирования вперед от текущей даты.
* `CANCELLATION_DEADLINE_HOURS = 48` — минимальное время до даты заезда, при котором арендатор может отменить бронирование.
* `REVIEW_SUBMISSION_WINDOW_DAYS = 30` — срок после даты выезда (`check_out`), в течение которого арендатор имеет право оставить отзыв.
* `MIN_LISTING_PRICE = 1.00` / `MAX_LISTING_PRICE = 100000.00` — допустимый диапазон стоимости проживания за ночь (EUR).
* `MIN_RATING_VALUE = 1` / `MAX_RATING_VALUE = 5` — шкала оценки в отзывах.
