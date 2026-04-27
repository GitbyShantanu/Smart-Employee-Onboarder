from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.routers import employee
from backend.routers import email_agent

app = FastAPI()

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