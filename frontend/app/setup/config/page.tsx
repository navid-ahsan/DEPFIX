'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import axios from 'axios';
import Navbar from '../../components/Navbar';
import SetupStepper from '../../components/SetupStepper';
import { api, getApiBase, setApiBase } from '../../lib/api';

// ── Types ─────────────────────────────────────────────────────────────────────

interface HardwareInfo {
  cpu: { cores: number; model: string; usage_pct: number };
  ram_gb: number;
  gpu: { available: boolean; name: string | null; vram_gb: number; type: string | null };
  recommended: { llm: string; embedding: string };
  platform: string;
  is_wsl2: boolean;
}

interface OllamaModel {
  name: string;
  size: number;
  modified_at: string;
}

interface UserConfig {
  ollama_url: string;
  postgres_url: string;
  llm_model: string;
  embedding_model: string;
  temperature: string;
  max_tokens: number;
  system_prompt: string | null;
  preferred_quantization: string;
}

// ── Style atoms ───────────────────────────────────────────────────────────────

const card: React.CSSProperties = {
  background: 'rgba(11,15,30,0.85)',
  border: '1px solid rgba(0,212,255,0.12)',
  borderRadius: '4px',
  padding: '24px',
};

const lbl: React.CSSProperties = {
  fontFamily: "'Share Tech Mono', monospace",
  fontSize: '10px',
  letterSpacing: '2px',
  color: '#607898',
  display: 'block',
  marginBottom: '6px',
};

const inp: React.CSSProperties = {
  width: '100%',
  background: 'rgba(0,0,0,0.4)',
  border: '1px solid rgba(0,212,255,0.18)',
  borderRadius: '2px',
  color: '#dce8f8',
  fontFamily: "'Share Tech Mono', monospace",
  fontSize: '12px',
  padding: '8px 12px',
  outline: 'none',
  boxSizing: 'border-box',
};

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionTitle({ children, color = '#00d4ff' }: { children: React.ReactNode; color?: string }) {
  return (
    <div style={{
      fontFamily: "'Share Tech Mono', monospace",
      fontSize: '10px',
      letterSpacing: '3px',
      color,
      marginBottom: '16px',
      paddingBottom: '8px',
      borderBottom: `1px solid ${color}22`,
    }}>
      {children}
    </div>
  );
}

function Btn({
  onClick, disabled = false, children, color = '#00d4ff', style,
}: {
  onClick?: () => void;
  disabled?: boolean;
  children: React.ReactNode;
  color?: string;
  style?: React.CSSProperties;
}) {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        fontFamily: "'Share Tech Mono', monospace",
        fontSize: '10px',
        letterSpacing: '2px',
        padding: '8px 18px',
        border: `1px solid ${color}`,
        color,
        background: hov ? `${color}18` : 'transparent',
        cursor: disabled ? 'not-allowed' : 'pointer',
        borderRadius: '2px',
        opacity: disabled ? 0.45 : 1,
        transition: 'background 0.15s',
        whiteSpace: 'nowrap' as const,
        ...style,
      }}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
    >
      {children}
    </button>
  );
}

function StatusDot({ status }: { status: 'untested' | 'ok' | 'err' }) {
  const color = status === 'ok' ? '#00ff88' : status === 'err' ? '#ff3c3c' : '#607898';
  return (
    <span style={{
      display: 'inline-block',
      width: 8, height: 8,
      borderRadius: '50%',
      background: color,
      flexShrink: 0,
    }} />
  );
}

// ── CI/CD snippet templates (shown in the webhook card) ─────────────────────

const GH_ACTIONS_SNIPPET = `# .github/workflows/your-workflow.yml  —  add as last step in any job
# Repo secret required: DEPFIX_URL

- name: Send failure log to DEPFIX
  if: failure()
  run: |
    jq -n \\
      --arg wf   "\${{ github.workflow }}" \\
      --arg run  "\${{ github.run_id }}" \\
      --arg repo "\${{ github.repository }}" \\
      --arg ref  "\${{ github.ref_name }}" \\
      --arg sha  "\${{ github.sha }}" \\
      --arg log  "$(cat job.log 2>/dev/null || echo '')" \\
      '{workflow_name:$wf,run_id:$run,repository:$repo,branch:$ref,commit_sha:$sha,conclusion:"failure",log_content:$log}' \\
    | curl -sf -X POST "\${{ secrets.DEPFIX_URL }}/api/v1/webhook/github-actions" \\
      -H "Content-Type: application/json" -d @-
  # Tip: pipe your build command through: your-cmd 2>&1 | tee job.log`.trim();

