from datetime import date
from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, UniqueConstraint
from app.database import Base


class DailyTask(Base):
    """Ежедневное задание пользователя. 5 заданий в день, типы выбираются рандомно."""
    __tablename__ = "daily_tasks"
    __table_args__ = (UniqueConstraint("user_id", "task_date", "position", name="uq_user_date_position"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_date = Column(Date, nullable=False)  # день (дата без времени)
    position = Column(Integer, nullable=False)  # 0..4
    task_type = Column(String(64), nullable=False)  # ключ типа: create_transaction, create_goal, ...
    completed = Column(Boolean, default=False, nullable=False)
