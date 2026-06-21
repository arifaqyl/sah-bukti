export function Logo({ size = 32, showText = true }: { size?: number; showText?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <div
        aria-label="Sah.Bukti"
        className="flex items-center justify-center rounded-[26%] bg-accent font-serif font-semibold text-accent-foreground shadow-sm"
        style={{ width: size, height: size, fontSize: size * 0.58 }}
      >
        S
      </div>
      {showText && (
        <span
          className="font-serif font-medium text-foreground"
          style={{ fontSize: size * 0.66, letterSpacing: "-0.02em" }}
        >
          Sah.Bukti
        </span>
      )}
    </div>
  );
}
