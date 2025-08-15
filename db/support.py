from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import relationship
from db.base import Base


class SupportTicket(Base):
    __tablename__ = 'support_tickets'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    username = Column(String, nullable=True)
    topic_id = Column(Integer, nullable=False, index=True)  # message_thread_id для поддержки
    is_closed = Column(Integer, default=0)  # 0 = False, 1 = True
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    messages = relationship('SupportMessage', back_populates='ticket', cascade='all, delete-orphan')

class SupportMessage(Base):
    __tablename__ = 'support_messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey('support_tickets.id'))
    message = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ticket = relationship('SupportTicket', back_populates='messages')

async def create_ticket(session: AsyncSession, user_id: int, username: str, topic_id: int, message: str = None):
    # Проверяем, есть ли открытый тикет
    ticket = await session.execute(select(SupportTicket).where(SupportTicket.user_id == user_id, SupportTicket.is_closed == 0))
    ticket = ticket.scalars().first()
    if ticket:
        return ticket
    ticket = SupportTicket(user_id=user_id, username=username, topic_id=topic_id, is_closed=0)
    session.add(ticket)
    await session.flush()
    if message:
        msg = SupportMessage(ticket_id=ticket.id, message=message)
        session.add(msg)
    await session.commit()
    return ticket

async def add_message_to_ticket(session: AsyncSession, user_id: int, message: str):
    ticket = await session.execute(select(SupportTicket).where(SupportTicket.user_id == user_id, SupportTicket.is_closed == 0))
    ticket = ticket.scalars().first()
    if not ticket:
        return False
    msg = SupportMessage(ticket_id=ticket.id, message=message)
    session.add(msg)
    await session.commit()
    return True

async def get_ticket_messages(session: AsyncSession, user_id: int):
    ticket = await session.execute(select(SupportTicket).where(SupportTicket.user_id == user_id, SupportTicket.is_closed == 0))
    ticket = ticket.scalars().first()
    if not ticket:
        return []
    result = await session.execute(select(SupportMessage).where(SupportMessage.ticket_id == ticket.id).order_by(SupportMessage.created_at))
    return [msg.message for msg in result.scalars().all()]

async def close_ticket(session: AsyncSession, user_id: int):
    ticket = await session.execute(select(SupportTicket).where(SupportTicket.user_id == user_id, SupportTicket.is_closed == 0))
    ticket = ticket.scalars().first()
    if ticket:
        ticket.is_closed = 1
        await session.commit()

async def get_user_id_by_topic(session, topic_id: int) -> int | None:
    """
    Получить user_id по topic_id (message_thread_id).
    Требует, чтобы в SupportTicket было поле topic_id.
    """
    ticket = await session.execute(select(SupportTicket).where(SupportTicket.topic_id == topic_id))
    ticket = ticket.scalars().first()
    return ticket.user_id if ticket else None

async def get_ticket(session, user_id: int):
    """
    Получить SupportTicket по user_id.
    """
    ticket = await session.execute(select(SupportTicket).where(SupportTicket.user_id == user_id))
    return ticket.scalars().first()