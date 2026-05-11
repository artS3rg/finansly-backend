from datetime import date, timedelta

from jose import jwt

from app import subscription_utils as su
from app.auth import ALGORITHM, SECRET_KEY, create_access_token, get_password_hash, verify_password


def test_iter_payment_dates_same_month():
    result = list(
        su.iter_payment_dates_from_to(
            payment_day=10,
            start=date(2026, 5, 1),
            end=date(2026, 5, 31),
        )
    )
    assert result == [date(2026, 5, 10)]


def test_iter_payment_dates_shift_to_first_of_next_month_when_day_absent():
    result = list(
        su.iter_payment_dates_from_to(
            payment_day=31,
            start=date(2026, 2, 1),
            end=date(2026, 3, 5),
        )
    )
    assert result == [date(2026, 3, 1)]


def test_iter_payment_dates_handles_year_boundary():
    result = list(
        su.iter_payment_dates_from_to(
            payment_day=31,
            start=date(2026, 12, 1),
            end=date(2027, 1, 31),
        )
    )
    assert result == [date(2026, 12, 31), date(2027, 1, 31)]


def test_iter_payment_dates_respects_inclusive_bounds():
    result = list(
        su.iter_payment_dates_from_to(
            payment_day=15,
            start=date(2026, 5, 15),
            end=date(2026, 5, 15),
        )
    )
    assert result == [date(2026, 5, 15)]


def test_get_next_payment_date_returns_current_month_candidate(monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 5, 10)

    monkeypatch.setattr(su, "date", FixedDate)
    assert su.get_next_payment_date(20) == date(2026, 5, 20)


def test_get_next_payment_date_returns_today_when_equal(monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 5, 10)

    monkeypatch.setattr(su, "date", FixedDate)
    assert su.get_next_payment_date(10) == date(2026, 5, 10)


def test_get_next_payment_date_moves_to_next_month_when_day_passed(monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 1, 30)

    monkeypatch.setattr(su, "date", FixedDate)
    assert su.get_next_payment_date(29) == date(2026, 2, 28)


def test_get_next_payment_date_returns_first_of_next_month_when_day_absent(monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 2, 10)

    monkeypatch.setattr(su, "date", FixedDate)
    assert su.get_next_payment_date(31) == date(2026, 3, 1)


def test_password_hash_and_verify_roundtrip():
    raw_password = "my-strong-password-123"
    hashed = get_password_hash(raw_password)
    assert verify_password(raw_password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_create_access_token_contains_sub_and_exp():
    token = create_access_token({"sub": "42"}, expires_delta=timedelta(minutes=5))
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    assert payload["sub"] == "42"
    assert isinstance(payload["exp"], int)
