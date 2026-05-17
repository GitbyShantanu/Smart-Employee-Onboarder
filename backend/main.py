from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.database import engine, Base
from backend.routers import employee
from backend.routers import email_agent
from backend import email_listener

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages startup and shutdown events."""
    # --- STARTUP ---
    email_listener.start_listener()
    yield
    # --- SHUTDOWN ---
    email_listener.stop_listener()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False
)

Base.metadata.create_all(bind=engine)

app.include_router(employee.router)
app.include_router(email_agent.router)

# Serve frontend static files (CSS, JS)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse(str(FRONTEND_DIR / "index.html"))

@app.get("/api/listener/status")
def listener_status():
    return email_listener.get_status()