from fastapi import Depends, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.auth import router as auth_router
from src.api.v1.dictionaries import router as dict_router
from src.api.v1.learning import router as learning_router
from src.api.v1.system_dictionaries import router as sys_dict_router
from src.api.v1.users import router as users_router
from src.api.v1.words import router as words_router
from src.database import get_db

app = FastAPI(
    title="English TMA API MVP",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(words_router, prefix="/api/v1")
app.include_router(dict_router, prefix="/api/v1")
app.include_router(sys_dict_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(learning_router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health_check(
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        await db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected",
            "step": "12_learning_engine",
        }
    except Exception as exc:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "error",
            "database": "disconnected",
            "step": "12_learning_engine",
            "detail": str(exc),
        }