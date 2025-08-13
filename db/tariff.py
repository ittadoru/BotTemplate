from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from db.base import Base
from typing import Optional

class Tariff(Base):
    __tablename__ = 'tariffs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    duration_days = Column(Integer, nullable=False)

async def create_tariff(session: AsyncSession, name: str, price: int, duration_days: int) -> int:
    tariff = Tariff(name=name, price=price, duration_days=duration_days)
    session.add(tariff)
    await session.commit()
    await session.refresh(tariff)
    return tariff.id

async def delete_tariff(session: AsyncSession, tariff_id: int):
    tariff = await session.get(Tariff, tariff_id)
    if tariff:
        await session.delete(tariff)
        await session.commit()

async def get_tariff_by_id(session: AsyncSession, tariff_id: int) -> Optional[Tariff]:
    return await session.get(Tariff, tariff_id)

async def get_all_tariffs(session: AsyncSession):
    result = await session.execute(select(Tariff))
    return result.scalars().all()
