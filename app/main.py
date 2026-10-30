from fastapi import FastAPI

from app.api.routes import auth, users
from app.core.exceptions import AppError, handle_app_error

app = FastAPI(title="Task Management API")

app.add_exception_handler(AppError, handle_app_error)

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
