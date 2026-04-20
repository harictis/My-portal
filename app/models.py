from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import Text

class AccessRequest(Base):
    __tablename__ = "access_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String, nullable=False)
    repository = Column(String, nullable=False)
    access_type = Column(String, nullable=False)  # read or write
    reason = Column(String, nullable=False)
    status = Column(String, default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)
    
class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("access_requests.id"))
    comment_by = Column(String, nullable=False)
    comment_text = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    performed_by = Column(String, nullable=False)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)