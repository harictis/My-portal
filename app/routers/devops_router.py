from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/devops-authorize/{request_id}")
def devops_authorize(request_id: int, team_slug: str, db: Session = Depends(get_db)):

    req = db.query(models.AccessRequest).filter(models.AccessRequest.id == request_id).first()

    if not req:
        return {"error": "Request not found"}

    if req.status != "LEADERSHIP_APPROVED":
        return {"error": "Request not approved by leadership yet"}

    req.status = "DEVOPS_APPROVED"

    db.commit()

    return {
        "message": "DevOps authorization completed",
        "team_assigned": team_slug,
        "status": req.status
    }