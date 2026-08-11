from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User, UserRole


async def list_users(session: AsyncSession, limit: int = 50, offset: int = 0) -> list[User]:
    result = await session.execute(select(User).order_by(User.id).limit(limit).offset(offset))
    return list(result.scalars().all())


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_user_by_phone(session: AsyncSession, phone: str) -> User | None:
    result = await session.execute(select(User).where(User.phone == phone))
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    full_name: str,
    phone: str | None = None,
    email: str | None = None,
    password_hash: str | None = None,
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


async def update_user(
    session: AsyncSession,
    user: User,
    full_name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    role: UserRole | None = None,
) -> User:
    if full_name is not None:
        user.full_name = full_name
    if phone is not None:
        user.phone = phone
    if email is not None:
        user.email = email
    if role is not None:
        user.role = role

    await session.commit()
    await session.refresh(user)
    return user


async def delete_user(session: AsyncSession, user: User) -> None:
    await session.delete(user)
    await session.commit()
