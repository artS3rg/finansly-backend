from sqlalchemy import Column, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class GoalMember(Base):
    __tablename__ = "goal_members"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    contributed_amount = Column(Float, default=0.0)

    __table_args__ = (UniqueConstraint("goal_id", "user_id", name="uq_goal_member"),)

    goal = relationship("Goal", back_populates="members")
    user = relationship("User", back_populates="goal_memberships")
