import InvestigationDetailPageClient from './detail-client';

export function generateStaticParams() {
  return [{ id: 'sample' }];
}

export default function InvestigationDetailPage() {
  return <InvestigationDetailPageClient />;
}
