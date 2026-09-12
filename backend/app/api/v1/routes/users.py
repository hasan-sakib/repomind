from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, get_current_user, require_csrf_header
from app.domain.user import User
from app.schemas.user import UserPublic, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def get_me(user: Annotated[User, Depends(get_current_user)]) -> UserPublic:
    return UserPublic.from_user(user)


@router.patch("/me", response_model=UserPublic, dependencies=[Depends(require_csrf_header)])
async def update_me(
    body: UserUpdateRequest, db: DbSession, user: Annotated[User, Depends(get_current_user)]
) -> UserPublic:
    user.full_name = body.full_name
    await db.commit()
    await db.refresh(user)
    return UserPublic.from_user(user)
