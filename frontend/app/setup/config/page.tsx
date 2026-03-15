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
  github_token: string | null;
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

function SectionTitle({ children, color = '#00d4ff', required = false }: { children: React.ReactNode; color?: string; required?: boolean }) {
  return (
    <div style={{
      fontFamily: "'Share Tech Mono', monospace",
      fontSize: '10px',
      letterSpacing: '3px',
      color,
      marginBottom: '16px',
      paddingBottom: '8px',
      borderBottom: `1px solid ${color}22`,
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
    }}>
      {children}
      {required && (
        <span style={{ color: '#ff3c3c', fontSize: '13px', lineHeight: 1, marginLeft: '2px' }} title="Required before continuing">*</span>
      )}
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
# Repo secrets required: DEPFIX_URL, DEPFIX_API_KEY

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
      -H "Content-Type: application/json" \\
      -H "X-API-Key: \${{ secrets.DEPFIX_API_KEY }}" \\
      -d @-
  # Tip: pipe your build command through: your-cmd 2>&1 | tee job.log`.trim();

const GITLAB_SNIPPET = `# .gitlab-ci.yml  —  add to any job's after_script
# CI/CD variables required: DEPFIX_URL, DEPFIX_API_KEY

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
        -H "Content-Type: application/json" \\
        -H "X-API-Key: \${DEPFIX_API_KEY}" \\
        -d @-
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

  // Derived: split models by type
  const llmModels = ollamaModels.filter(m => !m.name.toLowerCase().includes('embed'));
  const embedModels = ollamaModels.filter(m => m.name.toLowerCase().includes('embed'));

  // Model pull via SSE
  const [pullModel, setPullModel] = useState('');
  const [pullEmbedModel, setPullEmbedModel] = useState('');
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
  const [githubToken, setGithubToken] = useState('');
  const [showGhToken, setShowGhToken] = useState(false);
  const [savingGhToken, setSavingGhToken] = useState(false);
  const [ghTokenMsg, setGhTokenMsg] = useState('');

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
      setGithubToken(c.github_token || '');
      fetchOllamaModels();
    } catch {
      // no saved config yet
    }
  };

  const saveGithubToken = async () => {
    setSavingGhToken(true);
    setGhTokenMsg('');
    try {
      await axios.put(api('/api/v1/config/'), { github_token: githubToken || null });
      setGhTokenMsg(githubToken ? 'Token saved. GitHub API rate limit is now 5 000 req/hr.' : 'Token cleared.');
    } catch {
      setGhTokenMsg('Save failed.');
    }
    setSavingGhToken(false);
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

  const pullNewModel = async (tagOverride?: string) => {
    const tag = (tagOverride ?? pullModel).trim();
    if (!tag) return;
    setPulling(true);
    setPullLines([]);
    setPullDone(false);

    try {
      const response = await fetch(api('/api/v1/ollama/pull'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: tag }),
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
        github_token: githubToken || null,
      });
      setSaveMsg('Configuration saved.');
    } catch (err: unknown) {
      const msg =
        axios.isAxiosError(err)
          ? err.response
            ? `Save failed: HTTP ${err.response.status} — ${JSON.stringify(err.response.data)}`
            : `Save failed: cannot reach ${getApiBase()} — is the backend running?`
          : `Save failed: ${String(err)}`;
      setSaveMsg(msg);
    }
    setSaving(false);
  };

  const saveAndContinue = async () => {
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
        github_token: githubToken || null,
      });
      setSaving(false);
      router.push('/setup/dependencies');
    } catch (err: unknown) {
      const msg =
        axios.isAxiosError(err)
          ? err.response
            ? `Save failed: HTTP ${err.response.status} — ${JSON.stringify(err.response.data)}`
            : `Save failed: cannot reach ${getApiBase()} — is the backend running?`
          : `Save failed: ${String(err)}`;
      setSaveMsg(msg);
      setSaving(false);
    }
  };

  // ── Required-field gate ───────────────────────────────────────────────────
  const canContinue =
    ollamaStatus === 'ok' &&
    llmModel.trim() !== '' &&
    embeddingModel.trim() !== '' &&
    postgresStatus === 'ok';

  const requirements: { label: string; met: boolean }[] = [
    { label: 'Ollama connected', met: ollamaStatus === 'ok' },
    { label: 'LLM model selected', met: llmModel.trim() !== '' },
    { label: 'Embedding model selected', met: embeddingModel.trim() !== '' },
    { label: 'PostgreSQL connected', met: postgresStatus === 'ok' },
  ];

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
                      WSL2 limits RAM to 50% of host (max 8 GB) by default.<br />
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
          <SectionTitle color="#00d4ff" required>OLLAMA CONNECTION</SectionTitle>
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
                display: 'flex', flexDirection: 'column', gap: '6px',
                maxHeight: '160px', overflowY: 'auto', padding: '4px 0',
              }}>
                {ollamaModels.map(m => (
                  <div key={m.name} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '5px 10px',
                    border: '1px solid rgba(0,212,255,0.2)',
                    borderRadius: '2px',
                  }}>
                    <span style={{ fontFamily: "'Share Tech Mono'", fontSize: '10px', color: '#8cb4d4' }}>
                      {m.name}
                    </span>
                    <button
                      onClick={async () => {
                        if (!confirm(`Delete model "${m.name}"?`)) return;
                        try {
                          await axios.delete(api(`/api/v1/ollama/model/${encodeURIComponent(m.name)}`));
                          fetchOllamaModels();
                        } catch {
                          alert(`Failed to delete ${m.name}`);
                        }
                      }}
                      title="Delete model"
                      style={{
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: '#607898', fontSize: '12px', padding: '0 4px',
                        lineHeight: 1,
                      }}
                      onMouseEnter={e => (e.currentTarget.style.color = '#ff3c3c')}
                      onMouseLeave={e => (e.currentTarget.style.color = '#607898')}
                    >✕</button>
                  </div>
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
          <SectionTitle color="#00d4ff" required>MODEL SELECTION</SectionTitle>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <div>
              <label style={lbl}>LLM MODEL</label>
              {llmModels.length > 0 ? (
                <select
                  value={llmModel}
                  onChange={e => setLlmModel(e.target.value)}
                  style={{ ...inp, cursor: 'pointer' }}
                >
                  <option value="">— select a model —</option>
                  {llmModels.map(m => (
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
              {embedModels.length > 0 ? (
                <select
                  value={embeddingModel}
                  onChange={e => setEmbeddingModel(e.target.value)}
                  style={{ ...inp, cursor: 'pointer' }}
                >
                  <option value="">— select a model —</option>
                  {embedModels.map(m => (
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

          {/* LLM sub-section */}
          <p style={{ fontFamily: "'Share Tech Mono'", fontSize: '10px', letterSpacing: '3px', color: '#ffb700', marginBottom: '8px', marginTop: 0 }}>LLM MODEL</p>
          <p style={{ fontFamily: "'Exo 2'", fontSize: '12px', color: '#8cb4d4', marginTop: 0, marginBottom: '10px' }}>
            Enter a full Ollama model tag. Quantization is part of the tag name (e.g.&nbsp;
            <code style={{ fontFamily: "'Share Tech Mono'", color: '#00d4ff', fontSize: '11px' }}>llama3:8b-instruct-q4_K_M</code>).
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '12px', alignItems: 'end', marginBottom: '16px' }}>
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

          {/* Divider */}
          <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', margin: '4px 0 16px' }} />

          {/* Embedding sub-section */}
          <p style={{ fontFamily: "'Share Tech Mono'", fontSize: '10px', letterSpacing: '3px', color: '#a78bfa', marginBottom: '8px', marginTop: 0 }}>EMBEDDING MODEL</p>
          <p style={{ fontFamily: "'Exo 2'", fontSize: '12px', color: '#8cb4d4', marginTop: 0, marginBottom: '10px' }}>
            Pull a dedicated embedding model. Recommended:&nbsp;
            <code style={{ fontFamily: "'Share Tech Mono'", color: '#00d4ff', fontSize: '11px' }}>nomic-embed-text</code>
            &nbsp;or&nbsp;
            <code style={{ fontFamily: "'Share Tech Mono'", color: '#00d4ff', fontSize: '11px' }}>mxbai-embed-large</code>.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '12px', alignItems: 'end', marginBottom: '12px' }}>
            <div>
              <label style={lbl}>EMBEDDING TAG</label>
              <input
                value={pullEmbedModel}
                onChange={e => { setPullEmbedModel(e.target.value); setModelSizeGb(null); }}
                onBlur={e => checkModelSize(e.target.value)}
                placeholder={hw ? hw.recommended.embedding : 'nomic-embed-text'}
                style={inp}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !pulling && pullEmbedModel.trim()) {
                    pullNewModel(pullEmbedModel);
                  }
                }}
              />
            </div>
            <Btn
              onClick={() => pullNewModel(pullEmbedModel)}
              disabled={!pullEmbedModel.trim() || pulling}
              color="#a78bfa"
            >
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
            <SectionTitle color="#00ff88" required>POSTGRESQL / PGVECTOR</SectionTitle>
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

        {/* ── GitHub Personal Access Token ──────────────────────────── */}
        <div style={{ ...card, marginBottom: '20px' }}>
          <SectionTitle color="#a78bfa">GITHUB PERSONAL ACCESS TOKEN</SectionTitle>
          <p style={{ fontFamily: "'Exo 2'", fontSize: '12px', color: '#8cb4d4', marginTop: 0, marginBottom: '18px' }}>
            Used when fetching dependency documentation from GitHub. Without a token, the unauthenticated
            rate limit is only 60 requests/hour — enough for a few libraries. With a token it becomes
            5 000 requests/hour, which covers any number of dependencies without throttling.
          </p>
          <p style={{ fontFamily: "'Exo 2'", fontSize: '11px', color: '#607898', marginTop: 0, marginBottom: '16px' }}>
            Create one at <span style={{ color: '#00d4ff', fontFamily: "'Share Tech Mono'", fontSize: '11px' }}>github.com → Settings → Developer settings → Personal access tokens → Tokens (classic)</span>.
            The token only needs <span style={{ fontFamily: "'Share Tech Mono'", fontSize: '11px', color: '#00ff88' }}>public_repo</span> (read-only, for public repositories) or no scopes at all for public access.
          </p>
          <label style={lbl}>GITHUB TOKEN (ghp_...)</label>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input
              type={showGhToken ? 'text' : 'password'}
              value={githubToken}
              onChange={e => setGithubToken(e.target.value)}
              placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
              style={{
                ...inp,
                flex: 1,
                fontFamily: "'Share Tech Mono', monospace",
                fontSize: '12px',
                letterSpacing: githubToken && !showGhToken ? '2px' : 'normal',
              }}
            />
            <button
              onClick={() => setShowGhToken(v => !v)}
              style={{
                background: 'transparent',
                border: '1px solid rgba(167,139,250,0.3)',
                borderRadius: '4px',
                color: '#a78bfa',
                fontSize: '10px',
                fontFamily: "'Share Tech Mono', monospace",
                padding: '8px 12px',
                cursor: 'pointer',
                letterSpacing: '1px',
              }}
            >
              {showGhToken ? 'HIDE' : 'SHOW'}
            </button>
            <button
              onClick={saveGithubToken}
              disabled={savingGhToken}
              style={{
                background: savingGhToken ? 'transparent' : 'rgba(167,139,250,0.12)',
                border: '1px solid rgba(167,139,250,0.4)',
                borderRadius: '4px',
                color: savingGhToken ? '#607898' : '#a78bfa',
                fontSize: '10px',
                fontFamily: "'Share Tech Mono', monospace",
                padding: '8px 16px',
                cursor: savingGhToken ? 'not-allowed' : 'pointer',
                letterSpacing: '1px',
              }}
            >
              {savingGhToken ? 'SAVING...' : 'SAVE TOKEN'}
            </button>
          </div>
          {ghTokenMsg && (
            <p style={{
              fontFamily: "'Share Tech Mono', monospace",
              fontSize: '10px',
              color: ghTokenMsg.includes('failed') ? '#ff3c3c' : '#00ff88',
              marginTop: '8px',
              marginBottom: 0,
            }}>
              {ghTokenMsg}
            </p>
          )}
          {githubToken && (
            <p style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', color: '#607898', marginTop: '8px', marginBottom: 0 }}>
              ● Token stored — GitHub API will use authenticated mode (5 000 req/hr)
            </p>
          )}
        </div>

        {/* ── CI/CD Webhook Integration ──────────────────────────────── */}
        <div style={{ ...card, marginBottom: '20px' }}>
          <SectionTitle color="#00d4ff">CI / CD WEBHOOK INTEGRATION</SectionTitle>
          <p style={{ fontFamily: "'Exo 2'", fontSize: '12px', color: '#8cb4d4', marginTop: 0, marginBottom: '18px' }}>
            Automatically send failure logs to DEPFIX the moment a CI job fails — no manual uploads needed.
          </p>

          {/* Step-by-step guide */}
          <div style={{ marginBottom: '20px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {[
              {
                n: '1',
                title: 'Generate an API key',
                body: <>Go to <span style={{ color: '#00d4ff', fontFamily: "'Share Tech Mono'", fontSize: '11px' }}>Dashboard → API Keys</span> and create a new key. Copy it — you'll only see it once.</>,
              },
              {
                n: '2',
                title: 'Add secrets to your repo',
                body: <>In your GitHub repo go to <span style={{ color: '#00d4ff', fontFamily: "'Share Tech Mono'", fontSize: '11px' }}>Settings → Secrets → Actions</span> and add:<br />
                  <span style={{ fontFamily: "'Share Tech Mono'", fontSize: '11px', color: '#00ff88' }}>DEPFIX_URL</span> → <span style={{ fontFamily: "'Share Tech Mono'", fontSize: '11px', color: '#8cb4d4' }}>{backendUrl || 'http://your-depfix-host:8000'}</span><br />
                  <span style={{ fontFamily: "'Share Tech Mono'", fontSize: '11px', color: '#00ff88' }}>DEPFIX_API_KEY</span> → <span style={{ fontFamily: "'Share Tech Mono'", fontSize: '11px', color: '#8cb4d4' }}>depfix_…your key…</span>
                </>,
              },
              {
                n: '3',
                title: 'Add the step to your workflow',
                body: <>Copy the snippet below and paste it as the <strong style={{ color: '#dce8f8' }}>last step</strong> of any job in your <span style={{ fontFamily: "'Share Tech Mono'", fontSize: '11px', color: '#00d4ff' }}>.github/workflows/your-workflow.yml</span>. The <code style={{ fontFamily: "'Share Tech Mono'", fontSize: '11px', color: '#ffb700' }}>if: failure()</code> condition ensures it only fires on failure.</>,
              },
              {
                n: '4',
                title: 'Done — logs arrive automatically',
                body: <>When a job fails, DEPFIX receives the log, runs RAG analysis in the background, and the fix suggestion appears in your <span style={{ color: '#00d4ff', fontFamily: "'Share Tech Mono'", fontSize: '11px' }}>Dashboard → Logs</span>.</>,
              },
            ].map(({ n, title, body }) => (
              <div key={n} style={{
                display: 'flex', gap: '12px', alignItems: 'flex-start',
                padding: '10px 14px',
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid rgba(0,212,255,0.08)',
                borderRadius: '3px',
              }}>
                <div style={{
                  flexShrink: 0,
                  width: '22px', height: '22px',
                  borderRadius: '50%',
                  border: '1px solid rgba(0,212,255,0.4)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontFamily: "'Share Tech Mono'", fontSize: '10px', color: '#00d4ff',
                }}>{n}</div>
                <div>
                  <p style={{ fontFamily: "'Share Tech Mono'", fontSize: '10px', letterSpacing: '2px', color: '#dce8f8', margin: '0 0 4px' }}>{title.toUpperCase()}</p>
                  <p style={{ fontFamily: "'Exo 2'", fontSize: '12px', color: '#8cb4d4', margin: 0, lineHeight: 1.6 }}>{body}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Endpoint */}
          <label style={lbl}>WEBHOOK ENDPOINT (POST)</label>
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
          padding: '22px 24px',
          background: 'rgba(11,15,30,0.85)',
          border: '1px solid rgba(0,212,255,0.12)',
          borderRadius: '4px',
        }}>
          {/* Required-section checklist */}
          {!canContinue && (
            <div style={{
              marginBottom: '16px',
              padding: '12px 16px',
              background: 'rgba(255,60,60,0.05)',
              border: '1px solid rgba(255,60,60,0.2)',
              borderRadius: '3px',
            }}>
              <div style={{
                fontFamily: "'Share Tech Mono'",
                fontSize: '9px',
                letterSpacing: '2px',
                color: '#ff3c3c',
                marginBottom: '8px',
              }}>
                COMPLETE REQUIRED SECTIONS * BEFORE CONTINUING
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                {requirements.map(r => (
                  <div key={r.label} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontFamily: "'Share Tech Mono'",
                    fontSize: '10px',
                    color: r.met ? '#00ff88' : '#607898',
                  }}>
                    <span style={{ fontSize: '12px' }}>{r.met ? '✓' : '○'}</span>
                    {r.label}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              {saveMsg && (
                <span style={{
                  fontFamily: "'Share Tech Mono'",
                  fontSize: '11px',
                  color: saveMsg.includes('failed') || saveMsg.includes('Failed') ? '#ff3c3c' : '#00ff88',
                  maxWidth: '500px',
                  display: 'inline-block',
                  wordBreak: 'break-word',
                }}>
                  {saveMsg}
                </span>
              )}
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <Btn onClick={saveConfig} disabled={saving}>
                {saving ? 'SAVING…' : 'SAVE CONFIG'}
              </Btn>
              <Btn
                onClick={saveAndContinue}
                disabled={saving || !canContinue}
                color={canContinue ? '#00ff88' : '#607898'}
              >
                SAVE &amp; CONTINUE →
              </Btn>
            </div>
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
