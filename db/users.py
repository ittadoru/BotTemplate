from sqlalchemy import select, func, Column, Integer, String, DateTime
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from db.base import Base
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
    activity = UserActivity(user_id=user_id, activity_date=datetime.datetime.utcnow())
    session.add(activity)
    await session.commit()

async def get_user_id_by_username(session: AsyncSession, username: str) -> Optional[int]:
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    return user.id if user else None

async def get_all_user_ids(session: AsyncSession):
    result = await session.execute(select(User.id))
    return [row[0] for row in result.all()]

async def get_total_users(session):
    return await session.scalar(select(func.count()).select_from(User))

async def get_active_users_today(session):
    today = datetime.date.today()
    q = select(func.count(func.distinct(UserActivity.user_id))).where(func.date(UserActivity.activity_date) == today)
    return await session.scalar(q)

async def delete_user_by_id(session, user_id: int):
    user = await session.get(User, user_id)
    if user:
        await session.delete(user)

async def get_users_by_ids(session, user_ids: list[int]):
    if not user_ids:
        return []
    result = await session.execute(select(User).where(User.id.in_(user_ids)))
    return result.scalars().all()

async def is_user_exists(session: AsyncSession, user_id: int) -> bool:
    user = await session.get(User, user_id)
    return user is not None
