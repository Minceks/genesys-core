import { Link } from '@tanstack/react-router'

export function BrandMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="genesys-mark" x1="2" y1="2" x2="30" y2="30" gradientUnits="userSpaceOnUse">
          <stop stopColor="#8b93ff" />
          <stop offset=".55" stopColor="#6470ff" />
          <stop offset="1" stopColor="#38bdf8" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill="url(#genesys-mark)" />
      <path d="M16 6.5l2.6 6.9 6.9 2.6-6.9 2.6L16 25.5l-2.6-6.9-6.9-2.6 6.9-2.6L16 6.5z" fill="#fff" />
    </svg>
  )
}

export function Brand({ size = 28 }: { size?: number }) {
  return <Link to="/" className="g-brand" aria-label="GeneSys home"><BrandMark size={size} />GeneSys</Link>
}
