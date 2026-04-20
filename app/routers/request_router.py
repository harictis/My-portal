from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models, schemas
from app.services.audit_service import create_audit_log
from app import workflow

router = APIRouter()


# Database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/request-access", response_model=schemas.AccessRequestCreated)
def create_request(request: schemas.AccessRequestCreate, db: Session = Depends(get_db)):
    new_request = models.AccessRequest(
        user_name=request.user_name,
        repository=request.repository,
        access_type=request.access_type,
        reason=request.reason,
        status=workflow.STATUS_PENDING
    )

    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    
    create_audit_log(
    db=db,
    request_id=new_request.id,
    action=workflow.ACTION_REQUEST_CREATED,
    performed_by=request.user_name,
    details=f"Requested {request.access_type} access to {request.repository}"
)

    return {
        "message": "Access request created",
        "request_id": new_request.id
    }


@router.get("/requests", response_model=list[schemas.AccessRequestResponse])
def list_requests(
    status: Optional[str] = None,
    repository: Optional[str] = None,
    user_name: Optional[str] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.AccessRequest)

    if status:
        normalized_status = workflow.normalize_status(status)
        if normalized_status not in workflow.REQUEST_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid request status")
        query = query.filter(models.AccessRequest.status == normalized_status)

    if created_from and created_to and created_from > created_to:
        raise HTTPException(status_code=400, detail="created_from cannot be after created_to")

    if repository:
        query = query.filter(models.AccessRequest.repository == repository.strip())

    if user_name:
        query = query.filter(models.AccessRequest.user_name == user_name.strip())

    if created_from:
        query = query.filter(models.AccessRequest.created_at >= created_from)

    if created_to:
        query = query.filter(models.AccessRequest.created_at <= created_to)

    return query.order_by(models.AccessRequest.created_at.desc()).all()


@router.get("/requests/{request_id}", response_model=schemas.AccessRequestResponse)
def get_request(request_id: int, db: Session = Depends(get_db)):
    access_request = db.query(models.AccessRequest).filter(models.AccessRequest.id == request_id).first()

    if not access_request:
        raise HTTPException(status_code=404, detail="Request not found")

    return access_request


@router.patch("/requests/{request_id}/cancel", response_model=schemas.AccessRequestCancelled)
def cancel_request(
    request_id: int,
    cancellation: schemas.CancelAccessRequest,
    db: Session = Depends(get_db),
):
    access_request = db.query(models.AccessRequest).filter(models.AccessRequest.id == request_id).first()

    if not access_request:
        raise HTTPException(status_code=404, detail="Request not found")

    if not workflow.can_cancel(access_request.status):
        raise HTTPException(status_code=409, detail="Only pending requests can be cancelled")

    access_request.status = workflow.STATUS_CANCELLED

    details = f"{cancellation.cancelled_by} cancelled request {access_request.id}"
    if cancellation.reason:
        details = f"{details}: {cancellation.reason}"

    create_audit_log(
        db=db,
        request_id=access_request.id,
        action=workflow.ACTION_REQUEST_CANCELLED,
        performed_by=cancellation.cancelled_by,
        details=details,
    )

    db.refresh(access_request)

    return {
        "message": "Access request cancelled",
        "status": access_request.status,
    }
