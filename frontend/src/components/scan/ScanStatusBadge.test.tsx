import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ScanStatusBadge } from './ScanStatusBadge';
import type { ScanStatus } from '../../types/api';

describe('ScanStatusBadge', () => {
  it.each<[ScanStatus, string]>([
    ['pending', 'Na fila'],
    ['in_progress', 'Em andamento'],
    ['completed', 'Concluído'],
    ['failed', 'Falhou'],
  ])('mostra o rótulo em português para o status %s', (status, esperado) => {
    render(<ScanStatusBadge status={status} />);

    expect(screen.getByText(esperado)).toBeInTheDocument();
  });
});
