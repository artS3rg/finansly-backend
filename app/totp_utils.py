"""TOTP (RFC 6238) для двухфакторной аутентификации."""

import pyotp


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, account_email: str, issuer: str = "Finansly") -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=account_email, issuer_name=issuer)


def verify_totp_code(secret: str, code: str) -> bool:
    normalized = code.strip().replace(" ", "")
    if len(normalized) != 6 or not normalized.isdigit():
        return False
    return pyotp.TOTP(secret).verify(normalized, valid_window=1)
