'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import DepfixLogo from '../components/DepfixLogo';

// ── Inline SVG tech icons ─────────────────────────────────────────────────────

function IconDocker() {
  return (
    <svg viewBox="0 0 64 64" width="40" height="40" fill="none">
      {[0,1,2].map(col => (
        <rect key={`t${col}`} x={8 + col * 13} y={10} width={11} height={9} rx={1.5} fill="#2496ED" opacity={0.9} />
      ))}
      {[0,1,2,3].map(col => (
        <rect key={`m${col}`} x={8 + col * 13} y={22} width={11} height={9} rx={1.5} fill="#2496ED" />
      ))}
      <path d="M6 32 C6 32 5 29 7 28 L57 28 C57 28 61 28 59 36 C59 36 55 46 42 45 L22 45 C12 45 7 39 6 32Z" fill="#2496ED" opacity={0.7} />
      <path d="M55 28 C57 26 60 26 61 27" stroke="#2496ED" strokeWidth="2" fill="none" />
      <circle cx="60" cy="25" r="2.5" fill="#2496ED" />
    </svg>
  );
}

function IconOllama() {
  return (
    <svg viewBox="0 0 64 64" width="40" height="40" fill="none">
      <circle cx="32" cy="32" r="26" stroke="#e8e8f0" strokeWidth="2.5" opacity={0.85} />
      <ellipse cx="21" cy="27" rx="5" ry="7" fill="#e8e8f0" opacity={0.9} />
      <ellipse cx="43" cy="27" rx="5" ry="7" fill="#e8e8f0" opacity={0.9} />
      <rect x="22" y="32" width="20" height="10" rx="5" fill="#e8e8f0" opacity={0.9} />
      <circle cx="26" cy="44" r="4" fill="#e8e8f0" opacity={0.85} />
      <circle cx="38" cy="44" r="4" fill="#e8e8f0" opacity={0.85} />
    </svg>
  );
}

function IconPostgres() {
  return (
    <svg viewBox="0 0 64 64" width="40" height="40" fill="none">
      <ellipse cx="32" cy="16" rx="18" ry="7" fill="#336791" />
      <path d="M14 16 L14 48 C14 52 22 56 32 56 C42 56 50 52 50 48 L50 16" stroke="#336791" strokeWidth="3" fill="none" />
      <ellipse cx="32" cy="16" rx="18" ry="7" fill="#336791" stroke="#4a90d4" strokeWidth="1.5" />
      <ellipse cx="32" cy="28" rx="18" ry="5" fill="none" stroke="#4a90d4" strokeWidth="1.5" />
      <ellipse cx="32" cy="39" rx="18" ry="5" fill="none" stroke="#4a90d4" strokeWidth="1" opacity={0.6} />
      <path d="M50 28 C54 26 56 20 53 15" stroke="#4a90d4" strokeWidth="2" fill="none" opacity={0.7} />
    </svg>
  );
}

function IconPgvector() {
  return (
    <svg viewBox="0 0 64 64" width="40" height="40" fill="none">
      <circle cx="32" cy="32" r="5" fill="#a78bfa" />
      {([0,45,90,135,180,225,270,315] as number[]).map((deg, i) => {
        const r = deg * Math.PI / 180;
        const x1 = 32 + 8 * Math.cos(r), y1 = 32 + 8 * Math.sin(r);
        const x2 = 32 + 22 * Math.cos(r), y2 = 32 + 22 * Math.sin(r);
        return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#a78bfa" strokeWidth="2" opacity={0.7} />;
      })}
      {([0,45,90,135,180,225,270,315] as number[]).map((deg, i) => {
        const r = deg * Math.PI / 180;
        const x = 32 + 22 * Math.cos(r), y = 32 + 22 * Math.sin(r);
        return <circle key={i} cx={x} cy={y} r="3.5" fill="#a78bfa" opacity={0.85} />;
      })}
    </svg>
  );
}

