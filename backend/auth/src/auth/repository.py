from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import User, UserRole


async def get_by_phone(session: AsyncSession, phone: str) -> User | None:
    result = await session.execute(select(User).where(User.phone == phone))
    return result.scalar_one_or_none()


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def create_user(
    session: AsyncSession,
    full_name: str,
    phone: str | None,
    email: str | None,
    password_hash: str | None,
    role: UserRole = UserRole.patient,
) -> User:
    user = User(
        full_name=full_name,
        phone=phone,
        email=email,
        password_hash=password_hash,
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
