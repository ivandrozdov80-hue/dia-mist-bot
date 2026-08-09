# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## О проекте

VK-бот («Джинн Dia Mist») для кальянной: регистрация гостей, учёт визитов, уровни (99 шт.),
акция «6-й кальян бесплатно», еженедельные розыгрыши, напоминания неактивным гостям,
сбор отзывов. Весь пользовательский текст — на русском, в фирменном стиле «джинна».

## Команды

Линтера и сборки в проекте нет. Основные команды:

```powershell
python -m venv venv; .\venv\Scripts\Activate.ps1
pip install -r requirements.txt   # файл в кодировке UTF-16 LE с BOM — не перезаписывать как UTF-8 без нужды
python main.py                    # единственная точка входа; работает вечным циклом с переподключением

python -m unittest discover -s tests -t .                    # все тесты
python -m unittest tests.test_google_sheets -v               # один модуль
python -m unittest tests.test_google_sheets.TestRowCache     # один класс
```

Тесты на stdlib `unittest`, без сети: `gspread` и креды подменяются, лист эмулируется классом
`FakeWorksheet` (он повторяет поведение Sheets API, обрезающего пустые ячейки справа).

Если в системе включён SOCKS-прокси, `pip` падает с `Missing dependencies for SOCKS support`.
Обход — HTTP-порт того же клиента: `pip install --proxy http://127.0.0.1:10809 -r requirements.txt`.

Логи: `logs/bot.log` (RotatingFileHandler, 10 МБ × 5) + stdout.

### Переменные окружения (`.env`, читается через python-dotenv)

- `VK_TOKEN`, `VK_GROUP_ID` — обязательны, иначе `config.py` бросает `ValueError` при импорте.
- `ADMIN_IDS` — список ID через запятую (допускается запись в квадратных скобках).
- `GOOGLE_CREDS_JSON` — путь к JSON сервисного аккаунта Google.
- Файл `credentials.json` в корне используется в `get_today_master()` напрямую (через `from_json_keyfile_name`).

`.env`, `credentials.json` и `logs/` в `.gitignore`; **`bot_data.db` — нет**, база лежит в репозитории.

## Архитектура

### Поток обработки сообщения (`main.py`)

`VkLongPoll.listen()` → для каждого `MESSAGE_NEW`:
1. Антиспам: не чаще 1 сообщения в секунду на `user_id` (словарь в памяти `_last_msg_time`).
2. Стикеры → `handlers.handle_sticker`, пустые и длиннее `MAX_MESSAGE_LENGTH` (200) — отбрасываются.
3. Нет гостя в БД → создать в SQLite + Sheets, отправить приветствие, `continue`.
4. Обновить `last_activity` в SQLite и Sheets, `ensure_guest_in_sheet`.
5. `handle_registration_step(...)` — если вернул `True`, обработка закончена (гость ещё регистрируется).
6. Иначе `handle_main_menu(...)`.

Все ответы уходят через `send_func` — замыкание над `handlers.send_message(vk, ...)`. Модули хендлеров
никогда не вызывают `vk.messages.send` напрямую; `vk` передаётся только для API-вызовов (загрузка фото, `users.get`, `wall.post`).

### Диспетчеризация команд

`handlers.handle_main_menu` — единственный большой каскад `if` по тексту сообщения; **порядок проверок значим**:
приветствия → эмодзи → отзывы → админ-кнопки/команды → `/visit` → «визит»/«заявка» → кнопки подтверждения →
остальные кнопки меню → в конце `handle_random_joke` (отвечает с вероятностью 40 % на непонятый текст).

Кнопка `✅ Визит` попадает в ветку `'визит' in low_msg`, то есть в `handle_visit_request`;
`handle_visit_button` из-за этого — мёртвый код. Аналогично `handlers_modules/help.py: handle_help`
не используется — текст помощи продублирован внутри `handle_main_menu`.

Логика хендлеров живёт в `handlers_modules/*`; корневой `handlers.py` их реэкспортирует, а `handlers_modules/__init__.py`
дублирует те же импорты. Админские действия проходят цепочку `handlers.py` → `handlers_modules/admin.py` → `admin_commands.py`.

### Данные: SQLite + Google Sheets (двойная запись)

SQLite (`bot_data.db`) — источник истины, Google Sheets — зеркало для сотрудников заведения.
Почти каждое изменение гостя пишется в оба места: `db.*` / `db.cursor.execute(...)` и следом `gs.update_guest_sheet(...)`.
При добавлении полей гостя нужно править и `database.py`, и колонки в `google_sheets.py`.

**Гость — это кортеж `sqlite3`, обращение по индексам** (`guest[5]` — visits, `guest[9]` — registration_step и т. д.).
Порядок колонок задан в `init_db()`; добавлять новые поля можно **только в конец** (`columns_to_add` делает
`ALTER TABLE ... ADD COLUMN` при каждом старте и игнорирует `OperationalError`, если колонка уже есть).

