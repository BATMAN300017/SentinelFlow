export const APP_NAME = 'SentinelFlow';
export const APP_TAGLINE = 'Financial Crime & AML Intelligence';

export const SEVERITIES = {
  CRITICAL: {
    label: 'Critical',
    bg: 'bg-[#2A1414]',
    text: 'text-[#FF6B6B]',
    border: 'border-[#5A2020]',
  },
  HIGH: {
    label: 'High',
    bg: 'bg-[#2E1A0F]',
    text: 'text-[#FFA14A]',
    border: 'border-[#663518]',
  },
  MEDIUM: {
    label: 'Medium',
    bg: 'bg-[#2A230F]',
    text: 'text-[#FFD15C]',
    border: 'border-[#5E4C1A]',
  },
  LOW: {
    label: 'Low',
    bg: 'bg-[#142010]',
    text: 'text-[#B7F34A]',
    border: 'border-[#29421E]',
  },
  NEUTRAL: {
    label: 'Routine',
    bg: 'bg-[#121612]',
    text: 'text-[#929B90]',
    border: 'border-[#262D26]',
  },
} as const;

export const CASE_STATUSES = {
  NEW: { label: 'New', color: 'text-[#F2F4EF] bg-[#181E18] border-[#262D26]' },
  ASSIGNED: { label: 'Assigned', color: 'text-[#929B90] bg-[#121612] border-[#262D26]' },
  IN_PROGRESS: { label: 'In Progress', color: 'text-[#FFD15C] bg-[#2A230F] border-[#5E4C1A]' },
  PENDING_REVIEW: { label: 'Pending Review', color: 'text-[#FFA14A] bg-[#2E1A0F] border-[#663518]' },
  DISPOSITIONED: { label: 'Dispositioned', color: 'text-[#B7F34A] bg-[#142010] border-[#29421E]' },
  CLOSED: { label: 'Closed', color: 'text-[#687166] bg-[#0D100D] border-[#1C221C]' },
} as const;

export const CHANNELS = ['UPI', 'IMPS', 'NEFT', 'RTGS', 'SWIFT', 'ACH', 'CARD', 'CRYPTO'] as const;

export const NAVIGATION_SECTIONS = [
  {
    title: 'SURVEILLANCE & TRIAGE',
    items: [
      { name: 'Intelligence Overview', href: '/dashboard', icon: 'LayoutDashboard' },
      { name: 'Live Transactions', href: '/transactions', icon: 'ArrowLeftRight' },
      { name: 'Alerts Queue', href: '/alerts', icon: 'ShieldAlert' },
      { name: 'Investigations', href: '/investigations', icon: 'Briefcase' },
    ],
  },
  {
    title: 'GRAPH & TOPOLOGY',
    items: [
      { name: 'Fund Flow Tracing', href: '/fund-flow', icon: 'Workflow' },
      { name: 'Network Intelligence', href: '/network', icon: 'Network' },
      { name: 'Entity Profiles', href: '/entities', icon: 'Users' },
    ],
  },
  {
    title: 'ANALYTICS & GOVERNANCE',
    items: [
      { name: 'Model Intelligence', href: '/intelligence', icon: 'BrainCircuit' },
      { name: 'Model Learning', href: '/feedback', icon: 'Cpu' },
      { name: 'Detection Rules', href: '/rules', icon: 'FileCode2' },
      { name: 'Audit Log', href: '/audit', icon: 'ScrollText' },
    ],
  },
  {
    title: 'PLATFORM',
    items: [
      { name: 'System Settings', href: '/settings', icon: 'Settings' },
    ],
  },
];
