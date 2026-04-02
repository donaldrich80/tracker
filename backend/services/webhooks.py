from sqlalchemy.ext.asyncio import AsyncSession


async def fire_webhooks(db: AsyncSession, event: str, payload: dict) -> None:
    pass  # implemented in Task 10