Соответствие: `vk_id, name, phone, birth, created_at, visits, level, status, updated_at, registration_step,
last_activity, last_reminder, visits_in_cycle, free_visit_available, total_messages, unique_days, command_counts,
raffle_participations, raffle_wins, free_visits_used, cycles_completed, wrong_phone_attempts, last_request_time, awaiting_review`
(индексы 0..23). В Sheets на лист выгружаются первые 14 колонок: A=vk_id … N=free_visit_available.

`database.py` вызывает `init_db()` **при импорте**. `google_sheets.py`, наоборот, подключается лениво:
клиент, книга и лист создаются при первом обращении через `get_client()` / `get_spreadsheet()` / `get_sheet()`,
поэтому импорт не требует ни сети, ни кредов. Обращаться к листу нужно через `get_sheet()` — модульной
переменной `sheet` больше нет.

Соответствие полей гостя и колонок листа задано словарём `GUEST_COLUMNS` в `google_sheets.py`;
неизвестное поле в `update_guest_sheet` логируется предупреждением, а не игнорируется молча.

### Ключевые доменные механики

- **Регистрация** (`registration.py`): `registration_step` 0 → приветствие, 1 → телефон (нормализуется к 11 цифрам, `8`→`7`),
  2 → дата рождения либо «пропустить», 3 → завершено. Если `step >= 3`, но телефона нет — шаг сбрасывается в 1.
  При завершении регистрации с 0 визитов начисляется бонусный +1 визит.
- **Визиты** (`utils.apply_visit`): единственная точка начисления. Возвращает кортеж
  `(new_visits, new_level, level_name, ach_count, promo_line, reached_six, free_used)`; `ach_count` всегда 0 (достижения не реализованы).
  Сначала пытается списать накопленный бесплатный визит (`db.use_free_visit`), иначе инкрементит цикл.
- **Цикл акции**: `visits_in_cycle` растёт до `FREE_HOOKAH_VISITS` (6), затем ставится `free_visit_available=1`;
  следующее начисление сбрасывает цикл.
- **Уровни**: `LEVELS` в `config.py` генерируется квадратичной формулой (1..99 уровень, до `MAX_VISITS`=1500),
  `LEVEL_NAMES` — фиксированные названия; `utils.get_level_by_visits` считает уровень по числу визитов.
- **Подтверждение визита** двумя путями: гость шлёт «визит» → админам уходит клавиатура `✅ Подтвердить <id>` /
  `❌ Отклонить <id>` (кулдаун `VISIT_REQUEST_COOLDOWN` = 600 с); либо админ делает `/newvisit <id>` → генерируется
  6-значный код + QR (`utils.create_qr_image`, ссылка `vk.me/club<GROUP_ID>?text=визит <код>`), код живёт 1 час, гость шлёт `/visit КОД`.
- **Отзывы**: после засчитанного визита ставится флаг `awaiting_review`; пока он взведён, `handle_review_response`
  перехватывает сообщения и предлагает площадки (VK / Яндекс.Карты). Таблица `reviews` заполняется только API `database.py` — из хендлеров записи не создаются.
- **Планировщик** (`scheduler.py`): фоновый daemon-поток с библиотекой `schedule` — ежедневно 12:00 напоминания
  неактивным (>7 дней без активности и >14 дней с последнего напоминания), по воскресеньям 20:00 розыгрыш
  (выбор победителя, пост на стену группы, создание нового розыгрыша). Стартует один раз (`scheduler_started`),
  переподключение к VK его не перезапускает.

## Известные проблемы (учитывать при правках)

- `handlers_modules/admin.py: handle_stat` читает несуществующую таблицу `user_achievements` — `/stat` и кнопка «📊 Статистика» падают.
- Соединение SQLite одно на процесс с `check_same_thread=False` и общим курсором — планировщик и основной поток
  работают с ним конкурентно без блокировок.
- `main.py` на каждое входящее сообщение вызывает `update_guest_sheet` (запись `last_activity` в Sheets).
  При квоте 60 запросов в минуту это ограничивает пропускную способность; `ensure_guest_in_sheet` уже
  кэширует результат на процесс (`_verified_guests`), а вот запись активности — нет.
- `oauth2client` остаётся в `requirements.txt`, но кодом больше не используется: gspread 6.x работает
  только с `google-auth`. Не возвращать `ServiceAccountCredentials` — `gspread.authorize()` требует
  у кредов метод `before_request()`, которого в `oauth2client` нет.

## Стиль

- Сообщения гостю форматируются рамками `━━━` и эмодзи-заголовком; варианты ответов задаются списками и
  выбираются через `random.choice` — при добавлении текстов держаться этого паттерна.
- Проверка прав — `user_id in ADMIN_IDS` внутри самого хендлера (общего middleware нет).
