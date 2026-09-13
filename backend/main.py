from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
import certifi
import logging
from config import MONGODB_URI, MONGODB_DB, UPLOAD_DIR, FRAMES_DIR, REPORTS_DIR
from routers import audits, modules, reports

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Connecting to MongoDB...")

    # TLS is required for Atlas (mongodb+srv://) but breaks a local mongod,
    # which speaks plain TCP. Passing tlsCAFile at all implicitly enables TLS,
    # so only pass it for hosted connections.
    client_kwargs = {}
    if MONGODB_URI.startswith("mongodb+srv://"):
        client_kwargs["tlsCAFile"] = certifi.where()

    app.state.mongo_client = AsyncIOMotorClient(MONGODB_URI, **client_kwargs)
    app.state.db = app.state.mongo_client[MONGODB_DB]

    # Motor connects lazily, so verify now rather than failing later on an
    # unrelated route with a confusing traceback.
    await app.state.db.command("ping")
    logger.info(f"Connected to MongoDB database: {MONGODB_DB}")

    app.state.depth_estimator = None  # loaded lazily on first video upload
    yield
    # Shutdown
    app.state.mongo_client.close()
    logger.info("MongoDB connection closed.")


app = FastAPI(title="PASSLINE API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files and generated assets
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/frames", StaticFiles(directory=str(FRAMES_DIR)), name="frames")
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")

app.include_router(audits.router, prefix="/api", tags=["audits"])
app.include_router(modules.router, prefix="/api", tags=["modules"])
app.include_router(reports.router, prefix="/api", tags=["reports"])


@app.get("/health")
async def health():
    return {"status": "ok"}