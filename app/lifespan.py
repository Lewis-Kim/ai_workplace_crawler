from contextlib import asynccontextmanager
import logging

from pipeline.runner import start_pipeline, stop_pipeline

logger = logging.getLogger("lifespan")


@asynccontextmanager
async def lifespan(app):
    logger.info("🚀 FastAPI startup")
    start_pipeline()

    yield

    logger.info("🛑 FastAPI shutdown")
    stop_pipeline()
