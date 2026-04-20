from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models, schemas
from app.services.audit_service import create_audit_log
from app import workflow

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/approve-leadership/{request_id}", response_model=schemas.LeadershipApprovalResponse)
def approve_request(request_id: int, approval: schemas.LeadershipApproval, db: Session = Depends(get_db)):

    req = db.query(models.AccessRequest).filter(models.AccessRequest.id == request_id).first()

    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    decision = workflow.normalize_decision(approval.decision)

    if decision == workflow.DECISION_APPROVE:
        req.status = workflow.STATUS_LEADERSHIP_APPROVED
        audit_action = workflow.ACTION_LEADERSHIP_APPROVED
    elif decision == workflow.DECISION_REJECT:
        req.status = workflow.STATUS_REJECTED
        audit_action = workflow.ACTION_LEADERSHIP_REJECTED
    else:
        raise HTTPException(status_code=400, detail="Decision must be approve or reject")

    create_audit_log(
        db=db,
        request_id=req.id,
        action=audit_action,
        performed_by=approval.approved_by,
        details=f"{approval.approved_by} set request {req.id} to {req.status}"
    )

    db.refresh(req)

    return {
        "message": "Leadership decision recorded",
        "status": req.status
    }
    
@router.post("/add-comment", response_model=schemas.CommentCreated)
def add_comment(comment: schemas.CommentCreate, db: Session = Depends(get_db)):
    req = db.query(models.AccessRequest).filter(models.AccessRequest.id == comment.request_id).first()

    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    new_comment = models.Comment(
        request_id=comment.request_id,
        comment_by=comment.comment_by,
        comment_text=comment.comment_text
    )

    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    return {
        "message": "Comment added",
        "comment_id": new_comment.id,
    }