function IconPython() {
  return (
    <svg viewBox="0 0 64 64" width="40" height="40" fill="none">
      <path d="M32 8 C22 8 16 13 16 20 L16 28 L32 28 L32 30 L12 30 C8 30 6 34 6 38 L6 44 C6 51 12 56 22 56 L26 56 L26 48 L22 48 C18 48 16 46 16 44 L16 38 L36 38 C40 38 42 34 42 30 L42 20 C42 13 38 8 32 8Z" fill="#3776AB" />
      <path d="M32 56 C42 56 48 51 48 44 L48 36 L32 36 L32 34 L52 34 C56 34 58 30 58 26 L58 20 C58 13 52 8 42 8 L38 8 L38 16 L42 16 C46 16 48 18 48 20 L48 26 L28 26 C24 26 22 30 22 34 L22 44 C22 51 26 56 32 56Z" fill="#FFD43B" />
      <circle cx="27" cy="20" r="3" fill="#FFD43B" />
      <circle cx="37" cy="44" r="3" fill="#3776AB" />
    </svg>
  );
}

function IconFastAPI() {
  return (
    <svg viewBox="0 0 64 64" width="40" height="40" fill="none">
      <circle cx="32" cy="32" r="26" fill="#009688" opacity={0.15} stroke="#009688" strokeWidth="2" />
      <path d="M36 10 L24 34 L32 34 L28 54 L44 26 L35 26 Z" fill="#009688" />
    </svg>
  );
}

function IconNextJS() {
  return (
    <svg viewBox="0 0 64 64" width="40" height="40" fill="none">
      <circle cx="32" cy="32" r="26" fill="#1a1a2e" stroke="rgba(220,232,248,0.3)" strokeWidth="1.5" />
      <path d="M22 44 L22 20 L44 44 L44 20" stroke="#dce8f8" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <line x1="22" y1="20" x2="22" y2="44" stroke="#dce8f8" strokeWidth="3.5" strokeLinecap="round" />
    </svg>
  );
}

function IconLangChain() {
  return (
    <svg viewBox="0 0 64 64" width="40" height="40" fill="none">
      <rect x="5" y="26" width="18" height="12" rx="6" fill="none" stroke="#00C4B4" strokeWidth="2.5" />
      <rect x="41" y="26" width="18" height="12" rx="6" fill="none" stroke="#00C4B4" strokeWidth="2.5" />
      <line x1="23" y1="32" x2="41" y2="32" stroke="#00C4B4" strokeWidth="2.5" />
      <rect x="23" y="10" width="18" height="12" rx="6" fill="none" stroke="#00C4B4" strokeWidth="2" opacity={0.6} />
      <line x1="32" y1="22" x2="32" y2="26" stroke="#00C4B4" strokeWidth="2" opacity={0.6} />
      <rect x="23" y="42" width="18" height="12" rx="6" fill="none" stroke="#00C4B4" strokeWidth="2" opacity={0.6} />
      <line x1="32" y1="38" x2="32" y2="42" stroke="#00C4B4" strokeWidth="2" opacity={0.6} />
    </svg>
  );
}

function IconNVIDIA() {
  return (
    <svg viewBox="0 0 64 64" width="40" height="40" fill="none">
      <rect x="4" y="20" width="56" height="24" rx="4" fill="#76B900" opacity={0.15} stroke="#76B900" strokeWidth="1.5" />
      {[0,1,2,3,4,5,6].map(i => (
        <rect key={i} x={8 + i * 7} y={24} width={5} height={16} rx={1} fill="#76B900" opacity={0.7 + i * 0.03} />
      ))}
      <path d="M8 44 L8 54 L20 54 L20 48" stroke="#76B900" strokeWidth="2" fill="none" opacity={0.6} />
      <path d="M44 44 L44 54 L56 54 L56 48" stroke="#76B900" strokeWidth="2" fill="none" opacity={0.6} />
    </svg>
  );
}

// ── StepCard with OS tabs ─────────────────────────────────────────────────────

