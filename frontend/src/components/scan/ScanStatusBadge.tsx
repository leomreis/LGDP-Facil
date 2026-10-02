import type { ScanStatus } from '../../types/api';
import { Badge, type BadgeTone } from '../ui/Badge';

const LABEL_BY_STATUS: Record<ScanStatus, string> = {
  pending: 'Na fila',
  in_progress: 'Em andamento',
  completed: 'Concluído',
  failed: 'Falhou',
};

const TONE_BY_STATUS: Record<ScanStatus, BadgeTone> = {
  pending: 'neutral',
  in_progress: 'neutral',
  completed: 'success',
  failed: 'danger',
};

export function ScanStatusBadge({ status }: { status: ScanStatus }) {
  return <Badge tone={TONE_BY_STATUS[status]}>{LABEL_BY_STATUS[status]}</Badge>;
}
