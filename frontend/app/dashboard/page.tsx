'use client';

import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import axios from 'axios';
import Navbar from '../components/Navbar';

interface ErrorLog {
  id: string;
  filename: string;
  file_format: string;
  error_count: number;
  primary_error_type?: string;
  is_processed: boolean;
  created_at: string;
}

export default function Dashboard() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [errorLogs, setErrorLogs] = useState<ErrorLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (status === 'unauthenticated') router.push('/main');
  }, [status, router]);

  useEffect(() => {
    if (status === 'authenticated') fetchErrorLogs();
  }, [status]);

  const fetchErrorLogs = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/v1/logs', {
        headers: { Authorization: `Bearer ${session?.accessToken}` },
      });
      setErrorLogs(response.data || []);
    } catch (err) {
      console.error('Failed to fetch error logs:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeLog = (logId: string) => {
    router.push(`/setup/rag-analysis?log_id=${logId}`);
  };

  if (status === 'loading') {
    return (
      <div
        className="min-h-screen flex items-center justify-center depfix-grid-bg"
        style={{ background: '#060810' }}
      >
        <div className="text-center">
          <div
            className="w-10 h-10 rounded-full border-2 border-transparent animate-spin mx-auto mb-5"
            style={{ borderTopColor: '#00d4ff' }}
          />
          <p style={{ fontFamily: "'Share Tech Mono', monospace", color: '#607898', fontSize: '11px', letterSpacing: '4px' }}>
            AUTHENTICATING...
          </p>
        </div>
      </div>
    );
  }

  const analyzedCount = errorLogs.filter(l => l.is_processed).length;
  const pendingCount  = errorLogs.filter(l => !l.is_processed).length;

  return (
    <div
      className="min-h-screen depfix-grid-bg"
      style={{ background: '#060810', color: '#dce8f8' }}
    >
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 py-10">

        {/* Stats row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
          {[
            { label: 'TOTAL LOGS', value: errorLogs.length, accent: '#00d4ff' },
            { label: 'ANALYZED',   value: analyzedCount,     accent: '#00ff88' },
            { label: 'PENDING',    value: pendingCount,      accent: '#ffb700' },
          ].map(({ label, value, accent }) => (
            <div
              key={label}
              className="rounded-lg p-5"
              style={{ background: '#0b0f1e', border: `1px solid ${accent}22`, borderLeft: `3px solid ${accent}` }}
            >
              <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#607898' }}>
                {label}
              </p>
              <p style={{ fontFamily: "'Orbitron', monospace", fontSize: '34px', fontWeight: 700, color: accent, lineHeight: 1.15 }}>
                {value}
              </p>
            </div>
          ))}
        </div>

        {/* Error Logs panel */}
        <div className="rounded-lg" style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.1)' }}>

          {/* Panel header */}
          <div
            className="flex items-center justify-between px-6 py-4"
            style={{ borderBottom: '1px solid rgba(0,212,255,0.08)' }}
          >
            <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '11px', letterSpacing: '4px', color: '#00d4ff' }}>
              // ERROR LOGS
            </span>
            <button
              onClick={() => router.push('/setup/github-connection')}
              className="rounded text-xs transition-all"
              style={{
                background: 'rgba(0,255,136,0.07)',
                border: '1px solid rgba(0,255,136,0.35)',
                color: '#00ff88',
                fontFamily: "'Share Tech Mono', monospace",
                letterSpacing: '2px',
                padding: '6px 14px',
              }}
              onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(0,255,136,0.14)')}
              onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(0,255,136,0.07)')}
            >
              + UPLOAD NEW LOG
            </button>
          </div>

          {/* Loading */}
          {loading && (
            <div className="flex justify-center py-20">
              <div className="w-8 h-8 rounded-full border-2 border-transparent animate-spin"
                   style={{ borderTopColor: '#00d4ff' }} />
            </div>
          )}

          {/* Empty state */}
          {!loading && errorLogs.length === 0 && (
            <div className="text-center py-24">
              <div className="mb-4 text-4xl opacity-30">📂</div>
              <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '11px', letterSpacing: '3px', color: '#607898' }}>
                NO ERROR LOGS UPLOADED YET
              </p>
              <button
                onClick={() => router.push('/setup/github-connection')}
                className="mt-6 rounded text-xs transition-all"
                style={{
                  background: 'rgba(0,212,255,0.07)',
                  border: '1px solid rgba(0,212,255,0.3)',
                  color: '#00d4ff',
                  fontFamily: "'Share Tech Mono', monospace",
                  letterSpacing: '2px',
                  padding: '7px 18px',
                }}
                onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(0,212,255,0.14)')}
                onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(0,212,255,0.07)')}
              >
                UPLOAD YOUR FIRST LOG
              </button>
            </div>
          )}

          {/* Log list */}
          {!loading && errorLogs.length > 0 && (
            <div>
              {errorLogs.map((log, idx) => (
                <div
                  key={log.id}
                  className="px-6 py-5 flex items-center justify-between gap-4 transition-colors"
                  style={{
                    borderTop: idx === 0 ? 'none' : '1px solid rgba(0,212,255,0.06)',
                    borderLeft: '3px solid rgba(255,60,60,0.25)',
                  }}
                  onMouseEnter={e => {
                    (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.02)';
                    (e.currentTarget as HTMLElement).style.borderLeftColor = '#ff3c3c';
                  }}
                  onMouseLeave={e => {
                    (e.currentTarget as HTMLElement).style.background = 'transparent';
                    (e.currentTarget as HTMLElement).style.borderLeftColor = 'rgba(255,60,60,0.25)';
                  }}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      <span className="text-sm font-semibold truncate" style={{ color: '#dce8f8', maxWidth: '300px' }}>
                        {log.filename}
                      </span>
                      <span
                        className="text-xs rounded px-2 py-0.5"
                        style={{ background: 'rgba(255,60,60,0.1)', border: '1px solid rgba(255,60,60,0.25)', color: '#ff3c3c', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '1px' }}
                      >
                        {log.error_count} errors
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', color: '#607898' }}>
                        {new Date(log.created_at).toLocaleString()}
                      </span>
                      <span
                        className="text-xs rounded px-2 py-0.5"
                        style={{ background: 'rgba(0,212,255,0.06)', border: '1px solid rgba(0,212,255,0.15)', color: '#00d4ff', fontFamily: "'Share Tech Mono', monospace", fontSize: '10px' }}
                      >
                        {log.file_format.toUpperCase()}
                      </span>
                      {log.primary_error_type && (
                        <span
                          className="text-xs rounded px-2 py-0.5"
                          style={{ background: 'rgba(255,183,0,0.06)', border: '1px solid rgba(255,183,0,0.2)', color: '#ffb700', fontFamily: "'Share Tech Mono', monospace", fontSize: '10px' }}
                        >
                          {log.primary_error_type}
                        </span>
                      )}
                      <span
                        className="text-xs rounded px-2 py-0.5"
                        style={log.is_processed
                          ? { background: 'rgba(0,255,136,0.06)', border: '1px solid rgba(0,255,136,0.2)', color: '#00ff88', fontFamily: "'Share Tech Mono', monospace", fontSize: '10px' }
                          : { background: 'rgba(255,183,0,0.06)', border: '1px solid rgba(255,183,0,0.2)', color: '#ffb700', fontFamily: "'Share Tech Mono', monospace", fontSize: '10px' }
                        }
                      >
                        {log.is_processed ? '✓ ANALYZED' : '⏳ PENDING'}
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={() => handleAnalyzeLog(log.id)}
                    disabled={!log.is_processed}
                    className="flex-shrink-0 rounded text-xs transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                    style={{
                      background: log.is_processed ? 'rgba(0,255,136,0.08)' : 'rgba(255,255,255,0.03)',
                      border: log.is_processed ? '1px solid rgba(0,255,136,0.4)' : '1px solid rgba(255,255,255,0.08)',
                      color: log.is_processed ? '#00ff88' : '#607898',
                      fontFamily: "'Share Tech Mono', monospace",
                      letterSpacing: '2px',
                      padding: '7px 16px',
                      whiteSpace: 'nowrap',
                    }}
                    onMouseEnter={e => { if (log.is_processed) (e.currentTarget as HTMLElement).style.background = 'rgba(0,255,136,0.16)'; }}
                    onMouseLeave={e => { if (log.is_processed) (e.currentTarget as HTMLElement).style.background = 'rgba(0,255,136,0.08)'; }}
                  >
                    ANALYZE WITH AI →
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Pipeline footer */}
        <div className="mt-10 flex flex-wrap items-center justify-center gap-1 opacity-30">
          {[
            { t: 'error.log',    c: '#ff3c3c' }, { t: '→', c: '#607898' },
            { t: 'chunk·embed',  c: '#ffb700' }, { t: '→', c: '#607898' },
            { t: 'pgvector',     c: '#a78bfa' }, { t: '→', c: '#607898' },
            { t: 'local llm',    c: '#00d4ff' }, { t: '→', c: '#607898' },
            { t: 'verified fix', c: '#00ff88' },
          ].map(({ t, c }, i) => (
            <span key={i} style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', letterSpacing: '2px', color: c }}>
              {t}
            </span>
          ))}
        </div>

      </main>
    </div>
  );
}
