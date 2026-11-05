import unittest
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND_DIR)

from app.core.permissions import Role, Permission, has_permission

class TestPermissions(unittest.TestCase):
    def test_investigator_cannot_manage_rules(self):
        self.assertFalse(has_permission(Role.INVESTIGATOR.value, Permission.MANAGE_RULES))

    def test_fraud_admin_can_manage_rules(self):
        self.assertTrue(has_permission(Role.FRAUD_ADMIN.value, Permission.MANAGE_RULES))

    def test_investigator_can_submit_disposition(self):
        self.assertTrue(has_permission(Role.INVESTIGATOR.value, Permission.SUBMIT_DISPOSITION))

    def test_investigator_can_view_audit(self):
        self.assertTrue(has_permission(Role.INVESTIGATOR.value, Permission.VIEW_AUDIT))

    def test_senior_investigator_can_approve_disposition(self):
        self.assertTrue(has_permission(Role.SENIOR_INVESTIGATOR.value, Permission.APPROVE_DISPOSITION))

    def test_auditor_is_read_only(self):
        self.assertTrue(has_permission(Role.AUDITOR.value, Permission.VIEW_AUDIT))
        self.assertFalse(has_permission(Role.AUDITOR.value, Permission.SUBMIT_DISPOSITION))

if __name__ == "__main__":
    unittest.main()
