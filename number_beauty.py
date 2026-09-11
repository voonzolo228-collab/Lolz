"""
Алгоритм оцінки "краси" номера NFT (0-100), а не статичний список.

Враховує:
- дуже маленькі номери
- однакові цифри (111, 2222)
- паліндроми (12321, 1221)
- повторювані короткі патерни (1212, 123123)
- круглі числа (100, 1000)
- послідовності (123, 4321, 12345)
- дзеркальні пари (1001, 6996 - теж паліндром, але виділяємо окремо для читабельності)
"""


def _is_palindrome(s: str) -> bool:
    return s == s[::-1]


def _is_sequence(s: str) -> bool:
    if len(s) < 3:
        return False
    digits = [int(c) for c in s]
    ascending = all(digits[i] + 1 == digits[i + 1] for i in range(len(digits) - 1))
    descending = all(digits[i] - 1 == digits[i + 1] for i in range(len(digits) - 1))
    return ascending or descending


def _repeated_pattern(s: str) -> bool:
    n = len(s)
    for size in range(1, n // 2 + 1):
        if n % size == 0:
            block = s[:size]
            if block * (n // size) == s:
                return True
    return False


def _all_same_digit(s: str) -> bool:
    return len(set(s)) == 1


def score_number_beauty(number: int) -> tuple[int, list[str]]:
    """Повертає (score 0-100, список причин)."""
    if number is None or number < 0:
        return 0, []

    s = str(number)
    score = 0
    reasons: list[str] = []

    if number <= 10:
        score += 45
        reasons.append("дуже маленький номер")
    elif number <= 100:
        score += 25
        reasons.append("маленький номер")
    elif number <= 1000:
        score += 10
        reasons.append("тризначний преміум-діапазон")

    if _all_same_digit(s) and len(s) >= 2:
        score += 40
        reasons.append("всі цифри однакові")

    if _is_palindrome(s) and len(s) >= 3:
        score += 30
        reasons.append("паліндром")

    if _repeated_pattern(s) and len(s) >= 4:
        score += 20
        reasons.append("повторюваний патерн")

    if _is_sequence(s):
        score += 25
        reasons.append("числова послідовність")

    if s.endswith("000") or s == "1000" or (number % 1000 == 0 and number > 0):
        score += 15
        reasons.append("кругле число")

    if len(set(s)) == 2 and len(s) >= 4:
        score += 10
        reasons.append("лише дві унікальні цифри")

    return min(score, 100), reasons
