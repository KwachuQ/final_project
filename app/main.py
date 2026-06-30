from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, health, assessements, dashboard
from app.settings import get_settings


# Application factory
def create_app() -> FastAPI:
    settings = get_settings()
    
    # Lifespan context manager
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(bind=engine)
        yield

    application = FastAPI(title="PyMigScore", lifespan=lifespan)

    # CORS: comma-separated origins or allow all
    origins = (
        [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]
        if settings.ALLOWED_ORIGINS
        else ["*"]
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(assessements.router)
    application.include_router(dashboard.router)

    return application


# Application instance
app = create_app()
