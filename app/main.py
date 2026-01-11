import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.lifespan import lifespan
from app.api.pipeline import router as pipeline_router
from app.api.upload import router as upload_router
from app.api.status import router as status_router
from app.api.ui import router as ui_router
from app.api.upload_folder_raw import router as upload_folder_raw_router
from app.api.logs import router as log_router
from app.api.search import router as search_router
from app.api.documents import router as documents_router
from app.api.dashboard import router as dashboard_router
from app.api.rag import router as rag_router

print("🔥 MAIN APP LOADED")
LOG_DIR = Path("../logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "system.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),  # 콘솔도 같이
    ],
)

app = FastAPI(
    title="Ingest Pipeline API",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(pipeline_router)
app.include_router(upload_router)
app.include_router(status_router)
app.include_router(ui_router)
app.include_router(upload_folder_raw_router)
app.include_router(log_router, prefix="/api")
app.include_router(search_router)
app.include_router(documents_router)
app.include_router(dashboard_router)
app.include_router(rag_router)


