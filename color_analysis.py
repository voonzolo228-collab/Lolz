"""
ОБМЕЖЕННЯ ДАНИХ (читай перед використанням):
MRKT API (/gifts/saling) не повертає RGB/HEX кольори атрибутів -
тільки текстові НАЗВИ backdropName і symbolName (напр. "Black Sky",
"Golden Symbol"). Офіційного поля "колір" немає.

Тому надійно визначити монохромність по факту (аналіз пікселів)
НЕМОЖЛИВО без завантаження й аналізу самого зображення NFT, а бот
не має підтвердженого endpoint для отримання зображення в API.

Що реалізовано замість цього: евристика на основі КЛЮЧОВИХ СЛІВ
кольору в назвах backdrop/symbol/model. Це наближення, не гарантія.
Результат позначається як "евристична оцінка", а не факт.
"""
import re

# Групи кольорових ключових слів (розширюваний список, не вичерпний)
COLOR_GROUPS: dict[str, list[str]] = {
    "black": ["black", "dark", "night", "shadow", "onyx", "obsidian", "midnight"],
    "white": ["white", "snow", "ivory", "pearl", "cloud", "silver"],
    "gold": ["gold", "golden", "amber", "honey"],
    "red": ["red", "crimson", "ruby", "scarlet", "cherry"],
    "blue": ["blue", "sky", "ocean", "navy", "azure", "sapphire"],
    "green": ["green", "emerald", "jade", "mint", "forest"],
    "purple": ["purple", "violet", "lavender", "lilac", "amethyst"],
    "pink": ["pink", "rose", "magenta"],
    "gray": ["gray", "grey", "steel", "ash", "graphite"],
    "brown": ["brown", "bronze", "copper", "chocolate", "coffee"],
    "rainbow": ["rainbow", "multicolor", "prism", "spectrum"],
}


def _detect_color_group(name: str | None) -> str | None:
    if not name:
        return None
    lowered = name.lower()
    for group, keywords in COLOR_GROUPS.items():
        for kw in keywords:
            if re.search(rf"\b{kw}\b", lowered):
                return group
    return None


def classify_monochrome(
    backdrop_name: str | None,
    symbol_name: str | None,
    model_name: str | None,
) -> tuple[str, str]:
    """
    Повертає (category, explanation), category одна з:
    "mono", "semi_mono", "none", "unknown".

    "unknown" - коли жодна з назв не містить розпізнаваного кольорового
    ключового слова; в такому разі НЕ вигадуємо категорію.
    """
    backdrop_color = _detect_color_group(backdrop_name)
    symbol_color = _detect_color_group(symbol_name)
    model_color = _detect_color_group(model_name)

    detected = [c for c in (backdrop_color, symbol_color, model_color) if c]

    if not detected:
        return "unknown", (
            "У назвах backdrop/symbol/model немає розпізнаваних кольорових "
            "ключових слів - надійно оцінити монохромність неможливо."
        )

    unique_colors = set(detected)

    if len(unique_colors) == 1 and len(detected) >= 2:
        return "mono", (
            f"Backdrop, symbol та/або model узгоджені за кольоровою групою "
            f"'{unique_colors.pop()}' (евристика за назвами, не аналіз пікселів)."
        )

    if len(unique_colors) == 2 and len(detected) >= 2:
        return "semi_mono", (
            f"Часткова відповідність кольорових груп ({', '.join(sorted(unique_colors))}) "
            f"між атрибутами - евристична напівмонохромна оцінка."
        )

    return "none", "Кольорові групи атрибутів не збігаються."
