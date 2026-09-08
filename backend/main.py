"""Convenience runner for RETRACE backend."""
from backend.app.main import app
from backend.core.config import settings

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.ENVIRONMENT == "development"),
    )