function StepCard({
  step, title, accent, desc, linux, mac, windows,
}: {
  step: string; title: string; accent: string; desc: string;
  linux: string; mac: string; windows: string;
}) {
  const [os, setOs] = useState<'linux' | 'mac' | 'windows'>('linux');
  const [copied, setCopied] = useState(false);
  const code = os === 'linux' ? linux : os === 'mac' ? mac : windows;
  const tabs: { key: 'linux' | 'mac' | 'windows'; label: string }[] = [
    { key: 'linux',   label: '🐧 Linux'   },
    { key: 'mac',     label: '🍎 macOS'   },
    { key: 'windows', label: '🪟 Windows' },
  ];

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback for older browsers
      const el = document.createElement('textarea');
      el.value = code;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="mb-5 rounded-xl overflow-hidden" style={{ background: '#0b0f1e', border: `1px solid ${accent}22`, borderLeft: `3px solid ${accent}` }}>
      <div className="px-6 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
        <div className="flex items-center gap-3 mb-2">
          <span style={{ fontFamily: "'Orbitron', monospace", fontSize: '11px', fontWeight: 700, color: accent, letterSpacing: '2px' }}>STEP {step}</span>
          <span style={{ fontFamily: "'Orbitron', monospace", fontSize: '14px', fontWeight: 700, color: '#dce8f8' }}>{title}</span>
        </div>
        <p style={{ fontFamily: "'Exo 2', sans-serif", fontSize: '13px', color: '#8cb4d4', fontWeight: 300, lineHeight: 1.6 }}>{desc}</p>
      </div>
      {/* OS tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid rgba(255,255,255,0.04)', background: 'rgba(0,0,0,0.2)' }}>
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setOs(t.key)}
            style={{
              flex: 1, padding: '7px 4px',
              fontFamily: "'Share Tech Mono', monospace",
              fontSize: '10px', letterSpacing: '1px',
              background: os === t.key ? `${accent}14` : 'transparent',
              color: os === t.key ? accent : '#607898',
              border: 'none',
              borderBottom: os === t.key ? `2px solid ${accent}` : '2px solid transparent',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>
      {/* Code block with copy button */}
      <div style={{ position: 'relative' }}>
        <pre
          className="overflow-x-auto text-xs leading-relaxed px-6 py-4 m-0"
          style={{ fontFamily: "'Share Tech Mono', monospace", color: '#8cb4d4', background: 'rgba(0,0,0,0.3)' }}
        >
          <code>{code}</code>
        </pre>
        <button
          onClick={handleCopy}
          title="Copy to clipboard"
          style={{
            position: 'absolute', top: '10px', right: '12px',
            background: copied ? 'rgba(0,255,136,0.15)' : 'rgba(0,212,255,0.08)',
            border: `1px solid ${copied ? 'rgba(0,255,136,0.4)' : 'rgba(0,212,255,0.25)'}`,
            borderRadius: '5px',
            color: copied ? '#00ff88' : '#00d4ff',
            fontFamily: "'Share Tech Mono', monospace",
            fontSize: '9px', letterSpacing: '1px',
            padding: '4px 9px',
            cursor: 'pointer',
            transition: 'all 0.2s',
          }}
        >
          {copied ? '✓ COPIED' : 'COPY'}
        </button>
      </div>
    </div>
  );
}

