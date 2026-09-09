from fastapi import APIRouter

from app.api.v1.routes import (
    architecture,
    auth,
    chat,
    github,
    health,
    organizations,
    repositories,
    users,
    webhooks,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(users.router)
api_router.include_router(github.router)
api_router.include_router(github.callback_router)
api_router.include_router(repositories.org_router)
api_router.include_router(repositories.router)
api_router.include_router(chat.router)
api_router.include_router(architecture.router)
api_router.include_router(webhooks.router)
