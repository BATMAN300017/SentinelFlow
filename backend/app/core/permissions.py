from enum import Enum
from typing import Set

class Role(str, Enum):
    INVESTIGATOR = "investigator"
    SENIOR_INVESTIGATOR = "senior_investigator"
    FRAUD_ADMIN = "fraud_admin"
    AUDITOR = "auditor"

class Permission(str, Enum):
    # Case & Alert
    VIEW_ALERTS = "view_alerts"
    TRIAGE_ALERT = "triage_alert"
    DISMISS_ALERT = "dismiss_alert"
    VIEW_INVESTIGATION = "view_investigation"
    CREATE_INVESTIGATION = "create_investigation"
    EDIT_INVESTIGATION = "edit_investigation"
    ADD_EVIDENCE = "add_evidence"
    SUBMIT_DISPOSITION = "submit_disposition"
    APPROVE_DISPOSITION = "approve_disposition"
    REOPEN_INVESTIGATION = "reopen_investigation"
    
    # Rules & Config
    VIEW_RULES = "view_rules"
    MANAGE_RULES = "manage_rules"
    SIMULATE_RULES = "simulate_rules"
    
    # Simulation
    CONTROL_SIMULATION = "control_simulation"
    
    # Learning & Models
    VIEW_LEARNING = "view_learning"
    TRAIN_MODEL = "train_model"
    PROMOTE_MODEL = "promote_model"
    ROLLBACK_MODEL = "rollback_model"
    
    # Audit & Reports
    VIEW_AUDIT = "view_audit"
    EXPORT_REPORT = "export_report"

ROLE_PERMISSIONS = {
    Role.INVESTIGATOR: {
        Permission.VIEW_ALERTS,
        Permission.TRIAGE_ALERT,
        Permission.DISMISS_ALERT,
        Permission.VIEW_INVESTIGATION,
        Permission.CREATE_INVESTIGATION,
        Permission.EDIT_INVESTIGATION,
        Permission.ADD_EVIDENCE,
        Permission.SUBMIT_DISPOSITION,
        Permission.VIEW_RULES,
        Permission.SIMULATE_RULES,
        Permission.VIEW_LEARNING,
        Permission.VIEW_AUDIT,
        Permission.EXPORT_REPORT,
    },
    Role.SENIOR_INVESTIGATOR: {
        Permission.VIEW_ALERTS,
        Permission.TRIAGE_ALERT,
        Permission.DISMISS_ALERT,
        Permission.VIEW_INVESTIGATION,
        Permission.CREATE_INVESTIGATION,
        Permission.EDIT_INVESTIGATION,
        Permission.ADD_EVIDENCE,
        Permission.SUBMIT_DISPOSITION,
        Permission.APPROVE_DISPOSITION,
        Permission.REOPEN_INVESTIGATION,
        Permission.VIEW_RULES,
        Permission.SIMULATE_RULES,
        Permission.VIEW_LEARNING,
        Permission.TRAIN_MODEL,
        Permission.PROMOTE_MODEL,
        Permission.VIEW_AUDIT,
        Permission.EXPORT_REPORT,
    },
    Role.FRAUD_ADMIN: {
        Permission.VIEW_ALERTS,
        Permission.TRIAGE_ALERT,
        Permission.DISMISS_ALERT,
        Permission.VIEW_INVESTIGATION,
        Permission.CREATE_INVESTIGATION,
        Permission.EDIT_INVESTIGATION,
        Permission.ADD_EVIDENCE,
        Permission.SUBMIT_DISPOSITION,
        Permission.APPROVE_DISPOSITION,
        Permission.REOPEN_INVESTIGATION,
        Permission.VIEW_RULES,
        Permission.MANAGE_RULES,
        Permission.SIMULATE_RULES,
        Permission.CONTROL_SIMULATION,
        Permission.VIEW_LEARNING,
        Permission.TRAIN_MODEL,
        Permission.PROMOTE_MODEL,
        Permission.ROLLBACK_MODEL,
        Permission.VIEW_AUDIT,
        Permission.EXPORT_REPORT,
    },
    Role.AUDITOR: {
        Permission.VIEW_ALERTS,
        Permission.VIEW_INVESTIGATION,
        Permission.VIEW_RULES,
        Permission.VIEW_LEARNING,
        Permission.VIEW_AUDIT,
        Permission.EXPORT_REPORT,
    }
}

def has_permission(user_role: str, permission: Permission) -> bool:
    try:
        r = Role(user_role)
        perms = ROLE_PERMISSIONS.get(r, set())
        return permission in perms
    except ValueError:
        return False