export default function MainPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    if (menuOpen) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [menuOpen]);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') setMenuOpen(false); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  const navLinks = [
    { label: 'HOME', href: '/', accent: '#00d4ff' },
    { label: 'SIGN IN', href: '/auth/signin', accent: '#00ff88' },
    { label: 'DASHBOARD', href: '/dashboard', accent: '#00ff88' },
    { label: 'SYSTEM CONFIG', href: '/setup/config', accent: '#a78bfa' },
    { label: 'SETUP GUIDE', href: '/setup/dependencies', accent: '#ffb700' },
  ];

  const extLinks = [
    { label: 'OLLAMA', href: 'https://ollama.com', note: 'ollama.com' },
    { label: 'DOCKER', href: 'https://docker.com', note: 'docker.com' },
    { label: 'PGVECTOR', href: 'https://github.com/pgvector/pgvector', note: 'github.com' },
  ];

  return (
    <div
      className="min-h-screen depfix-grid-bg flex flex-col"
      style={{ background: '#060810', color: '#dce8f8' }}
    >
      {/* ── Hamburger button (fixed, top-left) ─────────────────────────── */}
      <button
        onClick={() => setMenuOpen(true)}
        aria-label="Open menu"
        style={{
          position: 'fixed', top: 16, left: 16, zIndex: 60,
          width: 42, height: 42,
          background: 'rgba(11,15,30,0.9)',
          border: '1px solid rgba(0,212,255,0.2)',
          borderRadius: '4px',
          cursor: 'pointer',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: '5px',
          backdropFilter: 'blur(8px)',
          transition: 'border-color 0.15s',
        }}
        onMouseEnter={e => (e.currentTarget.style.borderColor = 'rgba(0,212,255,0.55)')}
        onMouseLeave={e => (e.currentTarget.style.borderColor = 'rgba(0,212,255,0.2)')}
      >
        {[0, 1, 2].map(i => (
          <span key={i} style={{
            display: 'block', width: 18, height: 1.5,
            background: '#00d4ff', borderRadius: 1,
            opacity: i === 1 ? 0.6 : 1,
          }} />
        ))}
      </button>

      {/* ── Slide-out drawer backdrop ────────────────────────────────────── */}
      {menuOpen && (
        <div
          style={{
            position: 'fixed', inset: 0, zIndex: 70,
            background: 'rgba(6,8,16,0.65)',
            backdropFilter: 'blur(4px)',
            transition: 'opacity 0.2s',
          }}
        />
      )}

      {/* ── Slide-out drawer ─────────────────────────────────────────────── */}
      <div
        ref={drawerRef}
        style={{
          position: 'fixed', top: 0, left: 0, bottom: 0,
          width: 280, zIndex: 80,
          background: '#0b0f1e',
          borderRight: '1px solid rgba(0,212,255,0.15)',
          transform: menuOpen ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 0.25s cubic-bezier(0.4,0,0.2,1)',
          display: 'flex', flexDirection: 'column',
          padding: '20px 0 32px',
          overflowY: 'auto',
        }}
      >
        {/* Drawer header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 20px 20px',
          borderBottom: '1px solid rgba(0,212,255,0.08)',
          marginBottom: '8px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <DepfixLogo iconSize={32} showText={false} />
            <span style={{
              fontFamily: "'Orbitron', sans-serif", fontWeight: 900,
              fontSize: '18px',
            }}>
              <span style={{ color: '#ff3c3c' }}>DEP</span>
              <span style={{ color: '#00ff88' }}>FIX</span>
            </span>
          </div>
          <button
            onClick={() => setMenuOpen(false)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: '#607898', fontSize: '18px', lineHeight: 1,
              padding: '4px',
              transition: 'color 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.color = '#dce8f8')}
            onMouseLeave={e => (e.currentTarget.style.color = '#607898')}
          >
            ✕
          </button>
        </div>

        {/* Nav links */}
        <nav style={{ padding: '8px 0', flex: 1 }}>
          <div style={{
            fontFamily: "'Share Tech Mono', monospace",
            fontSize: '9px', letterSpacing: '3px', color: '#607898',
            padding: '6px 20px 10px',
          }}>
            NAVIGATION
          </div>
          {navLinks.map(({ label, href, accent }) => (
            <Link
              key={label}
              href={href}
              onClick={() => setMenuOpen(false)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '11px 20px',
                fontFamily: "'Share Tech Mono', monospace",
                fontSize: '11px', letterSpacing: '2px',
                color: '#8cb4d4',
                textDecoration: 'none',
                borderLeft: '2px solid transparent',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.color = accent;
                e.currentTarget.style.borderLeftColor = accent;
                e.currentTarget.style.background = `${accent}0d`;
              }}
              onMouseLeave={e => {
                e.currentTarget.style.color = '#8cb4d4';
                e.currentTarget.style.borderLeftColor = 'transparent';
                e.currentTarget.style.background = 'transparent';
              }}
            >
              <span style={{ opacity: 0.5 }}>▶</span>
              {label}
            </Link>
          ))}

          {/* External links */}
          <div style={{
            fontFamily: "'Share Tech Mono', monospace",
            fontSize: '9px', letterSpacing: '3px', color: '#607898',
            padding: '18px 20px 10px',
          }}>
            EXTERNAL
          </div>
          {extLinks.map(({ label, href, note }) => (
            <a
              key={label}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '11px 20px',
                fontFamily: "'Share Tech Mono', monospace",
                fontSize: '11px', letterSpacing: '2px',
                color: '#8cb4d4', textDecoration: 'none',
                borderLeft: '2px solid transparent',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.color = '#00d4ff';
                e.currentTarget.style.borderLeftColor = '#00d4ff';
                e.currentTarget.style.background = 'rgba(0,212,255,0.05)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.color = '#8cb4d4';
                e.currentTarget.style.borderLeftColor = 'transparent';
                e.currentTarget.style.background = 'transparent';
              }}
            >
              <span>{label} ↗</span>
              <span style={{ fontSize: '9px', color: '#607898' }}>{note}</span>
            </a>
          ))}
        </nav>

        {/* Version footer */}
        <div style={{
          padding: '16px 20px 0',
          borderTop: '1px solid rgba(0,212,255,0.06)',
        }}>
          <p style={{
            fontFamily: "'Share Tech Mono', monospace",
            fontSize: '9px', letterSpacing: '2px',
            color: '#607898', margin: 0,
          }}>
            DEPFIX v0.1.0
          </p>
          <p style={{
            fontFamily: "'Share Tech Mono', monospace",
            fontSize: '8px', letterSpacing: '2px',
            color: '#2a3a50', marginTop: 4,
          }}>
            LOCAL · PRIVATE · OPEN SOURCE
          </p>
        </div>
      </div>

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-20 text-center">

        {/* Logo mark — large */}
        <div className="mb-8">
          <DepfixLogo iconSize={110} showText={false} />
        </div>

        {/* Wordmark */}
        <h1
          className="mb-4 select-none"
          style={{ fontFamily: "'Orbitron', monospace", fontWeight: 900, fontSize: 'clamp(2.8rem, 8vw, 5rem)', letterSpacing: '0.05em', lineHeight: 1 }}
        >
          <span style={{ color: '#ff3c3c' }}>DEP</span><span style={{ color: '#00ff88' }}>FIX</span>
        </h1>

        {/* Tagline */}
        <p
          className="mb-3 max-w-xl"
          style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '13px', letterSpacing: '4px', color: '#00d4ff', textTransform: 'uppercase' }}
        >
          AI-Powered CI/CD Error Analysis
        </p>

        <p
          className="mb-12 max-w-lg leading-relaxed"
          style={{ fontFamily: "'Exo 2', sans-serif", fontSize: '15px', color: '#6080a0', fontWeight: 300 }}
        >
          Upload your CI/CD error logs, let the local LLM analyze them against embedded
          dependency documentation, and receive verified fixes — all running on your
          own infrastructure.
        </p>

        {/* CTA */}
        <Link
          href="/auth/signin"
          className="inline-block rounded transition-all hover:opacity-80"
          style={{
            background: 'rgba(0,255,136,0.09)',
            border: '1px solid rgba(0,255,136,0.5)',
            color: '#00ff88',
            fontFamily: "'Share Tech Mono', monospace",
            fontSize: '12px',
            letterSpacing: '4px',
            padding: '14px 40px',
          }}
        >
          GET STARTED →
        </Link>

        {/* Pipeline strip */}
        <div className="mt-16 flex flex-wrap items-center justify-center gap-1.5 opacity-40">
          {[
            { t: 'error.log',    c: '#ff3c3c' }, { t: '→', c: '#607898' },
            { t: 'chunk·embed',  c: '#ffb700' }, { t: '→', c: '#607898' },
            { t: 'pgvector',     c: '#a78bfa' }, { t: '→', c: '#607898' },
            { t: 'local llm',    c: '#00d4ff' }, { t: '→', c: '#607898' },
            { t: 'verified fix', c: '#00ff88' },
          ].map(({ t, c }, i) => (
            <span key={i} style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '2px', color: c }}>
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* ── Feature cards ────────────────────────────────────────────────── */}
      <div className="max-w-4xl mx-auto w-full px-4 pb-20">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            {
              accent: '#ff3c3c',
              title: 'ERROR EXTRACTION',
              body: 'Parses CI/CD log files, clusters errors by type, and identifies root causes automatically.',
            },
            {
              accent: '#a78bfa',
              title: 'RAG RETRIEVAL',
              body: 'Searches embedded dependency documentation via pgvector to find the most relevant fix context.',
            },
            {
              accent: '#00ff88',
              title: 'VERIFIED FIX',
              body: 'Local LLM generates a grounded solution with code patch, prevention tip, and CI/CD yaml fix.',
            },
          ].map(({ accent, title, body }) => (
            <div
              key={title}
              className="rounded-lg p-5"
              style={{ background: '#0b0f1e', border: `1px solid ${accent}22`, borderTop: `2px solid ${accent}` }}
            >
              <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: accent, marginBottom: '10px' }}>
                {title}
              </p>
              <p style={{ fontFamily: "'Exo 2', sans-serif", fontSize: '13px', color: '#6080a0', lineHeight: 1.6, fontWeight: 300 }}>
                {body}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Tech Stack ───────────────────────────────────────────────────── */}
      <div className="max-w-4xl mx-auto w-full px-4 pb-20">
        <div className="text-center mb-10">
          <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '5px', color: '#607898' }}>POWERED BY</p>
          <h2 style={{ fontFamily: "'Orbitron', monospace", fontWeight: 700, fontSize: '1.3rem', color: '#dce8f8', marginTop: '8px' }}>
            Open Source Stack
          </h2>
          <p style={{ fontFamily: "'Exo 2', sans-serif", fontSize: '13px', color: '#6080a0', marginTop: '6px', fontWeight: 300 }}>
            100% self-hosted. No vendor lock-in. All data stays on your machine.
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { icon: <IconOllama />,    name: 'Ollama',      desc: 'Local LLM runtime',    accent: '#e8e8f0', href: 'https://ollama.com' },
            { icon: <IconDocker />,    name: 'Docker',      desc: 'Containerization',     accent: '#2496ED', href: 'https://docker.com' },
            { icon: <IconPostgres />,  name: 'PostgreSQL',  desc: 'Relational database',  accent: '#336791', href: 'https://postgresql.org' },
            { icon: <IconPgvector />,  name: 'pgvector',    desc: 'Vector similarity',    accent: '#a78bfa', href: 'https://github.com/pgvector/pgvector' },
            { icon: <IconPython />,    name: 'Python',      desc: 'Backend runtime',      accent: '#3776AB', href: 'https://python.org' },
            { icon: <IconFastAPI />,   name: 'FastAPI',     desc: 'API framework',        accent: '#009688', href: 'https://fastapi.tiangolo.com' },
            { icon: <IconNextJS />,    name: 'Next.js',     desc: 'Frontend framework',   accent: '#dce8f8', href: 'https://nextjs.org' },
            { icon: <IconLangChain />, name: 'LangChain',   desc: 'RAG pipeline',         accent: '#00C4B4', href: 'https://langchain.com' },
          ].map(({ icon, name, desc, accent, href }) => (
            <a
              key={name}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-xl p-5 text-center flex flex-col items-center gap-3"
              style={{
                background: '#0b0f1e',
                border: `1px solid ${accent}18`,
                textDecoration: 'none',
                transition: 'border-color 0.2s, transform 0.15s, background 0.2s',
              }}
              onMouseEnter={e => {
                const el = e.currentTarget as HTMLElement;
                el.style.borderColor = `${accent}55`;
                el.style.background = `${accent}07`;
                el.style.transform = 'translateY(-2px)';
              }}
              onMouseLeave={e => {
                const el = e.currentTarget as HTMLElement;
                el.style.borderColor = `${accent}18`;
                el.style.background = '#0b0f1e';
                el.style.transform = 'translateY(0)';
              }}
            >
              <div style={{ opacity: 0.9 }}>{icon}</div>
              <div>
                <p style={{
                  fontFamily: "'Share Tech Mono', monospace",
                  fontSize: '11px', letterSpacing: '2px',
                  color: accent, margin: 0,
                }}>
                  {name}
                </p>
                <p style={{
                  fontFamily: "'Exo 2', sans-serif",
                  fontSize: '11px', color: '#6080a0',
                  fontWeight: 300, margin: '3px 0 0',
                }}>
                  {desc}
                </p>
              </div>
            </a>
          ))}
        </div>

        {/* NVIDIA optional note */}
        <div className="mt-6 flex items-center justify-center gap-4 opacity-50">
          <IconNVIDIA />
          <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '2px', color: '#76B900' }}>
            NVIDIA CUDA — optional GPU acceleration for faster inference
          </p>
        </div>
      </div>

      {/* ── GitHub / GitLab badges ────────────────────────────────────────── */}
      <div className="flex justify-center gap-6 pb-14 px-4">
        <a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2.5 rounded-lg px-5 py-3 transition-all"
          style={{ background: '#0b0f1e', border: '1px solid rgba(255,255,255,0.1)', color: '#dce8f8', fontFamily: "'Share Tech Mono', monospace", fontSize: '12px', letterSpacing: '2px', textDecoration: 'none' }}
          onMouseEnter={e => ((e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.3)')}
          onMouseLeave={e => ((e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.1)')}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" style={{ color: '#dce8f8' }}>
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12z"/>
          </svg>
          GITHUB
        </a>
        <a
          href="https://gitlab.com"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2.5 rounded-lg px-5 py-3 transition-all"
          style={{ background: '#0b0f1e', border: '1px solid rgba(252,109,38,0.25)', color: '#dce8f8', fontFamily: "'Share Tech Mono', monospace", fontSize: '12px', letterSpacing: '2px', textDecoration: 'none' }}
          onMouseEnter={e => ((e.currentTarget as HTMLElement).style.borderColor = 'rgba(252,109,38,0.55)')}
          onMouseLeave={e => ((e.currentTarget as HTMLElement).style.borderColor = 'rgba(252,109,38,0.25)')}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" style={{ color: '#fc6d26' }}>
            <path d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 01-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 014.82 2a.43.43 0 01.58 0 .42.42 0 01.11.18l2.44 7.49h8.1l2.44-7.49a.42.42 0 01.11-.18.43.43 0 01.58 0 .42.42 0 01.11.18l2.44 7.51L23 13.45a.84.84 0 01-.35.94z"/>
          </svg>
          GITLAB
        </a>
      </div>

      {/* ── Install Guide ─────────────────────────────────────────────────── */}
      <div className="max-w-3xl mx-auto w-full px-4 pb-24">
        <div className="text-center mb-10">
          <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '5px', color: '#607898' }}>GETTING STARTED</p>
          <h2 style={{ fontFamily: "'Orbitron', monospace", fontWeight: 700, fontSize: '1.3rem', color: '#dce8f8', marginTop: '8px' }}>Installation Guide</h2>
        </div>

        {/* OS tab state lives here */}
        {(() => {
          const steps: {
            step: string; title: string; accent: string; desc: string;
            linux: string; mac: string; windows: string;
          }[] = [
            {
              step: '01', title: 'Install Docker', accent: '#00d4ff',
              desc: 'Depfix uses Docker Compose to run PostgreSQL + pgvector and other services.',
              linux: `# Install Docker Engine\ncurl -fsSL https://get.docker.com | sh\nsudo usermod -aG docker $USER   # re-login after this\n\n# Verify\ndocker --version\ndocker compose version`,
              mac: `# Install Docker Desktop for macOS\n# Download from https://www.docker.com/products/docker-desktop/\n# — or via Homebrew:\nbrew install --cask docker\n\n# Verify\ndocker --version\ndocker compose version`,
              windows: `# Install Docker Desktop for Windows\n# Download from https://www.docker.com/products/docker-desktop/\n# Requires WSL2 (enabled automatically by the installer)\n\n# After install, open PowerShell:\ndocker --version\ndocker compose version`,
            },
            {
              step: '02', title: 'Install Ollama', accent: '#a78bfa',
              desc: 'Ollama runs the local LLM entirely on your machine — no cloud required.',
              linux: `# Install Ollama\ncurl -fsSL https://ollama.com/install.sh | sh\n\n# Pull a model (pick one)\nollama pull llama3\nollama pull mistral\nollama pull gemma3`,
              mac: `# Install Ollama for macOS\n# Download from https://ollama.com/download\n# — or via Homebrew:\nbrew install ollama\n\n# Start and pull a model\nollama serve &\nollama pull llama3`,
              windows: `# Install Ollama for Windows\n# Download the installer from https://ollama.com/download\n# Run OllamaSetup.exe — no WSL required\n\n# Open PowerShell after install:\nollama pull llama3\nollama pull mistral`,
            },
            {
              step: '03', title: 'Start Services', accent: '#ffb700',
              desc: 'Clone the repo and spin up PostgreSQL with pgvector and all supporting containers.',
              linux: `git clone https://github.com/your-org/depfix.git\ncd depfix\n\n# Start database + services\ndocker compose up -d\n\n# Verify containers are running\ndocker compose ps`,
              mac: `git clone https://github.com/your-org/depfix.git\ncd depfix\n\n# Start database + services\ndocker compose up -d\n\n# Verify containers are running\ndocker compose ps`,
              windows: `git clone https://github.com/your-org/depfix.git\ncd depfix\n\n# Open PowerShell in the project folder:\ndocker compose up -d\n\n# Verify containers are running\ndocker compose ps`,
            },
            {
              step: '04', title: 'Backend Setup', accent: '#00ff88',
              desc: 'Install Python dependencies and start the FastAPI backend.',
              linux: `python3 -m venv .venv\nsource .venv/bin/activate\n\npip install -r requirements.txt\n\n# Start backend (port 8000)\nuvicorn backend.app.main:app --reload --port 8000`,
              mac: `python3 -m venv .venv\nsource .venv/bin/activate\n\npip install -r requirements.txt\n\n# Start backend (port 8000)\nuvicorn backend.app.main:app --reload --port 8000`,
              windows: `# PowerShell:\npython -m venv .venv\n.venv\\Scripts\\Activate.ps1\n\npip install -r requirements.txt\n\n# Start backend (port 8000)\nuvicorn backend.app.main:app --reload --port 8000`,
            },
            {
              step: '05', title: 'Frontend Setup', accent: '#ff3c3c',
              desc: 'Install Node.js dependencies and launch the Next.js frontend.',
              linux: `cd frontend\nnpm install\nnpm run dev\n\n# Open in browser\nxdg-open http://localhost:3000`,
              mac: `cd frontend\nnpm install\nnpm run dev\n\n# Open in browser\nopen http://localhost:3000`,
              windows: `cd frontend\nnpm install\nnpm run dev\n\n# Open in browser (PowerShell)\nStart-Process http://localhost:3000`,
            },
          ];

          return steps.map(({ step, title, accent, desc, linux, mac, windows }) => (
            <StepCard
              key={step}
              step={step} title={title} accent={accent} desc={desc}
              linux={linux} mac={mac} windows={windows}
            />
          ));
        })()}

        {/* Requirements note */}
        <div className="mt-8 p-5 rounded-lg" style={{ background: 'rgba(0,212,255,0.03)', border: '1px solid rgba(0,212,255,0.1)' }}>
          <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', letterSpacing: '3px', color: '#607898', marginBottom: '12px' }}>SYSTEM REQUIREMENTS</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'RAM', value: '≥ 8 GB', note: '16 GB recommended' },
              { label: 'STORAGE', value: '≥ 10 GB', note: 'for models + data' },
              { label: 'OS', value: 'Linux / macOS / Win', note: 'WSL2 or native' },
              { label: 'GPU', value: 'Optional', note: 'CPU inference works' },
            ].map(({ label, value, note }) => (
              <div key={label}>
                <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', letterSpacing: '2px', color: '#607898' }}>{label}</p>
                <p style={{ fontFamily: "'Orbitron', monospace", fontSize: '13px', fontWeight: 700, color: '#dce8f8', marginTop: '2px' }}>{value}</p>
                <p style={{ fontFamily: "'Exo 2', sans-serif", fontSize: '11px', color: '#607898', fontWeight: 300 }}>{note}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <div className="text-center pb-8" style={{ borderTop: '1px solid rgba(0,212,255,0.06)', paddingTop: '24px' }}>
        <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#1a2840' }}>
          DEPFIX · LOCAL · PRIVATE · OPEN SOURCE
        </p>
      </div>
    </div>
  );
}
