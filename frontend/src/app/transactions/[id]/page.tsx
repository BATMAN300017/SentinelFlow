import TransactionDetailPageClient from './detail-client';

export function generateStaticParams() {
  return [{ id: 'sample' }];
}

export default function TransactionDetailPage() {
  return <TransactionDetailPageClient />;
}
