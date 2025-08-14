from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from db.base import Base
from datetime import datetime, timedelta

class Subscriber(Base):
    __tablename__ = 'subscribers'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    expire_at = Column(DateTime(timezone=True), nullable=False)

class Promocode(Base):
    __tablename__ = 'promocodes'
    code = Column(String, primary_key=True)
    duration_days = Column(Integer, nullable=False)

# --- Подписки ---
async def add_subscriber_with_duration(session: AsyncSession, user_id: int, days: int):
    subscriber = await session.get(Subscriber, user_id)
    now = datetime.utcnow()
    if subscriber and subscriber.expire_at > now:
        new_expire = subscriber.expire_at + timedelta(days=days)
        subscriber.expire_at = new_expire
    else:
        new_expire = now + timedelta(days=days)
        if not subscriber:
            subscriber = Subscriber(user_id=user_id, expire_at=new_expire)
            session.add(subscriber)
        else:
            subscriber.expire_at = new_expire
    await session.commit()
    return subscriber

async def is_subscriber(session: AsyncSession, user_id: int) -> bool:
    subscriber = await session.get(Subscriber, user_id)
    now = datetime.utcnow()
    return subscriber is not None and subscriber.expire_at > now

async def get_all_subscribers(session: AsyncSession):
    result = await session.execute(select(Subscriber))
    return result.scalars().all()

# --- Промокоды ---
async def add_promocode(session: AsyncSession, code: str, duration_days: int = 30):
    promocode = Promocode(code=code, duration_days=duration_days)
    session.add(promocode)
    await session.commit()
    return promocode

async def remove_promocode(session: AsyncSession, code: str):
    promocode = await session.get(Promocode, code)
    if promocode:
        await session.delete(promocode)
        await session.commit()

async def remove_all_promocodes(session: AsyncSession):
    await session.execute('DELETE FROM promocodes')
    await session.commit()

async def get_all_promocodes(session: AsyncSession):
    result = await session.execute(select(Promocode))
    return result.scalars().all()

async def activate_promocode(session: AsyncSession, user_id: int, code: str):
    promocode = await session.get(Promocode, code)
    if not promocode:
        return None
    await add_subscriber_with_duration(session, user_id, promocode.duration_days)
    await remove_promocode(session, code)
    return promocode.duration_days

async def get_total_subscribers(session):
    return await session.scalar(select(func.count()).select_from(Subscriber))

async def delete_subscriber_by_id(session, user_id: int):
    subscriber = await session.get(Subscriber, user_id)
    if subscriber:
        await session.delete(subscriber)

async def get_subscriber_expiry(session: AsyncSession, user_id: int):
    """Возвращает expire_at (datetime) для подписчика или None."""
    subscriber = await session.get(Subscriber, user_id)
    if subscriber:
        return subscriber.expire_at
    return None

async def get_promocode_duration(session: AsyncSession, code: str):
    """Возвращает количество дней действия промокода по коду или None."""
    promocode = await session.get(Promocode, code)
    if promocode:
        return promocode.duration_days
    return None