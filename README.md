# MRKT NFT Opportunity Monitor Bot

Telegram-бот, який моніторить лістинги NFT-подарунків на [MRKT](https://t.me/mrkt)
і шукає потенційно недооцінені пропозиції для перепродажу.

## 1. Структура проєкту

```
project/
├── main.py                  # точка входу
├── config.py                 # завантаження .env
├── requirements.txt
├── .env.example
├── README.md
│
├── bot/
│   ├── handlers/              # обробники меню (turnover, price_range, monochrome,
│   │                             rare_numbers, best_deals, settings)
│   ├── keyboards/              # inline/reply клавіатури
│   └── states/                 # aiogram FSM стани
│
├── mrkt/
│   ├── auth.py                # отримання MRKT token через Mini App init_data
│   ├── client.py               # HTTP-клієнт з retry/backoff/rate-limit/cursor pagination
│   └── models.py                # модель Gift
│
├── services/
│   ├── monitor.py               # фоновий цикл моніторингу
│   ├── analyzer.py               # оцінка ринкової ціни за аналогами
│   ├── scoring.py                 # Opportunity Score
│   └── notifications.py            # формат і відправка сповіщень
│
├── database/
│   └── db.py                        # SQLite (users, seen_gifts)
│
└── utils/
    ├── number_beauty.py              # алгоритм "краси" номера
    ├── color_analysis.py              # евристика монохромності
    ├── formatting.py                   # форматування списків NFT
    └── logger.py                        # логування з редагуванням секретів
```

## 2. Встановлення

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Налаштування

```bash
cp .env.example .env
```

Заповни `.env`:

| Змінна | Де взяти |
|---|---|
| `BOT_TOKEN` | @BotFather → `/newbot` |
| `API_ID`, `API_HASH` | https://my.telegram.org → API development tools |
| `OWNER_CHAT_ID` | напиши @userinfobot |
| `MRKT_BOT_USERNAME` | зазвичай `mrkt` |

## 4. Перший запуск

```bash
python main.py
```

Що відбудеться:

1. **Telegram-авторизація (Pyrogram).** Консоль запросить номер телефону
   (можна одразу прописати в коді при бажанні, зараз вводиться інтерактивно),
   потім **код підтвердження з Telegram** — його треба ввести прямо в
   термінал, а не надсилати боту. Якщо ввімкнена 2FA — консоль запросить
   і пароль. Після успіху створюється файл сесії
   `<PYROGRAM_SESSION_NAME>.session` — повторні запуски код не питають.
2. **MRKT авторизація.** Бот автоматично викликає Mini App `mrkt`,
   отримує `init_data` і обмінює його на MRKT auth token через
   `POST /api/v1/auth`. Токен зберігається лише в пам'яті процесу,
   ніколи не пишеться в файли чи логи. При отриманні 401 від MRKT API
   токен автоматично перевидається.
3. Запускається Telegram-бот і фоновий цикл моніторингу.

## 5. Команди запуску (наступні рази)

```bash
source venv/bin/activate
python main.py
```

## 6. Головне меню

- **🔄 За обороткою** — TOP 10/25/50/100 за кількістю активних лістингів
  (проксі попиту; MRKT API не дає історію продажів, тому справжній
  "оборот" вигадувати не можна — це чесно позначено в самому боті).
- **💰 За радіусом цін** — готові діапазони + власний (формат `120-180`).
- **🖤 Монохромні / ⚫ Напівмонохромні** — евристика за ключовими словами
  кольору в назвах backdrop/symbol/model (MRKT не дає RGB-даних).
- **🔢 Рідкісні номери** — алгоритм "краси" номера (паліндроми, однакові
  цифри, послідовності, круглі числа тощо), не статичний список.
- **🔥 Найвигідніші зараз** — головна функція: аналізує всі активні
  лістинги, шукає недооцінені відносно медіани найближчих аналогів.
- **⚙️ Налаштування** — monitoring on/off, інтервал, макс. ціна покупки,
  мін. прибуток, мін. Opportunity Score, діапазон ціни, collections,
  сповіщення on/off.

## 7. Opportunity Score — як рахується

Зважена сума 5 компонентів (детально в `services/scoring.py`):

| Компонент | Вага | Що враховує |
|---|---|---|
| price_gap | 40 | наскільки ціна нижча за медіану аналогів |
| liquidity | 20 | кількість активних лістингів того ж типу |
| sample_conf | 20 | надійність вибірки для оцінки ринку |
| rarity_number | 10 | "краса" номера NFT |
| profit_after_fees | 10 | чистий прибуток після комісії (5%, приблизна оцінка — уточни фактичну ставку MRKT) |

## 8. Як шукаються недооцінені NFT

1. Береться поточний NFT-лістинг.
2. Шукаються найближчі аналоги: спочатку точний збіг
   collection+model+backdrop+symbol, якщо зразків < 3 — розширюється
   до collection+model, потім до всієї collection.
3. Якщо навіть у межах collection зразків < 3 — оцінка НЕ видається
   ("недостатньо даних"), замість вигаданого числа.
4. Estimated Resale Price = медіана цін аналогів.
5. Potential Profit = Resale Price − Purchase Price − Fee (5%).

## 9. Які дані реально доступні з MRKT

З `/api/v1/gifts/saling`: collection, model, backdrop, symbol, number,
price, mintable, cursor для пагінації.

**Недоступно** (тому не використовується і не вигадується):
- історія продажів / офіційна статистика обороту;
- RGB/HEX кольори атрибутів;
- офіційний rarity score (якщо MRKT додасть таке поле в майбутньому —
  його легко підключити в `mrkt/models.py`).

## 10. Обробка помилок

`mrkt/client.py` обробляє: timeout, transport errors, HTTP 401
(автооновлення токена), HTTP 429 (rate limit з Retry-After), HTTP 5xx
(retry з exponential backoff), некоректний JSON. Один невдалий запит
не валить бот — цикл моніторингу продовжує роботу.

## 11. Деплой на безкоштовний хостинг (Railway)

Бот — це довготривалий процес (background monitoring loop), тому потрібен
хостинг, що тримає процес живим, а не serverless-функції. Railway підходить:
безкоштовний trial-кредит, підтримує Docker і persistent volume.

### Крок 1 — згенеруй сесію Telegram ЛОКАЛЬНО (обов'язково)

Хостинг зазвичай не дає інтерактивний термінал під час першого деплою,
а Pyrogram при першому вході питає код підтвердження. Тому:

```bash
python main.py
```

Запусти це у себе на комп'ютері, введи код з Telegram у консолі, дочекайся
рядка "Pyrogram user client авторизовано." і `Ctrl+C`. У тебе з'явиться
файл `mrkt_user_session.session` — саме його завантажимо на хостинг,
щоб повторний логін не був потрібен.

### Крок 2 — встанови Railway CLI і залогінься

```bash
npm i -g @railway/cli
railway login
```

### Крок 3 — створи проєкт і volume

```bash
cd project
railway init
railway volume create data --mount-path /app/data
```

### Крок 4 — постав змінні оточення (значення з твого .env)

```bash
railway variables set BOT_TOKEN=... API_ID=... API_HASH=... OWNER_CHAT_ID=... \
  MRKT_BOT_USERNAME=mrkt \
  PYROGRAM_SESSION_NAME=/app/data/mrkt_user_session \
  DB_PATH=/app/data/mrkt_bot.sqlite3
```

### Крок 5 — заливай сесію у volume і деплой

```bash
railway up
railway run bash -c "mkdir -p /app/data"
railway ssh -- true   # переконайся, що volume змонтовано
```

Скопіюй `mrkt_user_session.session` у примонтований `/app/data` через
`railway ssh` (`scp`-подібне копіювання доступне через `railway ssh` shell:
відкрий сесію й вручну перенеси файл, наприклад через `railway run` разом
з base64-кодуванням файлу, якщо прямого upload немає в твоїй версії CLI —
перевір актуальну команду в `railway docs`, вона періодично змінюється).

Після цього:

```bash
railway up
railway logs
```

Бот повинен запуститись без запиту коду (сесія вже є) і почати
моніторинг. Перевір `railway logs`, щоб побачити рядок
"Monitor service запущено."

### Альтернатива простіше: власний VPS/Raspberry Pi/домашній ПК

Якщо upload файлу сесії через Railway CLI виявиться незручним,
найпростіший безкоштовний варіант — тримати бота на власному
завжди-увімкненому пристрої (Raspberry Pi, старий ноутбук, VPS з
безкоштовним тарифом типу Oracle Cloud Free Tier) через `systemd`
або просто `tmux`/`screen` + `python main.py`. Це усуває всю
складність з volume/session upload, бо файл сесії й так локальний.

## 12. Безпека

- Жодні секрети не хардкодяться в коді — все через `.env`.
- `.env` має бути в `.gitignore` (додай, якщо ще немає).
- Логи редагують токени/паролі через `utils/logger.py`.
