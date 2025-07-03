# 🍲 Foodgram — Продуктовый помощник

## 🔍 Описание проекта

**Foodgram** — это онлайн-платформа для публикации и поиска рецептов.  
Пользователи могут:

- создавать рецепты;
- добавлять их в избранное;
- формировать список покупок;
- подписываться на других авторов;
- загружать аватар;
- скачивать список покупок в PDF.

---

## 🌐 Продакшен

Проект развернут на сервере:  
🔗 **https://truhost.hopto.org**

---

## 👤 Автор

**Даниил Труфанов**  
GitHub: [TRU-FUN](https://github.com/TRU-FUN)

---

## 🛠️ Стек технологий

- Python 3.10
- Django 5.1
- Django REST Framework
- PostgreSQL
- Docker / Docker Compose
- Nginx + Gunicorn
- React (frontend)
- GitHub Actions (CI/CD)

---

## 🧽 Архитектура

- **Backend** — Django + DRF (API)
- **Frontend** — React (c копированием build на сервер)
- **DB** — PostgreSQL
- **Media** — в volumes
- **Web** — Gunicorn + Nginx
- **CI/CD** — GitHub Actions, SSH-доступ

---

## ⚙️ CI/CD

Автодеплой через **GitHub Actions**:

- 🔎 прогон `flake8`
- ⚡️ сборка React frontend (`npm run build`)
- 📁 копирование build на сервер
- 🐳 перезапуск Docker-контейнеров

**Secrets**:
- `HOST`, `USER`, `SSH_KEY`, `PASSPHRASE`

---

## 📦 Docker развертывание

### 1. Клонирование
```bash
git clone git@github.com:TRU-FUN/foodgram.git
cd foodgram
```

### 2. Основные переменные `.env`

**infra/.env**
```env
SECRET_KEY=секретный_ключ_django
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

### 3. Собрать и запустить
```bash
cd infra
docker compose up -d --build
```

### 4. Суперюзер
```bash
docker compose exec backend python manage.py createsuperuser
```

### 5. Открыть: [http://localhost](http://localhost)

---

## ⚒️ Запуск без Docker

```bash
git clone git@github.com:TRU-FUN/foodgram.git
cd foodgram/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Миграции и статика
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py load_ingredients
python manage.py load_tags
python manage.py collectstatic --noinput
python manage.py runserver
```

---

## 📙 API документация

- Swagger UI: [http://localhost/api/docs/](http://localhost/api/docs/)
- Redoc (если есть): [http://localhost/api/redoc/](http://localhost/api/redoc/)

---

## ✅ Функции

- Регистрация и логин
- Управление рецептами и ингредиентами
- Списки покупок и избранное
- Подписки на авторов
- Аватар и его обновление
- Фильтрация и поиск

---

**⬆ Готово к продакшен-деплою!**