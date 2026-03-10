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
}

export default function DependenciesSetup() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [dependencies, setDependencies] = useState<Dependency[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [customDeps, setCustomDeps] = useState<CustomDependency[]>([]);
  const [customName, setCustomName] = useState('');
  const [customDesc, setCustomDesc] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      const response = await axios.get(
        api('/api/v1/setup/dependencies')
      );
      setDependencies(response.data);
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
    };
    setCustomDeps([...customDeps, newDep]);
    setSelected([...selected, customName]);
    setCustomName('');
    setCustomDesc('');
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
    try {
      await axios.post(
        api('/api/v1/setup/select'),
        { 
          dependency_names: selected,
          custom_dependencies: customDeps,
        },
        {
          headers: {
            Authorization: `Bearer ${session?.accessToken}`,
          },
        }
      );

      // Redirect to progress page
      router.push('/setup/progress');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to select dependencies');
      setSubmitting(false);
      console.error(err);
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
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-semibold" style={{ color: '#dce8f8' }}>{dep.display_name}</p>
                              <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', color: '#607898' }}>({dep.name})</span>
                            </div>
                            <p className="text-xs mt-1" style={{ color: '#8cb4d4' }}>{dep.description}</p>
                            {dep.documentation_url && (
                              <a href={dep.documentation_url} target="_blank" rel="noopener noreferrer"
                                className="text-xs mt-1 inline-block" style={{ color: '#00d4ff' }}
                                onClick={(e) => e.stopPropagation()}>
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
                  <textarea
                    placeholder="Description (optional)"
                    value={customDesc}
                    onChange={(e) => setCustomDesc(e.target.value)}
                    className="w-full rounded text-sm resize-none"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(167,139,250,0.25)', color: '#dce8f8', fontFamily: "'Share Tech Mono', monospace", fontSize: '12px', padding: '8px 10px', outline: 'none', height: '60px' }}
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
              {submitting ? 'LOADING DOCS...' : 'CONTINUE TO PHASE 2 →'}
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
      </div>
    </div>
  );
}
