import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_github_user_id(db: AsyncSession, github_user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.github_user_id == github_user_id))
    return result.scalar_one_or_none()


async def get_by_password_reset_token_hash(db: AsyncSession, token_hash: str) -> User | None:
    result = await db.execute(select(User).where(User.password_reset_token_hash == token_hash))
    return result.scalar_one_or_none()


async def get_by_email_verification_token_hash(db: AsyncSession, token_hash: str) -> User | None:
    result = await db.execute(select(User).where(User.email_verification_token_hash == token_hash))
    return result.scalar_one_or_none()


def create(
    db: AsyncSession,
    *,
    email: str,
    full_name: str,
    password_hash: str | None = None,
    github_user_id: int | None = None,
    avatar_url: str | None = None,
) -> User:
    user = User(
        email=email,
        full_name=full_name,
        password_hash=password_hash,
        github_user_id=github_user_id,
        avatar_url=avatar_url,
    )
    db.add(user)
    return user
