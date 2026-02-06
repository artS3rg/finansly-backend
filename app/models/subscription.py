from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    payment_day = Column(Integer, nullable=False)  # День месяца списания (1-31)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связь
    user = relationship("User", back_populates="subscriptions")
