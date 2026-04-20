import unittest

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas, workflow
from app.routers.approval_router import add_comment, approve_request


class LeadershipApprovalTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(bind=self.engine)
        testing_session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = testing_session()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def create_access_request(self):
        access_request = models.AccessRequest(
            user_name="hari",
            repository="harictis/My-portal",
            access_type="write",
            reason="Need to ship backend changes",
            status=workflow.STATUS_PENDING,
        )
        self.db.add(access_request)
        self.db.commit()
        self.db.refresh(access_request)
        return access_request

    def test_approve_request_updates_status_and_audit_log(self):
        access_request = self.create_access_request()
        approval = schemas.LeadershipApproval(
            approved_by="tech-lead",
            decision="approve",
        )

        response = approve_request(access_request.id, approval, self.db)

        self.db.refresh(access_request)
        audit_log = self.db.query(models.AuditLog).filter_by(request_id=access_request.id).one()

        self.assertEqual(response["status"], workflow.STATUS_LEADERSHIP_APPROVED)
        self.assertEqual(access_request.status, workflow.STATUS_LEADERSHIP_APPROVED)
        self.assertEqual(audit_log.action, workflow.ACTION_LEADERSHIP_APPROVED)
        self.assertEqual(audit_log.performed_by, "tech-lead")

    def test_reject_request_updates_status_and_audit_log(self):
        access_request = self.create_access_request()
        approval = schemas.LeadershipApproval(
            approved_by="tech-lead",
            decision="reject",
        )

        response = approve_request(access_request.id, approval, self.db)

        self.db.refresh(access_request)
        audit_log = self.db.query(models.AuditLog).filter_by(request_id=access_request.id).one()

        self.assertEqual(response["status"], workflow.STATUS_REJECTED)
        self.assertEqual(access_request.status, workflow.STATUS_REJECTED)
        self.assertEqual(audit_log.action, workflow.ACTION_LEADERSHIP_REJECTED)
        self.assertEqual(audit_log.performed_by, "tech-lead")

    def test_missing_request_returns_404(self):
        approval = schemas.LeadershipApproval(
            approved_by="tech-lead",
            decision="approve",
        )

        with self.assertRaises(HTTPException) as error:
            approve_request(999, approval, self.db)

        self.assertEqual(error.exception.status_code, 404)
        self.assertEqual(error.exception.detail, "Request not found")

    def test_invalid_decision_returns_400(self):
        access_request = self.create_access_request()

        approval = schemas.LeadershipApproval.model_construct(
            approved_by="tech-lead",
            decision="maybe",
        )

        with self.assertRaises(HTTPException) as error:
            approve_request(access_request.id, approval, self.db)

        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(error.exception.detail, "Decision must be approve or reject")

    def test_schema_rejects_invalid_decision(self):
        with self.assertRaises(ValidationError):
            schemas.LeadershipApproval(
                approved_by="tech-lead",
                decision="maybe",
            )

    def test_add_comment_creates_comment_for_existing_request(self):
        access_request = self.create_access_request()
        comment = schemas.CommentCreate(
            request_id=access_request.id,
            comment_by="devops-user",
            comment_text="Looks good",
        )

        response = add_comment(comment, self.db)

        saved_comment = self.db.query(models.Comment).filter_by(id=response["comment_id"]).one()

        self.assertEqual(response["message"], "Comment added")
        self.assertEqual(saved_comment.request_id, access_request.id)
        self.assertEqual(saved_comment.comment_by, "devops-user")
        self.assertEqual(saved_comment.comment_text, "Looks good")

    def test_add_comment_returns_404_for_missing_request(self):
        comment = schemas.CommentCreate(
            request_id=999,
            comment_by="devops-user",
            comment_text="Looks good",
        )

        with self.assertRaises(HTTPException) as error:
            add_comment(comment, self.db)

        self.assertEqual(error.exception.status_code, 404)
        self.assertEqual(error.exception.detail, "Request not found")


if __name__ == "__main__":
    unittest.main()
