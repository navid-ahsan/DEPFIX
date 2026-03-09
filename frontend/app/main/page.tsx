'use client';

import Link from 'next/link';
import DepfixLogo from '../components/DepfixLogo';

export default function MainPage() {
  return (
    <div
      className="min-h-screen depfix-grid-bg flex flex-col"
      style={{ background: '#060810', color: '#dce8f8' }}
    >
      {/* Hero */}
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

      {/* Feature cards */}
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

      {/* GitHub / GitLab badges */}
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
          {/* GitHub mark */}
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
          {/* GitLab mark */}
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" style={{ color: '#fc6d26' }}>
            <path d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 01-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 014.82 2a.43.43 0 01.58 0 .42.42 0 01.11.18l2.44 7.49h8.1l2.44-7.49a.42.42 0 01.11-.18.43.43 0 01.58 0 .42.42 0 01.11.18l2.44 7.51L23 13.45a.84.84 0 01-.35.94z"/>
          </svg>
          GITLAB
        </a>
      </div>

      {/* Install Guide */}
      <div className="max-w-3xl mx-auto w-full px-4 pb-24">
        <div className="text-center mb-10">
          <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '5px', color: '#607898' }}>GETTING STARTED</p>
          <h2 style={{ fontFamily: "'Orbitron', monospace", fontWeight: 700, fontSize: '1.3rem', color: '#dce8f8', marginTop: '8px' }}>Installation Guide</h2>
        </div>

        {/* Step cards */}
        {[
          {
            step: '01',
            title: 'Install Docker',
            accent: '#00d4ff',
            desc: 'Depfix uses Docker Compose to run PostgreSQL + pgvector and other services.',
            code: `# macOS / Linux
curl -fsSL https://get.docker.com | sh

# Verify
docker --version
docker compose version`,
          },
          {
            step: '02',
            title: 'Install Ollama',
            accent: '#a78bfa',
            desc: 'Ollama runs the local LLM (Llama 3, Mistral, Gemma 3, etc.) entirely on your machine — no cloud required.',
            code: `# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model (pick one)
ollama pull llama3
ollama pull mistral
ollama pull gemma3`,
          },
          {
            step: '03',
            title: 'Start Services',
            accent: '#ffb700',
            desc: 'Spin up PostgreSQL with pgvector and all supporting containers.',
            code: `git clone https://github.com/your-org/depfix.git
cd depfix

# Start database + services
docker compose up -d

# Verify containers are running
docker compose ps`,
          },
          {
            step: '04',
            title: 'Backend Setup',
            accent: '#00ff88',
            desc: 'Install Python dependencies and start the FastAPI backend.',
            code: `# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Start backend (port 8000)
uvicorn backend.app.main:app --reload --port 8000`,
          },
          {
            step: '05',
            title: 'Frontend Setup',
            accent: '#ff3c3c',
            desc: 'Install Node.js dependencies and launch the Next.js frontend.',
            code: `cd frontend

# Install packages
npm install

# Start dev server (port 3000)
npm run dev

# Open in browser
open http://localhost:3000`,
          },
        ].map(({ step, title, accent, desc, code }) => (
          <div key={step} className="mb-5 rounded-xl overflow-hidden" style={{ background: '#0b0f1e', border: `1px solid ${accent}22`, borderLeft: `3px solid ${accent}` }}>
            <div className="px-6 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
              <div className="flex items-center gap-3 mb-2">
                <span style={{ fontFamily: "'Orbitron', monospace", fontSize: '11px', fontWeight: 700, color: accent, letterSpacing: '2px' }}>STEP {step}</span>
                <span style={{ fontFamily: "'Orbitron', monospace", fontSize: '14px', fontWeight: 700, color: '#dce8f8' }}>{title}</span>
              </div>
              <p style={{ fontFamily: "'Exo 2', sans-serif", fontSize: '13px', color: '#8cb4d4', fontWeight: 300, lineHeight: 1.6 }}>{desc}</p>
            </div>
            <pre
              className="overflow-x-auto text-xs leading-relaxed px-6 py-4 m-0"
              style={{ fontFamily: "'Share Tech Mono', monospace", color: '#8cb4d4', background: 'rgba(0,0,0,0.3)' }}
            >
              <code>{code}</code>
            </pre>
          </div>
        ))}

        {/* Requirements note */}
        <div className="mt-8 p-5 rounded-lg" style={{ background: 'rgba(0,212,255,0.03)', border: '1px solid rgba(0,212,255,0.1)' }}>
          <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', letterSpacing: '3px', color: '#607898', marginBottom: '12px' }}>SYSTEM REQUIREMENTS</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'RAM', value: '≥ 8 GB', note: '16 GB recommended' },
              { label: 'STORAGE', value: '≥ 10 GB', note: 'for models + data' },
              { label: 'OS', value: 'Linux / macOS', note: 'WSL2 on Windows' },
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

      {/* Footer */}
      <div className="text-center pb-8" style={{ borderTop: '1px solid rgba(0,212,255,0.06)', paddingTop: '24px' }}>
        <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#1a2840' }}>
          DEPFIX · LOCAL · PRIVATE · OPEN SOURCE
        </p>
      </div>
    </div>
  );
}
