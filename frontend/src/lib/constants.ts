export const APP_NAME = 'SentinelFlow AI';
export const APP_TAGLINE = 'The Self-Directed Fraud Investigation Platform';

export const SEVERITIES = {
  CRITICAL: { label: 'Critical', bg: 'bg-rose-950/40', text: 'text-rose-400', border: 'border-rose-500/40' },
  HIGH: { label: 'High', bg: 'bg-orange-950/40', text: 'text-orange-400', border: 'border-orange-500/40' },
  MEDIUM: { label: 'Medium', bg: 'bg-amber-950/40', text: 'text-amber-400', border: 'border-amber-500/40' },
  LOW: { label: 'Low', bg: 'bg-emerald-950/40', text: 'text-emerald-400', border: 'border-emerald-500/40' },
  NEUTRAL: { label: 'Neutral', bg: 'bg-slate-900/60', text: 'text-slate-400', border: 'border-slate-700/40' },
} as const;

export const CASE_STATUSES = {
  NEW: { label: 'New', color: 'text-slate-300 bg-slate-900 border-slate-700' },
  ASSIGNED: { label: 'Assigned', color: 'text-slate-200 bg-slate-800 border-slate-600' },
  IN_PROGRESS: { label: 'In Progress', color: 'text-amber-400 bg-amber-950/50 border-amber-800/60' },
  PENDING_REVIEW: { label: 'Pending Review', color: 'text-orange-400 bg-orange-950/50 border-orange-800/60' },
  DISPOSITIONED: { label: 'Dispositioned', color: 'text-emerald-400 bg-emerald-950/50 border-emerald-800/60' },
  CLOSED: { label: 'Closed', color: 'text-slate-400 bg-slate-900/80 border-slate-800' },
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
