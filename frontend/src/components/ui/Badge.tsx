export type BadgeTone = 'neutral' | 'success' | 'danger' | 'warning';

const TONE_CLASSES: Record<BadgeTone, string> = {
  neutral: 'bg-border text-text-muted',
  success: 'bg-risk-low text-[#06210f]',
  danger: 'bg-risk-high text-[#2b0505]',
  warning: 'bg-risk-medium text-[#2b1c00]',
};

export function Badge({ tone, children }: { tone: BadgeTone; children: React.ReactNode }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${TONE_CLASSES[tone]}`}>
      {children}
    </span>
  );
}
