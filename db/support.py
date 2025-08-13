from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import relationship
from db.base import Base
from datetime import datetime
from typing import Optional

class SupportTicket(Base):
    __tablename__ = 'support_tickets'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    username = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    messages = relationship('SupportMessage', back_populates='ticket', cascade='all, delete-orphan')

class SupportMessage(Base):
    __tablename__ = 'support_messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey('support_tickets.id'))
    message = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ticket = relationship('SupportTicket', back_populates='messages')

async def create_ticket(session: AsyncSession, user_id: int, username: str, message: str):
    ticket = await session.execute(select(SupportTicket).where(SupportTicket.user_id == user_id))
    ticket = ticket.scalars().first()
    if ticket:
        return False
    ticket = SupportTicket(user_id=user_id, username=username)
    session.add(ticket)
    await session.flush()
    msg = SupportMessage(ticket_id=ticket.id, message=message)
    session.add(msg)
    await session.commit()
    return True

async def add_message_to_ticket(session: AsyncSession, user_id: int, message: str):
    ticket = await session.execute(select(SupportTicket).where(SupportTicket.user_id == user_id))
    ticket = ticket.scalars().first()
    if not ticket:
        return False
    msg = SupportMessage(ticket_id=ticket.id, message=message)
    session.add(msg)
    await session.commit()
    return True

async def get_ticket_messages(session: AsyncSession, user_id: int):
    ticket = await session.execute(select(SupportTicket).where(SupportTicket.user_id == user_id))
    ticket = ticket.scalars().first()
    if not ticket:
        return []
    result = await session.execute(select(SupportMessage).where(SupportMessage.ticket_id == ticket.id).order_by(SupportMessage.created_at))
    return [msg.message for msg in result.scalars().all()]

async def close_ticket(session: AsyncSession, user_id: int):
    ticket = await session.execute(select(SupportTicket).where(SupportTicket.user_id == user_id))
    ticket = ticket.scalars().first()
    if ticket:
        await session.delete(ticket)
        await session.commit()
