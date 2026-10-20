from fastapi import APIRouter

from app.api import admin, auth, chat, tasks

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(tasks.router)
api_router.include_router(admin.router)
api_router.include_router(chat.router)
