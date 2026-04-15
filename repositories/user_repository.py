from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.auth import User

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == username))
        return result.scalars().first()
