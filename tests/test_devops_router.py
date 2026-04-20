import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, workflow
from app.routers import devops_router


class DevOpsAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(bind=self.engine)
        testing_session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = testing_session()
        self.original_add_user_to_team = devops_router.add_user_to_team

    def tearDown(self):
        devops_router.add_user_to_team = self.original_add_user_to_team
        self.db.close()
        self.engine.dispose()

    def create_access_request(self, status=workflow.STATUS_LEADERSHIP_APPROVED):
        access_request = models.AccessRequest(
            user_name="hari",
            repository="harictis/My-portal",
            access_type=workflow.ACCESS_TYPE_WRITE,
            reason="Need backend access",
            status=status,
        )
        self.db.add(access_request)
        self.db.commit()
        self.db.refresh(access_request)
        return access_request

    def test_devops_authorize_completes_approved_request(self):
        access_request = self.create_access_request()
        devops_router.add_user_to_team = lambda username, team_slug: (
            200,
            {"user": username, "team": team_slug},
        )

        response = devops_router.devops_authorize(access_request.id, " backend-team ", self.db)

        self.db.refresh(access_request)

        self.assertEqual(response["team_assigned"], "backend-team")
        self.assertEqual(response["status"], workflow.STATUS_COMPLETED)
        self.assertEqual(access_request.status, workflow.STATUS_COMPLETED)

    def test_devops_authorize_returns_404_for_missing_request(self):
        with self.assertRaises(HTTPException) as error:
            devops_router.devops_authorize(999, "backend-team", self.db)

        self.assertEqual(error.exception.status_code, 404)
        self.assertEqual(error.exception.detail, "Request not found")

    def test_devops_authorize_rejects_unapproved_request(self):
        access_request = self.create_access_request(status=workflow.STATUS_PENDING)

        with self.assertRaises(HTTPException) as error:
            devops_router.devops_authorize(access_request.id, "backend-team", self.db)

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(error.exception.detail, "Request not approved by leadership yet")

    def test_devops_authorize_rejects_blank_team_slug(self):
        access_request = self.create_access_request()

        with self.assertRaises(HTTPException) as error:
            devops_router.devops_authorize(access_request.id, "   ", self.db)

        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(error.exception.detail, "Team slug cannot be blank")

    def test_devops_authorize_maps_github_failure_to_502(self):
        access_request = self.create_access_request()
        devops_router.add_user_to_team = lambda username, team_slug: (
            500,
            {"message": "GitHub failed"},
        )

        with self.assertRaises(HTTPException) as error:
            devops_router.devops_authorize(access_request.id, "backend-team", self.db)

        self.assertEqual(error.exception.status_code, 502)
        self.assertEqual(error.exception.detail["message"], "GitHub operation failed")
        self.assertEqual(
            error.exception.detail["github_response"],
            {"message": "GitHub failed"},
        )


if __name__ == "__main__":
    unittest.main()
