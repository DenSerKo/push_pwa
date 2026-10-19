# Django PWA + Web Push — минимальный демонстрационный проект

Проект показывает полный цикл Web Push для Android:
- Django + PostgreSQL;
- PWA manifest и service worker;
- подписка устройства на Web Push;
- VAPID-ключи;
- защищённая тестовая отправка push из панели после входа;
- кликабельное уведомление открывает сайт.

Это демонстрационный шаблон, не готовая система заказов. В нём каждый вошедший пользователь отправляет тестовое уведомление только на собственные подписанные устройства. Для будущих заказов нужно привязывать событие к конкретному аккаунту и проверять права доступа.

## 1. Локальный запуск (Windows PowerShell)

Требуется Python 3.12+.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py generate_vapid_keys
```

Команда `generate_vapid_keys` выведет три значения. Скопируй их в `.env` или задай в переменных окружения текущего терминала. Django сам не загружает `.env`, поэтому для простоты в PowerShell можно задать значения так:

```powershell
$env:VAPID_PUBLIC_KEY="значение_PUBLIC_KEY"
$env:VAPID_PRIVATE_KEY="значение_PRIVATE_KEY"
$env:VAPID_SUBJECT="mailto:you@example.com"
```

Для локального просмотра сайт можно открыть на `http://127.0.0.1:8000`, но **Web Push требует защищённого контекста**. Исключение — localhost для разработки. Для проверки на телефоне проще задеплоить на Render с HTTPS.

```powershell
python manage.py runserver
```

Открой `http://127.0.0.1:8000`, войди под созданным суперпользователем и попробуй включить уведомления. На телефоне используй публичный HTTPS-адрес Render.

## 2. GitHub

Создай пустой репозиторий на GitHub, затем из папки проекта:

```powershell
git init
git add .
git commit -m "Initial Django PWA Web Push demo"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

Не добавляй в Git реальные VAPID private key, `SECRET_KEY`, пароли или `.env`.

## 3. Render.com — рекомендуемый путь

### Вариант A: Blueprint из `render.yaml`

1. Отправь проект в GitHub.
2. В Render выбери **New + → Blueprint** и подключи репозиторий.
3. Render прочитает `render.yaml`, создаст веб-сервис и PostgreSQL.
4. В настройках веб-сервиса добавь `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` и проверь `VAPID_SUBJECT`.
5. Сгенерируй VAPID-ключи локально командой `python manage.py generate_vapid_keys` и перенеси значения в Render Environment. Публичный ключ и приватный ключ должны быть парой.
6. Нажми Deploy. В build script выполняются `collectstatic` и `migrate`.

> Важно: доступность бесплатного плана PostgreSQL и условия бесплатных сервисов Render меняются. Если Blueprint не позволяет создать базу на выбранном плане, создай PostgreSQL вручную и укажи его Internal Database URL в `DATABASE_URL`.

### Вариант B: вручную

Создай PostgreSQL в Render, затем Web Service из GitHub:
- **Build Command:** `./build.sh`
- **Start Command:** `gunicorn config.wsgi:application`
- **Environment:** `DATABASE_URL` (Internal Database URL), `SECRET_KEY` (случайный секрет), `DEBUG=False`, `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT=mailto:твой-email@example.com`.

Сервис должен использовать Python 3.12 или другую версию, совместимую с зависимостями.

После первого успешного деплоя создай пользователя:
- В Render Shell выполни `python manage.py createsuperuser`.
- Если Shell недоступен на выбранном плане, создай суперпользователя отдельной одноразовой командой/Job или локально подключившись к базе с защищённого окружения. Не добавляй пароль пользователя в репозиторий.

## 4. Проверка на Android

1. Открой `https://ИМЯ-СЕРВИСА.onrender.com` в Chrome на Android.
2. Войди под пользователем, созданным через `createsuperuser`.
3. Нажми **Включить push-уведомления** и разреши уведомления.
4. Нажми **Отправить тестовый push**.
5. Заблокируй телефон или сверни браузер и отправь уведомление снова.
6. По желанию установи PWA через меню Chrome → **Установить приложение** / **Добавить на главный экран**. Для проверки Web Push установка PWA не всегда обязательна в Chrome Android, но нужна для проверки именно установленного приложения.

Если push не приходит, проверь разрешение уведомлений сайта, что VAPID-ключи совпадают, что `VAPID_SUBJECT` — валидный `mailto:` или HTTPS URL, и логи Render. Не проверяй только с открытой вкладкой: для демонстрации доставки сверни Chrome или заблокируй экран.

## 5. Как устроен проект

- `pushdemo/models.py` — push-подписки, связанные с пользователем.
- `pushdemo/views.py` — панель, сохранение/удаление подписки, отправка тестового push.
- `pushdemo/urls.py` — маршруты.
- `pushdemo/management/commands/generate_vapid_keys.py` — генерация VAPID-пары.
- `static/manifest.json` — описание PWA.
- `static/service-worker.js` — обработка push и клика.
- `config/settings.py` — PostgreSQL, WhiteNoise, безопасные настройки Render.

## 6. Важные замечания

- Не публикуй панель отправки в открытом доступе без авторизации. В этом шаблоне она доступна только после входа.
- Браузерная push-подписка — это секретный endpoint с ключами; не выводи его на публичную страницу.
- При `404/410` от push-сервиса подписка удаляется как устаревшая.
- Web Push — best effort: доставка может задерживаться или блокироваться настройками энергосбережения, браузера или сети.
- Уведомления не гарантируют, что пользователь прочитал сообщение. Для критичных заказов храни статус в БД и показывай его в личном кабинете.
- Для реальной коммерческой версии добавь rate limiting, подтверждённые роли, управление несколькими устройствами, обработку повторов и аудит отправок.
