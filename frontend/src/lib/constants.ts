export const APP_NAME = 'SentinelFlow AI';
export const APP_TAGLINE = 'The Self-Directed Fraud Investigation Platform';

export const SEVERITIES = {
  CRITICAL: { label: 'Critical', bg: 'bg-rose-500/15', text: 'text-rose-400', border: 'border-rose-500/40' },
  HIGH: { label: 'High', bg: 'bg-rose-500/10', text: 'text-rose-300', border: 'border-rose-500/30' },
  MEDIUM: { label: 'Medium', bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30' },
  LOW: { label: 'Low', bg: 'bg-sky-500/10', text: 'text-sky-400', border: 'border-sky-500/30' },
} as const;

export const CASE_STATUSES = {
  NEW: { label: 'New', color: 'text-slate-300 bg-slate-800 border-slate-700' },
  ASSIGNED: { label: 'Assigned', color: 'text-sky-400 bg-sky-950/60 border-sky-800' },
  IN_PROGRESS: { label: 'In Progress', color: 'text-amber-400 bg-amber-950/60 border-amber-800' },
  PENDING_REVIEW: { label: 'Pending Review', color: 'text-purple-400 bg-purple-950/60 border-purple-800' },
  DISPOSITIONED: { label: 'Dispositioned', color: 'text-emerald-400 bg-emerald-950/60 border-emerald-800' },
  CLOSED: { label: 'Closed', color: 'text-slate-400 bg-slate-900 border-slate-800' },
} as const;

export const CHANNELS = ['UPI', 'IMPS', 'NEFT', 'RTGS', 'SWIFT', 'ACH', 'CARD', 'CRYPTO'] as const;

export const NAVIGATION_SECTIONS = [
  {
    title: 'OPERATIONS',
    items: [
      { name: 'Fraud Command Center', href: '/dashboard', icon: 'LayoutDashboard' },
      { name: 'Live Transactions', href: '/transactions', icon: 'ArrowLeftRight' },
      { name: 'Alerts Queue & Triage', href: '/alerts', icon: 'ShieldAlert' },
      { name: 'Investigation Workspace', href: '/investigations', icon: 'Briefcase' },
    ],
  },
  {
    title: 'GRAPH & SURVEILLANCE',
    items: [
      { name: 'Network Intelligence', href: '/network', icon: 'Network' },
      { name: 'Entities & Accounts', href: '/entities', icon: 'Users' },
    ],
  },
  {
    title: 'MACHINE LEARNING & AUDIT',
    items: [
      { name: 'Model Intelligence', href: '/intelligence', icon: 'BrainCircuit' },
      { name: 'Feedback & Learning', href: '/feedback', icon: 'Cpu' },
      { name: 'Detection Rules', href: '/rules', icon: 'FileCode2' },
      { name: 'Audit Trail', href: '/audit', icon: 'ScrollText' },
    ],
  },
  {
    title: 'CONFIGURATION',
    items: [
      { name: 'System Settings', href: '/settings', icon: 'Settings' },
    ],
  },
];
