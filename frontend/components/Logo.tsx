// No "use client" needed
export function Logo({ size = 28, label = 'Project Manthan' }: { size?: number; label?: string }) {
  // circular mark + fluid "M" made of two rising strokes (motion/churn)
  return (
    <div className="flex items-center gap-2" aria-label={label}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        role="img"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="manthanGradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#4F46E5" />
            <stop offset="1" stopColor="#8B5CF6" />
          </linearGradient>
        </defs>

        <!-- Outer circle -->
        <circle cx="16" cy="16" r="14" fill="url(#manthanGradient)" />

        <!-- Dynamic "M" (two flowing strokes that meet at center) -->
        <path
          d="M7.5 22.5 V11.5
             M7.5 11.5 L15.8 18.2
             M24.5 22.5 V11.5
             M24.5 11.5 L15.8 18.2"
          stroke="#FFFFFF"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
      </svg>

      <span className="font-display text-lg tracking-tight">Manthan</span>
    </div>
  )
}
