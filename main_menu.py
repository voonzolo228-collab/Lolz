from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

MAIN_MENU_BUTTONS = [
    "🔄 За обороткою",
    "💰 За радіусом цін",
    "🖤 Монохромні",
    "⚫ Напівмонохромні",
    "🔢 Рідкісні номери",
    "🔥 Найвигідніші зараз",
    "⚙️ Налаштування",
]


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=MAIN_MENU_BUTTONS[0]), KeyboardButton(text=MAIN_MENU_BUTTONS[1])],
        [KeyboardButton(text=MAIN_MENU_BUTTONS[2]), KeyboardButton(text=MAIN_MENU_BUTTONS[3])],
        [KeyboardButton(text=MAIN_MENU_BUTTONS[4])],
        [KeyboardButton(text=MAIN_MENU_BUTTONS[5])],
        [KeyboardButton(text=MAIN_MENU_BUTTONS[6])],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def turnover_submenu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="TOP 10", callback_data="turnover:10"),
                InlineKeyboardButton(text="TOP 25", callback_data="turnover:25"),
            ],
            [
                InlineKeyboardButton(text="TOP 50", callback_data="turnover:50"),
                InlineKeyboardButton(text="TOP 100", callback_data="turnover:100"),
            ],
        ]
    )


def price_range_submenu() -> InlineKeyboardMarkup:
    ranges = [
        ("0–50 TON", "0-50"),
        ("50–100 TON", "50-100"),
        ("100–250 TON", "100-250"),
        ("250–500 TON", "250-500"),
        ("500–1000 TON", "500-1000"),
        ("1000+ TON", "1000-999999"),
    ]
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"price_range:{value}")]
        for label, value in ranges
    ]
    rows.append([InlineKeyboardButton(text="✏️ Власний діапазон", callback_data="price_range:custom")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Моніторинг ON/OFF", callback_data="settings:toggle_monitoring")],
            [InlineKeyboardButton(text="Інтервал", callback_data="settings:interval")],
            [InlineKeyboardButton(text="Макс. ціна покупки", callback_data="settings:max_price")],
            [InlineKeyboardButton(text="Мін. прибуток", callback_data="settings:min_profit")],
            [InlineKeyboardButton(text="Мін. Opportunity Score", callback_data="settings:min_score")],
            [InlineKeyboardButton(text="Діапазон ціни", callback_data="settings:price_range")],
            [InlineKeyboardButton(text="Collections", callback_data="settings:collections")],
            [InlineKeyboardButton(text="Сповіщення ON/OFF", callback_data="settings:toggle_notifications")],
        ]
    )


def interval_submenu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="10 сек", callback_data="interval:10"),
                InlineKeyboardButton(text="30 сек", callback_data="interval:30"),
            ],
            [
                InlineKeyboardButton(text="1 хв", callback_data="interval:60"),
                InlineKeyboardButton(text="5 хв", callback_data="interval:300"),
            ],
        ]
    )
