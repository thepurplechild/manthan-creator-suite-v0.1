type Variant = 'flow' | 'sharp' | 'mono'

export function Logo({
  size = 28,
  label = 'Project Manthan',
  variant = 'sharp', // change to 'flow' or 'mono' if you prefer
}: { size?: number; label?: string; variant?: Variant }) {
  return (
    <div className="flex items-center gap-2" aria-label={label}>
      {variant === 'flow' && <FlowMark size={size} />}
      {variant === 'sharp' && <SharpMark size={size} />}
      {variant === 'mono' && <MonoMark size={size} />}
      <span className="font-display text-lg tracking-tight">Manthan</span>
    </div>
  )
}

/** Flow: circular gradient + flowing M */
function FlowMark({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <defs>
        <linearGradient id="manthanFlow" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#4F46E5" />
          <stop offset="1" stopColor="#8B5CF6" />
        </linearGradient>
      </defs>
      {/* Circle badge */}
      <circle cx="16" cy="16" r="14" fill="url(#manthanFlow)" />
      {/* Flowing M */}
      <path
        d="M8 22 V12 M8 12 L16 18 M24 22 V12 M24 12 L16 18"
        stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" fill="none"
      />
    </svg>
  )
}

/** Sharp Tech: hex badge + angular M */
function SharpMark({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <defs>
        <linearGradient id="manthanSharp" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#0EA5E9" />
          <stop offset="1" stopColor="#6366F1" />
        </linearGradient>
      </defs>
      {/* Hexagon */}
      <path d="M16 2 28 9.5 28 22.5 16 30 4 22.5 4 9.5 Z" fill="url(#manthanSharp)"/>
      {/* Angular M */}
      <path
        d="M7.8 22.2 L7.8 10.2 L12.6 18.0 L16.0 12.4 L19.4 18.0 L24.2 10.2 L24.2 22.2"
        stroke="#ffffff" strokeWidth="2.1" strokeLinejoin="round" strokeLinecap="round" fill="none"
      />
    </svg>
  )
}

/** Mono: single-color circular badge + simple M */
function MonoMark({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <circle cx="16" cy="16" r="14" fill="#111827" />
      <path
        d="M8 22 V12 M8 12 L16 18 M24 22 V12 M24 12 L16 18"
        stroke="#F9FAFB" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" fill="none"
      />
    </svg>
  )
}
