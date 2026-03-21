'use client';

import Link from 'next/link';
import { useSession, signOut } from 'next-auth/react';
import DepfixLogo from './DepfixLogo';

export default function Navbar() {
  const { data: session } = useSession();

  return (
    <header
      className="sticky top-0 z-50"
      style={{
        background: 'rgba(11,15,30,0.92)',
        borderBottom: '1px solid rgba(0,212,255,0.1)',
        backdropFilter: 'blur(10px)',
      }}
    >
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        {/* Logo — links to home */}
        <Link href="/" className="transition-opacity hover:opacity-75">
          <DepfixLogo iconSize={30} showText={true} />
        </Link>

        {/* Right: settings + user + sign out */}
        <div className="flex items-center gap-5">
          <Link
            href="/setup/config"
            title="Configuration"
            style={{
              fontFamily: "'Share Tech Mono', monospace",
              fontSize: '16px',
              color: '#607898',
              lineHeight: 1,
              textDecoration: 'none',
              transition: 'color 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.color = '#00d4ff')}
            onMouseLeave={e => (e.currentTarget.style.color = '#607898')}
          >
            ⚙
          </Link>
          {session?.user?.name && (
            <span
              style={{
                fontFamily: "'Share Tech Mono', monospace",
                color: '#607898',
                fontSize: '11px',
                letterSpacing: '2px',
              }}
            >
              {session.user.name.toUpperCase()}
            </span>
          )}
          <button
            onClick={() => signOut({ redirect: true, callbackUrl: '/' })}
            style={{
              fontFamily: "'Share Tech Mono', monospace",
              fontSize: '10px',
              letterSpacing: '2px',
              padding: '4px 12px',
              border: '1px solid rgba(255,60,60,0.35)',
              color: '#ff3c3c',
              background: 'rgba(255,60,60,0.05)',
              cursor: 'pointer',
              borderRadius: '2px',
              transition: 'background 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,60,60,0.12)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,60,60,0.05)')}
          >
            SIGN OUT
          </button>
        </div>
      </div>
    </header>
  );
}
