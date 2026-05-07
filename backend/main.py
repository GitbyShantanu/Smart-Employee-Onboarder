from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.routers import employee
from backend.routers import email_agent
from backend import email_listener


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

@app.get("/")
def greet():    
    return {"msg" : "Hello World"}

@app.get("/api/listener/status")
def listener_status():
    return email_listener.get_status()