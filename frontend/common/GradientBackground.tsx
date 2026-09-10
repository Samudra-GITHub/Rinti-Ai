export function GradientBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-base-black">
      <div className="absolute inset-0 bg-page-gradient" />
      <div className="absolute -top-40 left-1/4 h-[36rem] w-[36rem] rounded-full bg-purple-600/20 blur-[140px]" />
      <div className="absolute top-1/3 -right-32 h-[30rem] w-[30rem] rounded-full bg-cyan-500/15 blur-[140px]" />
      <div className="absolute bottom-[-10rem] left-1/3 h-[28rem] w-[28rem] rounded-full bg-purple-500/10 blur-[160px]" />
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='60' height='60'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
        }}
      />
    </div>
  );
}
