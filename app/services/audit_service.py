from app import models
from sqlalchemy.orm import Session


def create_audit_log(db: Session, request_id: int, action: str, performed_by: str, details: str = ""):
    
    log = models.AuditLog(
        request_id=request_id,
        action=action,
        performed_by=performed_by,
        details=details
    )

    db.add(log)
    db.commit()