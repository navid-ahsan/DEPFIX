'use client';

interface Props {
  iconSize?: number;
  showText?: boolean;
  className?: string;
}

export default function DepfixLogo({ iconSize = 40, showText = true, className = '' }: Props) {
  return (
    <div className={`flex items-center gap-3 select-none ${className}`}>
      {/* Animated icon mark */}
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 112 112"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ flexShrink: 0 }}
      >
        <defs>
          <path id="logo-p1" d="M16,56 L42,56" />
          <path id="logo-p2" d="M70,56 L96,56" />
          <path id="logo-p3" d="M56,16 L56,42" />
          <linearGradient id="logo-cg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#ff3c3c" stopOpacity="0.12" />
            <stop offset="100%" stopColor="#00ff88" stopOpacity="0.12" />
          </linearGradient>
        </defs>

        {/* Outer rotating ring */}
        <g className="logo-ro">
          <circle cx="56" cy="56" r="52" stroke="rgba(0,212,255,0.15)" strokeWidth="1" strokeDasharray="4 8" />
          <line x1="56" y1="4"   x2="56" y2="11"  stroke="rgba(0,212,255,0.4)" strokeWidth="1.5" />
          <line x1="56" y1="101" x2="56" y2="108" stroke="rgba(0,212,255,0.4)" strokeWidth="1.5" />
          <line x1="4"  y1="56"  x2="11" y2="56"  stroke="rgba(0,212,255,0.4)" strokeWidth="1.5" />
          <line x1="101" y1="56" x2="108" y2="56" stroke="rgba(0,212,255,0.4)" strokeWidth="1.5" />
        </g>

        {/* Inner rotating ring (reverse) */}
        <g className="logo-ri">
          <circle cx="56" cy="56" r="38" stroke="rgba(167,139,250,0.18)" strokeWidth="1" strokeDasharray="2 10" />
        </g>

        {/* Connector lines */}
        <line x1="16" y1="56" x2="44" y2="56" stroke="rgba(255,60,60,0.55)"   strokeWidth="1.5" />
        <line x1="68" y1="56" x2="96" y2="56" stroke="rgba(0,255,136,0.55)"   strokeWidth="1.5" />
        <line x1="56" y1="16" x2="56" y2="44" stroke="rgba(167,139,250,0.55)" strokeWidth="1.5" />
        <line x1="56" y1="68" x2="56" y2="94" stroke="rgba(0,212,255,0.45)"   strokeWidth="1.5" />

        {/* Left: error.log file node */}
        <g className="logo-ep">
          <rect x="6" y="49" width="12" height="14" rx="1"
            fill="rgba(255,60,60,0.1)" stroke="#ff3c3c" strokeWidth="1.5" />
          <line x1="8"  y1="53" x2="16" y2="53" stroke="rgba(255,60,60,0.7)" strokeWidth="0.9" />
          <line x1="8"  y1="56" x2="14" y2="56" stroke="rgba(255,60,60,0.5)" strokeWidth="0.9" />
          <line x1="8"  y1="59" x2="16" y2="59" stroke="rgba(255,60,60,0.7)" strokeWidth="0.9" />
        </g>

        {/* Right: verified fix (diamond + check) */}
        <g className="logo-fg">
          <polygon points="96,49 103,56 96,63 89,56"
            fill="rgba(0,255,136,0.09)" stroke="#00ff88" strokeWidth="1.5" />
          <polyline points="92,56 95,59 101,53" stroke="#00ff88" strokeWidth="1.5" fill="none" />
        </g>

        {/* Top: vector DB (cylinder) */}
        <ellipse cx="56" cy="14" rx="7.5" ry="2.5"
          fill="rgba(167,139,250,0.1)" stroke="rgba(167,139,250,0.55)" strokeWidth="1.2" />
        <line x1="48.5" y1="14" x2="48.5" y2="21" stroke="rgba(167,139,250,0.55)" strokeWidth="1.2" />
        <line x1="63.5" y1="14" x2="63.5" y2="21" stroke="rgba(167,139,250,0.55)" strokeWidth="1.2" />
        <ellipse cx="56" cy="21" rx="7.5" ry="2.5"
          fill="rgba(167,139,250,0.07)" stroke="rgba(167,139,250,0.45)" strokeWidth="1.2" />
        <line x1="50" y1="17" x2="62" y2="17" stroke="rgba(167,139,250,0.3)" strokeWidth="0.7" />

        {/* Bottom: CI/CD pipeline dots */}
        <rect x="50" y="93" width="12" height="8" rx="1"
          fill="rgba(0,212,255,0.06)" stroke="rgba(0,212,255,0.45)" strokeWidth="1.2" />
        <circle cx="53" cy="97" r="1.2" fill="rgba(0,212,255,0.7)" />
        <circle cx="56" cy="97" r="1.2" fill="rgba(0,212,255,0.5)" />
        <circle cx="59" cy="97" r="1.2" fill="rgba(0,212,255,0.3)" />

        {/* Core: LLM */}
        <circle cx="56" cy="56" r="16" fill="url(#logo-cg)" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
        <circle cx="56" cy="56" r="14" fill="none" stroke="rgba(0,212,255,0.28)" strokeWidth="1" strokeDasharray="2 3" />
        <line x1="47" y1="56" x2="65" y2="56" stroke="rgba(0,212,255,0.7)" strokeWidth="0.8" />
        <line x1="56" y1="47" x2="56" y2="65" stroke="rgba(0,212,255,0.7)" strokeWidth="0.8" />
        <circle cx="56" cy="56" r="3.5" fill="none" stroke="rgba(0,212,255,0.8)" strokeWidth="1.2" />
        <circle cx="56" cy="56" r="1.5" fill="white" opacity="0.92" />

        {/* Flow: error → core */}
        <circle r="2.2" fill="#ff3c3c">
          <animateMotion dur="1.8s" repeatCount="indefinite" begin="0s">
            <mpath href="#logo-p1" />
          </animateMotion>
          <animate attributeName="opacity" values="0;.9;.9;0" dur="1.8s" repeatCount="indefinite" begin="0s" />
        </circle>
        {/* Flow: core → fix */}
        <circle r="2.2" fill="#00ff88">
          <animateMotion dur="1.8s" repeatCount="indefinite" begin="0.9s">
            <mpath href="#logo-p2" />
          </animateMotion>
          <animate attributeName="opacity" values="0;.9;.9;0" dur="1.8s" repeatCount="indefinite" begin="0.9s" />
        </circle>
        {/* Flow: vector DB → core */}
        <circle r="2" fill="#a78bfa">
          <animateMotion dur="2s" repeatCount="indefinite" begin="0.45s">
            <mpath href="#logo-p3" />
          </animateMotion>
          <animate attributeName="opacity" values="0;.9;.9;0" dur="2s" repeatCount="indefinite" begin="0.45s" />
        </circle>
      </svg>

      {/* Wordmark */}
      {showText && (
        <span
          style={{
            fontFamily: "'Orbitron', monospace",
            fontWeight: 900,
            letterSpacing: '0.08em',
            lineHeight: 1,
          }}
          className="text-xl"
        >
          <span style={{ color: '#ff3c3c', textShadow: '0 0 14px rgba(255,60,60,0.5)' }}>DEP</span>
          <span style={{ color: '#00ff88', textShadow: '0 0 14px rgba(0,255,136,0.5)' }}>FIX</span>
        </span>
      )}
    </div>
  );
}
