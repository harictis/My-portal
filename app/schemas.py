from pydantic import BaseModel


class AccessRequestCreate(BaseModel):
    user_name: str
    repository: str
    access_type: str
    reason: str
    
class LeadershipApproval(BaseModel):
    approved_by: str
    decision: str
    
class CommentCreate(BaseModel):
    request_id: int
    comment_by: str
    comment_text: str