import unittest
from datetime import datetime, timedelta

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas, workflow
from app.routers.request_router import cancel_request, get_request, list_requests


class AccessRequestLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(bind=self.engine)
        testing_session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = testing_session()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def create_access_request(
        self,
        user_name="hari",
        repository="harictis/My-portal",
        access_type="write",
        reason="Need backend access",
        status=workflow.STATUS_PENDING,
        created_at=None,
    ):
        access_request = models.AccessRequest(
            user_name=user_name,
            repository=repository,
            access_type=access_type,
            reason=reason,
            status=status,
            created_at=created_at or datetime.utcnow(),
        )
        self.db.add(access_request)
        self.db.commit()
        self.db.refresh(access_request)
        return access_request

    def test_get_request_returns_request_detail(self):
        access_request = self.create_access_request()

        result = get_request(access_request.id, self.db)

        self.assertEqual(result.id, access_request.id)
        self.assertEqual(result.repository, "harictis/My-portal")
        self.assertEqual(result.status, workflow.STATUS_PENDING)

    def test_get_request_returns_404_for_missing_request(self):
        with self.assertRaises(HTTPException) as error:
            get_request(999, self.db)

        self.assertEqual(error.exception.status_code, 404)
        self.assertEqual(error.exception.detail, "Request not found")

    def test_list_requests_filters_by_status_repository_user_and_date(self):
        now = datetime.utcnow()
        matching = self.create_access_request(
            user_name="hari",
            repository="harictis/My-portal",
            status=workflow.STATUS_PENDING,
            created_at=now,
        )
        self.create_access_request(
            user_name="someone-else",
            repository="harictis/My-portal",
            status=workflow.STATUS_PENDING,
            created_at=now,
        )
        self.create_access_request(
            user_name="hari",
            repository="harictis/another-repo",
            status=workflow.STATUS_PENDING,
            created_at=now,
        )
        self.create_access_request(
            user_name="hari",
            repository="harictis/My-portal",
            status=workflow.STATUS_REJECTED,
            created_at=now,
        )
        self.create_access_request(
            user_name="hari",
            repository="harictis/My-portal",
            status=workflow.STATUS_PENDING,
            created_at=now - timedelta(days=5),
        )

        results = list_requests(
            status="pending",
            repository="harictis/My-portal",
            user_name="hari",
            created_from=now - timedelta(days=1),
            created_to=now + timedelta(days=1),
            db=self.db,
        )

        self.assertEqual([request.id for request in results], [matching.id])

    def test_list_requests_rejects_invalid_status_filter(self):
        with self.assertRaises(HTTPException) as error:
            list_requests(status="waiting", db=self.db)

        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(error.exception.detail, "Invalid request status")

    def test_list_requests_rejects_invalid_date_range(self):
        now = datetime.utcnow()

        with self.assertRaises(HTTPException) as error:
            list_requests(
                created_from=now + timedelta(days=1),
                created_to=now,
                db=self.db,
            )

        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(error.exception.detail, "created_from cannot be after created_to")

    def test_cancel_request_updates_status_and_audit_log(self):
        access_request = self.create_access_request()
        cancellation = schemas.CancelAccessRequest(
            cancelled_by="hari",
            reason="No longer needed",
        )

        response = cancel_request(access_request.id, cancellation, self.db)

        self.db.refresh(access_request)
        audit_log = self.db.query(models.AuditLog).filter_by(request_id=access_request.id).one()

        self.assertEqual(response["status"], workflow.STATUS_CANCELLED)
        self.assertEqual(access_request.status, workflow.STATUS_CANCELLED)
        self.assertEqual(audit_log.action, workflow.ACTION_REQUEST_CANCELLED)
        self.assertEqual(audit_log.performed_by, "hari")
        self.assertIn("No longer needed", audit_log.details)

    def test_cancel_request_rejects_non_pending_request(self):
        access_request = self.create_access_request(status=workflow.STATUS_LEADERSHIP_APPROVED)
        cancellation = schemas.CancelAccessRequest(cancelled_by="hari")

        with self.assertRaises(HTTPException) as error:
            cancel_request(access_request.id, cancellation, self.db)

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(error.exception.detail, "Only pending requests can be cancelled")

    def test_create_schema_normalizes_and_validates_access_type(self):
        request = schemas.AccessRequestCreate(
            user_name=" hari ",
            repository=" harictis/My-portal ",
            access_type=" WRITE ",
            reason=" backend work ",
        )

        self.assertEqual(request.user_name, "hari")
        self.assertEqual(request.repository, "harictis/My-portal")
        self.assertEqual(request.access_type, workflow.ACCESS_TYPE_WRITE)
        self.assertEqual(request.reason, "backend work")

    def test_create_schema_rejects_invalid_access_type(self):
        with self.assertRaises(ValidationError):
            schemas.AccessRequestCreate(
                user_name="hari",
                repository="harictis/My-portal",
                access_type="admin",
                reason="Need access",
            )

    def test_cancel_schema_normalizes_optional_reason(self):
        cancellation = schemas.CancelAccessRequest(
            cancelled_by=" hari ",
            reason="   ",
        )

        self.assertEqual(cancellation.cancelled_by, "hari")
        self.assertIsNone(cancellation.reason)


if __name__ == "__main__":
    unittest.main()
