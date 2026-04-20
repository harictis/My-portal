import unittest

from app import workflow


class WorkflowTests(unittest.TestCase):
    def test_normalize_status(self):
        self.assertEqual(workflow.normalize_status(" pending "), workflow.STATUS_PENDING)

    def test_only_pending_requests_can_be_cancelled(self):
        self.assertTrue(workflow.can_cancel(workflow.STATUS_PENDING))
        self.assertFalse(workflow.can_cancel(workflow.STATUS_LEADERSHIP_APPROVED))
        self.assertFalse(workflow.can_cancel(workflow.STATUS_COMPLETED))


if __name__ == "__main__":
    unittest.main()
