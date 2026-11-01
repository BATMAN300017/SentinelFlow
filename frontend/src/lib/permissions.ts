import { UserRole } from './auth';

export interface RolePermissions {
  canViewDashboard: boolean;
  canViewTransactions: boolean;
  canViewAlerts: boolean;
  canInvestigate: boolean;
  canSubmitDisposition: boolean;
  canApproveDisposition: boolean;
  canManageRules: boolean;
  canRetrainModel: boolean;
  canAccessDatasetLab: boolean;
  canViewAuditLogs: boolean;
  isReadOnly: boolean;
}

export function getPermissionsForRole(role: UserRole): RolePermissions {
  switch (role) {
    case 'FRAUD_ADMIN':
      return {
        canViewDashboard: true,
        canViewTransactions: true,
        canViewAlerts: true,
        canInvestigate: true,
        canSubmitDisposition: true,
        canApproveDisposition: true,
        canManageRules: true,
        canRetrainModel: true,
        canAccessDatasetLab: true,
        canViewAuditLogs: true,
        isReadOnly: false,
      };
    case 'SENIOR_INVESTIGATOR':
      return {
        canViewDashboard: true,
        canViewTransactions: true,
        canViewAlerts: true,
        canInvestigate: true,
        canSubmitDisposition: true,
        canApproveDisposition: true,
        canManageRules: false,
        canRetrainModel: false,
        canAccessDatasetLab: true,
        canViewAuditLogs: true,
        isReadOnly: false,
      };
    case 'INVESTIGATOR':
      return {
        canViewDashboard: true,
        canViewTransactions: true,
        canViewAlerts: true,
        canInvestigate: true,
        canSubmitDisposition: true,
        canApproveDisposition: false,
        canManageRules: false,
        canRetrainModel: false,
        canAccessDatasetLab: false,
        canViewAuditLogs: true,
        isReadOnly: false,
      };
    case 'AUDITOR':
    default:
      return {
        canViewDashboard: true,
        canViewTransactions: true,
        canViewAlerts: true,
        canInvestigate: false,
        canSubmitDisposition: false,
        canApproveDisposition: false,
        canManageRules: false,
        canRetrainModel: false,
        canAccessDatasetLab: true,
        canViewAuditLogs: true,
        isReadOnly: true,
      };
  }
}
