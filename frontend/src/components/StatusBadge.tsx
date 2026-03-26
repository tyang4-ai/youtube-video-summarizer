interface Props {
  status: string;
}

function getColor(status: string): string {
  const s = status.toLowerCase();
  if (s === 'success' || s === 'sent' || s === 'active') return 'green';
  if (s === 'failed' || s === 'error') return 'red';
  if (s === 'pending' || s === 'processing' || s === 'paused') return 'orange';
  return 'gray';
}

export default function StatusBadge({ status }: Props) {
  const color = getColor(status);
  return <span className={`status-badge status-badge-${color}`}>{status}</span>;
}