const GITLAB_SNIPPET = `# .gitlab-ci.yml  —  add to any job's after_script
# CI/CD variable required: DEPFIX_URL

after_script:
  - |
    if [ "$CI_JOB_STATUS" = "failed" ]; then
      jq -n \\
        --arg wf   "$CI_JOB_NAME" \\
        --arg run  "$CI_PIPELINE_ID" \\
        --arg repo "$CI_PROJECT_PATH" \\
        --arg ref  "$CI_COMMIT_BRANCH" \\
        --arg sha  "$CI_COMMIT_SHA" \\
        --arg log  "$(cat job.log 2>/dev/null || echo '')" \\
        '{workflow_name:$wf,run_id:$run,repository:$repo,branch:$ref,commit_sha:$sha,conclusion:"failure",log_content:$log}' \\
      | curl -sf -X POST "\${DEPFIX_URL}/api/v1/webhook/github-actions" \\
        -H "Content-Type: application/json" -d @-
    fi
  # Tip: pipe your build command through: your-cmd 2>&1 | tee job.log`.trim();

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function ConfigPage() {
  const router = useRouter();
  const { data: session, status } = useSession();

  // Hardware
  const [hw, setHw] = useState<HardwareInfo | null>(null);
  const [hwLoading, setHwLoading] = useState(true);

  // Backend URL (localStorage only)
  const [backendUrl, setBackendUrl] = useState('');

  // Persisted config
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  const [postgresUrl, setPostgresUrl] = useState('');
  const [llmModel, setLlmModel] = useState('');
  const [embeddingModel, setEmbeddingModel] = useState('nomic-embed-text');
  const [temperature, setTemperature] = useState('0.2');
  const [maxTokens, setMaxTokens] = useState(2048);
  const [systemPrompt, setSystemPrompt] = useState('');

  // Connection tests
  const [ollamaStatus, setOllamaStatus] = useState<'untested' | 'ok' | 'err'>('untested');
  const [postgresStatus, setPostgresStatus] = useState<'untested' | 'ok' | 'err'>('untested');
  const [testingOllama, setTestingOllama] = useState(false);
  const [testingPostgres, setTestingPostgres] = useState(false);

  // Available Ollama models
  const [ollamaModels, setOllamaModels] = useState<OllamaModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);

  // Model pull via SSE
  const [pullModel, setPullModel] = useState('');
  const [pulling, setPulling] = useState(false);
  const [pullLines, setPullLines] = useState<string[]>([]);
  const [pullDone, setPullDone] = useState(false);
  const pullLogRef = useRef<HTMLDivElement>(null);

  // Model size check before pull
  const [modelSizeGb, setModelSizeGb] = useState<number | null>(null);
  const [sizeChecking, setSizeChecking] = useState(false);

  // Docker health check
  const [dockerContainers, setDockerContainers] = useState<{ name: string; status: string; image: string }[] | null>(null);
  const [dockerChecking, setDockerChecking] = useState(false);

  // CI/CD webhook tab
  const [ciTab, setCiTab] = useState<'github' | 'gitlab'>('github');

  // Save feedback
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');

  // ── Auth guard ────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (status === 'unauthenticated') router.push('/auth/signin');
  }, [status, router]);

  // ── Init on auth ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (status !== 'authenticated') return;
    setBackendUrl(getApiBase());
    loadHardware();
    loadConfig();
  }, [status]);

  // ── Data loaders ──────────────────────────────────────────────────────────────
  const loadHardware = async () => {
    setHwLoading(true);
    try {
      const r = await axios.get(api('/api/v1/system/info'));
      setHw(r.data);
    } catch {
      // backend might not be reachable yet
    } finally {
      setHwLoading(false);
    }
  };

  const loadConfig = async () => {
    try {
      const r = await axios.get(api('/api/v1/config/'));
      const c: UserConfig = r.data;
      setOllamaUrl(c.ollama_url);
      setPostgresUrl(c.postgres_url);
      setLlmModel(c.llm_model || '');
      setEmbeddingModel(c.embedding_model);
      setTemperature(c.temperature);
      setMaxTokens(c.max_tokens);
      setSystemPrompt(c.system_prompt || '');
      fetchOllamaModels();
    } catch {
      // no saved config yet
    }
  };

  const fetchOllamaModels = async () => {
    setModelsLoading(true);
    try {
      const r = await axios.get(api('/api/v1/ollama/models'));
      setOllamaModels(r.data.models || []);
    } catch {
      setOllamaModels([]);
    } finally {
      setModelsLoading(false);
    }
  };

  // ── Handlers ──────────────────────────────────────────────────────────────────
  const applyBackendUrl = () => {
    setApiBase(backendUrl);
    loadHardware();
    loadConfig();
  };

  const testOllama = async () => {
    setTestingOllama(true);
    try {
      const r = await axios.post(api('/api/v1/config/test/ollama'), { url: ollamaUrl });
      setOllamaStatus(r.data.ok ? 'ok' : 'err');
      if (r.data.ok) fetchOllamaModels();
    } catch {
      setOllamaStatus('err');
    }
    setTestingOllama(false);
  };

  const testPostgres = async () => {
    setTestingPostgres(true);
    try {
      const r = await axios.post(api('/api/v1/config/test/postgres'), { url: postgresUrl });
      setPostgresStatus(r.data.ok ? 'ok' : 'err');
    } catch {
      setPostgresStatus('err');
    }
    setTestingPostgres(false);
  };

  const checkModelSize = async (name: string) => {
    if (!name.trim()) { setModelSizeGb(null); return; }
    setSizeChecking(true);
    try {
      const r = await axios.get(api(`/api/v1/ollama/model-info/${encodeURIComponent(name.trim())}`));
      setModelSizeGb(r.data.size_gb ?? null);
    } catch {
      setModelSizeGb(null);
    } finally {
      setSizeChecking(false);
    }
  };

  const checkDocker = async () => {
    setDockerChecking(true);
    try {
      const r = await axios.get(api('/api/v1/system/docker'));
      setDockerContainers(r.data.containers || []);
    } catch {
      setDockerContainers([]);
    } finally {
      setDockerChecking(false);
    }
  };

  const pullNewModel = async () => {
    if (!pullModel.trim()) return;
    setPulling(true);
    setPullLines([]);
    setPullDone(false);

    try {
      const response = await fetch(api('/api/v1/ollama/pull'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: pullModel.trim() }),
      });
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) { setPulling(false); return; }

      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            const msg = data.status || data.error || '';
            if (msg) {
              setPullLines(prev => [...prev, msg].slice(-80));
              if (pullLogRef.current) pullLogRef.current.scrollTop = pullLogRef.current.scrollHeight;
            }
            if (data.status === 'success' || data.status === 'done') {
              setPullDone(true);
              fetchOllamaModels();
            }
          } catch { /* ignore malformed lines */ }
        }
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unknown error';
      setPullLines(prev => [...prev, `Error: ${msg}`]);
    }

    setPulling(false);
  };

  const saveConfig = async (): Promise<void> => {
    setSaving(true);
    setSaveMsg('');
    try {
      await axios.put(api('/api/v1/config/'), {
        ollama_url: ollamaUrl,
        postgres_url: postgresUrl,
        llm_model: llmModel,
        embedding_model: embeddingModel,
        temperature,
        max_tokens: maxTokens,
        system_prompt: systemPrompt || null,
      });
      setSaveMsg('Configuration saved.');
    } catch {
      setSaveMsg('Failed to save. Is the backend reachable?');
    }
    setSaving(false);
  };

  const saveAndContinue = async () => {
    await saveConfig();
    router.push('/setup/dependencies');
  };

  const useRecommended = () => {
    if (!hw) return;
    setLlmModel(hw.recommended.llm);
    setEmbeddingModel(hw.recommended.embedding);
  };

  // ── Render ────────────────────────────────────────────────────────────────────
  if (status === 'loading') return null;

  return (
    <div
      className="depfix-grid-bg"
      style={{ minHeight: '100vh', color: '#dce8f8' }}
    >
      <Navbar />
      <SetupStepper currentStep={0} />

      <main style={{ maxWidth: '1100px', margin: '0 auto', padding: '40px 24px 80px' }}>
        {/* Page header */}
        <div style={{ marginBottom: '40px' }}>
          <div style={{
            fontFamily: "'Share Tech Mono', monospace",
            fontSize: '10px',
            letterSpacing: '4px',
            color: '#607898',
            marginBottom: '6px',
          }}>
            SETUP / PHASE 0
          </div>
          <h1 style={{
            fontFamily: "'Orbitron', sans-serif",
            fontSize: '24px',
            fontWeight: 700,
            color: '#dce8f8',
            margin: 0,
          }}>
            System{' '}
            <span style={{ color: '#00d4ff' }}>Configuration</span>
          </h1>
          <p style={{
            fontFamily: "'Exo 2', sans-serif",
            fontSize: '13px',
            color: '#8cb4d4',
            marginTop: '8px',
            marginBottom: 0,
          }}>
            Connect to your self-hosted Ollama instance, PostgreSQL/pgvector, and configure AI model settings.
          </p>
        </div>

        {/* ── Row 1: Hardware + Backend URL ─────────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>

          {/* Hardware Detection */}
          <div style={card}>
            <SectionTitle color="#a78bfa">HARDWARE DETECTION</SectionTitle>
            {hwLoading ? (
              <span style={{ ...lbl, color: '#607898' }}>SCANNING HARDWARE…</span>
            ) : hw ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <Row label="CPU" value={`${hw.cpu.cores}× ${(hw.cpu.model || hw.platform).slice(0, 32)}`} />
                <Row label="RAM" value={`${hw.ram_gb} GB`} />
                <Row
                  label="GPU"
                  value={hw.gpu.available ? hw.gpu.name ?? 'GPU detected' : 'None detected'}
                  valueColor={hw.gpu.available ? '#00ff88' : '#607898'}
                />
                <Row
                  label="VRAM"
                  value={hw.gpu.available ? `${hw.gpu.vram_gb} GB` : '—'}
                  valueColor={hw.gpu.available
                    ? hw.gpu.vram_gb >= 16 ? '#00ff88'
                    : hw.gpu.vram_gb >= 8 ? '#ffb700'
                    : '#ff6b6b'
                    : '#607898'}
                />

                {/* WSL2 warning */}
                {hw.is_wsl2 && (
                  <div style={{
                    padding: '10px 14px',
                    background: 'rgba(255,183,0,0.07)',
                    border: '1px solid rgba(255,183,0,0.35)',
                    borderRadius: '3px',
                  }}>
                    <div style={{ fontFamily: "'Share Tech Mono'", fontSize: '10px', color: '#ffb700', marginBottom: '4px', letterSpacing: '0.08em' }}>
                      ⚠ WSL2 DETECTED — RAM / VRAM MAY BE CAPPED
                    </div>
                    <div style={{ fontFamily: "'Share Tech Mono'", fontSize: '10px', color: '#8cb4d4', lineHeight: '1.5' }}>
                      WSL2 limits RAM to 50% of host (max 8 GB) by default.
                      Create <span style={{ color: '#00d4ff' }}>C:\Users\&lt;you&gt;\.wslconfig</span> to increase it:
                    </div>
                    <pre style={{
                      margin: '6px 0 0',
                      padding: '8px 10px',
                      background: 'rgba(0,0,0,0.35)',
                      borderRadius: '3px',
                      fontFamily: "'Share Tech Mono'",
                      fontSize: '10px',
                      color: '#00ff88',
                      whiteSpace: 'pre',
                      overflowX: 'auto',
                    }}>{`[wsl2]\nmemory=16GB      # adjust to your host RAM\nswap=8GB\nprocessors=8`}</pre>
                    <div style={{ fontFamily: "'Share Tech Mono'", fontSize: '9px', color: '#607898', marginTop: '6px' }}>
                      Restart WSL after saving: <span style={{ color: '#00d4ff' }}>wsl --shutdown</span>
                    </div>
                  </div>
                )}

                {/* Recommendation banner */}
                <div style={{
                  marginTop: '10px',
                  padding: '12px 14px',
                  background: 'rgba(0,255,136,0.05)',
                  border: '1px solid rgba(0,255,136,0.2)',
                  borderRadius: '3px',
                }}>
                  <div style={{ ...lbl, color: '#00ff88', marginBottom: '8px' }}>RECOMMENDED FOR YOUR HARDWARE</div>
                  <div style={{ fontFamily: "'Share Tech Mono'", fontSize: '11px', color: '#dce8f8' }}>
                    LLM:&nbsp;<span style={{ color: '#00d4ff' }}>{hw.recommended.llm}</span>
                  </div>
                  <div style={{ fontFamily: "'Share Tech Mono'", fontSize: '11px', color: '#dce8f8', marginTop: '4px' }}>
                    Embedding:&nbsp;<span style={{ color: '#00d4ff' }}>{hw.recommended.embedding}</span>
                  </div>
                  <Btn onClick={useRecommended} color="#00ff88" style={{ marginTop: '10px', padding: '5px 12px', fontSize: '9px' }}>
                    USE RECOMMENDED
                  </Btn>
                </div>
              </div>
            ) : (
              <div>
                <span style={{ ...lbl, color: '#ff3c3c' }}>Backend unreachable — set URL on the right.</span>
                <Btn onClick={loadHardware} color="#a78bfa" style={{ marginTop: '10px' }}>RETRY</Btn>
              </div>
            )}
          </div>

          {/* Backend URL */}
          <div style={card}>
            <SectionTitle color="#ffb700">BACKEND CONNECTION</SectionTitle>
            <p style={{
              fontFamily: "'Exo 2'", fontSize: '12px', color: '#8cb4d4',
              marginTop: 0, marginBottom: '16px',
            }}>
              URL of the DEPFIX backend API.{' '}
              <span style={{ color: '#607898' }}>Stored in your browser — not sent to the server.</span>
            </p>
            <label style={lbl}>BACKEND URL</label>
            <input
              value={backendUrl}
              onChange={e => setBackendUrl(e.target.value)}
              placeholder="http://localhost:8000"
              style={inp}
              onKeyDown={e => e.key === 'Enter' && applyBackendUrl()}
            />
            <Btn onClick={applyBackendUrl} color="#ffb700" style={{ marginTop: '12px' }}>
              APPLY &amp; RELOAD
            </Btn>
          </div>
        </div>

        {/* ── Ollama Connection ─────────────────────────────────────────── */}
        <div style={{ ...card, marginBottom: '20px' }}>
          <SectionTitle color="#00d4ff">OLLAMA CONNECTION</SectionTitle>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '12px', alignItems: 'end', marginBottom: '20px' }}>
            <div>
              <label style={lbl}>OLLAMA URL</label>
              <input
                value={ollamaUrl}
                onChange={e => { setOllamaUrl(e.target.value); setOllamaStatus('untested'); }}
                placeholder="http://localhost:11434"
                style={inp}
              />
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <Btn onClick={testOllama} disabled={testingOllama}>
                {testingOllama ? 'TESTING…' : 'TEST'}
              </Btn>
              <StatusDot status={ollamaStatus} />
              <Btn onClick={fetchOllamaModels} disabled={modelsLoading} color="#a78bfa">
                {modelsLoading ? 'LOADING…' : 'REFRESH MODELS'}
              </Btn>
            </div>
          </div>

          {ollamaStatus === 'err' && (
            <p style={{ fontFamily: "'Share Tech Mono'", fontSize: '10px', color: '#ff3c3c', margin: '0 0 12px' }}>
              ✗ Cannot connect — verify Ollama is running and the URL is correct.
            </p>
          )}
          {ollamaStatus === 'ok' && (
            <p style={{ fontFamily: "'Share Tech Mono'", fontSize: '10px', color: '#00ff88', margin: '0 0 12px' }}>
              ✓ Connected
            </p>
          )}

          {ollamaModels.length > 0 && (
            <div>
              <label style={lbl}>AVAILABLE MODELS ({ollamaModels.length})</label>
              <div style={{
                display: 'flex', flexWrap: 'wrap', gap: '8px',
                maxHeight: '100px', overflowY: 'auto', padding: '4px 0',
              }}>
                {ollamaModels.map(m => (
                  <span key={m.name} style={{
                    fontFamily: "'Share Tech Mono'", fontSize: '10px',
                    padding: '3px 10px',
                    border: '1px solid rgba(0,212,255,0.2)',
                    borderRadius: '2px', color: '#8cb4d4',
                  }}>
                    {m.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {ollamaModels.length === 0 && ollamaStatus !== 'err' && (
            <span style={{ ...lbl, color: '#607898' }}>
              No models found — test connection or pull a model below.
            </span>
          )}
        </div>

        {/* ── Model Selection ────────────────────────────────────────────── */}
        <div style={{ ...card, marginBottom: '20px' }}>
          <SectionTitle color="#00d4ff">MODEL SELECTION</SectionTitle>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <div>
              <label style={lbl}>LLM MODEL</label>
              {ollamaModels.length > 0 ? (
                <select
                  value={llmModel}
                  onChange={e => setLlmModel(e.target.value)}
                  style={{ ...inp, cursor: 'pointer' }}
                >
                  <option value="">— select a model —</option>
                  {ollamaModels.map(m => (
                    <option key={m.name} value={m.name}>
                      {m.name}{hw && m.name === hw.recommended.llm ? '  ★ recommended' : ''}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  value={llmModel}
                  onChange={e => setLlmModel(e.target.value)}
                  placeholder="e.g. llama3:8b-q4_K_M"
                  style={inp}
                />
              )}
            </div>
            <div>
              <label style={lbl}>EMBEDDING MODEL</label>
              {ollamaModels.length > 0 ? (
                <select
                  value={embeddingModel}
                  onChange={e => setEmbeddingModel(e.target.value)}
                  style={{ ...inp, cursor: 'pointer' }}
                >
                  <option value="">— select a model —</option>
                  {ollamaModels.map(m => (
                    <option key={m.name} value={m.name}>
                      {m.name}{hw && m.name === hw.recommended.embedding ? '  ★ recommended' : ''}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  value={embeddingModel}
                  onChange={e => setEmbeddingModel(e.target.value)}
                  placeholder="e.g. nomic-embed-text"
                  style={inp}
                />
              )}
            </div>
          </div>
          {hw && (
            <Btn onClick={useRecommended} color="#00ff88" style={{ marginTop: '16px' }}>
              ↓ APPLY RECOMMENDED MODELS
            </Btn>
          )}
        </div>

        {/* ── Pull New Model ─────────────────────────────────────────────── */}
        <div style={{ ...card, marginBottom: '20px' }}>
          <SectionTitle color="#ffb700">PULL NEW MODEL</SectionTitle>
          <p style={{ fontFamily: "'Exo 2'", fontSize: '12px', color: '#8cb4d4', marginTop: 0, marginBottom: '16px' }}>
            Enter a full Ollama model tag. Quantization is part of the tag name (e.g.&nbsp;
            <code style={{ fontFamily: "'Share Tech Mono'", color: '#00d4ff', fontSize: '11px' }}>
              llama3:8b-instruct-q4_K_M
            </code>).
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '12px', alignItems: 'end', marginBottom: '12px' }}>
            <div>
              <label style={lbl}>MODEL TAG</label>
              <input
                value={pullModel}
                onChange={e => { setPullModel(e.target.value); setModelSizeGb(null); }}
                onBlur={e => checkModelSize(e.target.value)}
                placeholder={hw ? hw.recommended.llm : 'llama3:8b-q4_K_M'}
                style={inp}
                onKeyDown={e => e.key === 'Enter' && !pulling && pullNewModel()}
              />
            </div>
            <Btn onClick={pullNewModel} disabled={!pullModel.trim() || pulling} color="#ffb700">
              {pulling ? 'PULLING…' : 'PULL →'}
            </Btn>
          </div>

          {/* Model size warning */}
          {sizeChecking && (
            <p style={{ fontFamily: "'Share Tech Mono'", fontSize: '10px', color: '#607898', marginBottom: '14px', letterSpacing: '1px' }}>
              ⏳ Checking download size…
            </p>
          )}
          {!sizeChecking && modelSizeGb !== null && (
            <div
              style={{
                background: modelSizeGb > 15 ? 'rgba(255,60,60,0.07)' : 'rgba(255,183,0,0.07)',
                border: `1px solid ${modelSizeGb > 15 ? 'rgba(255,60,60,0.3)' : 'rgba(255,183,0,0.3)'}`,
                borderRadius: '4px',
                padding: '8px 14px',
                marginBottom: '14px',
                fontFamily: "'Share Tech Mono', monospace",
                fontSize: '10px',
                letterSpacing: '1.5px',
                color: modelSizeGb > 15 ? '#ff3c3c' : '#ffb700',
              }}
            >
              ⚠ ESTIMATED DOWNLOAD: ~{modelSizeGb} GB
              {modelSizeGb > 15 && '  ·  Large model – ensure adequate disk space'}
            </div>
          )}

          {pullLines.length > 0 && (
            <div
              ref={pullLogRef}
              style={{
                background: 'rgba(0,0,0,0.5)',
                border: '1px solid rgba(255,183,0,0.15)',
                borderRadius: '3px',
                padding: '12px 14px',
                maxHeight: '200px',
                overflowY: 'auto',
                fontFamily: "'Share Tech Mono'",
                fontSize: '11px',
                color: '#8cb4d4',
                lineHeight: 1.7,
              }}
            >
              {pullLines.map((line, i) => (
                <div
                  key={i}
                  style={{ color: line.startsWith('Error') ? '#ff3c3c' : '#8cb4d4' }}
                >
                  {line}
                </div>
              ))}
              {pullDone && (
                <div style={{ color: '#00ff88', marginTop: '6px', fontWeight: 700 }}>
                  ✓ Pull complete — model is now available
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Row: LLM Settings + Postgres ──────────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>

          {/* LLM Settings */}
          <div style={card}>
            <SectionTitle color="#a78bfa">LLM SETTINGS</SectionTitle>

            <label style={lbl}>TEMPERATURE — {parseFloat(temperature).toFixed(2)}</label>
            <input
              type="range"
              min="0" max="1" step="0.05"
              value={temperature}
              onChange={e => setTemperature(e.target.value)}
              style={{ width: '100%', accentColor: '#a78bfa', marginBottom: '16px' }}
            />

            <label style={lbl}>MAX TOKENS</label>
            <input
              type="number"
              min={256} max={32768} step={256}
              value={maxTokens}
              onChange={e => setMaxTokens(Number(e.target.value))}
              style={{ ...inp, marginBottom: '16px' }}
            />

            <label style={lbl}>SYSTEM PROMPT (optional)</label>
            <textarea
              value={systemPrompt}
              onChange={e => setSystemPrompt(e.target.value)}
              placeholder="You are an expert software engineer specializing in debugging CI/CD errors..."
              rows={5}
              style={{ ...inp, resize: 'vertical', lineHeight: 1.6 }}
            />
          </div>

          {/* Postgres */}
          <div style={card}>
            <SectionTitle color="#00ff88">POSTGRESQL / PGVECTOR</SectionTitle>
            <p style={{ fontFamily: "'Exo 2'", fontSize: '12px', color: '#8cb4d4', marginTop: 0, marginBottom: '16px' }}>
              PostgreSQL with the pgvector extension is used for embedding storage and similarity search.
            </p>
            <label style={lbl}>CONNECTION URL</label>
            <textarea
              value={postgresUrl}
              onChange={e => { setPostgresUrl(e.target.value); setPostgresStatus('untested'); }}
              placeholder="postgresql+psycopg2://user:password@host:5432/dbname"
              rows={3}
              style={{ ...inp, resize: 'none', marginBottom: '12px' }}
            />
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '10px' }}>
              <Btn onClick={testPostgres} disabled={testingPostgres} color="#00ff88">
                {testingPostgres ? 'TESTING…' : 'TEST CONNECTION'}
              </Btn>
              <StatusDot status={postgresStatus} />
            </div>
            {postgresStatus === 'ok' && (
              <p style={{ fontFamily: "'Share Tech Mono'", fontSize: '10px', color: '#00ff88', margin: 0 }}>
                ✓ Connected successfully
              </p>
            )}
            {postgresStatus === 'err' && (
              <p style={{ fontFamily: "'Share Tech Mono'", fontSize: '10px', color: '#ff3c3c', margin: 0 }}>
                ✗ Connection failed — check URL, credentials, and that pgvector is running.
              </p>
            )}
          </div>
        </div>

        {/* ── Docker Health Check ──────────────────────────────────────── */}
        <div style={{ ...card, marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <SectionTitle color="#a78bfa">DOCKER CONTAINERS</SectionTitle>
            <Btn onClick={checkDocker} disabled={dockerChecking} color="#a78bfa">
              {dockerChecking ? 'CHECKING…' : '⟳ CHECK'}
            </Btn>
          </div>
          <p style={{ fontFamily: "'Exo 2'", fontSize: '12px', color: '#8cb4d4', marginTop: 0, marginBottom: '12px' }}>
            Verify that DEPFIX-related Docker containers (pgvector, ollama, etc.) are running.
          </p>
          {dockerContainers === null && !dockerChecking && (
            <p style={{ fontFamily: "'Share Tech Mono'", fontSize: '10px', color: '#607898', letterSpacing: '2px' }}>
              Click CHECK to inspect running containers.
            </p>
          )}
          {dockerContainers !== null && dockerContainers.length === 0 && !dockerChecking && (
            <p style={{ fontFamily: "'Share Tech Mono'", fontSize: '10px', color: '#ffb700', letterSpacing: '2px' }}>
              ⚠ No running containers found. Ensure Docker is running and services are started.
            </p>
          )}
          {dockerContainers !== null && dockerContainers.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {dockerContainers.map((c, i) => {
                const isUp = c.status.toLowerCase().startsWith('up');
                return (
                  <div
                    key={i}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '10px',
                      padding: '8px 12px',
                      background: isUp ? 'rgba(0,255,136,0.04)' : 'rgba(255,60,60,0.04)',
                      border: `1px solid ${isUp ? 'rgba(0,255,136,0.15)' : 'rgba(255,60,60,0.2)'}`,
                      borderRadius: '4px',
                    }}
                  >
                    <span style={{ color: isUp ? '#00ff88' : '#ff3c3c', fontSize: '11px' }}>{isUp ? '●' : '●'}</span>
                    <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '10px', color: '#dce8f8', flex: 1 }}>{c.name}</span>
                    <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', color: '#607898' }}>{c.image}</span>
                    <span style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', color: isUp ? '#00ff88' : '#ff3c3c', letterSpacing: '1px' }}>{c.status}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ── CI/CD Webhook Integration ──────────────────────────────── */}
        <div style={{ ...card, marginBottom: '20px' }}>
          <SectionTitle color="#00d4ff">CI / CD WEBHOOK INTEGRATION</SectionTitle>
          <p style={{ fontFamily: "'Exo 2'", fontSize: '12px', color: '#8cb4d4', marginTop: 0, marginBottom: '14px' }}>
            Point your CI/CD pipeline at this endpoint. DEPFIX stores every failure log and makes it
            available for RAG-powered analysis in the dashboard.
          </p>

          {/* Endpoint */}
          <label style={lbl}>ENDPOINT (POST)</label>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
            <code style={{
              flex: 1,
              fontFamily: "'Share Tech Mono', monospace",
              fontSize: '11px',
              color: '#00d4ff',
              background: 'rgba(0,0,0,0.35)',
              border: '1px solid rgba(0,212,255,0.2)',
              borderRadius: '3px',
              padding: '8px 12px',
              overflowX: 'auto' as const,
              whiteSpace: 'nowrap' as const,
              display: 'block',
            }}>
              {backendUrl || 'http://localhost:8000'}/api/v1/webhook/github-actions
            </code>
          </div>

          {/* Tab switcher */}
          <div style={{ display: 'flex', gap: '4px', marginBottom: '12px' }}>
            {(['github', 'gitlab'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setCiTab(tab)}
                style={{
                  fontFamily: "'Share Tech Mono', monospace",
                  fontSize: '10px',
                  letterSpacing: '2px',
                  padding: '6px 16px',
                  border: `1px solid ${ciTab === tab ? '#00d4ff' : 'rgba(0,212,255,0.2)'}`,
                  background: ciTab === tab ? 'rgba(0,212,255,0.12)' : 'transparent',
                  color: ciTab === tab ? '#00d4ff' : '#607898',
                  borderRadius: '2px',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                {tab === 'github' ? 'GITHUB ACTIONS' : 'GITLAB CI'}
              </button>
            ))}
          </div>

          {/* Snippet + copy button */}
          <div style={{ position: 'relative' }}>
            <pre style={{
              margin: 0,
              padding: '14px 50px 14px 16px',
              background: 'rgba(0,0,0,0.45)',
              border: '1px solid rgba(0,212,255,0.15)',
              borderRadius: '3px',
              fontFamily: "'Share Tech Mono', monospace",
              fontSize: '10px',
              color: '#8cb4d4',
              lineHeight: 1.75,
              overflowX: 'auto',
              whiteSpace: 'pre',
            }}>
              {ciTab === 'github' ? GH_ACTIONS_SNIPPET : GITLAB_SNIPPET}
            </pre>
            <button
              onClick={() => navigator.clipboard.writeText(ciTab === 'github' ? GH_ACTIONS_SNIPPET : GITLAB_SNIPPET)}
              style={{
                position: 'absolute',
                top: '8px',
                right: '8px',
                fontFamily: "'Share Tech Mono', monospace",
                fontSize: '9px',
                letterSpacing: '1px',
                padding: '4px 10px',
                border: '1px solid rgba(0,212,255,0.25)',
                background: 'rgba(0,0,0,0.55)',
                color: '#607898',
                borderRadius: '2px',
                cursor: 'pointer',
              }}
            >
              COPY
            </button>
          </div>
        </div>

        {/* ── Save / Continue ────────────────────────────────────────────── */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '22px 24px',
          background: 'rgba(11,15,30,0.85)',
          border: '1px solid rgba(0,212,255,0.12)',
          borderRadius: '4px',
        }}>
          <div>
            {saveMsg && (
              <span style={{
                fontFamily: "'Share Tech Mono'",
                fontSize: '11px',
                color: saveMsg.includes('Failed') ? '#ff3c3c' : '#00ff88',
              }}>
                {saveMsg}
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: '12px' }}>
            <Btn onClick={saveConfig} disabled={saving}>
              {saving ? 'SAVING…' : 'SAVE CONFIG'}
            </Btn>
            <Btn onClick={saveAndContinue} disabled={saving} color="#00ff88">
              SAVE &amp; CONTINUE →
            </Btn>
          </div>
        </div>
      </main>
    </div>
  );
}

// ── Helper: key-value row ─────────────────────────────────────────────────────
function Row({
  label, value, valueColor = '#dce8f8',
}: {
  label: string; value: string; valueColor?: string;
}) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
      <span style={{
        fontFamily: "'Share Tech Mono', monospace",
        fontSize: '10px',
        letterSpacing: '2px',
        color: '#607898',
        flexShrink: 0,
      }}>
        {label}
      </span>
      <span style={{
        fontFamily: "'Share Tech Mono'",
        fontSize: '11px',
        color: valueColor,
        textAlign: 'right',
        wordBreak: 'break-all',
      }}>
        {value}
      </span>
    </div>
  );
}
