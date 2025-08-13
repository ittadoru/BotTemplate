from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from db.base import Base
from datetime import date, datetime
from typing import Optional

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=False)  # Telegram user_id
    first_name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserActivity(Base):
    __tablename__ = 'user_activity'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    activity_date = Column(DateTime(timezone=True), default=func.now())

# --- Пользователи ---
async def add_user(session: AsyncSession, user_id: int, first_name: str = None, username: str = None):
    user = await session.get(User, user_id)
    if not user:
        user = User(id=user_id, first_name=first_name, username=username)
        session.add(user)
        await session.commit()
        return user
    return user

async def log_user_activity(session: AsyncSession, user_id: int):
    activity = UserActivity(user_id=user_id, activity_date=datetime.utcnow())
    session.add(activity)
    await session.commit()

async def get_user_id_by_username(session: AsyncSession, username: str) -> Optional[int]:
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    return user.id if user else None
