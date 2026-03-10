'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useSession } from 'next-auth/react';
import axios from 'axios';
import Navbar from '../../components/Navbar';
import SetupStepper from '../../components/SetupStepper';
import { api } from '../../lib/api';

interface RagResult {
  query_id: string;
  log_id: string;
  error_summary: any;
  retrieved_docs_count: number;
  fix: {
    root_cause: string;
    solution: string;
    code_fix: string;
    prevention: string;
    cicd_fix: string;
    full_response: string;
  };
  dependencies_analyzed: string[];
  ragas_scores?: {
    faithfulness: number;
    answer_relevance: number;
    context_precision: number;
    context_recall: number;
  } | null;
}

export default function RAGAnalysisPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data: session, status } = useSession();
  
  const logId = searchParams.get('log_id') || '';
  const urlDeps = searchParams.get('dependencies')?.split(',').filter(d => d) || [];
  
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<RagResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [approved, setApproved] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [resolvedDeps, setResolvedDeps] = useState<string[]>(urlDeps);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin');
    }

    if (status === 'authenticated' && logId && !result) {
      // If no deps in URL, fetch from setup status first
      if (urlDeps.length === 0) {
        axios.get(api('/api/v1/embedding/status'), {
          headers: { Authorization: `Bearer ${session?.accessToken}` },
        }).then(r => {
          const deps = r.data?.dependencies || [];
          setResolvedDeps(deps);
          analyzeError(deps);
        }).catch(() => analyzeError([]));
      } else {
        analyzeError(urlDeps);
      }
    }
  }, [status, logId]);

  const analyzeError = async (deps?: string[]) => {
    try {
      setAnalyzing(true);
      setError(null);

      const response = await axios.post(
        api(`/api/v1/rag/analyze-error-log`),
        {
          log_id: logId,
          dependencies: (deps ?? resolvedDeps).filter(d => d),
        },
        {
          headers: {
            Authorization: `Bearer ${session?.accessToken}`,
          },
        }
      );

      setResult(response.data.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to analyze error log');
      console.error(err);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleApproveFix = async () => {
    if (!result) return;

    try {
      await axios.post(
        api(`/api/v1/rag/approve-fix/${result.query_id}`),
        {
          fix_index: 0,
          feedback: feedback || undefined,
        },
        {
          headers: {
            Authorization: `Bearer ${session?.accessToken}`,
          },
        }
      );

      setApproved(true);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to approve fix');
      console.error(err);
    }
  };

  const handleRejectFix = async () => {
    if (!result) return;

    try {
      await axios.post(
        api(`/api/v1/rag/reject-fix/${result.query_id}`),
        {
          reason: feedback || undefined,
        },
        {
          headers: {
            Authorization: `Bearer ${session?.accessToken}`,
          },
        }
      );

      setApproved(false);
      setError(null);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reject fix');
      console.error(err);
    }
  };

  if (status === 'loading') {
    return (
      <div className="min-h-screen depfix-grid-bg" style={{ background: '#060810' }}>
        <Navbar />
        <SetupStepper currentStep={5} />
        <div className="flex items-center justify-center py-24">
          <div className="text-center">
            <div className="w-10 h-10 rounded-full border-2 border-transparent animate-spin mx-auto mb-5" style={{ borderTopColor: '#00d4ff' }} />
            <p style={{ fontFamily: "'Share Tech Mono', monospace", color: '#607898', fontSize: '11px', letterSpacing: '4px' }}>LOADING...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen depfix-grid-bg" style={{ background: '#060810', color: '#dce8f8' }}>
      <Navbar />
      <SetupStepper currentStep={5} />
      <div className="max-w-4xl mx-auto py-10 px-4">
        <div className="rounded-xl p-8" style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.1)' }}>
          {/* Header */}
          <div className="mb-8">
            <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '4px', color: '#607898' }}>ANALYSIS / RAG ENGINE</p>
            <h1 style={{ fontFamily: "'Orbitron', monospace", fontWeight: 700, fontSize: '1.6rem', color: '#dce8f8', marginTop: '6px' }}>
              AI-Powered Error Analysis
            </h1>
            <p style={{ fontFamily: "'Exo 2', sans-serif", fontSize: '14px', color: '#8cb4d4', marginTop: '6px', fontWeight: 300 }}>
              Using RAG to find solutions from dependency documentation.
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-3 rounded text-xs" style={{ background: 'rgba(255,60,60,0.08)', border: '1px solid rgba(255,60,60,0.3)', color: '#ff3c3c', fontFamily: "'Share Tech Mono', monospace" }}>
              {error}
            </div>
          )}

          {/* Loading State */}
          {analyzing && !result && (
            <div className="space-y-4 py-6">
              <div className="animate-pulse space-y-3">
                <div className="h-3 rounded w-3/4" style={{ background: 'rgba(0,212,255,0.08)' }} />
                <div className="h-3 rounded w-1/2" style={{ background: 'rgba(0,212,255,0.05)' }} />
              </div>
              <p className="text-xs" style={{ color: '#607898', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '3px' }}>ANALYZING ERROR AND SEARCHING DOCUMENTATION...</p>
            </div>
          )}

          {/* Results */}
          {result && (
            <div className="space-y-8">
              {/* Error Summary */}
              <div className="p-4 rounded-lg" style={{ background: 'rgba(255,60,60,0.04)', borderLeft: '3px solid rgba(255,60,60,0.5)', border: '1px solid rgba(255,60,60,0.12)' }}>
                <p className="text-xs mb-3" style={{ fontFamily: "'Share Tech Mono', monospace", letterSpacing: '3px', color: '#ff3c3c' }}>ERROR SUMMARY</p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs mb-1" style={{ color: '#607898' }}>Total Errors</p>
                    <p style={{ fontFamily: "'Orbitron', monospace", fontSize: '1.8rem', fontWeight: 700, color: '#ff3c3c' }}>
                      {result.error_summary?.total_errors || 0}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs mb-1" style={{ color: '#607898' }}>Primary Error Type</p>
                    <p className="text-sm font-semibold" style={{ color: '#dce8f8' }}>
                      {result.error_summary?.primary_error_type || 'Unknown'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Retrieved Documentation */}
              <div className="p-4 rounded-lg" style={{ background: 'rgba(0,212,255,0.03)', borderLeft: '3px solid rgba(0,212,255,0.4)', border: '1px solid rgba(0,212,255,0.1)' }}>
                <p className="text-xs mb-3" style={{ fontFamily: "'Share Tech Mono', monospace", letterSpacing: '3px', color: '#00d4ff' }}>RETRIEVED DOCUMENTATION</p>
                <p className="text-xs mb-3" style={{ color: '#607898' }}>
                  Found {result.retrieved_docs_count} relevant documentation chunks
                </p>
                <div className="flex flex-wrap gap-2">
                  {result.dependencies_analyzed?.map((dep) => (
                    <span key={dep} className="inline-block px-3 py-1 text-xs rounded" style={{ background: 'rgba(0,212,255,0.1)', color: '#00d4ff', border: '1px solid rgba(0,212,255,0.2)', fontFamily: "'Share Tech Mono', monospace" }}>
                      {dep}
                    </span>
                  ))}
                  {result.dependencies_analyzed?.length === 0 && (
                    <p className="text-xs" style={{ color: '#607898' }}>No specific dependencies analyzed</p>
                  )}
                </div>
              </div>

              {/* Fix Suggestion */}
              <div className="space-y-4">
                <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#00ff88' }}>AI-SUGGESTED FIX</p>

                {/* Root Cause */}
                <div className="p-4 rounded-lg" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(0,212,255,0.08)' }}>
                  <p className="text-xs font-semibold mb-2" style={{ color: '#ffb700', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '2px' }}>ROOT CAUSE</p>
                  <p className="text-sm" style={{ color: '#dce8f8' }}>{result.fix.root_cause}</p>
                </div>

                {/* Solution */}
                <div className="p-4 rounded-lg" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(0,212,255,0.08)' }}>
                  <p className="text-xs font-semibold mb-2" style={{ color: '#00ff88', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '2px' }}>SOLUTION</p>
                  <p className="text-sm" style={{ color: '#dce8f8' }}>{result.fix.solution}</p>
                </div>

                {/* Code Fix */}
                {result.fix.code_fix && (
                  <div className="bg-gray-900 p-4 rounded-lg overflow-x-auto">
                    <h3 className="font-semibold text-white mb-2">Code Fix</h3>
                    <pre className="text-gray-100 text-sm whitespace-pre-wrap break-words">
                      {result.fix.code_fix}
                    </pre>
                  </div>
                )}

                {/* Prevention */}
                <div className="p-4 rounded-lg" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(0,212,255,0.08)' }}>
                  <p className="text-xs font-semibold mb-2" style={{ color: '#a78bfa', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '2px' }}>PREVENTION</p>
                  <p className="text-sm" style={{ color: '#dce8f8' }}>{result.fix.prevention}</p>
                </div>

                {/* CI/CD Fix */}
                {result.fix.cicd_fix && (
                  <div className="p-4 rounded-lg" style={{ background: 'rgba(0,255,136,0.03)', borderLeft: '3px solid rgba(0,255,136,0.4)', border: '1px solid rgba(0,255,136,0.1)' }}>
                    <p className="text-xs font-semibold mb-2" style={{ color: '#00ff88', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '2px' }}>🔧 CI/CD INTEGRATION</p>
                    <pre className="text-xs font-mono whitespace-pre-wrap" style={{ color: '#dce8f8' }}>{result.fix.cicd_fix}</pre>
                  </div>
                )}
              </div>

              {/* RAGAS Evaluation Metrics */}
              {result.ragas_scores && (
                <div className="mt-6 rounded-xl overflow-hidden" style={{ background: '#0b0f1e', border: '1px solid rgba(167,139,250,0.22)' }}>
                  {/* Header */}
                  <div className="px-5 py-3 flex items-center gap-3" style={{ borderBottom: '1px solid rgba(167,139,250,0.12)' }}>
                    <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '11px', letterSpacing: '3px', color: '#a78bfa' }}>
                      📊 RAGAS EVAL
                    </span>
                    <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', color: '#607898' }}>
                      retrieval-augmented generation assessment score
                    </span>
                  </div>

                  {/* Metric cards */}
                  <div className="p-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {([
                      {
                        key: 'faithfulness' as const,
                        label: 'Faithfulness',
                        shortDesc: 'Answer grounded in retrieved docs',
                        barColor: '#3b82f6',
                        tip: 'Every claim in the AI answer must be backed by the retrieved documentation. High score means the AI only stated things found in the retrieved context — no hallucinations.',
                        good: '≥75%: Answer stays within what the docs say',
                        bad:  '<50%: AI may have hallucinated or over-generalised',
                      },
                      {
                        key: 'answer_relevance' as const,
                        label: 'Answer Relevance',
                        shortDesc: 'Fix targets this specific error',
                        barColor: '#8b5cf6',
                        tip: 'How directly the generated fix addresses the original error log. High score = targeted, on-topic response. Low score = vague, generic, or off-topic answer.',
                        good: '≥75%: Fix is specific and actionable',
                        bad:  '<50%: Fix may be too generic or miss the issue',
                      },
                      {
                        key: 'context_precision' as const,
                        label: 'Context Precision',
                        shortDesc: 'Retrieved docs are on-topic',
                        barColor: '#10b981',
                        tip: 'Whether the pgvector search retrieved documentation actually relevant to this error. High score = right sections found. Low score = wrong docs were fetched from the vector DB.',
                        good: '≥75%: Vector search fetched relevant documentation',
                        bad:  '<50%: Consider re-embedding with more data',
                      },
                      {
                        key: 'context_recall' as const,
                        label: 'Context Recall',
                        shortDesc: 'Docs cover all needed knowledge',
                        barColor: '#f97316',
                        tip: 'Whether the retrieved docs cover ALL information needed to fully explain and fix this error. High score = knowledge base is complete for this topic.',
                        good: '≥75%: Knowledge base is comprehensive',
                        bad:  '<50%: Embed more dependencies for better coverage',
                      },
                    ] as const).map(({ key, label, shortDesc, barColor, tip, good, bad }) => {
                      const score = result.ragas_scores![key as keyof typeof result.ragas_scores];
                      const pct = typeof score === 'number' ? Math.round(score * 100) : 0;
                      const scoreColor = pct >= 75 ? '#00ff88' : pct >= 50 ? '#ffb700' : '#ff3c3c';
                      return (
                        <div
                          key={key}
                          className="rounded-lg p-3"
                          style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(0,212,255,0.1)' }}
                        >
                          {/* Header row */}
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-1.5">
                              <span className="text-sm font-semibold" style={{ color: '#dce8f8' }}>{label}</span>

                              {/* (i) info tooltip */}
                              <div className="relative group">
                                <button
                                  type="button"
                                  className="w-4 h-4 rounded-full text-xs font-bold flex items-center justify-center cursor-help"
                                  style={{
                                    background: 'rgba(167,139,250,0.15)',
                                    color: '#a78bfa',
                                    border: '1px solid rgba(167,139,250,0.35)',
                                    lineHeight: 1,
                                    fontSize: '10px',
                                  }}
                                  aria-label={`What is ${label}?`}
                                >
                                  i
                                </button>
                                {/* Tooltip panel */}
                                <div
                                  className="absolute bottom-full left-0 mb-2 rounded-lg shadow-2xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-150 z-50 pointer-events-none p-3"
                                  style={{
                                    background: '#0b0f1e',
                                    border: '1px solid rgba(167,139,250,0.35)',
                                    minWidth: '260px',
                                    width: '280px',
                                  }}
                                >
                                  <p
                                    className="text-xs font-bold mb-2"
                                    style={{ color: '#a78bfa', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '2px' }}
                                  >
                                    {label.toUpperCase()}
                                  </p>
                                  <p className="text-xs leading-relaxed mb-3" style={{ color: '#dce8f8' }}>
                                    {tip}
                                  </p>
                                  <div className="space-y-1.5 pt-2" style={{ borderTop: '1px solid rgba(167,139,250,0.15)' }}>
                                    <p className="text-xs flex gap-1.5" style={{ color: '#00ff88' }}>
                                      <span className="flex-shrink-0 font-bold">✓</span><span>{good}</span>
                                    </p>
                                    <p className="text-xs flex gap-1.5" style={{ color: '#ff3c3c' }}>
                                      <span className="flex-shrink-0 font-bold">✗</span><span>{bad}</span>
                                    </p>
                                  </div>
                                </div>
                              </div>
                            </div>

                            <span
                              style={{
                                fontFamily: "'Orbitron', monospace",
                                fontSize: '18px',
                                fontWeight: 700,
                                color: scoreColor,
                              }}
                            >
                              {pct}<span style={{ fontSize: '11px' }}>%</span>
                            </span>
                          </div>

                          {/* Progress bar */}
                          <div className="w-full h-1.5 rounded-full mb-1.5" style={{ background: 'rgba(255,255,255,0.07)' }}>
                            <div
                              className="h-1.5 rounded-full transition-all duration-700"
                              style={{
                                width: `${pct}%`,
                                background: barColor,
                                boxShadow: pct >= 50 ? `0 0 6px ${barColor}99` : 'none',
                              }}
                            />
                          </div>
                          <p className="text-xs" style={{ color: '#607898' }}>{shortDesc}</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Feedback */}
              {!approved && (
                <div className="space-y-3">
                  <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#607898' }}>FEEDBACK (OPTIONAL)</p>
                  <textarea
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    placeholder="Did this fix help? Any comments on the suggestion?"
                    className="w-full rounded resize-none h-20 text-sm"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(0,212,255,0.18)', color: '#dce8f8', fontFamily: "'Share Tech Mono', monospace", fontSize: '12px', padding: '10px 12px', outline: 'none' }}
                  />
                </div>
              )}

              {/* Approval Message */}
              {approved && (
                <div className="p-4 rounded-lg text-sm" style={{ background: 'rgba(0,255,136,0.06)', border: '1px solid rgba(0,255,136,0.25)', color: '#00ff88' }}>
                  ✓ Fix approved and recorded. Thank you for your feedback!
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-4 justify-between pt-6" style={{ borderTop: '1px solid rgba(0,212,255,0.08)' }}>
                <button
                  onClick={() => router.push('/dashboard')}
                  className="rounded text-xs transition-all"
                  style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.1)', color: '#607898', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '2px', padding: '10px 20px' }}
                >
                  BACK TO DASHBOARD
                </button>

                <div className="flex gap-3">
                  <button
                    onClick={handleRejectFix}
                    disabled={approved}
                    className="rounded text-xs transition-all disabled:opacity-40"
                    style={{ background: 'rgba(255,60,60,0.08)', border: '1px solid rgba(255,60,60,0.3)', color: '#ff3c3c', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '2px', padding: '10px 18px' }}
                    onMouseEnter={e => (!approved && ((e.currentTarget as HTMLElement).style.background = 'rgba(255,60,60,0.16)'))}
                    onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(255,60,60,0.08)')}
                  >
                    NOT HELPFUL
                  </button>
                  <button
                    onClick={handleApproveFix}
                    disabled={approved}
                    className="rounded text-xs transition-all disabled:opacity-40"
                    style={{ background: 'rgba(0,255,136,0.08)', border: '1px solid rgba(0,255,136,0.35)', color: '#00ff88', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '2px', padding: '10px 18px' }}
                    onMouseEnter={e => (!approved && ((e.currentTarget as HTMLElement).style.background = 'rgba(0,255,136,0.16)'))}
                    onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(0,255,136,0.08)')}
                  >
                    THIS HELPS!
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Empty State */}
          {!result && !analyzing && (
            <div className="text-center py-12">
              <p className="text-sm mb-5" style={{ color: '#607898' }}>No log selected for analysis</p>
              <button
                onClick={() => router.push('/dashboard')}
                className="rounded text-xs transition-all"
                style={{ background: 'rgba(0,212,255,0.08)', border: '1px solid rgba(0,212,255,0.35)', color: '#00d4ff', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '2px', padding: '10px 24px' }}
                onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(0,212,255,0.16)')}
                onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(0,212,255,0.08)')}
              >
                GO TO DASHBOARD
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
