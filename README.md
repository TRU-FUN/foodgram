# Foodgram — Продуктовый помощник

## Описание проекта

**Foodgram** — это онлайн‑платформа для публикации и поиска рецептов.
Пользователи могут:

* регистрироваться и авторизоваться;
* добавлять рецепты с ингредиентами и инструкциями;
* просматривать и фильтровать рецепты по тегам;
* сохранять понравившиеся рецепты в избранное;
* скачивать рецепты в PDF.

---

## Ссылки на проект

* Сайт: [https://truhost.hopto.org](https://truhost.hopto.org)

---

## Исходный код

GitHub: [TRU-FUN](https://github.com/TRU-FUN/foodgram)

---

## Технологии

* Python 3.10
* Django 5.1
* Django REST Framework
* PostgreSQL
* Docker и Docker Compose
* Nginx + Gunicorn
* React (frontend)
* GitHub Actions (CI/CD)

---

## Архитектура

* **Backend** — Django + DRF (REST API)
* **Frontend** — React (production build)
* **База данных** — PostgreSQL
* **Хранение медиа** — Docker volumes
* **Веб‑сервер** — Gunicorn + Nginx
* **CI/CD** — GitHub Actions, деплой по SSH

---

## CI/CD

В GitHub Actions настроены следующие шаги:

1. Проверка кода линтером flake8
2. Сборка фронтенда (`npm run build`)
3. Сборка и запуск контейнеров Docker
4. Деплой на сервер через SSH с использованием Docker

Секреты:

* HOST
* USER
* SSH\_KEY
* PASSPHRASE

---

## Запуск через Docker

1. Клонировать репозиторий и перейти в папку проекта:

   ```bash
   git clone git@github.com:TRU-FUN/foodgram.git
   cd foodgram
   ```

2. Создать файл `.env` в директории `infra` со следующими переменными:

   ```
   SECRET_KEY=<ваш секретный ключ Django>
   DEBUG=False
   ALLOWED_HOSTS=127.0.0.1,localhost
   CSRF_TRUSTED_ORIGINS=http://localhost
   POSTGRES_DB=foodgram
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   DB_HOST=db
   DB_PORT=5432
   REACT_APP_API_URL=http://localhost/api/
   ```

3. Запустить контейнеры:

   ```bash
   cd infra
   docker compose up -d --build
   ```

4. Создать суперпользователя:

   ```bash
   docker compose exec backend python manage.py createsuperuser
   ```

5. Открыть в браузере: [http://localhost](http://localhost)

---

## Запуск без Docker

1. Клонировать репозиторий и перейти в папку backend:

   ```bash
   git clone git@github.com:TRU-FUN/foodgram.git
   cd foodgram/backend
   ```

2. Создать и активировать виртуальное окружение:

   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Установить зависимости:

   ```bash
   pip install -r requirements.txt
   ```

4. Провести миграции и загрузить данные:

   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py load_ingredients
   python manage.py load_tags
   python manage.py collectstatic --noinput
   ```

5. Запустить сервер разработки:

   ```bash
   python manage.py runserver
   ```

---

## Документация API

* Swagger UI: [http://localhost/api/docs/](http://localhost/api/docs/)
* Redoc: [http://localhost/api/redoc/](http://localhost/api/redoc/)

---

## Возможности

* Пользователи могут создавать и редактировать рецепты.
* Работают фильтры по тегам и ингредиентам.
* Есть избранное и список покупок.
* Загрузка и отображение изображений через Docker volumes.
* Автоматические тесты и линтинг в CI.
* Автоматический деплой на сервер.