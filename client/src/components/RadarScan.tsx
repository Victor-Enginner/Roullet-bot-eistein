// Animated radar scan component — rotating green beam + pulsing rings
export function RadarScan({ size = 120, active = true }: { size?: number; active?: boolean }) {
  const r = size / 2;
  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      {/* Outer ring pulse */}
      <div
        className="absolute inset-0 rounded-full border border-primary/20"
        style={{ animation: active ? "ring-pulse 3s ease-in-out infinite" : "none" }}
      />
      <div
        className="absolute rounded-full border border-primary/15"
        style={{
          inset: "10%",
          animation: active ? "ring-pulse 3s ease-in-out infinite 1s" : "none",
        }}
      />
      <div
        className="absolute rounded-full border border-primary/10"
        style={{
          inset: "20%",
          animation: active ? "ring-pulse 3s ease-in-out infinite 2s" : "none",
        }}
      />

      {/* Grid crosshairs */}
      <div className="absolute inset-0 rounded-full overflow-hidden opacity-20">
        <div className="absolute left-1/2 top-0 bottom-0 w-px bg-primary/60 -translate-x-1/2" />
        <div className="absolute top-1/2 left-0 right-0 h-px bg-primary/60 -translate-y-1/2" />
      </div>

      {/* Rotating beam */}
      {active && (
        <div
          className="absolute inset-0 rounded-full overflow-hidden"
          style={{ animation: "radar-spin 3s linear infinite" }}
        >
          <div
            className="absolute"
            style={{
              top: 0,
              left: "50%",
              width: "50%",
              height: "50%",
              transformOrigin: "0% 100%",
              background:
                "conic-gradient(from 0deg, transparent 80%, rgba(34,197,94,0.6) 100%)",
            }}
          />
        </div>
      )}

      {/* Center dot */}
      <div
        className="absolute w-2 h-2 rounded-full bg-primary"
        style={{
          boxShadow: "0 0 8px rgba(34,197,94,0.8), 0 0 16px rgba(34,197,94,0.4)",
          animation: active ? "live-blink 1.2s ease-in-out infinite" : "none",
        }}
      />
    </div>
  );
}
