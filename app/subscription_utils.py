"""Расчёт следующей даты списания по дню месяца (1-31)."""
import calendar
from datetime import date


def get_next_payment_date(payment_day: int) -> date:
    """
    Возвращает следующую дату списания с учётом числа дней в месяце.

    - Если указанный день есть в текущем месяце и ещё не прошёл — эта дата.
    - Если день уже прошёл в текущем месяце — тот же день в следующем месяце
      (с учётом 28/29/30/31: например 31 января → 28 или 29 февраля).
    - Если указанного дня нет в текущем месяце (например 29 или 31 в феврале с 28 днями),
      следующее списание — 1-е число следующего месяца (1 марта), а не 29 марта.
    """
    today = date.today()
    _, last_day_this = calendar.monthrange(today.year, today.month)

    # Указанный день есть в текущем месяце
    if payment_day <= last_day_this:
        candidate = today.replace(day=payment_day)
        if candidate >= today:
            return candidate
        # День уже прошёл — следующий раз в следующем месяце (тот же день или последний)
        if today.month == 12:
            next_first = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_first = today.replace(month=today.month + 1, day=1)
        _, last_day_next = calendar.monthrange(next_first.year, next_first.month)
        day_next = min(payment_day, last_day_next)
        return next_first.replace(day=day_next)

    # Указанного дня нет в этом месяце (напр. 29 или 31 в феврале) — следующее списание 1-го числа следующего месяца
    if today.month == 12:
        return today.replace(year=today.year + 1, month=1, day=1)
    return today.replace(month=today.month + 1, day=1)
