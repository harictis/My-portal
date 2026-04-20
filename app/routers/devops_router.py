from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models, schemas
from app.services.github_service import add_user_to_team
from app import workflow

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/devops-authorize/{request_id}", response_model=schemas.DevOpsAuthorizationResponse)
def devops_authorize(request_id: int, team_slug: str, db: Session = Depends(get_db)):

    req = db.query(models.AccessRequest).filter(models.AccessRequest.id == request_id).first()

    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.status != workflow.STATUS_LEADERSHIP_APPROVED:
        raise HTTPException(status_code=409, detail="Request not approved by leadership yet")

    team_slug = team_slug.strip()
    if not team_slug:
        raise HTTPException(status_code=400, detail="Team slug cannot be blank")

    req.status = workflow.STATUS_DEVOPS_APPROVED
    
        # Step 2: Call GitHub (or mock)
    status_code, response = add_user_to_team(req.user_name, team_slug)

    # Step 3: Handle failure
    if status_code not in [200, 201]:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "GitHub operation failed",
                "github_response": response,
            },
        )

    # Step 4: Final state
    req.status = workflow.STATUS_COMPLETED

    db.commit()

    return {
        "message": "DevOps authorization completed",
        "team_assigned": team_slug,
        "status": req.status
    }
