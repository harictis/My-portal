from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models, schemas

router = APIRouter()


# Database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/request-access")
def create_request(request: schemas.AccessRequestCreate, db: Session = Depends(get_db)):
    new_request = models.AccessRequest(
        user_name=request.user_name,
        repository=request.repository,
        access_type=request.access_type,
        reason=request.reason,
        status="PENDING"
    )

    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    return {
        "message": "Access request created",
        "request_id": new_request.id
    }