from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.routers import employee

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)


Base.metadata.create_all(bind=engine)

app.include_router(employee.router)

@app.get("/")
def greet():
    return {"msg" : "Hello World"}