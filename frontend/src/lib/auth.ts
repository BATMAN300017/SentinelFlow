export type UserRole = 'AUDITOR' | 'INVESTIGATOR' | 'SENIOR_INVESTIGATOR' | 'FRAUD_ADMIN';

export interface UserSession {
  userId: string;
  name: string;
  email: string;
  role: UserRole;
  token?: string;
  avatarInitials: string;
}

const DEFAULT_USERS: Record<UserRole, UserSession> = {
  SENIOR_INVESTIGATOR: {
    userId: 'usr_sarah_chen',
    name: 'Sarah Chen',
    email: 'sarah.chen@sentinelflow.bank',
    role: 'SENIOR_INVESTIGATOR',
    avatarInitials: 'SC',
  },
  INVESTIGATOR: {
    userId: 'usr_marcus_vance',
    name: 'Marcus Vance',
    email: 'marcus.vance@sentinelflow.bank',
    role: 'INVESTIGATOR',
    avatarInitials: 'MV',
  },
  FRAUD_ADMIN: {
    userId: 'usr_elena_rostova',
    name: 'Elena Rostova',
    email: 'elena.rostova@sentinelflow.bank',
    role: 'FRAUD_ADMIN',
    avatarInitials: 'ER',
  },
  AUDITOR: {
    userId: 'usr_david_kim',
    name: 'David Kim',
    email: 'david.kim@audit.sentinelflow.bank',
    role: 'AUDITOR',
    avatarInitials: 'DK',
  },
};

const SESSION_KEY = 'sentinel_user_session';

export function getCurrentUser(): UserSession {
  if (typeof window === 'undefined') {
    return DEFAULT_USERS.SENIOR_INVESTIGATOR;
  }
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch (e) {
    // fallback
  }
  return DEFAULT_USERS.SENIOR_INVESTIGATOR;
}

export function setCurrentRole(role: UserRole): UserSession {
  const user = DEFAULT_USERS[role] || DEFAULT_USERS.SENIOR_INVESTIGATOR;
  if (typeof window !== 'undefined') {
    try {
      localStorage.setItem(SESSION_KEY, JSON.stringify(user));
      window.dispatchEvent(new Event('sentinel-auth-changed'));
    } catch (e) {
      // ignore
    }
  }
  return user;
}

export function logout(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem('sentinel_token');
    window.dispatchEvent(new Event('sentinel-auth-changed'));
  }
}
