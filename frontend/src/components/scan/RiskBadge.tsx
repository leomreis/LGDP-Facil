import type { RiskType } from '../../types/api';
import { Badge, type BadgeTone } from '../ui/Badge';

const LABEL_BY_RISK: Record<RiskType, string> = {
  high: 'Alto',
  medium: 'Médio',
  low: 'Baixo',
};

const TONE_BY_RISK: Record<RiskType, BadgeTone> = {
  high: 'danger',
  medium: 'warning',
  low: 'success',
};

export function RiskBadge({ risk }: { risk: RiskType }) {
  return <Badge tone={TONE_BY_RISK[risk]}>{LABEL_BY_RISK[risk]}</Badge>;
}
