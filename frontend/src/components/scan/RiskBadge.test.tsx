import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { RiskBadge } from './RiskBadge';
import type { RiskType } from '../../types/api';

describe('RiskBadge', () => {
  it.each<[RiskType, string]>([
    ['high', 'Alto'],
    ['medium', 'Médio'],
    ['low', 'Baixo'],
  ])('mostra o rótulo em português para o risco %s', (risk, esperado) => {
    render(<RiskBadge risk={risk} />);

    expect(screen.getByText(esperado)).toBeInTheDocument();
  });

  it('aplica o tom de risco alto (vermelho) para risco high', () => {
    render(<RiskBadge risk="high" />);

    expect(screen.getByText('Alto')).toHaveClass('bg-risk-high');
  });

  it('aplica o tom de risco baixo (verde) para risco low', () => {
    render(<RiskBadge risk="low" />);

    expect(screen.getByText('Baixo')).toHaveClass('bg-risk-low');
  });
});
