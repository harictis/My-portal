from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models, schemas

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/approve-leadership/{request_id}")
def approve_request(request_id: int, approval: schemas.LeadershipApproval, db: Session = Depends(get_db)):

    req = db.query(models.AccessRequest).filter(models.AccessRequest.id == request_id).first()

    if not req:
        return {"error": "Request not found"}

    if approval.decision == "approve":
        req.status = "LEADERSHIP_APPROVED"
    else:
        req.status = "REJECTED"

    db.commit()

    return {
        "message": "Leadership decision recorded",
        "status": req.status
    }
    
@router.post("/add-comment")
def add_comment(comment: schemas.CommentCreate, db: Session = Depends(get_db)):

    new_comment = models.Comment(
        request_id=comment.request_id,
        comment_by=comment.comment_by,
        comment_text=comment.comment_text
    )

    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    return {"message": "Comment added"}