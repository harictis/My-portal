from fastapi import FastAPI
from app.database import engine
from app import models
from app.routers import request_router, approval_router, devops_router

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(request_router.router)
app.include_router(approval_router.router)
app.include_router(devops_router.router)

@app.get("/")
def home():
    return {"message": "DevOps Access Portal API running"}