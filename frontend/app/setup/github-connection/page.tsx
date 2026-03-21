'use client';

import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { useState, useEffect } from 'react';
import axios from 'axios';
import Navbar from '../../components/Navbar';
import SetupStepper from '../../components/SetupStepper';
import { api } from '../../lib/api';

interface ErrorLog {
  id: string;
  filename: string;
  file_format: string;
  error_count: number;
  primary_error_type?: string;
  is_processed: boolean;
  created_at: string;
}

interface ErrorLogDetails extends ErrorLog {
  content: string;
  file_size_bytes?: number;
  error_summary?: Record<string, unknown>;
}

export default function GitHubConnection() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [uploadedLogs, setUploadedLogs] = useState<ErrorLog[]>([]);
  const [selectedLog, setSelectedLog] = useState<ErrorLogDetails | null>(null);
  const [viewingLog, setViewingLog] = useState(false);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin');
    }

    if (status === 'authenticated') {
      fetchUploadedLogs();
      setLoading(false);
    }
  }, [status, router]);

  const fetchUploadedLogs = async () => {
    try {
      const response = await axios.get(api('/api/v1/logs'), {
        headers: {
          Authorization: `Bearer ${session?.accessToken}`,
        },
      });
      setUploadedLogs(response.data);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  };

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(
        api('/api/v1/logs/upload'),
        formData,
        {
          headers: {
            Authorization: `Bearer ${session?.accessToken}`,
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      setSuccess(`✓ Uploaded: ${file.name} (${response.data.error_count} errors found)`);
      setUploading(false);
      await fetchUploadedLogs();
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to upload file';
      setError(errorMsg);
      setUploading(false);
    }
  };

  const handleDeleteLog = async (logId: string) => {
    if (!confirm('Delete this log?')) return;

    try {
      await axios.delete(api(`/api/v1/logs/${logId}`), {
        headers: {
          Authorization: `Bearer ${session?.accessToken}`,
        },
      });
      setSuccess('Log deleted');
      await fetchUploadedLogs();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete log');
    }
  };

  const handleAnalyzeLog = (logId: string) => {
    router.push(`/setup/rag-analysis?log_id=${logId}`);
  };

  const handleViewLog = async (logId: string) => {
    setError(null);
    setViewingLog(true);
    try {
      const response = await axios.get(api(`/api/v1/logs/${logId}`), {
        headers: {
          Authorization: `Bearer ${session?.accessToken}`,
        },
      });
      setSelectedLog(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load log file');
    } finally {
      setViewingLog(false);
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
      <SetupStepper currentStep={4} />
      <div className="max-w-4xl mx-auto px-4 py-10">

        {/* Header */}
        <div className="mb-8">
          <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '4px', color: '#607898' }}>SETUP / PHASE 3</p>
          <h1 style={{ fontFamily: "'Orbitron', monospace", fontWeight: 700, fontSize: '1.6rem', color: '#dce8f8', marginTop: '6px' }}>
            Upload Error Logs
          </h1>
          <p style={{ fontFamily: "'Exo 2', sans-serif", fontSize: '14px', color: '#8cb4d4', marginTop: '6px', fontWeight: 300 }}>
            Upload CI/CD error logs to get AI-powered fix recommendations.
          </p>
        </div>

        {error && (
          <div className="mb-5 p-3 rounded text-xs" style={{ background: 'rgba(255,60,60,0.08)', border: '1px solid rgba(255,60,60,0.3)', color: '#ff3c3c', fontFamily: "'Share Tech Mono', monospace" }}>
            {error}
          </div>
        )}
        {success && (
          <div className="mb-5 p-3 rounded text-xs" style={{ background: 'rgba(0,255,136,0.06)', border: '1px solid rgba(0,255,136,0.3)', color: '#00ff88', fontFamily: "'Share Tech Mono', monospace" }}>
            {success}
          </div>
        )}

        {/* Upload Section */}
        <div className="mb-8 rounded-lg p-6" style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.1)' }}>
          <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#607898', marginBottom: '16px' }}>UPLOAD ERROR LOGS</p>
          <p className="text-xs mb-5" style={{ color: '#8cb4d4' }}>Drag and drop your CI/CD error logs here (.log, .txt, .json)</p>

          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className="rounded-lg p-10 text-center transition-all"
            style={{
              border: `2px dashed ${dragActive ? 'rgba(0,212,255,0.6)' : 'rgba(0,212,255,0.2)'}`,
              background: dragActive ? 'rgba(0,212,255,0.04)' : 'transparent',
            }}
          >
            <svg className="mx-auto mb-3" width="40" height="40" stroke="rgba(0,212,255,0.35)" fill="none" viewBox="0 0 48 48">
              <path d="M28 8H12a4 4 0 00-4 4v20a4 4 0 004 4h24a4 4 0 004-4V20m-12-8v12m0 0l-4-4m4 4l4-4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>

            <input type="file" id="file-upload" className="hidden" onChange={handleFileSelect} accept=".log,.txt,.json,.jsonl,.csv" disabled={uploading} />

            <label htmlFor="file-upload" className="cursor-pointer block">
              <p className="text-sm" style={{ color: '#8cb4d4' }}>
                {uploading ? (
                  <>
                    <span className="inline-block w-4 h-4 rounded-full border-2 border-transparent animate-spin mr-2" style={{ borderTopColor: '#00d4ff', verticalAlign: 'middle' }} />
                    Uploading...
                  </>
                ) : (
                  <>
                    Drag &amp; drop, or{' '}
                    <span className="font-semibold" style={{ color: '#00d4ff' }}>click to browse</span>
                  </>
                )}
              </p>
            </label>
          </div>
        </div>

        {/* Uploaded Logs */}
        {uploadedLogs.length > 0 && (
          <div className="mb-8">
            <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', letterSpacing: '3px', color: '#607898', marginBottom: '12px' }}>
              UPLOADED LOGS ({uploadedLogs.length})
            </p>
            <div className="space-y-3">
              {uploadedLogs.map((log) => (
                <div key={log.id} className="rounded-lg p-4 flex items-start justify-between gap-4 transition-all" style={{ background: '#0b0f1e', border: '1px solid rgba(255,60,60,0.12)', borderLeft: '3px solid rgba(255,60,60,0.5)' }}>
                  <div className="flex-1">
                    <p className="font-semibold text-sm" style={{ color: '#dce8f8' }}>{log.filename}</p>
                    <p className="text-xs mt-0.5" style={{ color: '#607898' }}>
                      {log.error_count} errors
                      {log.primary_error_type && <> · {log.primary_error_type}</>}
                      {' · '}{log.is_processed ? <span style={{ color: '#00ff88' }}>✓ Analyzed</span> : <span style={{ color: '#ffb700' }}>⏳ Queued</span>}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleViewLog(log.id)}
                      className="rounded text-xs transition-all"
                      style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.2)', color: '#dce8f8', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '1px', padding: '6px 14px' }}
                      onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.08)')}
                      onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
                      disabled={viewingLog}
                    >
                      VIEW
                    </button>
                    <button
                      onClick={() => handleAnalyzeLog(log.id)}
                      className="rounded text-xs transition-all"
                      style={{ background: 'rgba(0,212,255,0.08)', border: '1px solid rgba(0,212,255,0.3)', color: '#00d4ff', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '1px', padding: '6px 14px' }}
                      onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,212,255,0.16)')}
                      onMouseLeave={e => (e.currentTarget.style.background = 'rgba(0,212,255,0.08)')}
                    >
                      ANALYZE
                    </button>
                    <button
                      onClick={() => handleDeleteLog(log.id)}
                      className="rounded text-xs transition-all"
                      style={{ background: 'rgba(255,60,60,0.06)', border: '1px solid rgba(255,60,60,0.25)', color: '#ff3c3c', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '1px', padding: '6px 14px' }}
                      onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,60,60,0.12)')}
                      onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,60,60,0.06)')}
                    >
                      DELETE
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* What happens next */}
        {selectedLog && (
          <div className="mb-8 rounded-lg" style={{ background: '#0b0f1e', border: '1px solid rgba(255,255,255,0.12)' }}>
            <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
              <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '11px', color: '#dce8f8', letterSpacing: '1.5px' }}>
                LOG FILE: {selectedLog.filename}
              </p>
              <button
                onClick={() => setSelectedLog(null)}
                className="rounded text-xs"
                style={{ background: 'rgba(255,60,60,0.08)', border: '1px solid rgba(255,60,60,0.35)', color: '#ff7f7f', fontFamily: "'Share Tech Mono', monospace", padding: '4px 10px' }}
              >
                CLOSE
              </button>
            </div>
            <pre className="p-4 overflow-auto max-h-[360px]" style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '11px', lineHeight: 1.45, color: '#8cb4d4' }}>
{selectedLog.content || '(empty log content)'}
            </pre>
          </div>
        )}

        {/* What happens next */}
        <div className="mb-8 p-5 rounded-lg" style={{ background: '#0b0f1e', border: '1px solid rgba(0,212,255,0.07)' }}>
          <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', letterSpacing: '3px', color: '#607898', marginBottom: '10px' }}>WHAT HAPPENS NEXT</p>
          <div className="space-y-2">
            {['RAG system analyzes your error logs', 'Searches relevant documentation for solutions', 'Generates AI-powered fix recommendations', 'Ready to create a PR with the fix'].map((s, i) => (
              <p key={i} className="text-xs" style={{ color: '#8cb4d4' }}>
                <span style={{ color: '#00d4ff', marginRight: '8px' }}>{'>'}</span>{s}
              </p>
            ))}
          </div>
        </div>

        {/* Navigation */}
        <div className="pt-4" style={{ borderTop: '1px solid rgba(0,212,255,0.08)' }}>
          <button
            onClick={() => router.push('/dashboard')}
            className="w-full rounded text-xs transition-all"
            style={{ background: 'rgba(0,212,255,0.07)', border: '1px solid rgba(0,212,255,0.4)', color: '#00d4ff', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '3px', padding: '13px' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,212,255,0.14)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'rgba(0,212,255,0.07)')}
          >
            GO TO DASHBOARD →
          </button>
        </div>
      </div>
    </div>
  );
}
