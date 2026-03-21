'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import Navbar from '../../components/Navbar';
import { api } from '../../lib/api';

type RunStep = {
  step_order: number;
  agent_name: string;
  status: string;
  latency_ms?: number;
  retry_count?: number;
  error_text?: string;
  output_summary?: Record<string, unknown>;
};

type RunData = {
  run: {
    run_id: string;
    status: string;
    query_text?: string;
    started_at?: string;
    ended_at?: string;
    metrics?: Record<string, unknown>;
  };
  steps: RunStep[];
};

export default function RunDetailPage({ params }: { params: { id: string } }) {
  const [data, setData] = useState<RunData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const resp = await axios.get(api(`/api/v1/agent-runs/${params.id}`));
        setData(resp.data);
      } catch (e: any) {
        setError(e?.response?.data?.detail || 'Failed to load run details');
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [params.id]);

  const summary = useMemo(() => {
    if (!data) return { retries: 0, fallbacks: 0, totalMs: 0 };
    const retries = data.steps.reduce((n, s) => n + (s.retry_count || 0), 0);
    const fallbacks = data.steps.filter((s) => s.status === 'fallback').length;
    const totalMs = data.steps.reduce((n, s) => n + (s.latency_ms || 0), 0);
    return { retries, fallbacks, totalMs: Math.round(totalMs) };
  }, [data]);

  const statusColor = (status: string) => {
    if (status === 'completed') return '#00ff88';
    if (status === 'failed') return '#ff3c3c';
    if (status === 'fallback') return '#ffb700';
    if (status === 'running') return '#00d4ff';
    return '#607898';
  };

  return (
    <div className="min-h-screen depfix-grid-bg" style={{ background: '#060810', color: '#dce8f8' }}>
      <Navbar />
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between">
          <div>
            <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '4px', color: '#607898' }}>
              RUNTIME / INSPECTOR
            </p>
            <h1 style={{ fontFamily: "'Orbitron', monospace", fontSize: '1.4rem', marginTop: '6px' }}>
              Run Detail
            </h1>
          </div>
          <Link href="/runs" className="text-xs" style={{ color: '#00d4ff' }}>← back to runs</Link>
        </div>

        {loading && <p className="mt-6 text-sm" style={{ color: '#8cb4d4' }}>Loading run...</p>}
        {error && (
          <div className="mt-6 p-3 rounded" style={{ border: '1px solid rgba(255,60,60,0.3)', color: '#ff7f7f', background: 'rgba(255,60,60,0.08)' }}>
            {error}
          </div>
        )}

        {data && (
          <>
            <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-3">
              <div className="rounded p-3" style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.12)' }}>
                <p className="text-xs" style={{ color: '#607898' }}>STATUS</p>
                <p className="text-sm mt-1" style={{ color: statusColor(data.run.status) }}>{data.run.status}</p>
              </div>
              <div className="rounded p-3" style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.12)' }}>
                <p className="text-xs" style={{ color: '#607898' }}>RETRIES</p>
                <p className="text-sm mt-1">{summary.retries}</p>
              </div>
              <div className="rounded p-3" style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.12)' }}>
                <p className="text-xs" style={{ color: '#607898' }}>FALLBACKS</p>
                <p className="text-sm mt-1">{summary.fallbacks}</p>
              </div>
              <div className="rounded p-3" style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.12)' }}>
                <p className="text-xs" style={{ color: '#607898' }}>TOTAL LATENCY</p>
                <p className="text-sm mt-1">{summary.totalMs} ms</p>
              </div>
            </div>

            <div className="mt-6 space-y-3">
              {data.steps.map((step) => (
                <div key={`${step.step_order}-${step.agent_name}`} className="rounded p-4" style={{ background: '#0b0f1e', border: `1px solid ${statusColor(step.status)}40` }}>
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm" style={{ color: '#dce8f8' }}>
                      {step.step_order}. {step.agent_name}
                    </p>
                    <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', color: statusColor(step.status) }}>
                      {step.status.toUpperCase()}
                    </span>
                  </div>
                  <p className="mt-1 text-xs" style={{ color: '#8cb4d4' }}>
                    latency: {Math.round(step.latency_ms || 0)} ms · retries: {step.retry_count || 0}
                  </p>
                  {step.error_text && (
                    <pre className="mt-2 p-2 rounded overflow-auto max-h-28" style={{ background: 'rgba(255,60,60,0.08)', color: '#ff9c9c', fontSize: '11px' }}>
{step.error_text}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
