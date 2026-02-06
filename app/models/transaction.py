from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    is_income = Column(Boolean, default=True)  # True - доход, False - расход
    category = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связь
    user = relationship("User", back_populates="transactions")
