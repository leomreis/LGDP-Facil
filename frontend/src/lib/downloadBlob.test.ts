import { afterEach, describe, expect, it, vi } from 'vitest';
import { downloadBlob } from './downloadBlob';

describe('downloadBlob', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('cria um link com o nome de arquivo certo e dispara o clique', () => {
    const createObjectURL = vi.fn().mockReturnValue('blob:fake-url');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL });

    const clickSpy = vi.fn();
    const linkFalso = document.createElement('a');
    vi.spyOn(linkFalso, 'click').mockImplementation(clickSpy);
    vi.spyOn(document, 'createElement').mockReturnValue(linkFalso);

    downloadBlob(new Blob(['conteúdo']), 'relatorio-123.pdf');

    expect(linkFalso.download).toBe('relatorio-123.pdf');
    expect(linkFalso.href).toContain('blob:fake-url');
    expect(clickSpy).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:fake-url');
  });
});
