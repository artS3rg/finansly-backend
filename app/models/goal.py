from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    start_amount = Column(Float, default=0.0)
    finish_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    party_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    is_completed = Column(Boolean, default=False)
    
    # Связи
    user = relationship("User", back_populates="goals")
    members = relationship("GoalMember", back_populates="goal", cascade="all, delete-orphan")
