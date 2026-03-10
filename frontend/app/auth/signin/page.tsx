'use client';

import { signIn } from 'next-auth/react';
import { useState } from 'react';
import DepfixLogo from '../../components/DepfixLogo';

export default function SignIn() {
  const [testEmail, setTestEmail] = useState('test@example.com');
  const [testPassword, setTestPassword] = useState('test123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleTestLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await signIn('credentials', {
        email: testEmail,
        password: testPassword,
        redirect: true,
        callbackUrl: '/setup/config',
      });

      if (result?.error) {
        setError('Invalid test credentials. Use test@example.com / test123');
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGitHubLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      await signIn('github', {
        redirect: true,
        callbackUrl: '/setup/config',
      });
    } catch (err) {
      setError('GitHub authentication failed.');
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center depfix-grid-bg"
      style={{ background: '#060810' }}
    >
      <div className="w-full max-w-md mx-auto px-4 py-12">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="flex justify-center mb-5">
            <DepfixLogo iconSize={72} showText={false} />
          </div>
          <h1 className="select-none" style={{ fontFamily: "'Orbitron', monospace", fontWeight: 900, fontSize: '2.4rem', lineHeight: 1 }}>
            <span style={{ color: '#ff3c3c' }}>DEP</span><span style={{ color: '#00ff88' }}>FIX</span>
          </h1>
          <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '4px', color: '#607898', marginTop: '8px' }}>
            SIGN IN TO CONTINUE
          </p>
        </div>

        {/* Card */}
        <div className="rounded-xl p-8" style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.12)' }}>

          {error && (
            <div className="mb-6 p-3 rounded text-xs" style={{ background: 'rgba(255,60,60,0.08)', border: '1px solid rgba(255,60,60,0.3)', color: '#ff3c3c', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '1px' }}>
              {error}
            </div>
          )}

          {/* GitHub */}
          <div className="mb-6">
            <button
              onClick={handleGitHubLogin}
              disabled={loading}
              className="w-full rounded transition-all disabled:opacity-40"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.14)', color: '#dce8f8', fontFamily: "'Share Tech Mono', monospace", fontSize: '11px', letterSpacing: '3px', padding: '13px' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.09)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
            >
              {loading ? 'SIGNING IN...' : '⬡  SIGN IN WITH GITHUB'}
            </button>
          </div>

          {/* Divider */}
          <div className="relative mb-6 flex items-center gap-3">
            <div className="flex-1 h-px" style={{ background: 'rgba(0,212,255,0.08)' }} />
            <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#1a2840' }}>OR DEMO</span>
            <div className="flex-1 h-px" style={{ background: 'rgba(0,212,255,0.08)' }} />
          </div>

          {/* Demo login */}
          <form onSubmit={handleTestLogin} className="space-y-4">
            <div>
              <label style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#607898', display: 'block', marginBottom: '6px' }}>
                EMAIL
              </label>
              <input
                type="email"
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
                disabled={loading}
                className="w-full rounded disabled:opacity-40"
                style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(0,212,255,0.18)', color: '#dce8f8', fontFamily: "'Share Tech Mono', monospace", fontSize: '13px', padding: '10px 12px', outline: 'none' }}
                placeholder="test@example.com"
              />
            </div>
            <div>
              <label style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#607898', display: 'block', marginBottom: '6px' }}>
                PASSWORD
              </label>
              <input
                type="password"
                value={testPassword}
                onChange={(e) => setTestPassword(e.target.value)}
                disabled={loading}
                className="w-full rounded disabled:opacity-40"
                style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(0,212,255,0.18)', color: '#dce8f8', fontFamily: "'Share Tech Mono', monospace", fontSize: '13px', padding: '10px 12px', outline: 'none' }}
                placeholder="test123"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded transition-all disabled:opacity-40"
              style={{ background: 'rgba(0,212,255,0.07)', border: '1px solid rgba(0,212,255,0.4)', color: '#00d4ff', fontFamily: "'Share Tech Mono', monospace", fontSize: '11px', letterSpacing: '3px', padding: '13px' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,212,255,0.14)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'rgba(0,212,255,0.07)')}
            >
              {loading ? 'SIGNING IN...' : 'SIGN IN WITH DEMO ACCOUNT'}
            </button>
          </form>

          <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', color: '#1a2840', textAlign: 'center', marginTop: '20px', letterSpacing: '2px' }}>
            demo: test@example.com / test123
          </p>
        </div>
      </div>
    </div>
  );
}
