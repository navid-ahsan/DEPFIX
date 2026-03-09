'use client';

import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { useEffect, useState } from 'react';
import axios from 'axios';
import Navbar from '../../components/Navbar';

interface EmbeddingStatus {
  status: string;
  dependencies: string[];
  progress_percent: number;
}

export default function EmbeddingSetup() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [embeddingStatus, setEmbeddingStatus] = useState<EmbeddingStatus | null>(null);
  const [selectedDeps, setSelectedDeps] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [startingEmbedding, setStartingEmbedding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin');
    }

    if (status === 'authenticated') {
      initializePage();
    }
  }, [status, router]);

  useEffect(() => {
    if (embeddingStatus?.status === 'in_progress') {
      const interval = setInterval(pollStatus, 2000);
      return () => clearInterval(interval);
    }
  }, [embeddingStatus]);

  const initializePage = async () => {
    try {
      const statusResponse = await axios.get('http://localhost:8000/api/v1/setup/status', {
        headers: {
          Authorization: `Bearer ${session?.accessToken}`,
        },
      });

      if (statusResponse.data.selected_dependencies) {
        setSelectedDeps(statusResponse.data.selected_dependencies);
      }

      await pollStatus();
      setLoading(false);
    } catch (err) {
      console.error('Failed to initialize embedding page:', err);
      setLoading(false);
    }
  };

  const pollStatus = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/v1/embedding/status', {
        headers: {
          Authorization: `Bearer ${session?.accessToken}`,
        },
      });
      setEmbeddingStatus(response.data);
    } catch (err) {
      console.error('Failed to poll status:', err);
    }
  };

  const startEmbedding = async () => {
    if (!selectedDeps.length) {
      setError('No dependencies selected');
      return;
    }

    setStartingEmbedding(true);
    try {
      await axios.post(
        'http://localhost:8000/api/v1/embedding/start',
        { dependency_names: selectedDeps },
        {
          headers: {
            Authorization: `Bearer ${session?.accessToken}`,
          },
        }
      );

      // Start polling
      await pollStatus();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start embedding');
      setStartingEmbedding(false);
    }
  };

  const handleComplete = async () => {
    try {
      await axios.post('http://localhost:8000/api/v1/embedding/complete-phase2', {}, {
        headers: {
          Authorization: `Bearer ${session?.accessToken}`,
        },
      });
      router.push('/setup/github-connection');
    } catch (err) {
      console.error('Failed to complete Phase 2:', err);
    }
  };

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

  const isEmbeddingStarted = embeddingStatus?.status === 'in_progress' || embeddingStatus?.status === 'completed';
  const isComplete = embeddingStatus?.status === 'completed';

  return (
    <div className="min-h-screen depfix-grid-bg" style={{ background: '#060810', color: '#dce8f8' }}>
      <Navbar />
      <div className="max-w-4xl mx-auto px-4 py-10">

        {/* Header */}
        <div className="mb-8">
          <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '4px', color: '#607898' }}>SETUP / PHASE 2</p>
          <h1 style={{ fontFamily: "'Orbitron', monospace", fontWeight: 700, fontSize: '1.6rem', color: '#dce8f8', marginTop: '6px' }}>
            Embedding &amp; Vector DB
          </h1>
          <p style={{ fontFamily: "'Exo 2', sans-serif", fontSize: '14px', color: '#8cb4d4', marginTop: '6px', fontWeight: 300 }}>
            Converting documentation into AI embeddings for semantic search.
          </p>
        </div>

        {error && (
          <div className="mb-6 p-3 rounded text-xs" style={{ background: 'rgba(255,60,60,0.08)', border: '1px solid rgba(255,60,60,0.3)', color: '#ff3c3c', fontFamily: "'Share Tech Mono', monospace" }}>
            {error}
          </div>
        )}

        {/* Selected deps */}
        <div className="mb-6 p-4 rounded-lg" style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.1)' }}>
          <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#00d4ff', marginBottom: '8px' }}>SELECTED PACKAGES</p>
          <p className="text-sm" style={{ color: '#dce8f8' }}>{selectedDeps.join(', ')}</p>
        </div>

        {!isEmbeddingStarted ? (
          <div className="rounded-lg p-6" style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.1)' }}>
            <p className="text-sm mb-5" style={{ color: '#8cb4d4' }}>Click below to start embedding. This will:</p>
            <div className="space-y-2 mb-8">
              {['Split documentation into chunks', 'Generate embeddings using Ollama AI', 'Index vectors in the database', 'Prepare for semantic search queries'].map((s, i) => (
                <p key={i} className="text-xs" style={{ color: '#8cb4d4' }}>
                  <span style={{ color: '#00d4ff', marginRight: '8px' }}>{'>'}</span>{s}
                </p>
              ))}
            </div>
            <button
              onClick={startEmbedding}
              disabled={startingEmbedding}
              className="w-full rounded text-xs transition-all disabled:opacity-40"
              style={{ background: 'rgba(0,212,255,0.08)', border: '1px solid rgba(0,212,255,0.4)', color: '#00d4ff', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '3px', padding: '13px' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,212,255,0.16)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'rgba(0,212,255,0.08)')}
            >
              {startingEmbedding ? 'STARTING...' : 'START EMBEDDING PROCESS'}
            </button>
          </div>
        ) : (
          <div>
            {/* Progress Bar */}
            <div className="mb-6 p-5 rounded-lg" style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.1)' }}>
              <div className="flex justify-between items-center mb-3">
                <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#607898' }}>EMBEDDING PROGRESS</p>
                <p style={{ fontFamily: "'Orbitron', monospace", fontSize: '14px', fontWeight: 700, color: isComplete ? '#00ff88' : '#00d4ff' }}>
                  {embeddingStatus?.progress_percent || 0}%
                </p>
              </div>
              <div className="w-full rounded-full h-2" style={{ background: 'rgba(255,255,255,0.05)' }}>
                <div
                  className="h-2 rounded-full transition-all duration-500"
                  style={{
                    width: `${embeddingStatus?.progress_percent || 0}%`,
                    background: isComplete ? '#00ff88' : '#00d4ff',
                    boxShadow: `0 0 8px ${isComplete ? 'rgba(0,255,136,0.5)' : 'rgba(0,212,255,0.5)'}`,
                  }}
                />
              </div>
            </div>

            {/* Status */}
            <div className="mb-6 p-5 rounded-lg text-center" style={{ background: '#0b0f1e', border: `1px solid ${isComplete ? 'rgba(0,255,136,0.2)' : 'rgba(0,212,255,0.1)'}` }}>
              {isComplete ? (
                <>
                  <p className="font-semibold mb-1" style={{ color: '#00ff88' }}>✓ Embedding Complete!</p>
                  <p className="text-xs" style={{ color: '#8cb4d4' }}>{selectedDeps.length} package(s) embedded and indexed</p>
                </>
              ) : (
                <>
                  <div className="w-7 h-7 rounded-full border-2 border-transparent animate-spin mx-auto mb-3" style={{ borderTopColor: '#00d4ff' }} />
                  <p className="text-sm font-semibold" style={{ color: '#dce8f8' }}>Embedding in progress...</p>
                  <p className="text-xs mt-1" style={{ color: '#607898' }}>This may take a few minutes</p>
                </>
              )}
            </div>

            {/* Details */}
            <div className="p-4 rounded-lg mb-6" style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.07)' }}>
              <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#607898', marginBottom: '8px' }}>
                STATUS: <span style={{ color: '#00d4ff' }}>{embeddingStatus?.status?.toUpperCase()}</span>
              </p>
              {embeddingStatus?.dependencies?.map((dep: string) => (
                <p key={dep} className="text-xs" style={{ color: '#8cb4d4' }}>• {dep}</p>
              ))}
            </div>

            {/* Navigation */}
            <div className="flex gap-4 pt-4" style={{ borderTop: '1px solid rgba(0,212,255,0.08)' }}>
              {isComplete && (
                <button
                  onClick={handleComplete}
                  className="flex-1 rounded text-xs transition-all"
                  style={{ background: 'rgba(0,255,136,0.08)', border: '1px solid rgba(0,255,136,0.4)', color: '#00ff88', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '2px', padding: '12px' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,255,136,0.16)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'rgba(0,255,136,0.08)')}
                >
                  CONTINUE TO PHASE 3 →
                </button>
              )}
              <button
                onClick={() => router.push('/dashboard')}
                className="rounded text-xs transition-all"
                style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.1)', color: '#607898', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '2px', padding: '12px 20px' }}
              >
                SKIP TO DASHBOARD
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

