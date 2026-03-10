'use client';

import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect, useState, useCallback, useRef } from 'react';
import axios from 'axios';
import Navbar from '../components/Navbar';
import { api } from '../lib/api';

interface ErrorLog {
  id: string;
  filename: string;
  file_format: string;
  error_count: number;
  primary_error_type?: string;
  is_processed: boolean;
  created_at: string;
}

interface ServiceStatus {
  backend: 'ok' | 'error' | 'checking';
  ollama:  'ok' | 'error' | 'checking';
  pgvector: 'ok' | 'error' | 'checking';
}

// ── Connection status bar ────────────────────────────────────────────────────
function ConnectionBar({ statuses }: { statuses: ServiceStatus }) {
  const dot = (label: string, state: 'ok' | 'error' | 'checking') => {
    const color  = state === 'ok' ? '#00ff88' : state === 'error' ? '#ff3c3c' : '#ffb700';
    const symbol = state === 'ok' ? '●' : state === 'error' ? '●' : '◌';
    return (
      <span key={label} className="flex items-center gap-1.5" style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', letterSpacing: '2px', color: '#607898' }}>
        <span style={{ color, fontSize: '11px', lineHeight: 1, animation: state === 'checking' ? 'ep-pulse 1.2s infinite' : 'none' }}>{symbol}</span>
        <span style={{ color: state === 'ok' ? '#8cb4d4' : state === 'error' ? '#ff3c3c' : '#ffb700' }}>{label.toUpperCase()}</span>
      </span>
    );
  };

  return (
    <div
      style={{
        background: 'rgba(11,15,30,0.8)',
        borderBottom: '1px solid rgba(0,212,255,0.06)',
        padding: '7px 0',
        backdropFilter: 'blur(4px)',
      }}
    >
      <div className="max-w-7xl mx-auto px-4 flex items-center gap-6">
        <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', letterSpacing: '3px', color: '#607898', opacity: 0.6 }}>
          STATUS
        </span>
        {dot('backend', statuses.backend)}
        {dot('ollama', statuses.ollama)}
        {dot('pgvector', statuses.pgvector)}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [errorLogs, setErrorLogs] = useState<ErrorLog[]>([]);
  const [loading, setLoading] = useState(true);

  // Connection statuses
  const [services, setServices] = useState<ServiceStatus>({
    backend: 'checking', ollama: 'checking', pgvector: 'checking',
  });

  // First-run modal
  const [showFirstRun, setShowFirstRun] = useState(false);

  // Drag-and-drop upload
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (status === 'unauthenticated') router.push('/main');
  }, [status, router]);

  useEffect(() => {
    if (status === 'authenticated') {
      fetchErrorLogs();
      checkServices();
      checkFirstRun();
    }
  }, [status]); // eslint-disable-line react-hooks/exhaustive-deps

  const checkFirstRun = async () => {
    try {
      const res = await axios.get(api('/api/v1/config/'));
      if (!res.data?.llm_model) setShowFirstRun(true);
    } catch {
      // backend unreachable — still show dashboard
    }
  };

  const checkServices = async () => {
    // backend
    try {
      await axios.get(api('/api/v1/config/'));
      setServices(s => ({ ...s, backend: 'ok' }));
    } catch {
      setServices(s => ({ ...s, backend: 'error' }));
    }

    // ollama
    try {
      const res = await axios.post(api('/api/v1/config/test/ollama'), {});
      setServices(s => ({ ...s, ollama: res.data?.ok ? 'ok' : 'error' }));
    } catch {
      setServices(s => ({ ...s, ollama: 'error' }));
    }

    // pgvector
    try {
      const res = await axios.post(api('/api/v1/config/test/postgres'), {});
      setServices(s => ({ ...s, pgvector: res.data?.ok ? 'ok' : 'error' }));
    } catch {
      setServices(s => ({ ...s, pgvector: 'error' }));
    }
  };

  const fetchErrorLogs = async () => {
    try {
      const response = await axios.get(api('/api/v1/logs'), {
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

  // ── Drag-and-drop handlers ─────────────────────────────────────────────────
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
  }, []);

  const uploadFile = async (file: File) => {
    setUploading(true);
    setUploadError(null);
    const form = new FormData();
    form.append('file', file);
    try {
      await axios.post(api('/api/v1/logs/upload'), form, {
        headers: { Authorization: `Bearer ${session?.accessToken}`, 'Content-Type': 'multipart/form-data' },
      });
      await fetchErrorLogs();
    } catch (err: unknown) {
      const msg = axios.isAxiosError(err) ? (err.response?.data?.detail ?? err.message) : String(err);
      setUploadError(msg);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) await uploadFile(file);
  }, [session]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) await uploadFile(file);
    e.target.value = '';
  };

  // ─────────────────────────────────────────────────────────────────────────
  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center depfix-grid-bg" style={{ background: '#060810' }}>
        <div className="text-center">
          <div className="w-10 h-10 rounded-full border-2 border-transparent animate-spin mx-auto mb-5" style={{ borderTopColor: '#00d4ff' }} />
          <p style={{ fontFamily: "'Share Tech Mono', monospace", color: '#607898', fontSize: '11px', letterSpacing: '4px' }}>AUTHENTICATING...</p>
        </div>
      </div>
    );
  }

  const analyzedCount = errorLogs.filter(l => l.is_processed).length;
  const pendingCount  = errorLogs.filter(l => !l.is_processed).length;

  return (
    <div className="min-h-screen depfix-grid-bg" style={{ background: '#060810', color: '#dce8f8' }}>
      <Navbar />
      <ConnectionBar statuses={services} />

      {/* ── First-run modal ─────────────────────────────────────────────── */}
      {showFirstRun && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{ background: 'rgba(6,8,16,0.85)', backdropFilter: 'blur(6px)' }}
        >
          <div
            className="rounded-2xl p-8 max-w-md w-full mx-4"
            style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.2)', boxShadow: '0 0 60px rgba(0,212,255,0.06)' }}
          >
            <div className="mb-5">
              <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', letterSpacing: '4px', color: '#607898' }}>INITIAL SETUP REQUIRED</p>
              <h2 style={{ fontFamily: "'Orbitron', monospace", fontWeight: 700, fontSize: '1.4rem', color: '#dce8f8', marginTop: '6px' }}>
                Welcome to DEPFIX
              </h2>
              <p style={{ fontFamily: "'Exo 2', sans-serif", fontSize: '13px', color: '#8cb4d4', marginTop: '10px', lineHeight: 1.65, fontWeight: 300 }}>
                No LLM model is configured yet. Complete the setup wizard to connect your Ollama instance, select a model, and configure your vector database before analysing logs.
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => router.push('/setup/config')}
                className="flex-1 rounded-lg py-3 text-sm transition-all"
                style={{
                  background: 'rgba(0,212,255,0.1)',
                  border: '1px solid rgba(0,212,255,0.4)',
                  color: '#00d4ff',
                  fontFamily: "'Share Tech Mono', monospace",
                  letterSpacing: '2px',
                  cursor: 'pointer',
                }}
                onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(0,212,255,0.18)')}
                onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(0,212,255,0.1)')}
              >
                START SETUP →
              </button>
              <button
                onClick={() => setShowFirstRun(false)}
                className="rounded-lg py-3 px-5 text-sm transition-all"
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  color: '#607898',
                  fontFamily: "'Share Tech Mono', monospace",
                  letterSpacing: '2px',
                  cursor: 'pointer',
                }}
                onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.06)')}
                onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)')}
              >
                SKIP
              </button>
            </div>
          </div>
        </div>
      )}

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
              <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#607898' }}>{label}</p>
              <p style={{ fontFamily: "'Orbitron', monospace", fontSize: '34px', fontWeight: 700, color: accent, lineHeight: 1.15 }}>{value}</p>
            </div>
          ))}
        </div>

        {/* ── Drag-and-drop upload zone ──────────────────────────────────── */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className="mb-8 rounded-xl flex flex-col items-center justify-center gap-3 cursor-pointer transition-all"
          style={{
            padding: '32px 20px',
            background: dragging ? 'rgba(0,212,255,0.06)' : 'rgba(11,15,30,0.5)',
            border: `2px dashed ${dragging ? '#00d4ff' : 'rgba(0,212,255,0.2)'}`,
            transition: 'all 0.2s',
          }}
        >
          <input ref={fileInputRef} type="file" accept=".log,.txt,.json,.jsonl" className="hidden" onChange={handleFileInput} />
          {uploading ? (
            <>
              <div className="w-8 h-8 rounded-full border-2 border-transparent animate-spin" style={{ borderTopColor: '#00d4ff' }} />
              <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#00d4ff' }}>UPLOADING...</p>
            </>
          ) : (
            <>
              <div style={{ fontSize: '28px', opacity: dragging ? 1 : 0.4, transition: 'opacity 0.2s' }}>📂</div>
              <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: dragging ? '#00d4ff' : '#607898', transition: 'color 0.2s' }}>
                {dragging ? 'DROP TO UPLOAD' : 'DRAG & DROP LOG FILE · OR CLICK TO BROWSE'}
              </p>
              <p style={{ fontFamily: "'Exo 2', sans-serif", fontSize: '11px', color: '#607898', opacity: 0.6 }}>
                .log · .txt · .json · .jsonl
              </p>
            </>
          )}
        </div>

        {uploadError && (
          <div className="mb-6 p-3 rounded text-xs" style={{ background: 'rgba(255,60,60,0.08)', border: '1px solid rgba(255,60,60,0.3)', color: '#ff3c3c', fontFamily: "'Share Tech Mono', monospace" }}>
            UPLOAD ERROR: {uploadError}
          </div>
        )}

        {/* ── Error Logs panel ───────────────────────────────────────────── */}
        <div className="rounded-lg" style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.1)' }}>

          {/* Panel header */}
          <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: '1px solid rgba(0,212,255,0.08)' }}>
            <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '11px', letterSpacing: '4px', color: '#00d4ff' }}>
              // SESSION HISTORY
            </span>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="rounded text-xs transition-all"
              style={{
                background: 'rgba(0,255,136,0.07)',
                border: '1px solid rgba(0,255,136,0.35)',
                color: '#00ff88',
                fontFamily: "'Share Tech Mono', monospace",
                letterSpacing: '2px',
                padding: '6px 14px',
                cursor: 'pointer',
              }}
              onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(0,255,136,0.14)')}
              onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(0,255,136,0.07)')}
            >
              + UPLOAD LOG
            </button>
          </div>

          {/* Loading */}
          {loading && (
            <div className="flex justify-center py-20">
              <div className="w-8 h-8 rounded-full border-2 border-transparent animate-spin" style={{ borderTopColor: '#00d4ff' }} />
            </div>
          )}

          {/* Empty state */}
          {!loading && errorLogs.length === 0 && (
            <div className="text-center py-20">
              <div className="mb-4 text-4xl opacity-30">📋</div>
              <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '11px', letterSpacing: '3px', color: '#607898' }}>
                NO LOGS YET — DROP A FILE ABOVE TO START
              </p>
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
                      <span className="text-sm font-semibold truncate" style={{ color: '#dce8f8', maxWidth: '300px' }}>{log.filename}</span>
                      <span className="text-xs rounded px-2 py-0.5" style={{ background: 'rgba(255,60,60,0.1)', border: '1px solid rgba(255,60,60,0.25)', color: '#ff3c3c', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '1px' }}>
                        {log.error_count} errors
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', color: '#607898' }}>
                        {new Date(log.created_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}
                      </span>
                      <span className="text-xs rounded px-2 py-0.5" style={{ background: 'rgba(0,212,255,0.06)', border: '1px solid rgba(0,212,255,0.15)', color: '#00d4ff', fontFamily: "'Share Tech Mono', monospace", fontSize: '10px' }}>
                        {log.file_format.toUpperCase()}
                      </span>
                      {log.primary_error_type && (
                        <span className="text-xs rounded px-2 py-0.5" style={{ background: 'rgba(255,183,0,0.06)', border: '1px solid rgba(255,183,0,0.2)', color: '#ffb700', fontFamily: "'Share Tech Mono', monospace", fontSize: '10px' }}>
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
                      cursor: log.is_processed ? 'pointer' : 'not-allowed',
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
            <span key={i} style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', letterSpacing: '2px', color: c }}>{t}</span>
          ))}
        </div>

      </main>
    </div>
  );
}

