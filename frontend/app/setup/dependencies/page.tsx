'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import axios from 'axios';
import Navbar from '../../components/Navbar';
import SetupStepper from '../../components/SetupStepper';
import { api } from '../../lib/api';

interface Dependency {
  id: string;
  name: string;
  display_name: string;
  description: string;
  category: string;
  documentation_url: string;
  repository_url: string;
}

interface CustomDependency {
  name: string;
  description: string;
  repository_url?: string;
}

export default function DependenciesSetup() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [dependencies, setDependencies] = useState<Dependency[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [customDeps, setCustomDeps] = useState<CustomDependency[]>([]);
  const [customName, setCustomName] = useState('');
  const [customDesc, setCustomDesc] = useState('');
  const [customRepoUrl, setCustomRepoUrl] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchingDocs, setFetchingDocs] = useState(false);
  const [fetchStatus, setFetchStatus] = useState<Record<string, {
    status: string; chunks?: number; files?: number; message?: string; source?: string;
  }>>({});
  const [docsHealth, setDocsHealth] = useState<Record<string, {
    chunks: number; source_type: string; stale: boolean; sections: string[];
  }>>({}); 

  type FetchDepth = 'quick' | 'balanced' | 'full';
  const [fetchDepth, setFetchDepth] = useState<FetchDepth>('balanced');
  const [pipelinePhase, setPipelinePhase] = useState<'fetching' | 'embedding' | 'done' | 'error'>('fetching');
  const [pipelineError, setPipelineError] = useState<string | null>(null);
  const [rateLimit, setRateLimit] = useState<{
    remaining: number | null; limit: number | null; reset_in_min: number | null;
    authenticated: boolean; can_fetch: boolean; error?: string;
  } | null>(null);

  const DEPTH_FILES: Record<FetchDepth, { files: number; label: string }> = {
    quick:    { files: 15, label: 'QUICK · 15 files · ~16 req/dep' },
    balanced: { files: 40, label: 'BALANCED · 40 files · ~41 req/dep' },
    full:     { files: 80, label: 'FULL · 80 files · ~81 req/dep' },
  };

  const normalizeUrl = (url: string) => {
    if (!url) return '';
    if (url.startsWith('http://') || url.startsWith('https://')) return url;
    return `https://${url}`;
  };

  const openDocs = (e: React.MouseEvent, url: string) => {
    e.preventDefault();
    e.stopPropagation();
    const safeUrl = normalizeUrl(url);
    if (!safeUrl) return;
    window.open(safeUrl, '_blank', 'noopener,noreferrer');
  };

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin');
      return;
    }

    if (status === 'authenticated') {
      fetchDependencies();
    }
  }, [status, router]);

  const fetchDependencies = async () => {
    try {
      const [depsResp, healthResp, rlResp] = await Promise.all([
        axios.get(api('/api/v1/setup/dependencies')),
        axios.get(api('/api/v1/setup/docs-health')).catch(() => ({ data: { deps: {} } })),
        axios.get(api('/api/v1/setup/github-rate-limit')).catch(() => ({ data: null })),
      ]);
      setDependencies(depsResp.data);
      setDocsHealth(healthResp.data.deps || {});
      setRateLimit(rlResp.data);
      setLoading(false);
    } catch (err) {
      setError('Failed to load dependencies');
      setLoading(false);
      console.error(err);
    }
  };

  const toggleDependency = (name: string) => {
    setSelected((prev) =>
      prev.includes(name)
        ? prev.filter((d) => d !== name)
        : [...prev, name]
    );
  };

  const addCustomDependency = () => {
    if (!customName.trim()) {
      setError('Please enter a dependency name');
      return;
    }

    if (customDeps.some((d) => d.name.toLowerCase() === customName.toLowerCase())) {
      setError('This custom dependency already exists');
      return;
    }

    if (dependencies.some((d) => d.name.toLowerCase() === customName.toLowerCase())) {
      setError('This dependency already exists in the preset list');
      return;
    }

    const newDep: CustomDependency = {
      name: customName,
      description: customDesc || 'Custom dependency',
      ...(customRepoUrl.trim() ? { repository_url: customRepoUrl.trim() } : {}),
    };
    setCustomDeps([...customDeps, newDep]);
    setSelected([...selected, customName]);
    setCustomName('');
    setCustomDesc('');
    setCustomRepoUrl('');
    setError(null);
  };

  const removeCustomDependency = (name: string) => {
    setCustomDeps((prev) => prev.filter((d) => d.name !== name));
    setSelected((prev) => prev.filter((d) => d !== name));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (selected.length === 0) {
      setError('Please select at least one dependency');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await axios.post(
        api('/api/v1/setup/select'),
        {
          dependency_names: selected,
          custom_dependencies: customDeps,
          fetch_depth: fetchDepth,
        },
        {
          headers: {
            Authorization: `Bearer ${session?.accessToken}`,
          },
        }
      );

      // Switch to doc-fetch progress view
      const initialStatus: typeof fetchStatus = {};
      [...selected, ...customDeps.map((d) => d.name)].forEach((n) => {
        initialStatus[n] = { status: 'pending' };
      });
      setFetchStatus(initialStatus);
      setFetchingDocs(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to select dependencies');
      setSubmitting(false);
    }
  };

  // Poll the full pipeline (fetch → embed) while in progress
  useEffect(() => {
    if (!fetchingDocs) return;
    const interval = setInterval(async () => {
      try {
        const resp = await axios.get(api('/api/v1/setup/fetch-docs/status'));
        setFetchStatus(resp.data.deps || {});
        setPipelinePhase(resp.data.pipeline_phase || 'fetching');
        if (resp.data.pipeline_error) setPipelineError(resp.data.pipeline_error);
        if (resp.data.pipeline_complete) {
          clearInterval(interval);
        }
      } catch {
        // non-fatal — keep polling
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [fetchingDocs]);

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen depfix-grid-bg flex items-center justify-center" style={{ background: '#060810' }}>
        <div className="text-center">
          <div className="w-10 h-10 rounded-full border-2 border-transparent animate-spin mx-auto mb-5" style={{ borderTopColor: '#00d4ff' }} />
          <p style={{ fontFamily: "'Share Tech Mono', monospace", color: '#607898', fontSize: '11px', letterSpacing: '4px' }}>LOADING...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen depfix-grid-bg" style={{ background: '#060810', color: '#dce8f8' }}>
      <Navbar />
      <SetupStepper currentStep={1} />
      <div className="max-w-5xl mx-auto px-4 py-10">

        {/* Header */}
        <div className="mb-8">
          <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '4px', color: '#607898' }}>SETUP / PHASE 1</p>
          <h1 style={{ fontFamily: "'Orbitron', monospace", fontWeight: 700, fontSize: '1.6rem', color: '#dce8f8', marginTop: '6px' }}>
            Select Dependencies
          </h1>
          <p style={{ fontFamily: "'Exo 2', sans-serif", fontSize: '14px', color: '#8cb4d4', marginTop: '6px', fontWeight: 300 }}>
            Choose packages to embed. We'll download their documentation to help resolve CI/CD errors.
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-3 rounded text-xs" style={{ background: 'rgba(255,60,60,0.08)', border: '1px solid rgba(255,60,60,0.3)', color: '#ff3c3c', fontFamily: "'Share Tech Mono', monospace" }}>
            {error}
          </div>
        )}

        {/* ---- Pipeline progress view (fetch → embed → done) ---- */}
        {fetchingDocs ? (
          <div className="space-y-4">

            {/* Stage 1: Fetch */}
            <div className="p-4 rounded-lg" style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.18)' }}>
              <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '4px', color: '#00d4ff', marginBottom: '16px' }}>
                // STAGE 1 · FETCHING DOCUMENTATION
              </p>
              <div className="space-y-3">
                {Object.entries(fetchStatus).map(([name, info]) => {
                  const statusColor =
                    info.status === 'done' ? '#00ff88' :
                    info.status === 'fetching' ? '#00d4ff' :
                    info.status === 'warning' ? '#ffb700' :
                    info.status === 'error' ? '#ff3c3c' : '#607898';
                  const icon =
                    info.status === 'done' ? '✓' :
                    info.status === 'fetching' ? '◌' :
                    info.status === 'warning' ? '⚠' :
                    info.status === 'error' ? '✗' : '○';
                  const label =
                    info.status === 'done'
                      ? `${info.chunks ?? 0} chunks from ${info.files ?? 0} files${info.source === 'local' ? ' (local cache)' : ''}`
                      : info.status === 'fetching' ? 'fetching...'
                      : info.status === 'warning' ? (info.message ?? 'no docs found')
                      : info.status === 'error' ? (info.message ?? 'error')
                      : 'queued';
                  return (
                    <div key={name} className="flex items-center gap-3 rounded px-3 py-2" style={{ background: 'rgba(255,255,255,0.02)', border: `1px solid ${statusColor}22` }}>
                      <span style={{ color: statusColor, fontFamily: "'Share Tech Mono', monospace", fontSize: '14px', minWidth: '16px' }}>
                        {info.status === 'fetching' ? <span className="inline-block animate-spin">◌</span> : icon}
                      </span>
                      <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '12px', color: '#dce8f8', minWidth: '140px' }}>{name}</span>
                      <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', color: statusColor }}>{label}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Stage 2: Embedding (visible once fetch is done) */}
            {(pipelinePhase === 'embedding' || pipelinePhase === 'done' || pipelinePhase === 'error') && (
              <div className="p-4 rounded-lg" style={{
                background: '#0b0f1e',
                border: `1px solid ${pipelinePhase === 'done' ? 'rgba(0,255,136,0.25)' : pipelinePhase === 'error' ? 'rgba(255,60,60,0.25)' : 'rgba(0,212,255,0.18)'}`,
              }}>
                <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '4px', color: pipelinePhase === 'done' ? '#00ff88' : pipelinePhase === 'error' ? '#ff3c3c' : '#00d4ff', marginBottom: '16px' }}>
                  // STAGE 2 · EMBEDDING &amp; VECTOR INDEXING
                </p>
                {pipelinePhase === 'embedding' && (
                  <div className="flex items-center gap-3">
                    <span className="inline-block animate-spin" style={{ color: '#00d4ff', fontSize: '14px' }}>◌</span>
                    <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '12px', color: '#8cb4d4' }}>
                      Generating embeddings and indexing into vector database...
                    </span>
                  </div>
                )}
                {pipelinePhase === 'done' && (
                  <div className="flex items-center gap-3">
                    <span style={{ color: '#00ff88', fontSize: '14px' }}>✓</span>
                    <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '12px', color: '#00ff88' }}>
                      Indexed and ready for RAG analysis
                    </span>
                  </div>
                )}
                {pipelinePhase === 'error' && (
                  <div>
                    <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '11px', color: '#ff3c3c' }}>
                      ⚠ {pipelineError || 'Embedding failed — docs were fetched but could not be indexed.'}
                    </p>
                    <button
                      onClick={() => router.push('/setup/embedding')}
                      className="mt-3 text-xs"
                      style={{ color: '#ffb700', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '1px' }}
                    >
                      Retry embedding →
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Done: go to dashboard */}
            {pipelinePhase === 'done' && (
              <div className="flex justify-end">
                <button
                  onClick={() => router.push('/dashboard')}
                  className="rounded text-xs transition-all"
                  style={{ background: 'rgba(0,255,136,0.08)', border: '1px solid rgba(0,255,136,0.4)', color: '#00ff88', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '2px', padding: '9px 24px' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,255,136,0.16)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'rgba(0,255,136,0.08)')}
                >
                  GO TO DASHBOARD →
                </button>
              </div>
            )}

          </div>
        ) : (
        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">

            {/* Dep list */}
            <div className="lg:col-span-2">
              <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#00d4ff', marginBottom: '12px' }}>// AVAILABLE PACKAGES</p>
              <div className="space-y-4 max-h-[600px] overflow-y-auto pr-1" style={{ scrollbarWidth: 'thin', scrollbarColor: '#607898 transparent' }}>
                {Object.entries(
                  dependencies.reduce((acc: { [key: string]: Dependency[] }, dep) => {
                    if (!acc[dep.category]) acc[dep.category] = [];
                    acc[dep.category].push(dep);
                    return acc;
                  }, {})
                ).map(([category, deps]) => (
                  <div key={category} className="mb-4">
                    <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', letterSpacing: '3px', color: '#607898', marginBottom: '8px', textTransform: 'uppercase' }}>
                      {category}
                    </p>
                    <div className="space-y-2">
                      {deps.map((dep) => (
                        <label
                          key={dep.id}
                          className="flex items-start gap-3 p-3 rounded cursor-pointer transition-all"
                          style={{
                            background: selected.includes(dep.name) ? 'rgba(0,212,255,0.07)' : 'rgba(255,255,255,0.02)',
                            border: selected.includes(dep.name) ? '1px solid rgba(0,212,255,0.35)' : '1px solid rgba(255,255,255,0.06)',
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={selected.includes(dep.name)}
                            onChange={() => toggleDependency(dep.name)}
                            className="mt-1 flex-shrink-0"
                            style={{ accentColor: '#00d4ff' }}
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <p className="text-sm font-semibold" style={{ color: '#dce8f8' }}>{dep.display_name}</p>
                              <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', color: '#607898' }}>({dep.name})</span>
                              {docsHealth[dep.name] && (
                                docsHealth[dep.name].stale ? (
                                  <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', color: '#ffb700', background: 'rgba(255,183,0,0.08)', border: '1px solid rgba(255,183,0,0.25)', borderRadius: '3px', padding: '1px 6px', letterSpacing: '0.5px' }}>
                                    ⚠ STALE — re-fetch
                                  </span>
                                ) : (
                                  <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', color: '#00ff88', background: 'rgba(0,255,136,0.05)', border: '1px solid rgba(0,255,136,0.2)', borderRadius: '3px', padding: '1px 6px' }}>
                                    {docsHealth[dep.name].chunks} chunks
                                  </span>
                                )
                              )}
                            </div>
                            <p className="text-xs mt-1" style={{ color: '#8cb4d4' }}>{dep.description}</p>
                            {dep.documentation_url && (
                              <a
                                href={normalizeUrl(dep.documentation_url)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs mt-1 inline-block"
                                style={{ color: '#00d4ff' }}
                                onClick={(e) => openDocs(e, dep.documentation_url)}
                              >
                                docs →
                              </a>
                            )}
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right: custom + selected */}
            <div className="space-y-4">
              {/* Custom dep card */}
              <div className="rounded-lg p-4" style={{ background: '#0b0f1e', border: '1px solid rgba(167,139,250,0.2)' }}>
                <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#a78bfa', marginBottom: '12px' }}>+ CUSTOM PACKAGE</p>
                <div className="space-y-2">
                  <input
                    type="text"
                    placeholder="Package name"
                    value={customName}
                    onChange={(e) => setCustomName(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && addCustomDependency()}
                    className="w-full rounded text-sm"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(167,139,250,0.25)', color: '#dce8f8', fontFamily: "'Share Tech Mono', monospace", fontSize: '12px', padding: '8px 10px', outline: 'none' }}
                  />
                  <input
                    type="text"
                    placeholder="Description (optional)"
                    value={customDesc}
                    onChange={(e) => setCustomDesc(e.target.value)}
                    className="w-full rounded text-sm"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(167,139,250,0.25)', color: '#dce8f8', fontFamily: "'Share Tech Mono', monospace", fontSize: '12px', padding: '8px 10px', outline: 'none' }}
                  />
                  <input
                    type="text"
                    placeholder="GitHub URL (optional)"
                    value={customRepoUrl}
                    onChange={(e) => setCustomRepoUrl(e.target.value)}
                    className="w-full rounded text-sm"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(167,139,250,0.25)', color: '#dce8f8', fontFamily: "'Share Tech Mono', monospace", fontSize: '12px', padding: '8px 10px', outline: 'none' }}
                  />
                  <button
                    type="button"
                    onClick={addCustomDependency}
                    className="w-full rounded text-xs transition-all"
                    style={{ background: 'rgba(167,139,250,0.08)', border: '1px solid rgba(167,139,250,0.35)', color: '#a78bfa', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '2px', padding: '8px' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'rgba(167,139,250,0.16)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'rgba(167,139,250,0.08)')}
                  >
                    ADD
                  </button>
                </div>
              </div>

              {/* Selected summary */}
              <div className="rounded-lg p-4 sticky top-4" style={{ background: '#0b0f1e', border: '1px solid rgba(0,255,136,0.18)' }}>
                <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#00ff88', marginBottom: '12px' }}>
                  SELECTED — {selected.length}
                </p>
                <div className="max-h-[380px] overflow-y-auto space-y-2">
                  {selected.length === 0 ? (
                    <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', color: '#1a2840' }}>none selected</p>
                  ) : (
                    <>
                      {dependencies.filter((d) => selected.includes(d.name)).map((dep) => (
                        <div key={dep.id} className="flex items-center justify-between rounded px-2 py-1.5" style={{ background: 'rgba(0,255,136,0.05)', border: '1px solid rgba(0,255,136,0.15)' }}>
                          <span className="text-xs font-medium" style={{ color: '#dce8f8' }}>{dep.display_name}</span>
                          <button type="button" onClick={() => toggleDependency(dep.name)} style={{ color: '#ff3c3c', fontSize: '11px' }}>✕</button>
                        </div>
                      ))}
                      {customDeps.map((dep) => (
                        <div key={dep.name} className="flex items-center justify-between rounded px-2 py-1.5" style={{ background: 'rgba(167,139,250,0.06)', border: '1px solid rgba(167,139,250,0.2)' }}>
                          <span className="text-xs font-medium" style={{ color: '#dce8f8' }}>{dep.name} <span style={{ color: '#607898' }}>(custom)</span></span>
                          <button type="button" onClick={() => removeCustomDependency(dep.name)} style={{ color: '#ff3c3c', fontSize: '11px' }}>✕</button>
                        </div>
                      ))}
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* ---- Rate limit + depth picker ---- */}
          {(() => {
            const totalDeps = selected.length + customDeps.length;
            const estRequests = totalDeps * (1 + DEPTH_FILES[fetchDepth].files);
            const remaining = rateLimit?.remaining ?? null;
            const overBudget = remaining !== null && totalDeps > 0 && estRequests > remaining;
            const rlColor = remaining === null ? '#607898' : remaining > 200 ? '#00ff88' : remaining > 30 ? '#ffb700' : '#ff3c3c';
            return (
              <div className="space-y-3 mb-6">

                {/* Rate limit bar */}
                <div className="rounded-lg px-4 py-3 flex items-center justify-between gap-4" style={{ background: '#0b0f1e', border: `1px solid ${rlColor}33` }}>
                  <div className="flex items-center gap-3">
                    <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', letterSpacing: '3px', color: '#607898' }}>GITHUB RATE LIMIT</span>
                    {rateLimit?.authenticated ? (
                      <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', color: '#00d4ff', background: 'rgba(0,212,255,0.08)', border: '1px solid rgba(0,212,255,0.2)', borderRadius: '3px', padding: '1px 6px' }}>TOKEN</span>
                    ) : (
                      <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', color: '#607898', background: 'rgba(96,120,152,0.1)', border: '1px solid rgba(96,120,152,0.2)', borderRadius: '3px', padding: '1px 6px' }}>ANON</span>
                    )}
                  </div>
                  {rateLimit?.error ? (
                    <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', color: '#607898' }}>unavailable</span>
                  ) : remaining !== null ? (
                    <div className="flex items-center gap-3">
                      <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '12px', color: rlColor, fontWeight: 700 }}>
                        {remaining.toLocaleString()} / {(rateLimit?.limit ?? 60).toLocaleString()} remaining
                      </span>
                      {(rateLimit?.reset_in_min ?? 0) > 0 && (
                        <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', color: '#607898' }}>resets in {rateLimit?.reset_in_min}m</span>
                      )}
                    </div>
                  ) : (
                    <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', color: '#607898' }}>loading...</span>
                  )}
                </div>

                {/* Depth picker */}
                <div className="rounded-lg px-4 py-3" style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.12)' }}>
                  <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', letterSpacing: '3px', color: '#607898', marginBottom: '10px' }}>FETCH DEPTH</p>
                  <div className="flex gap-2 flex-wrap">
                    {(['quick', 'balanced', 'full'] as FetchDepth[]).map((d) => (
                      <button
                        key={d}
                        type="button"
                        onClick={() => setFetchDepth(d)}
                        className="rounded text-xs transition-all"
                        style={{
                          fontFamily: "'Share Tech Mono', monospace", letterSpacing: '1.5px', padding: '7px 14px', fontSize: '10px',
                          background: fetchDepth === d ? 'rgba(0,212,255,0.12)' : 'rgba(255,255,255,0.02)',
                          border: fetchDepth === d ? '1px solid rgba(0,212,255,0.5)' : '1px solid rgba(255,255,255,0.08)',
                          color: fetchDepth === d ? '#00d4ff' : '#607898',
                        }}
                      >
                        {DEPTH_FILES[d].label}
                      </button>
                    ))}
                  </div>
                  {totalDeps > 0 && (
                    <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', color: overBudget ? '#ff3c3c' : '#8cb4d4', marginTop: '8px' }}>
                      {totalDeps} dep{totalDeps !== 1 ? 's' : ''} × ~{(1 + DEPTH_FILES[fetchDepth].files)} req = ~{estRequests} requests
                      {overBudget && ` — exceeds remaining budget!`}
                    </p>
                  )}
                </div>

                {/* Over-budget warning */}
                {overBudget && (
                  <div className="rounded px-4 py-3" style={{ background: 'rgba(255,60,60,0.06)', border: '1px solid rgba(255,60,60,0.3)' }}>
                    <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', color: '#ff3c3c' }}>
                      ⚠ ~{estRequests} requests needed but only {remaining} remaining. Switch to QUICK depth or add a GitHub token in Config to get 5 000 req/hr.
                    </p>
                  </div>
                )}

              </div>
            );
          })()}

          {/* Navigation */}
          <div className="flex gap-4 justify-between pt-6" style={{ borderTop: '1px solid rgba(0,212,255,0.08)' }}>
            <button
              type="button"
              onClick={() => router.push('/dashboard')}
              className="rounded text-xs transition-all"
              style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.1)', color: '#607898', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '2px', padding: '9px 20px' }}
            >
              SKIP FOR NOW
            </button>
            <button
              type="submit"
              disabled={submitting || selected.length === 0}
              className="rounded text-xs transition-all disabled:opacity-30 disabled:cursor-not-allowed"
              style={{ background: 'rgba(0,255,136,0.08)', border: '1px solid rgba(0,255,136,0.4)', color: '#00ff88', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '2px', padding: '9px 24px' }}
              onMouseEnter={e => { if (!submitting && selected.length > 0) (e.currentTarget as HTMLElement).style.background = 'rgba(0,255,136,0.16)'; }}
              onMouseLeave={e => { if (!submitting && selected.length > 0) (e.currentTarget as HTMLElement).style.background = 'rgba(0,255,136,0.08)'; }}
            >
              {submitting ? 'STARTING...' : 'FETCH & INDEX DOCUMENTATION →'}
            </button>
          </div>

          {/* Info */}
          <div className="mt-6 p-4 rounded" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(0,212,255,0.06)' }}>
            <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', letterSpacing: '3px', color: '#607898', marginBottom: '8px' }}>WHAT HAPPENS NEXT</p>
            <div className="space-y-1">
              {['Download docs for selected packages', 'Process into AI embeddings', 'Index in vector database', 'Ready for RAG queries on your error logs'].map((s, i) => (
                <p key={i} className="text-xs" style={{ color: '#8cb4d4' }}>✓ {s}</p>
              ))}
            </div>
          </div>
        </form>
        )}
      </div>
    </div>
  );
}
