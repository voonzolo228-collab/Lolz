from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    waiting_max_price = State()
    waiting_min_profit = State()
    waiting_min_score = State()
    waiting_price_range = State()
    waiting_collections = State()


class BrowseStates(StatesGroup):
    waiting_custom_price_range = State()
