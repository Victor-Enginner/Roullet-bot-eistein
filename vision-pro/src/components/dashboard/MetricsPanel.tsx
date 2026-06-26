export function MetricsPanel() {
  return (
    <div className="bg-card px-4 py-2 rounded-lg border border-border flex items-center space-x-4">
      <div>
        <div className="text-xs text-muted-foreground uppercase">Win Rate</div>
        <div className="font-bold text-primary">87.3%</div>
      </div>
      <div className="w-px h-8 bg-border"></div>
      <div>
        <div className="text-xs text-muted-foreground uppercase">Sinais</div>
        <div className="font-bold">1,248</div>
      </div>
    </div>
  );
}
