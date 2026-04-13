'use client';

import { useEffect, useRef } from 'react';

export type StepStatus = 'idle' | 'running' | 'done' | 'error';

export interface PipelineStepDef {
  id: string;
  label: string;
  description: string;
}

export interface PipelineStepState {
  status: StepStatus;
  duration_ms?: number;
  detail?: string;
}

interface PipelineGraphProps {
  steps: PipelineStepDef[];
  stepStates: Record<string, PipelineStepState>;
  overallStatus: 'running' | 'complete' | 'error';
}

const STATUS_COLORS: Record<StepStatus, string> = {
  idle:    'rgba(96,120,152,0.5)',
  running: '#00d4ff',
  done:    '#00ff88',
  error:   '#ff3c3c',
};

const STATUS_BG: Record<StepStatus, string> = {
  idle:    'rgba(11,15,30,0.8)',
  running: 'rgba(0,212,255,0.06)',
  done:    'rgba(0,255,136,0.06)',
  error:   'rgba(255,60,60,0.06)',
};

function NodeIcon({ status }: { status: StepStatus }) {
  if (status === 'running') {
    return (
      <div
        className="w-5 h-5 rounded-full border-2 border-transparent animate-spin flex-shrink-0"
        style={{ borderTopColor: '#00d4ff' }}
      />
    );
  }
  if (status === 'done') {
    return (
      <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 20 20" fill="none">
        <circle cx="10" cy="10" r="9" stroke="#00ff88" strokeWidth="1.5" />
        <path d="M6 10l3 3 5-5" stroke="#00ff88" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (status === 'error') {
    return (
      <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 20 20" fill="none">
        <circle cx="10" cy="10" r="9" stroke="#ff3c3c" strokeWidth="1.5" />
        <path d="M7 7l6 6M13 7l-6 6" stroke="#ff3c3c" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    );
  }
  // idle
  return (
    <div
      className="w-5 h-5 rounded-full flex-shrink-0"
      style={{ background: 'rgba(96,120,152,0.25)', border: '1px dashed rgba(96,120,152,0.5)' }}
    />
  );
}

function ConnectorArrow({ fromStatus }: { fromStatus: StepStatus }) {
  const active = fromStatus === 'done';
  const running = fromStatus === 'running';
  return (
    <div className="flex items-center justify-center" style={{ minWidth: 32 }}>
      <svg width="32" height="16" viewBox="0 0 32 16" fill="none">
        <line
          x1="0" y1="8" x2="26" y2="8"
          stroke={active ? '#00ff88' : running ? '#00d4ff' : 'rgba(96,120,152,0.3)'}
          strokeWidth="1.5"
          strokeDasharray={active ? 'none' : '4 3'}
        />
        <path
          d="M22 4l6 4-6 4"
          stroke={active ? '#00ff88' : running ? '#00d4ff' : 'rgba(96,120,152,0.3)'}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
      </svg>
    </div>
  );
}

export default function PipelineGraph({ steps, stepStates, overallStatus }: PipelineGraphProps) {
  return (
    <div>
      {/* Overall status bar */}
      <div className="flex items-center gap-3 mb-6">
        <div
          className="h-1 flex-1 rounded-full overflow-hidden"
          style={{ background: 'rgba(255,255,255,0.05)' }}
        >
          {(() => {
            const doneCount = steps.filter(s => stepStates[s.id]?.status === 'done').length;
            const pct = Math.round((doneCount / steps.length) * 100);
            const color = overallStatus === 'error' ? '#ff3c3c' : overallStatus === 'complete' ? '#00ff88' : '#00d4ff';
            return (
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{ width: `${pct}%`, background: color, boxShadow: `0 0 8px ${color}66` }}
              />
            );
          })()}
        </div>
        <span
          style={{
            fontFamily: "'Share Tech Mono', monospace",
            fontSize: '10px',
            letterSpacing: '3px',
            color: overallStatus === 'error' ? '#ff3c3c' : overallStatus === 'complete' ? '#00ff88' : '#00d4ff',
          }}
        >
          {overallStatus === 'complete' ? 'COMPLETE' : overallStatus === 'error' ? 'FAILED' : 'RUNNING'}
        </span>
      </div>

      {/* Pipeline nodes — horizontal on desktop, vertical on mobile */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-0 overflow-x-auto pb-2">
        {steps.map((step, i) => {
          const state = stepStates[step.id] ?? { status: 'idle' as StepStatus };
          const color = STATUS_COLORS[state.status];
          const bg = STATUS_BG[state.status];
          const isRunning = state.status === 'running';

          return (
            <div key={step.id} className="flex sm:flex-col flex-row sm:items-center items-start gap-2 sm:gap-0 flex-1 min-w-0">
              {/* Node card */}
              <div
                className="rounded-lg transition-all duration-500 flex-1 sm:w-full"
                style={{
                  background: bg,
                  border: `1px solid ${color}`,
                  padding: '10px 12px',
                  boxShadow: isRunning ? `0 0 12px ${color}33` : 'none',
                  minWidth: 0,
                }}
              >
                <div className="flex items-center gap-2 mb-1">
                  <NodeIcon status={state.status} />
                  <span
                    className="font-semibold truncate"
                    style={{
                      fontFamily: "'Share Tech Mono', monospace",
                      fontSize: '10px',
                      letterSpacing: '2px',
                      color,
                    }}
                  >
                    {step.label.toUpperCase()}
                  </span>
                </div>

                <p
                  className="text-xs truncate"
                  style={{ color: 'rgba(140,180,212,0.7)', fontSize: '11px', paddingLeft: '28px' }}
                >
                  {state.detail ?? step.description}
                </p>

                {state.duration_ms !== undefined && (
                  <p
                    className="text-xs mt-1"
                    style={{
                      color: 'rgba(96,120,152,0.8)',
                      fontFamily: "'Share Tech Mono', monospace",
                      fontSize: '9px',
                      paddingLeft: '28px',
                    }}
                  >
                    {state.duration_ms < 1000
                      ? `${state.duration_ms}ms`
                      : `${(state.duration_ms / 1000).toFixed(1)}s`}
                  </p>
                )}
              </div>

              {/* Connector (not after last node) */}
              {i < steps.length - 1 && (
                <div className="sm:hidden flex items-center" style={{ paddingLeft: '28px', paddingTop: '2px', paddingBottom: '2px' }}>
                  <svg width="16" height="24" viewBox="0 0 16 24" fill="none">
                    <line x1="8" y1="0" x2="8" y2="18"
                      stroke={state.status === 'done' ? '#00ff88' : state.status === 'running' ? '#00d4ff' : 'rgba(96,120,152,0.3)'}
                      strokeWidth="1.5" strokeDasharray={state.status === 'done' ? 'none' : '4 3'} />
                    <path d="M4 14l4 6 4-6"
                      stroke={state.status === 'done' ? '#00ff88' : state.status === 'running' ? '#00d4ff' : 'rgba(96,120,152,0.3)'}
                      strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                  </svg>
                </div>
              )}

              {/* Horizontal connector for desktop */}
              {i < steps.length - 1 && (
                <div className="hidden sm:block flex-shrink-0">
                  <ConnectorArrow fromStatus={state.status} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Running hint */}
      {overallStatus === 'running' && (
        <p
          className="text-xs mt-5 text-center"
          style={{ color: '#607898', fontFamily: "'Share Tech Mono', monospace", letterSpacing: '2px' }}
        >
          PIPELINE RUNNING · THIS MAY TAKE 15–60s
        </p>
      )}
    </div>
  );
}
