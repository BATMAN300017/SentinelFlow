import AlertDetailPageClient from './detail-client';

export function generateStaticParams() {
  return [{ id: 'sample' }];
}

export default function AlertDetailPage() {
  return <AlertDetailPageClient />;
}
