# Telegram-бот «Дыхание» — MVP

Лид-бот с ветками **Сон / Longevity / Спорт**, гейтом подписки, тестом BOLT (таймер СТАРТ/СТОП), промокодом и 7-дневной рассылкой.

## Стек

- Python 3.12+
- aiogram 3
- SQLite (aiosqlite)
- APScheduler

## Быстрый старт

```bash
cd tgBot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# заполни BOT_TOKEN, CHANNEL_ID, CHANNEL_URL, ADMIN_IDS
python main.py
```

### `.env`

| Переменная | Пример | Описание |
|---|---|---|
| `BOT_TOKEN` | от @BotFather | токен бота |
| `CHANNEL_ID` | `@channel` или `-100…` | канал для гейта (бот должен быть админом) |
| `CHANNEL_URL` | `https://t.me/…` | кнопка «Подписаться» |
| `REQUIRE_SUBSCRIPTION` | `false` | `true` — включить гейт подписки |
| `ADMIN_IDS` | `123,456` | Telegram ID админов |
| `PROMO_CODE` | `DYHANIE30` | код −30% |
| `PURCHASE_URL_*` | ссылки | оффер по веткам |

## Deep-link

- `t.me/<bot>?start=sleep`
- `t.me/<bot>?start=longevity`
- `t.me/<bot>?start=sport`

Без параметра — меню выбора ветки.

## Админ-команды

- `/stats` — метрики воронки по веткам
- `/broadcast` — ручная рассылка (вся база или одна ветка)

## Контент

Плейсхолдеры лежат в `content/`. Замени PDF/mp3 и правь тексты в `bot/content.py`.

## Воронка

1. Deep-link / выбор ветки  
2. Гейт подписки (`getChatMember`)  
3. Лид-магнит (PDF; для Сон — ещё аудио)  
4. Тест (3 вопроса + BOLT СТАРТ/СТОП)  
5. Разбор + промокод 48 ч  
6. Автоцепочка дней 1, 2, 3, 5, 7  

## Запуск на сервере (systemd)

Шаблон: `deploy/dyhanie-bot.service` (пути под `/root/tgBot`).

```bash
# на сервере в /root/tgBot:
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

sudo cp deploy/dyhanie-bot.service /etc/systemd/system/dyhanie-bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now dyhanie-bot
```

Полезное:

```bash
sudo systemctl status dyhanie-bot
sudo journalctl -u dyhanie-bot -f
sudo systemctl restart dyhanie-bot
```

После перезагрузки сервера сервис поднимется сам (`enable`).  
`Restart=always` — перезапустит бота, если процесс упадёт.
# tgBot
