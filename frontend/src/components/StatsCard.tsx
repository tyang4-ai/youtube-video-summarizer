interface Props {
  label: string;
  value: string | number;
}

export default function StatsCard({ label, value }: Props) {
  return (
    <div className="stats-card">
      <div className="stats-card-label">{label}</div>
      <div className="stats-card-value">{value}</div>
    </div>
  );
}
