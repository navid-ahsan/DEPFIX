'use client';

import Link from 'next/link';

const STEPS = [
  { label: 'CONFIG',        href: '/setup/config' },
  { label: 'DEPENDENCIES',  href: '/setup/dependencies' },
  { label: 'PROGRESS',      href: '/setup/progress' },
  { label: 'EMBEDDING',     href: '/setup/embedding' },
  { label: 'GITHUB',        href: '/setup/github-connection' },
  { label: 'RAG ANALYSIS',  href: '/setup/rag-analysis' },
];

interface SetupStepperProps {
  currentStep: number;
}

function StepDot({ color, isCurrent, isDone }: { color: string; isCurrent: boolean; isDone: boolean }) {
  if (isDone) {
    return (
      <div style={{ width: '18px', height: '18px', borderRadius: '50%', background: 'rgba(0,255,136,0.12)', border: '1.5px solid #00ff88', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        <span style={{ color: '#00ff88', fontSize: '10px', lineHeight: 1 }}>✓</span>
      </div>
    );
  }
  if (isCurrent) {
    return (
      <div className="step-dot-pulse" style={{ width: '18px', height: '18px', borderRadius: '50%', background: 'rgba(0,212,255,0.15)', border: '1.5px solid #00d4ff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, animation: 'stepPulse 2s ease-in-out infinite' }}>
        <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#00d4ff' }} />
      </div>
    );
  }
  return (
    <div style={{ width: '18px', height: '18px', borderRadius: '50%', background: 'rgba(96,120,152,0.08)', border: '1.5px solid rgba(96,120,152,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
      <div style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#607898', opacity: 0.5 }} />
    </div>
  );
}

export default function SetupStepper({ currentStep }: SetupStepperProps) {
  return (
    <div className="w-full" style={{ background: 'rgba(11,15,30,0.7)', borderBottom: '1px solid rgba(0,212,255,0.08)', backdropFilter: 'blur(4px)' }}>
      <div className="max-w-7xl mx-auto px-4 py-3">
        <div className="flex items-center justify-between gap-1 overflow-x-auto">
          {STEPS.map((step, idx) => {
            const isDone    = idx < currentStep;
            const isCurrent = idx === currentStep;
            const color     = isCurrent ? '#00d4ff' : isDone ? '#00ff88' : '#607898';
            return (
              <div key={step.href} className="flex items-center gap-1 flex-shrink-0">
                {isDone ? (
                  <Link href={step.href} className="flex items-center gap-1.5 group" style={{ textDecoration: 'none' }}>
                    <StepDot color={color} isCurrent={false} isDone />
                    <span className="hidden sm:inline" style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', letterSpacing: '2px', color }}>
                      {step.label}
                    </span>
                  </Link>
                ) : (
                  <div className="flex items-center gap-1.5">
                    <StepDot color={color} isCurrent={isCurrent} isDone={false} />
                    <span className="hidden sm:inline" style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: '9px', letterSpacing: '2px', color }}>
                      {step.label}
                    </span>
                  </div>
                )}
                {idx < STEPS.length - 1 && (
                  <div className="hidden sm:block" style={{ width: '24px', height: '1px', background: isDone ? 'rgba(0,255,136,0.4)' : 'rgba(96,120,152,0.25)', marginLeft: '4px' }} />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
