'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import axios from 'axios';
import Navbar from '../components/Navbar';
import { api } from '../lib/api';

type AgentRunListItem = {
  run_id: string;
  status: string;
  intent?: string;
  query_text?: string;
  started_at?: string;
  ended_at?: string;
  metrics?: Record<string, unknown>;
};

export default function RunsPage() {
  const [runs, setRuns] = useState<AgentRunListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const resp = await axios.get(api('/api/v1/agent-runs?limit=50'));
        setRuns(resp.data?.runs || []);
      } catch (e: any) {
        setError(e?.response?.data?.detail || 'Failed to load run list');
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const statusColor = (status: string) => {
    if (status === 'completed') return '#00ff88';
    if (status === 'failed') return '#ff3c3c';
    if (status === 'running') return '#00d4ff';
    return '#ffb700';
  };

  return (
    <div className="min-h-screen depfix-grid-bg" style={{ background: '#060810', color: '#dce8f8' }}>
      <Navbar />
      <div className="max-w-6xl mx-auto px-4 py-8">
        <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '4px', color: '#607898' }}>
          RUNTIME / INSPECTOR
        </p>
        <h1 style={{ fontFamily: "'Orbitron', monospace", fontSize: '1.6rem', marginTop: '6px' }}>
          Agent Runs
        </h1>

        {loading && <p className="mt-6 text-sm" style={{ color: '#8cb4d4' }}>Loading runs...</p>}
        {error && (
          <div className="mt-6 p-3 rounded" style={{ border: '1px solid rgba(255,60,60,0.3)', color: '#ff7f7f', background: 'rgba(255,60,60,0.08)' }}>
            {error}
          </div>
        )}

        {!loading && !error && (
          <div className="mt-6 space-y-3">
            {runs.length === 0 ? (
              <p className="text-sm" style={{ color: '#8cb4d4' }}>No runs yet.</p>
            ) : runs.map((run) => (
              <Link
                key={run.run_id}
                href={`/runs/${run.run_id}`}
                className="block rounded-lg p-4 transition-all"
                style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.15)' }}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '11px', color: '#607898' }}>{run.run_id}</p>
                    <p className="mt-1 text-sm" style={{ color: '#dce8f8' }}>{run.query_text || run.intent || 'Run'}</p>
                    <p className="mt-1 text-xs" style={{ color: '#8cb4d4' }}>
                      started: {run.started_at || '-'}
                    </p>
                  </div>
                  <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '1.5px', color: statusColor(run.status), border: `1px solid ${statusColor(run.status)}66`, padding: '4px 8px', borderRadius: '3px' }}>
                    {run.status.toUpperCase()}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
