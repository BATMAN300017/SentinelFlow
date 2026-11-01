import EntityDetailPageClient from './detail-client';

export function generateStaticParams() {
  return [{ id: 'sample' }];
}

export default function EntityDetailPage() {
  return <EntityDetailPageClient />;
}
