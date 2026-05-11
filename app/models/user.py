from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    username = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    banner_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    totp_enabled = Column(Boolean, default=False)
    totp_secret = Column(String, nullable=True)
    totp_pending_secret = Column(String, nullable=True)

    # Связи
    transactions = relationship("Transaction", back_populates="user")
    goals = relationship("Goal", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")
    goal_memberships = relationship("GoalMember", back_populates="user")
