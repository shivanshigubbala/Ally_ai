export default function MedicalTeamIllustration() {
  return (
    <svg
      viewBox="0 0 480 420"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="w-full h-auto max-w-md"
    >
      <ellipse cx="240" cy="230" rx="220" ry="180" fill="#CFEDEA" />
      <circle cx="90" cy="90" r="34" fill="#FFFFFF" opacity="0.6" />
      <circle cx="410" cy="320" r="26" fill="#FFFFFF" opacity="0.5" />

      {Array.from({ length: 5 }).map((_, row) =>
        Array.from({ length: 5 }).map((_, col) => (
          <circle
            key={`${row}-${col}`}
            cx={40 + col * 14}
            cy={40 + row * 14}
            r="2"
            fill="#0E9488"
            opacity="0.25"
          />
        ))
      )}

      <g>
        <rect x="58" y="200" width="74" height="120" rx="30" fill="#0F766E" />
        <circle cx="95" cy="178" r="30" fill="#F2C29B" />
        <path d="M70 160c0-18 14-30 25-30s25 12 25 30" fill="#4A2E1F" />
        <rect x="80" y="188" width="30" height="14" rx="6" fill="#FFFFFF" />
        <circle cx="138" cy="230" r="10" fill="#F2C29B" />
        <path d="M120 215c10-4 20-2 24 8" stroke="#F2C29B" strokeWidth="10" strokeLinecap="round" />
      </g>

      <g>
        <rect x="190" y="160" width="100" height="160" rx="36" fill="#14B8A6" />
        <circle cx="240" cy="128" r="38" fill="#E8B086" />
        <path d="M205 110c0-22 16-38 35-38s35 16 35 38" fill="#2B2B2B" />
        <rect x="222" y="142" width="36" height="16" rx="7" fill="#FFFFFF" />
        <path
          d="M214 180c0 24 8 36 26 36s26-12 26-36"
          stroke="#0E9488"
          strokeWidth="6"
          fill="none"
          strokeLinecap="round"
        />
        <circle cx="240" cy="216" r="7" fill="#0E9488" />
        <rect x="206" y="178" width="14" height="8" rx="4" fill="#FFFFFF" />
        <rect x="260" y="178" width="14" height="8" rx="4" fill="#FFFFFF" />
      </g>

      <g>
        <rect x="330" y="206" width="76" height="116" rx="30" fill="#0D9488" />
        <circle cx="368" cy="184" r="29" fill="#C9885F" />
        <path d="M340 168c10-22 50-22 56 0" fill="#1F1208" />
        <rect x="354" y="194" width="28" height="14" rx="6" fill="#FFFFFF" />
        <rect x="392" y="232" width="28" height="36" rx="4" fill="#FFFFFF" stroke="#0E9488" strokeWidth="2" />
        <line x1="397" y1="240" x2="415" y2="240" stroke="#0E9488" strokeWidth="2" />
        <line x1="397" y1="248" x2="415" y2="248" stroke="#0E9488" strokeWidth="2" />
        <line x1="397" y1="256" x2="409" y2="256" stroke="#0E9488" strokeWidth="2" />
      </g>

      <g>
        <circle cx="150" cy="120" r="20" fill="#FFFFFF" />
        <rect x="143" y="110" width="14" height="20" rx="3" fill="#14B8A6" />
        <rect x="136" y="117" width="28" height="6" rx="3" fill="#14B8A6" />
      </g>

      <path d="M120 95l4 10 10 4-10 4-4 10-4-10-10-4 10-4z" fill="#FBBF24" />
      <path d="M360 110l3 7 7 3-7 3-3 7-3-7-7-3 7-3z" fill="#FBBF24" />
    </svg>
  );
}