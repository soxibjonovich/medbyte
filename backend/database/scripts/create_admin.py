"""Insert default admin user (id=1, phone/password 'admin') if missing.

Run from backend/database/: uv run python scripts/create_admin.py
"""

import asyncio
import sys
from pathlib import Path

import bcrypt
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from database.models import User, UserRole  # noqa: E402
from database.session import SessionLocal, init_models  # noqa: E402


async def main() -> None:
    await init_models()
    password_hash = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode()

    async with SessionLocal() as session:
        existing = await session.execute(select(User).where(User.id == 1))
        user = existing.scalar_one_or_none()
        if user is not None:
            print(f"user id=1 already exists (phone={user.phone!r}, role={user.role})")
            return

        session.add(
            User(
                id=1,
                full_name="admin",
                username="admin",
                phone="admin",
                email=None,
                password_hash=password_hash,
                role=UserRole.admin,
            )
        )
        await session.commit()
        print("created admin user id=1 (phone=admin, password=admin)")


if __name__ == "__main__":
    asyncio.run(main())
