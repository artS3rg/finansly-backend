from sqlalchemy import Column, Integer, ForeignKey, BigInteger
from app.database import Base


class UserBonus(Base):
    """Бонусные очки пользователя для уровня. Уровень = points // 100 + 1."""
    __tablename__ = "user_bonus"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    points = Column(BigInteger, default=0, nullable=False)
