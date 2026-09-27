"""Google Photos Discovery Engine — Main Application Entrypoint.

Starts the FastAPI application which serves both:
1. Analytical REST API endpoints (/api/health, /api/overview, /api/evidence, /api/clusters, /api/opportunities, /api/findings)
2. Interactive React 18 + Vite PM Analytical Workbench (mounted at root /)
"""

import sys
import uvicorn
from src.config.settings import settings
from src.config.logger import logger
from src.api.main import app


def main():
    logger.info("==================================================")
    logger.info("Starting Google Photos Discovery Engine Server...")
    logger.info(f"Host: {settings.HOST} | Port: {settings.PORT}")
    logger.info(
        f"Groq Model: {settings.GROQ_MODEL} (Configured: {bool(settings.GROQ_API_KEY)})"
    )
    logger.info(f"Access Dashboard: http://127.0.0.1:{settings.PORT}/")
    logger.info(f"Access API Docs:  http://127.0.0.1:{settings.PORT}/docs")
    logger.info("==================================================")

    uvicorn.run(
        "src.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=False,
    )


if __name__ == "__main__":
    main()
