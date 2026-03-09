'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import axios from 'axios';
import Navbar from '../../components/Navbar';

interface DependencyProgress {
  name: string;
  status: 'loading' | 'completed' | 'failed';
  chunks_loaded: number;
  total_chunks?: number;
}

export default function SetupProgress() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [setupStatus, setSetupStatus] = useState<any>(null);
  const [depProgress, setDepProgress] = useState<DependencyProgress[]>([]);
  const [loading, setLoading] = useState(true);
  const [docsLoaded, setDocsLoaded] = useState<Record<string, any>>({});
  const [allComplete, setAllComplete] = useState(false);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin');
      return;
    }

    if (status === 'authenticated') {
      fetchSetupStatus();
      const interval = setInterval(fetchSetupStatus, 2000); // Poll every 2 seconds
      return () => clearInterval(interval);
    }
  }, [status, router]);

  const fetchSetupStatus = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/v1/setup/status', {
        headers: {
          Authorization: `Bearer ${session?.accessToken}`,
        },
      });

      setSetupStatus(response.data);

      // Load docs for each selected dependency
      if (response.data.selected_dependencies) {
        loadDependencyDocs(response.data.selected_dependencies);
      }

      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch setup status:', err);
      setLoading(false);
    }
  };

  const loadDependencyDocs = async (depNames: string[]) => {
    const newProgress: DependencyProgress[] = [];
    const newDocsLoaded: Record<string, any> = {};

    for (const depName of depNames) {
      try {
        // Add to progress
        newProgress.push({
          name: depName,
          status: 'loading',
          chunks_loaded: 0,
        });

        // Fetch doc data
        const response = await axios.get(
          `http://localhost:8000/api/v1/setup/docs/${depName}`,
          {
            headers: {
              Authorization: `Bearer ${session?.accessToken}`,
            },
          }
        );

        newDocsLoaded[depName] = response.data;

        // Update progress
        setDepProgress((prev) => {
          const updated = prev.filter((p) => p.name !== depName);
          updated.push({
            name: depName,
            status: 'completed',
            chunks_loaded: response.data.total_chunks,
            total_chunks: response.data.total_chunks,
          });
          return updated;
        });
      } catch (err) {
        console.error(`Failed to load docs for ${depName}:`, err);
        setDepProgress((prev) => {
          const updated = prev.filter((p) => p.name !== depName);
          updated.push({
            name: depName,
            status: 'failed',
            chunks_loaded: 0,
          });
          return updated;
        });
      }
    }

    setDepProgress(newProgress);
    setDocsLoaded(newDocsLoaded);
  };

  const handleComplete = async () => {
    try {
      await axios.post('http://localhost:8000/api/v1/setup/complete-phase1', {}, {
        headers: {
          Authorization: `Bearer ${session?.accessToken}`,
        },
      });
      router.push('/setup/embedding'); // Go to Phase 2
    } catch (err) {
      console.error('Failed to complete Phase 1:', err);
    }
  };

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen depfix-grid-bg flex items-center justify-center" style={{ background: '#060810' }}>
        <div className="text-center">
          <div className="w-10 h-10 rounded-full border-2 border-transparent animate-spin mx-auto mb-5" style={{ borderTopColor: '#00d4ff' }} />
          <p style={{ fontFamily: "'Share Tech Mono', monospace", color: '#607898', fontSize: '11px', letterSpacing: '4px' }}>LOADING SETUP STATUS...</p>
        </div>
      </div>
    );
  }

  const allDocsLoaded = setupStatus?.selected_dependencies?.every(
    (dep: string) => docsLoaded[dep]
  );

  return (
    <div className="min-h-screen depfix-grid-bg" style={{ background: '#060810', color: '#dce8f8' }}>
      <Navbar />
      <div className="max-w-4xl mx-auto px-4 py-10">

        {/* Header */}
        <div className="mb-8">
          <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '4px', color: '#607898' }}>SETUP / PHASE 1</p>
          <h1 style={{ fontFamily: "'Orbitron', monospace", fontWeight: 700, fontSize: '1.6rem', color: '#dce8f8', marginTop: '6px' }}>
            Loading Documentation
          </h1>
          <p style={{ fontFamily: "'Exo 2', sans-serif", fontSize: '14px', color: '#8cb4d4', marginTop: '6px', fontWeight: 300 }}>
            Downloading and preparing documentation for selected dependencies.
          </p>
        </div>

        {/* Dep items */}
        <div className="space-y-3 mb-8">
          {setupStatus?.selected_dependencies?.map((depName: string) => {
            const doc = docsLoaded[depName];
            const isComplete = !!doc;
            return (
              <div key={depName} className="rounded-lg p-4" style={{ background: '#0b0f1e', border: `1px solid ${isComplete ? 'rgba(0,255,136,0.2)' : 'rgba(0,212,255,0.1)'}` }}>
                <div className="flex items-center gap-4">
                  {isComplete ? (
                    <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0" style={{ background: 'rgba(0,255,136,0.15)', border: '1px solid rgba(0,255,136,0.4)', color: '#00ff88' }}>✓</div>
                  ) : (
                    <div className="w-6 h-6 rounded-full border-2 border-transparent animate-spin flex-shrink-0" style={{ borderTopColor: '#00d4ff' }} />
                  )}
                  <div className="flex-1">
                    <p className="font-semibold text-sm" style={{ color: '#dce8f8' }}>{depName}</p>
                    {isComplete ? (
                      <p className="text-xs mt-0.5" style={{ color: '#607898' }}>{doc.total_chunks} chunks loaded</p>
                    ) : (
                      <p className="text-xs mt-0.5" style={{ color: '#607898' }}>loading...</p>
                    )}
                  </div>
                </div>
                {isComplete && doc.sample_chunks && (
                  <div className="mt-3 pl-10">
                    {doc.sample_chunks.slice(0, 2).map((chunk: any, idx: number) => (
                      <p key={idx} className="text-xs mb-1 line-clamp-2" style={{ color: '#607898' }}>{chunk.text?.substring(0, 100)}...</p>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Progress bar */}
        {setupStatus?.selected_dependencies && (
          <div className="mb-8 rounded-lg p-4" style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.1)' }}>
            <div className="flex justify-between items-center mb-3">
              <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#607898' }}>OVERALL PROGRESS</p>
              <p style={{ fontFamily: "'Orbitron', monospace", fontSize: '14px', fontWeight: 700, color: '#00d4ff' }}>
                {Object.keys(docsLoaded).length} / {setupStatus.selected_dependencies.length}
              </p>
            </div>
            <div className="w-full rounded-full h-2" style={{ background: 'rgba(255,255,255,0.05)' }}>
              <div
                className="h-2 rounded-full transition-all duration-500"
                style={{ width: `${(Object.keys(docsLoaded).length / setupStatus.selected_dependencies.length) * 100}%`, background: '#00d4ff', boxShadow: '0 0 8px rgba(0,212,255,0.5)' }}
              />
            </div>
          </div>
        )}

        {/* All loaded banner */}
        {allDocsLoaded && (
          <div className="mb-6 p-4 rounded-lg" style={{ background: 'rgba(0,255,136,0.06)', border: '1px solid rgba(0,255,136,0.25)' }}>
            <p className="font-semibold text-sm mb-1" style={{ color: '#00ff88' }}>✓ All documentation loaded!</p>
            <p className="text-xs" style={{ color: '#8cb4d4' }}>Next: embed documents and index them in the vector database.</p>
          </div>
        )}

        {/* Navigation */}
        <div className="flex gap-4 pt-6" style={{ borderTop: '1px solid rgba(0,212,255,0.08)' }}>
          {allDocsLoaded && (
            <button
              onClick={handleComplete}
              className="flex-1 rounded text-xs transition-all"
              style={{ background: 'rgba(0,255,136,0.08)', border: '1px solid rgba(0,255,136,0.4)', color: '#00ff88', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '2px', padding: '12px' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,255,136,0.16)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'rgba(0,255,136,0.08)')}
            >
              CONTINUE TO PHASE 2 →
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
    </div>
  );
}

