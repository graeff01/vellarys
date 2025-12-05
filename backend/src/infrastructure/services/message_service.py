from src.domain.entities import Message
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime


async def save_message(
    db: AsyncSession,
    lead_id: int,
    role: str,
    content: str
):
    msg = Message(
        lead_id=lead_id,
        role=role,
        content=content,
        created_at=datetime.utcnow()
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg
