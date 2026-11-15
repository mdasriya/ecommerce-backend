from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.database.dependencies import get_db
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.category.router import router as category_router

# NOTE: tables are managed by Alembic migrations (`alembic upgrade head`),
# not created on startup.

app = FastAPI(
    title=settings.APP_NAME,
    # Hide interactive API docs in production.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# ---------------------------------------------------------------- CORS
# Only the frontends listed in CORS_ORIGINS may call this API from a browser.
# allow_credentials=True because refresh token is sent via HttpOnly cookie.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ------------------------------------------------------ Exception handlers
register_exception_handlers(app)

# ----------------------------------------------------------------- Routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(category_router)


@app.get("/")
def home():
    return {"message": "Welcome to our E-commerce API"}


@app.get("/db_check")
def db_check(db: Session = Depends(get_db)):
    # Perform a simple query to check the database connection
    value = db.execute(text("SELECT 1")).scalar()
    return {"message": "Database connection is successful", "value": value}
