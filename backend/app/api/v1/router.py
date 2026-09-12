from fastapi import APIRouter

from app.api.v1.routes import (
    analytics,
    architecture,
    auth,
    chat,
    github,
    health,
    onboarding,
    organizations,
    pull_requests,
    repositories,
    users,
    webhooks,
    websocket,
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
api_router.include_router(pull_requests.router)
api_router.include_router(onboarding.router)
api_router.include_router(analytics.router)
api_router.include_router(webhooks.router)
api_router.include_router(websocket.router)
